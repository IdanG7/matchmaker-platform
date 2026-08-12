# Deploying the demo to a VPS

The whole stack runs from the same compose files used in development, with a
production overlay that keeps everything bound to localhost and puts Caddy in
front.

## What you need

- A VPS with Docker and the compose plugin
- A **domain pointed at the box**. Not optional if the demo is embedded in a
  site served over https: browsers block a page on https from opening `ws://`
  or loading `http://`, and Let's Encrypt will not issue a certificate for a
  bare IP address. Serving the demo over plain http on an IP works only if the
  page linking to it is also plain http, or links out rather than embedding.
- A checkout of both repositories on the box:
  - `matchmaker-platform` (this one)
  - [`multiplayer-demo`](https://github.com/IdanG7/multiplayer-demo), for the
    game server agent and the WASM client

## 1. Configure

```bash
cd matchmaker-platform
cp deployments/docker/.env.example deployments/docker/.env
```

Edit `deployments/docker/.env`:

```ini
POSTGRES_PASSWORD=<something random>
GRAFANA_ADMIN_PASSWORD=<something random>
JWT_SECRET_KEY=<python -c "import secrets; print(secrets.token_urlsafe(64))">

# Where the game repository is checked out, relative to deployments/docker/
GAME_REPO_PATH=../../../multiplayer-demo

# Your domain. PUBLIC_ORIGIN is the exact origin the browser client is served
# from; the API refuses to start with a wildcard outside development.
PUBLIC_HOST=demo.example.com
PUBLIC_ORIGIN=https://demo.example.com
```

## 2. Start the stack

```bash
docker compose \
  -f deployments/docker/docker-compose.yml \
  -f deployments/vps/docker-compose.prod.yml \
  --profile game up -d --build
```

Then apply the schema (first run only):

```bash
docker compose -f deployments/docker/docker-compose.yml exec -T postgres \
  psql -v ON_ERROR_STOP=1 -U multiplayer -d multiplayer -f /migrations/init.sql
```

## 3. Build the browser client

From the game repository, with Docker doing the Emscripten work:

```bash
docker run --rm -v "$PWD:/src" -w /src emscripten/emsdk:3.1.50 bash -c "
  emcmake cmake -S . -B build-wasm \
    -DENABLE_MATCHMAKER_SDK=ON \
    -DBUILD_TESTING=OFF &&
  cmake --build build-wasm -j\$(nproc)"
```

That writes `game_client.{html,js,wasm}` into `web/`. Serve that directory —
`deployments/vps/Caddyfile` expects it at `/srv/zone-control/web`.

## 4. Reverse proxy

Two configurations ship here. Pick by what the box already runs — nothing can
share ports 80 and 443, so a host already serving a site keeps its own web
server and gains a virtual host, rather than handing the ports to Caddy.

Whichever you use, the game-server route is the piece worth understanding: each
match gets its own port, and per-port certificates are not practical, so ports
are routed by path (`/gs/9100` → `127.0.0.1:9100`). The agent is configured with
a matching `PUBLIC_URL_TEMPLATE`, so a client is told to connect to
`wss://demo.example.com/gs/9100`. **If you change the port range, change it in
the compose overlay and in the proxy config together.**

### A box with nothing on 80/443: Caddy

Edit `deployments/vps/Caddyfile`, replacing `demo.example.com`, then:

```bash
sudo caddy run --config deployments/vps/Caddyfile
```

Caddy obtains and renews certificates on its own.

### A box already running nginx

```bash
sudo cp deployments/vps/nginx-websocket-map.conf /etc/nginx/conf.d/
sudo cp deployments/vps/nginx-demo.conf /etc/nginx/sites-available/zone-control
sudo sed -i 's/demo.example.com/YOUR.HOST/' /etc/nginx/sites-available/zone-control
sudo ln -s /etc/nginx/sites-available/zone-control /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d YOUR.HOST
```

Three things differ from Caddy and each one fails quietly if missed:

- **The map file is not optional.** `$connection_upgrade` can only be declared
  in the http context, so it cannot live in the server block that uses it.
  Without it nginx refuses to start.
- **nginx does not upgrade WebSockets by default.** Both proxying locations set
  `Upgrade`/`Connection` explicitly; drop them and the handshake returns 200
  while the client waits for a socket that never opens.
- **Run certbot after DNS resolves.** It rewrites the file in place to add the
  TLS listener, and its HTTP-01 challenge fails against a hostname that does
  not yet point at the box.

Existing sites are untouched: this is a new `server_name`, and nginx routes by
that, so anything already configured keeps serving exactly as before.

## 5. Keep bots in the queue

A visitor queueing alone waits forever. Run bots that queue as players:

```bash
docker compose -f deployments/docker/docker-compose.yml exec game-agent \
  /usr/local/bin/zone_bot \
    --matchmaker http://api:8080 \
    --name filler --mode duo --team-size 1 \
    --queue-timeout 600
```

A bot leaves the queue when it times out, so run this under something that
restarts it, or use a small loop. Two bots queued means a visitor is matched
almost immediately.

## Checking it works

```bash
curl https://demo.example.com/health
curl https://demo.example.com/v1/leaderboard
docker compose -f deployments/docker/docker-compose.yml logs -f matchmaker
```

The matchmaker logs a line per match formed, and the agent logs the port it
allocated.

## Notes

- **Accounts are created freely.** The demo registers a throwaway account per
  visitor, and there is no rate limit on registration beyond the API's general
  one. Fine for a portfolio piece, not for anything larger.
- **Game servers are not authenticated.** The API mints an HMAC session token
  and the client receives it, but the game's wire protocol has no auth message,
  so anyone who knows a port can join a match in progress. Closing that means
  adding a protocol message and validating it server-side.
- **Ports 9100-9110 cap you at eleven concurrent matches.** The agent returns
  503 beyond that; widen the range in the compose overlay and in whichever
  proxy config you are using, together.
- **Only the API and the game-server range are published to the host.**
  Postgres, Redis, NATS and the observability stack are reachable over the
  compose network and nowhere else, so they cannot collide with anything else
  on the box. To reach one, go through the container
  (`docker compose exec postgres psql -U multiplayer`) rather than publishing
  a port.

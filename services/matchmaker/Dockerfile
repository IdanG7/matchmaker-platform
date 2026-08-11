# Build stage - compiles the matchmaker and its vendored dependencies.
FROM debian:bookworm-slim AS build

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        git \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src

# CMakeLists alone is enough to resolve dependencies, so this layer is reused
# whenever only the sources change.
COPY CMakeLists.txt ./
COPY include ./include
COPY src ./src
COPY tests ./tests

# Tests need network access for GoogleTest; the image only ships the binary,
# so they are built and run in CI rather than here.
RUN cmake -S . -B build \
        -DCMAKE_BUILD_TYPE=Release \
        -DBUILD_TESTS=OFF \
    && cmake --build build --parallel "$(nproc)"

# Runtime stage - just the binary and libstdc++.
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --system --create-home --uid 10001 matchmaker

COPY --from=build /src/build/matchmaker /usr/local/bin/matchmaker

USER matchmaker

# Overridden by compose; sensible default for a bare `docker run`.
ENV NATS_URL=nats://nats:4222

ENTRYPOINT ["/usr/local/bin/matchmaker"]

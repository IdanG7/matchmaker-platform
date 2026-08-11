"""
Contract test: every endpoint the C++ SDK calls must exist in the FastAPI app.

The SDK shipped for several releases calling four party endpoints that did not
exist (POST /v1/party/queue instead of /v1/party/{id}/queue, DELETE instead of
POST for leave, and so on). Nothing caught it: the SDK unit tests only assert
that calls fail when no server is running, which is equally true of a correct
path and a typo.

This test reads the request paths straight out of the SDK source and checks
them against the real route table, so the two cannot drift apart silently.
It needs no database and no running stack - only the app object.
"""

import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SDK_SRC = REPO_ROOT / "sdk" / "cpp" / "src"
API_DIR = REPO_ROOT / "services" / "api"

# Any path parameter name works; only the shape of the path matters here.
PARAM = "{}"

# A C++ path argument: string literals and identifiers joined by '+'. Anchoring
# on this rather than a lazy .+? keeps the match from running past the path and
# into the request body argument.
_TERM = r'(?:"[^"]*"|[A-Za-z_]\w*)'
PATH_EXPR = rf"{_TERM}(?:\s*\+\s*{_TERM})*"


def _normalise(path: str) -> str:
    """Reduce a path to its shape: /v1/party/{party_id}/join -> /v1/party/{}/join."""
    return re.sub(r"\{[^}]*\}", PARAM, path)


def _cpp_expr_to_path(expr: str) -> str | None:
    """
    Turn a C++ path expression into a path template.

        "/v1/party/" + party_id + "/join"   ->  /v1/party/{}/join
        "/v1/profile/me"                    ->  /v1/profile/me

    Returns None if the expression is not a plain concatenation of literals
    and identifiers, so an unparsable call is reported rather than skipped.
    """
    parts = []
    for piece in expr.split("+"):
        piece = piece.strip()
        if not piece:
            return None
        if piece.startswith('"') and piece.endswith('"') and len(piece) >= 2:
            parts.append(piece[1:-1])
        elif re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.:>()\[\]-]*", piece):
            parts.append(PARAM)
        else:
            return None
    return "".join(parts)


def _sdk_calls() -> list[tuple[str, str, str]]:
    """Extract (method, path, source_location) for every HTTP call in the SDK."""
    calls: list[tuple[str, str, str]] = []

    client_cpp = (SDK_SRC / "client.cpp").read_text(encoding="utf-8")
    # impl_->request("POST", "/v1/party/" + party_id + "/join", ...)
    for match in re.finditer(
        rf'request\(\s*"(GET|POST|PATCH|DELETE)"\s*,\s*({PATH_EXPR})\s*,', client_cpp
    ):
        method, expr = match.group(1), match.group(2)
        path = _cpp_expr_to_path(expr)
        assert path is not None, f"could not parse SDK path expression: {expr!r}"
        calls.append((method, path, "client.cpp"))

    auth_cpp = (SDK_SRC / "auth.cpp").read_text(encoding="utf-8")
    # client.Post("/v1/auth/login", ...)
    for match in re.finditer(r'\.(Get|Post|Patch|Delete)\(\s*"([^"]+)"', auth_cpp):
        calls.append((match.group(1).upper(), match.group(2), "auth.cpp"))

    return calls


def _sdk_websocket_paths() -> list[str]:
    """Extract WebSocket paths the SDK connects to."""
    client_cpp = (SDK_SRC / "client.cpp").read_text(encoding="utf-8")
    paths = []
    # ws_url += "/v1/ws/party/" + party_id;
    for match in re.finditer(rf"ws_url\s*\+=\s*({PATH_EXPR})\s*;", client_cpp):
        path = _cpp_expr_to_path(match.group(1))
        if path:
            paths.append(path)
    return paths


@pytest.fixture(scope="module")
def app_routes():
    """(methods, path) for every route registered on the FastAPI app."""
    sys.path.insert(0, str(API_DIR))
    try:
        from main import app
    finally:
        sys.path.pop(0)

    http_routes = set()
    ws_routes = set()
    for route in app.routes:
        path = _normalise(route.path)
        if hasattr(route, "methods") and route.methods:
            for method in route.methods:
                http_routes.add((method, path))
        else:
            ws_routes.add(path)
    return http_routes, ws_routes


def test_sdk_source_was_found():
    """Guard against the extractors silently matching nothing."""
    assert (SDK_SRC / "client.cpp").exists()
    assert (SDK_SRC / "auth.cpp").exists()
    assert len(_sdk_calls()) >= 10, "expected the SDK to make at least 10 HTTP calls"


@pytest.mark.parametrize("method,path,source", _sdk_calls())
def test_sdk_http_call_exists_in_api(method, path, source, app_routes):
    http_routes, _ = app_routes
    shape = _normalise(path)

    if (method, shape) in http_routes:
        return

    # Give a useful failure: was it the method or the path that was wrong?
    same_path = sorted(m for m, p in http_routes if p == shape)
    if same_path:
        pytest.fail(
            f"{source}: SDK calls {method} {path}, but the API serves only "
            f"{', '.join(same_path)} on that path"
        )

    # Otherwise list the paths sharing its prefix, which is usually enough to
    # spot the intended one.
    segments = shape.split("/")
    prefix = "/".join(segments[:3]) if len(segments) > 2 else "/v1"
    nearby = sorted({p for _, p in http_routes if p.startswith(prefix)})
    pytest.fail(
        f"{source}: SDK calls {method} {path}, which the API does not serve. "
        f"Paths under {prefix}: {nearby}"
    )


def test_sdk_websocket_path_exists_in_api(app_routes):
    _, ws_routes = app_routes
    sdk_ws = _sdk_websocket_paths()
    assert sdk_ws, "no WebSocket path found in the SDK source"
    for path in sdk_ws:
        assert _normalise(path) in ws_routes, (
            f"SDK opens a WebSocket at {path}, which the API does not serve. "
            f"Available: {sorted(ws_routes)}"
        )


def test_every_v1_literal_in_sdk_is_covered():
    """
    Catch a new endpoint added to the SDK that the extractors above miss, so
    this test cannot be defeated by writing the call in an unusual shape.
    """
    covered = {p for _, p, _ in _sdk_calls()} | set(_sdk_websocket_paths())
    covered_prefixes = {p.split("{")[0].rstrip("/") for p in covered}

    for cpp in ("client.cpp", "auth.cpp"):
        text = (SDK_SRC / cpp).read_text(encoding="utf-8")
        for literal in re.findall(r'"(/v1/[^"]*)"', text):
            prefix = literal.split("{")[0].rstrip("/")
            assert any(
                prefix.startswith(c) or c.startswith(prefix) for c in covered_prefixes
            ), (
                f"{cpp} contains the path literal {literal!r} that no extracted "
                f"call accounts for. Add it to the contract check."
            )


# ---------------------------------------------------------------------------
# Response field contract
#
# Three of the SDK's bugs were field-name mismatches rather than wrong routes:
# it read "member_ids" where the API sends "members", "token" where the API
# sends "server_token", and "id" where the profile sends "player_id". Each one
# compiled, parsed without error, and silently produced an empty value.
#
# These checks compare the JSON keys each parse_* function reads against the
# fields the corresponding response model declares.
# ---------------------------------------------------------------------------

# Keys the SDK may read that are not model fields, with the reason.
ALLOWED_EXTRA_KEYS = {
    # Accepted as a fallback so a rename cannot silently empty the field again.
    "parse_profile": {"id"},
}


def _parse_function_body(name: str) -> str:
    """Return the body of a parse_* function from client.cpp."""
    source = (SDK_SRC / "client.cpp").read_text(encoding="utf-8")
    start = re.search(
        rf"^\w[\w:<>]*\s+{re.escape(name)}\(const json& j\)\s*\{{", source, re.MULTILINE
    )
    assert start, f"could not find {name} in client.cpp"

    # Walk braces from the opening one to find the matching close.
    i = source.index("{", start.start())
    depth = 0
    for end in range(i, len(source)):
        if source[end] == "{":
            depth += 1
        elif source[end] == "}":
            depth -= 1
            if depth == 0:
                return source[i : end + 1]
    raise AssertionError(f"unbalanced braces in {name}")


def _keys_read(body: str, var: str) -> set[str]:
    """JSON keys read from `var` within a function body."""
    keys = set()
    keys |= set(re.findall(rf'get_(?:string|int|bool)\(\s*{var}\s*,\s*"([^"]+)"', body))
    keys |= set(re.findall(rf'{var}\.contains\(\s*"([^"]+)"\s*\)', body))
    keys |= set(re.findall(rf'{var}\[\s*"([^"]+)"\s*\]', body))
    return keys


@pytest.fixture(scope="module")
def schemas():
    sys.path.insert(0, str(API_DIR))
    try:
        import models.schemas as s
    finally:
        sys.path.pop(0)
    return s


@pytest.mark.parametrize(
    "fn_name,var,model_name",
    [
        ("parse_profile", "j", "ProfileResponse"),
        ("parse_party", "j", "PartyResponse"),
        ("parse_party", "m", "PartyMemberResponse"),
        ("parse_ready_check", "j", "ReadyCheckResponse"),
    ],
)
def test_sdk_reads_fields_the_model_declares(fn_name, var, model_name, schemas):
    model = getattr(schemas, model_name)
    declared = set(model.model_fields)

    read = _keys_read(_parse_function_body(fn_name), var)
    assert read, f"{fn_name} appears to read no keys from '{var}' - check the extractor"

    allowed = declared | ALLOWED_EXTRA_KEYS.get(fn_name, set())
    unknown = read - allowed
    assert not unknown, (
        f"{fn_name} reads {sorted(unknown)} from '{var}', which {model_name} does not "
        f"declare. Its fields are {sorted(declared)}."
    )


def test_sdk_reads_the_fields_match_found_actually_sends():
    """
    match.found is a plain dict rather than a response model, so its keys come
    from the broadcast call in the consumer.
    """
    consumer = (API_DIR / "consumers" / "match_consumer.py").read_text(encoding="utf-8")

    call = re.search(
        r"broadcast_match_found_to_parties\(.*?\{(.*?)\},\s*\)", consumer, re.DOTALL
    )
    assert call, "could not find the match.found broadcast payload"
    sent = set(re.findall(r'"(\w+)":', call.group(1)))
    assert sent, "extracted no keys from the match.found payload"

    read = _keys_read(_parse_function_body("parse_match_info"), "j")
    unknown = read - sent
    assert not unknown, (
        f"parse_match_info reads {sorted(unknown)}, which match.found does not send. "
        f"It sends {sorted(sent)}."
    )

from __future__ import annotations

import json
import sqlite3
from io import BytesIO
from pathlib import Path

import server


def configure_test_backend(tmpdir: Path) -> None:
    tmpdir.mkdir(exist_ok=True)
    db_path = tmpdir / "security_test.sqlite3"
    if db_path.exists():
        db_path.unlink()
    server.DB_PATH = tmpdir / "security_test.sqlite3"
    server.UPLOAD_DIR = tmpdir / "uploaded_templates"
    server._WSGI_READY = False


def request(method: str, path: str, body: object | bytes | None = None, headers: dict[str, str] | None = None):
    headers = headers or {}
    if body is None:
        raw = b""
    elif isinstance(body, bytes):
        raw = body
    else:
        raw = json.dumps(body).encode("utf-8")

    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "HTTP_HOST": headers.get("Host", "alibehram11.pythonanywhere.com"),
        "wsgi.input": BytesIO(raw),
        "CONTENT_LENGTH": headers.get("Content-Length", str(len(raw))),
    }
    if "Origin" in headers:
        environ["HTTP_ORIGIN"] = headers["Origin"]
    if "X-CSRF-Token" in headers:
        environ["HTTP_X_CSRF_TOKEN"] = headers["X-CSRF-Token"]
    if "Content-Type" in headers:
        environ["CONTENT_TYPE"] = headers["Content-Type"]

    captured: list[tuple[str, list[tuple[str, str]]]] = []
    chunks = server.application(
        environ,
        lambda status, response_headers, exc_info=None: captured.append((status, response_headers)),
    )
    body_bytes = b"".join(chunks)
    return captured[0][0], dict(captured[0][1]), body_bytes


def expect_status(name: str, actual: str, expected_prefix: str) -> None:
    if not actual.startswith(expected_prefix):
        raise AssertionError(f"{name}: expected {expected_prefix}, got {actual}")


def run() -> None:
    csrf_headers = {
        "Origin": "https://alibehram11.pythonanywhere.com",
        "X-CSRF-Token": server.CSRF_TOKEN,
        "Content-Type": "application/json",
    }
    tests: list[tuple[str, object]] = []

    def add(name, fn):
        tests.append((name, fn))

    add("01 health endpoint works", lambda: expect_status("health", request("GET", "/api/health")[0], "200"))
    add(
        "02 security headers are present",
        lambda: (
            lambda result: (
                expect_status("security header status", result[0], "200"),
                (_ for _ in ()).throw(AssertionError("missing CSP"))
                if "Content-Security-Policy" not in result[1]
                else None,
            )
        )(request("GET", "/api/health")),
    )
    add("03 root page allowed", lambda: expect_status("root", request("GET", "/")[0], "200"))
    add("04 static app alias allowed", lambda: expect_status("app", request("GET", "/static/app.js")[0], "200"))
    add("05 server.py disclosure blocked", lambda: expect_status("server.py", request("GET", "/server.py")[0], "403"))
    add("06 wsgi.py disclosure blocked", lambda: expect_status("wsgi.py", request("GET", "/wsgi.py")[0], "403"))
    add("07 sqlite disclosure blocked", lambda: expect_status("db", request("GET", "/app_data.sqlite3")[0], "403"))
    add("08 sqlite wal disclosure blocked", lambda: expect_status("db wal", request("GET", "/app_data.sqlite3-wal")[0], "403"))
    add("09 git config disclosure blocked", lambda: expect_status("git config", request("GET", "/.git/config")[0], "403"))
    add("10 requirements disclosure blocked", lambda: expect_status("requirements", request("GET", "/requirements.txt")[0], "403"))
    add("11 readme disclosure blocked", lambda: expect_status("readme", request("GET", "/README.md")[0], "403"))
    add("12 plain path traversal blocked", lambda: expect_status("plain traversal", request("GET", "/../server.py")[0], "403"))
    add("13 encoded path traversal blocked", lambda: expect_status("encoded traversal", request("GET", "/%2e%2e/server.py")[0], "403"))
    add("14 uploaded template direct read blocked", lambda: expect_status("uploaded", request("GET", "/uploaded_templates/a.docx")[0], "403"))
    add("15 missing csrf rejected", lambda: expect_status("missing csrf", request("POST", "/api/log", {}, {"Content-Type": "application/json"})[0], "403"))
    add(
        "16 wrong csrf rejected",
        lambda: expect_status(
            "wrong csrf",
            request(
                "POST",
                "/api/log",
                {},
                {
                    "Origin": "https://alibehram11.pythonanywhere.com",
                    "X-CSRF-Token": "bad-token",
                    "Content-Type": "application/json",
                },
            )[0],
            "403",
        ),
    )
    add(
        "17 foreign origin rejected",
        lambda: expect_status(
            "foreign origin",
            request(
                "POST",
                "/api/log",
                {},
                {
                    "Origin": "https://evil.example",
                    "X-CSRF-Token": server.CSRF_TOKEN,
                    "Content-Type": "application/json",
                },
            )[0],
            "403",
        ),
    )
    add("18 valid log post accepted", lambda: expect_status("valid log", request("POST", "/api/log", {"actor": "a", "action": "ok"}, csrf_headers)[0], "200"))

    def sql_injection_payload_safe():
        payload = "x'); DROP TABLE logs; --"
        status, _, _ = request(
            "POST",
            "/api/log",
            {"actor": payload, "action": "sql-injection-test", "detail": {"payload": payload}},
            csrf_headers,
        )
        expect_status("sql payload post", status, "200")
        with sqlite3.connect(server.DB_PATH) as conn:
            count = conn.execute("SELECT COUNT(*) FROM logs WHERE action = ?", ("sql-injection-test",)).fetchone()[0]
        if count < 1:
            raise AssertionError("sql injection payload was not stored safely")

    add("19 sql injection payload stays data", sql_injection_payload_safe)
    add("20 text/plain json body rejected", lambda: expect_status("text/plain", request("POST", "/api/log", b"{}", {**csrf_headers, "Content-Type": "text/plain"})[0], "400"))
    add("21 json array body rejected", lambda: expect_status("json array", request("POST", "/api/log", b"[]", csrf_headers)[0], "400"))
    add("22 malformed json rejected", lambda: expect_status("malformed", request("POST", "/api/log", b"{not-json", csrf_headers)[0], "400"))
    add(
        "23 oversized body rejected before read",
        lambda: expect_status(
            "oversized",
            request("POST", "/api/log", b"", {**csrf_headers, "Content-Length": str(server.MAX_UPLOAD_BYTES + 1)})[0],
            "400",
        ),
    )
    add("24 negative content length rejected", lambda: expect_status("negative length", request("POST", "/api/log", b"", {**csrf_headers, "Content-Length": "-1"})[0], "400"))
    add("25 unknown api returns 404", lambda: expect_status("unknown api", request("POST", "/api/unknown", {}, csrf_headers)[0], "404"))
    add("26 unsupported method returns 405", lambda: expect_status("put method", request("PUT", "/api/log", {}, csrf_headers)[0], "405"))
    add("27 docx upload traversal filename rejected", lambda: expect_status("upload traversal", request("POST", "/api/docx/upload", {"fileName": "../server.py", "dataBase64": ""}, csrf_headers)[0], "400"))
    add(
        "28 frontend request privacy helper exists",
        lambda: (
            lambda text: None
            if "function visibleAtolyeRequests()" in text and "request.createdBy === session.userId" in text
            else (_ for _ in ()).throw(AssertionError("frontend request privacy helper missing"))
        )(Path("app.js").read_text(encoding="utf-8")),
    )

    passed = []
    configure_test_backend(Path(".security_test_runtime"))
    for name, fn in tests:
        fn()
        passed.append(name)

    for name in passed:
        print(f"PASS {name}")
    print(f"PASS total={len(passed)}")


if __name__ == "__main__":
    run()

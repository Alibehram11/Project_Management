from __future__ import annotations

import base64
import json
import math
import sqlite3
import zipfile
from io import BytesIO
from pathlib import Path

import server


def configure_test_backend(tmpdir: Path) -> None:
    tmpdir.mkdir(parents=True, exist_ok=True)
    db_path = tmpdir / "security_test.sqlite3"
    if db_path.exists():
        db_path.unlink()
    server.DB_PATH = db_path
    server.UPLOAD_DIR = tmpdir / "uploaded_templates"
    server.API_SESSIONS.clear()
    server.RATE_BUCKETS.clear()
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
        "REMOTE_ADDR": headers.get("Remote-Addr", "127.0.0.1"),
        "wsgi.input": BytesIO(raw),
        "CONTENT_LENGTH": headers.get("Content-Length", str(len(raw))),
    }
    if "Origin" in headers:
        environ["HTTP_ORIGIN"] = headers["Origin"]
    if "Authorization" in headers:
        environ["HTTP_AUTHORIZATION"] = headers["Authorization"]
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


def json_body(body: bytes) -> dict:
    return json.loads(body.decode("utf-8"))


def login(email: str, password: str, remote: str = "127.0.0.1") -> dict:
    status, _, body = request(
        "POST",
        "/api/auth/login",
        {"email": email, "password": password},
        {
            "Origin": "https://alibehram11.pythonanywhere.com",
            "Content-Type": "application/json",
            "Remote-Addr": remote,
        },
    )
    expect_status(f"login {email}", status, "200")
    result = json_body(body)
    return {
        "Authorization": f"Bearer {result['token']}",
        "X-CSRF-Token": result["csrfToken"],
        "Origin": "https://alibehram11.pythonanywhere.com",
        "Content-Type": "application/json",
        "Remote-Addr": remote,
    }


def minimal_docx_b64(extra_name: str | None = None, extra_data: bytes = b"") -> str:
    output = BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as docx:
        docx.writestr(
            "[Content_Types].xml",
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            "</Types>",
        )
        docx.writestr(
            "_rels/.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            "</Relationships>",
        )
        docx.writestr("word/document.xml", '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>')
        if extra_name:
            docx.writestr(extra_name, extra_data)
    return base64.b64encode(output.getvalue()).decode("ascii")


def custom_docx_b64(replacements: dict[str, bytes | str], duplicate: tuple[str, bytes] | None = None) -> str:
    base = {
        "[Content_Types].xml": (
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            "</Types>"
        ),
        "_rels/.rels": (
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            "</Relationships>"
        ),
        "word/document.xml": '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>',
    }
    base.update(replacements)
    output = BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as docx:
        for name, value in base.items():
            docx.writestr(name, value)
        if duplicate:
            docx.writestr(duplicate[0], duplicate[1])
    return base64.b64encode(output.getvalue()).decode("ascii")


def initial_state() -> dict:
    users = [dict(user) for user in server.DEMO_USERS]
    member_ids = [user["id"] for user in users]
    return {
        "users": users,
        "projects": [{
            "id": "project-1",
            "name": "Security Test",
            "ownerId": "demo-admin",
            "memberIds": member_ids,
            "adminIds": ["demo-admin", "demo-mentor", "demo-atolye"],
            "memberProfiles": {user_id: {"role": "member", "team": "Yönetim"} for user_id in member_ids},
        }],
        "tasks": [],
        "invites": [],
        "calendarEvents": [],
        "crmItems": [],
        "feedItems": [],
        "documents": {},
        "documentTemplates": [],
        "atolyeRequests": [],
        "trash": [],
    }


def run() -> None:
    tests: list[tuple[str, object]] = []
    context: dict[str, dict] = {}

    def add(name, fn):
        tests.append((name, fn))

    add("01 health endpoint is public but minimal", lambda: (
        lambda result: (
            expect_status("health", result[0], "200"),
            (_ for _ in ()).throw(AssertionError("health leaked csrf/database"))
            if any(key in json_body(result[2]) for key in ("csrfToken", "database", "templateCount"))
            else None,
        )
    )(request("GET", "/api/health")))
    add("02 security headers include CSP and HSTS", lambda: (
        lambda result: (
            expect_status("security header status", result[0], "200"),
            (_ for _ in ()).throw(AssertionError("missing CSP/HSTS"))
            if "Content-Security-Policy" not in result[1] or "Strict-Transport-Security" not in result[1]
            else None,
        )
    )(request("GET", "/api/health")))
    add("03 root page allowed", lambda: expect_status("root", request("GET", "/")[0], "200"))
    add("04 static app alias allowed", lambda: expect_status("app", request("GET", "/static/app.js")[0], "200"))
    add("05 hostile host header rejected", lambda: expect_status("host", request("GET", "/api/health", headers={"Host": "evil.example"})[0], "403"))
    add("06 server.py disclosure blocked", lambda: expect_status("server.py", request("GET", "/server.py")[0], "403"))
    add("07 wsgi.py disclosure blocked", lambda: expect_status("wsgi.py", request("GET", "/wsgi.py")[0], "403"))
    add("08 sqlite disclosure blocked", lambda: expect_status("db", request("GET", "/app_data.sqlite3")[0], "403"))
    add("09 sqlite wal disclosure blocked", lambda: expect_status("db wal", request("GET", "/app_data.sqlite3-wal")[0], "403"))
    add("10 git config disclosure blocked", lambda: expect_status("git config", request("GET", "/.git/config")[0], "403"))
    add("11 path traversal blocked", lambda: expect_status("traversal", request("GET", "/%2e%2e/server.py")[0], "403"))
    add("12 state get requires auth", lambda: expect_status("state unauth", request("GET", "/api/state")[0], "401"))
    add("13 state post requires origin", lambda: expect_status("state no origin", request("POST", "/api/state", {}, {"Content-Type": "application/json"})[0], "403"))
    add("14 auth login rejects bad password", lambda: expect_status("bad login", request("POST", "/api/auth/login", {"email": "admin@proje.local", "password": "wrong"}, {"Origin": "https://alibehram11.pythonanywhere.com", "Content-Type": "application/json"})[0], "401"))
    add("15 admin login issues session csrf", lambda: context.setdefault("admin", login("admin@proje.local", "123456")))
    add("16 member login issues member token", lambda: context.setdefault("member", login("tasarim@proje.local", "123456", "127.0.0.2")))
    add("17 missing bearer token rejected", lambda: expect_status("missing bearer", request("POST", "/api/log", {"action": "x"}, {"Origin": "https://alibehram11.pythonanywhere.com", "Content-Type": "application/json"})[0], "401"))
    add("18 wrong csrf rejected", lambda: expect_status("wrong csrf", request("POST", "/api/log", {"action": "x"}, {**context["admin"], "X-CSRF-Token": "bad"})[0], "403"))
    add("19 valid auth log accepted", lambda: expect_status("valid log", request("POST", "/api/log", {"action": "ok"}, context["admin"])[0], "200"))
    add("20 member cannot write state", lambda: expect_status("member state", request("POST", "/api/state", {"payload": {}, "revision": 0}, context["member"])[0], "403"))
    add("21 admin can write state", lambda: expect_status("admin state", request("POST", "/api/state", {"payload": initial_state(), "revision": 0, "reason": "test"}, context["admin"])[0], "200"))
    add("22 snapshot requires admin", lambda: expect_status("member snapshot", request("POST", "/api/snapshot", {"payload": {}}, context["member"])[0], "403"))
    add("23 admin can create snapshot", lambda: expect_status("admin snapshot", request("POST", "/api/snapshot", {"payload": {}}, context["admin"])[0], "200"))
    add("24 logs require admin", lambda: expect_status("member logs", request("GET", "/api/logs", headers=context["member"])[0], "403"))
    add("25 foreign origin rejected", lambda: expect_status("foreign origin", request("POST", "/api/log", {"action": "x"}, {**context["admin"], "Origin": "https://evil.example"})[0], "403"))

    def sql_injection_payload_safe():
        payload = "x'); DROP TABLE logs; --"
        status, _, _ = request("POST", "/api/log", {"action": "sql-injection-test", "detail": {"payload": payload}}, context["admin"])
        expect_status("sql payload post", status, "200")
        with sqlite3.connect(server.DB_PATH) as conn:
            count = conn.execute("SELECT COUNT(*) FROM logs WHERE action = ?", ("sql-injection-test",)).fetchone()[0]
        if count < 1:
            raise AssertionError("sql injection payload was not stored safely")

    add("26 sql injection payload stays data", sql_injection_payload_safe)
    add("27 text/plain json body rejected", lambda: expect_status("text/plain", request("POST", "/api/log", b"{}", {**context["admin"], "Content-Type": "text/plain"})[0], "400"))
    add("28 json array body rejected", lambda: expect_status("json array", request("POST", "/api/log", b"[]", context["admin"])[0], "400"))
    add("29 malformed json rejected", lambda: expect_status("malformed", request("POST", "/api/log", b"{not-json", context["admin"])[0], "400"))
    add("30 oversized body rejected before read", lambda: expect_status("oversized", request("POST", "/api/log", b"", {**context["admin"], "Content-Length": str(server.MAX_UPLOAD_BYTES + 1)})[0], "400"))
    add("31 negative content length rejected", lambda: expect_status("negative length", request("POST", "/api/log", b"", {**context["admin"], "Content-Length": "-1"})[0], "400"))
    add("32 docx upload requires admin", lambda: expect_status("member upload", request("POST", "/api/docx/upload", {"fileName": "01_FR-01_Proje_Tanim_Karti.docx", "dataBase64": minimal_docx_b64()}, context["member"])[0], "403"))
    add("33 docx upload rejects macros", lambda: expect_status("macro upload", request("POST", "/api/docx/upload", {"fileName": "01_FR-01_Proje_Tanim_Karti.docx", "dataBase64": minimal_docx_b64("word/vbaProject.bin", b"x")}, context["admin"])[0], "400"))
    add("34 docx upload rejects external rels", lambda: expect_status("external rels", request("POST", "/api/docx/upload", {"fileName": "01_FR-01_Proje_Tanim_Karti.docx", "dataBase64": minimal_docx_b64("word/_rels/document.xml.rels", b'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId9" TargetMode="External" Target="https://evil.example/payload"/></Relationships>')}, context["admin"])[0], "400"))
    add("35 docx upload rejects invalid base64", lambda: expect_status("invalid base64", request("POST", "/api/docx/upload", {"fileName": "01_FR-01_Proje_Tanim_Karti.docx", "dataBase64": "not-base64!!"}, context["admin"])[0], "400"))
    add("36 docx upload traversal filename rejected", lambda: expect_status("upload traversal", request("POST", "/api/docx/upload", {"fileName": "../server.py", "dataBase64": ""}, context["admin"])[0], "400"))
    add("37 docx export requires auth", lambda: expect_status("export unauth", request("POST", "/api/docx/export", {}, {"Origin": "https://alibehram11.pythonanywhere.com", "Content-Type": "application/json"})[0], "401"))
    add("38 unsupported method returns 405", lambda: expect_status("put method", request("PUT", "/api/log", {}, context["admin"])[0], "405"))
    add("39 frontend request privacy helper exists", lambda: (
        lambda text: None
        if "function visibleAtolyeRequests()" in text and "request.createdBy === session.userId" in text
        else (_ for _ in ()).throw(AssertionError("frontend request privacy helper missing"))
    )((Path("app.js") if Path("app.js").exists() else Path("static/app.js")).read_text(encoding="utf-8")))

    def malformed_json_hides_exception():
        status, _, body = request("POST", "/api/log", b"{not-json", context["admin"])
        expect_status("malformed hidden", status, "400")
        if json_body(body) != {"ok": False, "error": "bad-request"}:
            raise AssertionError("JSON decoder details leaked")

    add("40 malformed JSON hides parser exception", malformed_json_hides_exception)

    def unexpected_exception_is_generic():
        original = server.find_auth_user
        server.find_auth_user = lambda *_: (_ for _ in ()).throw(RuntimeError("SECRET_PATH:C:/private/app.db"))
        try:
            status, _, body = request(
                "POST",
                "/api/auth/login",
                {"email": "admin@proje.local", "password": "123456"},
                {"Origin": "https://alibehram11.pythonanywhere.com", "Content-Type": "application/json", "Remote-Addr": "127.0.0.9"},
            )
        finally:
            server.find_auth_user = original
        expect_status("internal exception", status, "500")
        if json_body(body) != {"ok": False, "error": "internal-error"} or b"SECRET_PATH" in body:
            raise AssertionError("internal exception details leaked")

    add("41 unexpected exception response is generic", unexpected_exception_is_generic)

    def sanitizer_blocks_dangerous_values():
        clean = server.sanitize_value({
            "__proto__": {"admin": True},
            "constructor": "pollute",
            "visible": "normal\u202etext\x00",
            "number": math.nan,
        })
        if "__proto__" in clean or "constructor" in clean:
            raise AssertionError("prototype pollution keys survived")
        if "\u202e" in clean["visible"] or "\x00" in clean["visible"] or clean["number"] is not None:
            raise AssertionError("unsafe scalar value survived")

    add("42 sanitizer blocks prototype keys and unsafe scalars", sanitizer_blocks_dangerous_values)

    def sanitizer_enforces_limits():
        deep: object = "leaf"
        for _ in range(server.MAX_SANITIZE_DEPTH + 4):
            deep = {"next": deep}
        clean = server.sanitize_value({"deep": deep, "long": "x" * (server.MAX_SANITIZE_STRING + 500)})
        if len(clean["long"]) != server.MAX_SANITIZE_STRING:
            raise AssertionError("string length limit failed")
        cursor = clean["deep"]
        for _ in range(server.MAX_SANITIZE_DEPTH + 2):
            if cursor is None:
                return
            cursor = cursor.get("next") if isinstance(cursor, dict) else None
        raise AssertionError("depth limit failed")

    add("43 sanitizer enforces depth and string limits", sanitizer_enforces_limits)
    add("44 JSON NaN is rejected", lambda: expect_status("nan json", request("POST", "/api/log", b'{"action":NaN}', context["admin"])[0], "400"))
    add("45 valid DOCX upload is accepted", lambda: expect_status("valid docx", request("POST", "/api/docx/upload", {"fileName": "01_FR-01_Proje_Tanim_Karti.docx", "dataBase64": minimal_docx_b64()}, context["admin"])[0], "200"))
    add("46 DOCX malformed XML is rejected", lambda: expect_status("malformed xml", request("POST", "/api/docx/upload", {"fileName": "01_FR-01_Proje_Tanim_Karti.docx", "dataBase64": custom_docx_b64({"word/document.xml": "<w:document>"})}, context["admin"])[0], "400"))
    add("47 DOCX DTD is rejected", lambda: expect_status("docx dtd", request("POST", "/api/docx/upload", {"fileName": "01_FR-01_Proje_Tanim_Karti.docx", "dataBase64": custom_docx_b64({"word/document.xml": '<!DOCTYPE x [<!ENTITY e "boom">]><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">&e;</w:document>'})}, context["admin"])[0], "400"))
    add("48 DOCX duplicate canonical path is rejected", lambda: expect_status("duplicate path", request("POST", "/api/docx/upload", {"fileName": "01_FR-01_Proje_Tanim_Karti.docx", "dataBase64": custom_docx_b64({}, ("WORD/DOCUMENT.XML", b"x"))}, context["admin"])[0], "400"))
    add("49 DOCX compression bomb is rejected", lambda: expect_status("zip bomb", request("POST", "/api/docx/upload", {"fileName": "01_FR-01_Proje_Tanim_Karti.docx", "dataBase64": custom_docx_b64({"word/media/image.png": b"A" * 1_000_000})}, context["admin"])[0], "400"))
    add("50 DOCX embedded object is rejected", lambda: expect_status("embedded object", request("POST", "/api/docx/upload", {"fileName": "01_FR-01_Proje_Tanim_Karti.docx", "dataBase64": custom_docx_b64({"word/embeddings/oleObject1.bin": b"payload"})}, context["admin"])[0], "400"))
    add("51 DOCX macro content type is rejected", lambda: expect_status("macro content type", request("POST", "/api/docx/upload", {"fileName": "01_FR-01_Proje_Tanim_Karti.docx", "dataBase64": custom_docx_b64({"[Content_Types].xml": '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Override PartName="/word/document.xml" ContentType="application/vnd.ms-word.document.macroEnabled.main+xml"/></Types>'})}, context["admin"])[0], "400"))
    add("52 DOCX relationship traversal is rejected", lambda: expect_status("relationship traversal", request("POST", "/api/docx/upload", {"fileName": "01_FR-01_Proje_Tanim_Karti.docx", "dataBase64": custom_docx_b64({"word/_rels/document.xml.rels": '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId2" Target="../../outside.bin"/></Relationships>'})}, context["admin"])[0], "400"))

    def valid_docx_export_works():
        status, headers, body = request(
            "POST",
            "/api/docx/export",
            {"projectId": "project-1", "templateId": "fr01", "projectName": "Guvenlik Testi", "title": "Rapor", "questions": ["Sonuc"], "answers": {"q0": "Basarili"}},
            context["admin"],
        )
        expect_status("valid export", status, "200")
        if headers.get("Content-Type") != server.DOCX_MIME or not zipfile.is_zipfile(BytesIO(body)):
            raise AssertionError("valid DOCX export failed")

    add("53 valid provided template exports as DOCX", valid_docx_export_works)

    def frontend_role_controls_exist():
        text = Path("app.js").read_text(encoding="utf-8")
        markup = Path("index.html").read_text(encoding="utf-8")
        if "function updateProjectMemberRole" not in text or "data-member-role" not in text or "adminUserPermissionHint" not in markup:
            raise AssertionError("project role assignment controls are missing")

    add("54 frontend exposes project role assignment controls", frontend_role_controls_exist)

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

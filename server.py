from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import mimetypes
import os
import secrets
import sqlite3
import sys
import time
import zipfile
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
from urllib.parse import unquote, urlparse
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "app_data.sqlite3"
TEMPLATE_DIR = ROOT / "proje_yonetimi_ogrenci_belgeleri_word"
UPLOAD_DIR = ROOT / "uploaded_templates"
STATE_KEY = "main"
MAX_UPLOAD_BYTES = 12 * 1024 * 1024
SESSION_TTL_SECONDS = 8 * 60 * 60
RATE_WINDOW_SECONDS = 60
RATE_LIMIT_DEFAULT = 90
RATE_LIMIT_LOGIN = 12
JSON_MIME = "application/json; charset=utf-8"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
BLOCKED_STATIC_PATHS = {"/app_data.sqlite3", "/server.py", "/wsgi.py"}
ALLOWED_STATIC_PATHS = {
    "",
    "index.html",
    "app.js",
    "styles.css",
    "static/app.js",
    "static/styles.css",
    "templates/index.html",
}
_WSGI_READY = False
API_SESSIONS: dict[str, dict] = {}
RATE_BUCKETS: dict[tuple[str, str], list[float]] = {}
SECURITY_HEADERS = [
    ("X-Content-Type-Options", "nosniff"),
    ("X-Frame-Options", "DENY"),
    ("Strict-Transport-Security", "max-age=31536000; includeSubDomains"),
    ("Referrer-Policy", "same-origin"),
    ("Permissions-Policy", "camera=(), microphone=(), geolocation=()"),
    ("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; form-action 'self'; base-uri 'self'"),
]

DEFAULT_ALLOWED_HOSTS = {
    "127.0.0.1",
    "localhost",
    "alibehram11.pythonanywhere.com",
}
CONFIGURED_ALLOWED_HOSTS = {
    host.strip().lower()
    for host in os.environ.get("PROJECT_ALLOWED_HOSTS", "").split(",")
    if host.strip()
}
ALLOWED_HOSTS = DEFAULT_ALLOWED_HOSTS | CONFIGURED_ALLOWED_HOSTS

DEMO_USERS = [
    {"id": "demo-admin", "name": "Ana Admin", "email": "admin@proje.local", "password": "123456", "role": "admin"},
    {"id": "demo-yazilim", "name": "Yazilim Kaptani", "email": "yazilim@proje.local", "password": "123456", "role": "member"},
    {"id": "demo-yazilim2", "name": "Yazilim Uyesi", "email": "yazilim2@proje.local", "password": "123456", "role": "member"},
    {"id": "demo-tasarim", "name": "Tasarim Uyesi", "email": "tasarim@proje.local", "password": "123456", "role": "member"},
    {"id": "demo-mekanik", "name": "Mekanik Kaptani", "email": "mekanik@proje.local", "password": "123456", "role": "member"},
    {"id": "demo-elektronik", "name": "Elektronik Uyesi", "email": "elektronik@proje.local", "password": "123456", "role": "member"},
    {"id": "demo-mentor", "name": "Mentor Kullanicisi", "email": "mentor@proje.local", "password": "123456", "role": "admin"},
    {"id": "demo-atolye", "name": "Atolye Sorumlusu", "email": "atolye@proje.local", "password": "123456", "role": "admin"},
]

KNOWN_TEMPLATES = {
    "fr01": "01_FR-01_Proje_Tanim_Karti.docx",
    "fr02": "02_FR-02_Kural_Gereksinim_Matrisi.docx",
    "fr03": "03_FR-03_On_Tasarim_Formu.docx",
    "fr04": "04_FR-04_Malzeme_Ihtiyac_Listesi.docx",
    "fr05": "05_FR-05_Kritik_Parca_Yedek_Listesi.docx",
    "fr06": "06_FR-06_Gorev_Dagilim_Matrisi.docx",
    "fr07": "07_FR-07_Zaman_Cizelgesi.docx",
    "fr08": "08_FR-08_Risk_Kayit_Formu.docx",
    "fr09": "09_FR-09_Test_Plani_Hata_Defteri.docx",
    "fr10": "10_FR-10_Yarisma_Gunu_Kapanis_Raporu.docx",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def host_name(host: str | None) -> str:
    return (host or "").split(":", 1)[0].strip().lower()


def is_allowed_host(host: str | None) -> bool:
    return host_name(host) in ALLOWED_HOSTS


def client_ip_from_headers(headers: dict | object) -> str:
    if isinstance(headers, dict):
        forwarded = headers.get("X-Forwarded-For") or headers.get("HTTP_X_FORWARDED_FOR") or ""
        remote = headers.get("REMOTE_ADDR") or ""
    else:
        forwarded = headers.get("X-Forwarded-For", "")
        remote = getattr(headers, "client_address", [""])[0] if hasattr(headers, "client_address") else ""
    return (str(forwarded).split(",", 1)[0].strip() or str(remote) or "unknown")[:80]


def rate_limit_key(ip: str, bucket: str, limit: int) -> bool:
    now = time.time()
    key = (ip, bucket)
    entries = [item for item in RATE_BUCKETS.get(key, []) if now - item < RATE_WINDOW_SECONDS]
    if len(entries) >= limit:
        RATE_BUCKETS[key] = entries
        return False
    entries.append(now)
    RATE_BUCKETS[key] = entries
    return True


def load_app_state() -> dict | None:
    with connect_db() as conn:
        row = conn.execute("SELECT payload_json FROM app_state WHERE key = ?", (STATE_KEY,)).fetchone()
    if not row:
        return None
    try:
        payload = json.loads(row[0])
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def user_role_from_state(state: dict | None, user_id: str, email: str) -> str:
    normalized_email = email.lower()
    if normalized_email in {"admin@proje.local", "mentor@proje.local", "atolye@proje.local"}:
        return "admin"
    for project in (state or {}).get("projects", []) if isinstance((state or {}).get("projects"), list) else []:
        if not isinstance(project, dict):
            continue
        if project.get("ownerId") == user_id or user_id in (project.get("adminIds") or []):
            return "admin"
    return "member"


def find_auth_user(email: str, password: str) -> dict | None:
    normalized_email = (email or "").strip().lower()
    state = load_app_state()
    users = []
    if isinstance(state, dict) and isinstance(state.get("users"), list):
        users.extend(user for user in state["users"] if isinstance(user, dict))
    if not users:
        users.extend(DEMO_USERS)

    for user in users:
        if str(user.get("email", "")).lower() != normalized_email:
            continue
        if not secrets.compare_digest(str(user.get("password") or ""), str(password or "")):
            continue
        return {
            "id": str(user.get("id") or normalized_email),
            "name": str(user.get("name") or normalized_email),
            "email": normalized_email,
            "role": user.get("role") or user_role_from_state(state, str(user.get("id") or ""), normalized_email),
        }
    return None


def create_api_session(user: dict) -> dict:
    token = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(32)
    API_SESSIONS[token] = {
        "userId": user["id"],
        "email": user["email"],
        "name": user["name"],
        "role": user.get("role", "member"),
        "csrf": csrf,
        "expires": time.time() + SESSION_TTL_SECONDS,
    }
    return {"token": token, "csrfToken": csrf, "user": {key: user[key] for key in ("id", "name", "email", "role")}}


def auth_from_headers(headers: dict, require_csrf: bool = False, admin: bool = False) -> tuple[dict | None, str | None]:
    authorization = headers.get("Authorization") or headers.get("HTTP_AUTHORIZATION") or ""
    if not authorization.startswith("Bearer "):
        return None, "auth-required"
    token = authorization.removeprefix("Bearer ").strip()
    session = API_SESSIONS.get(token)
    if not session or session.get("expires", 0) < time.time():
        API_SESSIONS.pop(token, None)
        return None, "auth-expired"
    if require_csrf:
        csrf = headers.get("X-CSRF-Token") or headers.get("HTTP_X_CSRF_TOKEN") or ""
        if not secrets.compare_digest(csrf, session.get("csrf", "")):
            return None, "csrf-token-invalid"
    if admin and session.get("role") != "admin":
        return None, "admin-required"
    session["expires"] = time.time() + SESSION_TTL_SECONDS
    return session, None


def safe_error(error: str) -> str:
    allowed = {
        "auth-required",
        "auth-expired",
        "admin-required",
        "csrf-token-invalid",
        "origin-blocked",
        "host-blocked",
        "rate-limit",
        "content-type-json-required",
        "json-object-required",
        "request-too-large",
        "content-length-invalid",
        "invalid-docx",
        "unknown-template",
        "file-too-large",
        "not-found",
        "method-not-allowed",
    }
    return error if error in allowed else "bad-request"


def connect_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def init_db() -> None:
    UPLOAD_DIR.mkdir(exist_ok=True)
    with connect_db() as conn:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app_state (
                key TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                updated_by TEXT,
                reason TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                actor TEXT,
                action TEXT NOT NULL,
                detail_json TEXT
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_ts ON logs (ts)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_action ON logs (action)")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                actor TEXT,
                payload_json TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_ts ON snapshots (ts)")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS uploaded_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT NOT NULL,
                stored_path TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                uploaded_at TEXT NOT NULL,
                uploaded_by TEXT
            )
            """
        )
        row = conn.execute("SELECT payload_json FROM app_state WHERE key = ?", (STATE_KEY,)).fetchone()
        if row:
            clean_payload = sanitize_state_payload(json.loads(row[0]))
            conn.execute(
                "UPDATE app_state SET payload_json = ?, updated_at = ?, reason = ? WHERE key = ?",
                (json.dumps(clean_payload, ensure_ascii=False), now_iso(), "security-sanitize", STATE_KEY),
            )


def db_log(actor: str, action: str, detail: object | None = None) -> None:
    with connect_db() as conn:
        conn.execute(
            "INSERT INTO logs (ts, actor, action, detail_json) VALUES (?, ?, ?, ?)",
            (
                now_iso(),
                safe_text(actor or "anonim", 120),
                safe_text(action or "unknown", 120),
                json.dumps(sanitize_value(detail or {}, depth=0), ensure_ascii=False),
            ),
        )
        conn.execute(
            "DELETE FROM logs WHERE id NOT IN (SELECT id FROM logs ORDER BY id DESC LIMIT 1000)"
        )


def json_response(handler: SimpleHTTPRequestHandler, payload: object, status: int = 200) -> None:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", JSON_MIME)
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def safe_text(value: object, limit: int = 5000) -> str:
    text = str(value or "")
    text = "".join(char if char >= " " and char != "\x7f" else " " for char in text)
    return text[:limit]


def sanitize_value(value: object, depth: int = 0) -> object:
    if depth > 8:
        return ""
    if isinstance(value, dict):
        return {safe_text(key, 120): sanitize_value(item, depth + 1) for key, item in list(value.items())[:200]}
    if isinstance(value, list):
        return [sanitize_value(item, depth + 1) for item in value[:500]]
    if isinstance(value, str):
        return safe_text(value, 200_000)
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return safe_text(value)


def safe_download_name(value: object, fallback: str = "belge.docx") -> str:
    text = safe_text(value, 120)
    allowed = []
    for char in text:
        if char.isascii() and (char.isalnum() or char in {".", "_", "-"}):
            allowed.append(char)
        elif char.isspace():
            allowed.append("-")
    name = "".join(allowed).strip(".-_")[:100]
    if not name:
        name = fallback
    if not name.lower().endswith(".docx"):
        name = f"{name}.docx"
    return name


def parse_content_length(value: str | None) -> int:
    length = int(value or "0")
    if length < 0:
        raise ValueError("content-length-invalid")
    if length > MAX_UPLOAD_BYTES:
        raise ValueError("request-too-large")
    return length


def read_json(handler: SimpleHTTPRequestHandler) -> dict:
    content_type = handler.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
    length = parse_content_length(handler.headers.get("Content-Length"))
    if length and content_type != "application/json":
        raise ValueError("content-type-json-required")
    raw = handler.rfile.read(length)
    if not raw:
        return {}
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("json-object-required")
    return payload


def template_path(template_id: str | None, file_name: str | None) -> Path | None:
    expected = KNOWN_TEMPLATES.get(template_id or "") or file_name
    if not expected or expected not in KNOWN_TEMPLATES.values():
        return None
    uploaded = UPLOAD_DIR / expected
    if uploaded.exists():
        return uploaded
    candidate = TEMPLATE_DIR / expected
    return candidate if candidate.exists() else None


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def xml_paragraph(text: str, style: str | None = None) -> str:
    style_xml = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    return f"<w:p>{style_xml}<w:r><w:t xml:space=\"preserve\">{escape(text)}</w:t></w:r></w:p>"


def document_xml(payload: dict, source_file: str) -> str:
    questions = payload.get("questions") or []
    answers = payload.get("answers") or {}
    paragraphs = [
        xml_paragraph(str(payload.get("title") or "Proje Belgesi"), "Title"),
        xml_paragraph(f"Proje: {payload.get('projectName') or ''}"),
        xml_paragraph(f"Şablon kontrolü: {source_file}"),
        xml_paragraph(f"Dolduran: {payload.get('actor') or ''}"),
        xml_paragraph(f"Oluşturma zamanı: {now_iso()}"),
        xml_paragraph(""),
    ]
    for index, question in enumerate(questions):
        answer = answers.get(f"q{index}") or ""
        paragraphs.append(xml_paragraph(str(question), "Heading1"))
        paragraphs.append(xml_paragraph(str(answer) if str(answer).strip() else "-"))
    body = "".join(paragraphs)
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:wpc="http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas"
 xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
 xmlns:o="urn:schemas-microsoft-com:office:office"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
 xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"
 xmlns:v="urn:schemas-microsoft-com:vml"
 xmlns:wp14="http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing"
 xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
 xmlns:w10="urn:schemas-microsoft-com:office:word"
 xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
 xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml"
 xmlns:wpg="http://schemas.microsoft.com/office/word/2010/wordprocessingGroup"
 xmlns:wpi="http://schemas.microsoft.com/office/word/2010/wordprocessingInk"
 xmlns:wne="http://schemas.microsoft.com/office/word/2006/wordml"
 xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape"
 mc:Ignorable="w14 wp14"><w:body>{body}<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="708" w:footer="708" w:gutter="0"/></w:sectPr></w:body></w:document>"""


def minimal_docx(payload: dict, source_file: str) -> bytes:
    from io import BytesIO

    output = BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as docx:
        docx.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>""",
        )
        docx.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>""",
        )
        docx.writestr("word/document.xml", document_xml(payload, source_file))
    return output.getvalue()


def filled_docx(payload: dict) -> tuple[bytes, str]:
    source = template_path(payload.get("templateId"), payload.get("fileName"))
    source_name = source.name if source else str(payload.get("fileName") or "boş şablon")
    if not source or not zipfile.is_zipfile(source):
        return minimal_docx(payload, source_name), source_name

    from io import BytesIO

    output = BytesIO()
    with zipfile.ZipFile(source, "r") as original, zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as docx:
        written = set()
        for entry in original.infolist():
            if entry.filename == "word/document.xml":
                continue
            if entry.filename in written:
                continue
            docx.writestr(entry, original.read(entry.filename))
            written.add(entry.filename)
        docx.writestr("word/document.xml", document_xml(payload, source_name))
    return output.getvalue(), source_name


def validate_docx_bytes(data: bytes) -> tuple[bool, str]:
    if len(data) > MAX_UPLOAD_BYTES:
        return False, "file-too-large"
    try:
        with zipfile.ZipFile(BytesIO(data), "r") as docx:
            names = docx.namelist()
            if len(names) > 250:
                return False, "invalid-docx"
            total = 0
            for entry in docx.infolist():
                name = entry.filename.replace("\\", "/").lower()
                total += entry.file_size
                if total > MAX_UPLOAD_BYTES * 3:
                    return False, "file-too-large"
                if name.startswith("/") or "../" in name or name.startswith("../"):
                    return False, "invalid-docx"
                if name.endswith("vbaproject.bin") or "vba" in name or name.endswith(".exe"):
                    return False, "invalid-docx"
                if name.endswith(".rels"):
                    rels = docx.read(entry.filename)[:1_000_000].decode("utf-8", errors="ignore").lower()
                    if "targetmode=\"external\"" in rels or "targetmode='external'" in rels:
                        return False, "invalid-docx"
            required = {"[content_types].xml", "_rels/.rels", "word/document.xml"}
            if not required.issubset({name.lower() for name in names}):
                return False, "invalid-docx"
    except zipfile.BadZipFile:
        return False, "invalid-docx"
    return True, "ok"


def sanitize_state_payload(payload: object) -> object:
    if not isinstance(payload, dict):
        return {}
    clean = sanitize_value(payload)
    if not isinstance(clean, dict):
        return {}
    users = clean.get("users")
    if isinstance(users, list):
        clean["users"] = [
            dict(user)
            for user in users
            if isinstance(user, dict)
        ]
    return clean


def same_host_origins(host: str) -> set[str]:
    clean_host = host_name(host)
    if clean_host not in ALLOWED_HOSTS:
        return set()
    return {f"http://{clean_host}", f"https://{clean_host}"}


def allowed_origin(handler: SimpleHTTPRequestHandler) -> str | None:
    origin = handler.headers.get("Origin")
    host = handler.headers.get("Host", "")
    return origin if origin in same_host_origins(host) else None


def request_origin_is_allowed(handler: SimpleHTTPRequestHandler) -> bool:
    origin = handler.headers.get("Origin")
    if not origin:
        return False
    return bool(allowed_origin(handler))


def csrf_is_valid(handler: SimpleHTTPRequestHandler) -> bool:
    return False


def handler_headers(handler: SimpleHTTPRequestHandler) -> dict[str, str]:
    return {key: value for key, value in handler.headers.items()}


def handler_auth(handler: SimpleHTTPRequestHandler, require_csrf: bool = False, admin: bool = False) -> tuple[dict | None, str | None]:
    return auth_from_headers(handler_headers(handler), require_csrf=require_csrf, admin=admin)


def static_file_path(request_path: str) -> Path | None:
    path = urlparse(request_path).path
    if path in BLOCKED_STATIC_PATHS or path.startswith("/uploaded_templates/"):
        return None
    clean = unquote(path).lstrip("/")
    if clean not in ALLOWED_STATIC_PATHS:
        return None
    candidates = [ROOT / clean] if clean else [ROOT / "index.html", ROOT / "templates" / "index.html"]
    if clean in {"app.js", "styles.css"}:
        candidates.append(ROOT / "static" / clean)
    if clean == "static/app.js":
        candidates.append(ROOT / "app.js")
    if clean == "static/styles.css":
        candidates.append(ROOT / "styles.css")
    if clean == "templates/index.html":
        candidates.append(ROOT / "index.html")

    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved != ROOT and ROOT not in resolved.parents:
            continue
        if resolved.is_dir():
            resolved = resolved / "index.html"
        if resolved.exists():
            return resolved
    return None


class Handler(SimpleHTTPRequestHandler):
    server_version = "ProjeYonetimiLocal/1.0"

    def translate_path(self, path: str) -> str:
        return str(static_file_path(path) or (ROOT / "index.html"))

    def end_headers(self) -> None:
        origin = allowed_origin(self)
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-CSRF-Token")
        for name, value in SECURITY_HEADERS:
            self.send_header(name, value)
        super().end_headers()

    def do_OPTIONS(self) -> None:
        if not is_allowed_host(self.headers.get("Host", "")):
            json_response(self, {"ok": False, "error": "host-blocked"}, 403)
            return
        if not request_origin_is_allowed(self):
            json_response(self, {"ok": False, "error": "origin-blocked"}, 403)
            return
        self.send_response(204)
        self.end_headers()

    def do_GET(self) -> None:
        if not is_allowed_host(self.headers.get("Host", "")):
            json_response(self, {"ok": False, "error": "host-blocked"}, 403)
            return
        path = urlparse(self.path).path
        if path == "/api/health":
            session, _ = handler_auth(self)
            json_response(self, {"ok": True, "authenticated": bool(session)})
            return
        if path == "/api/state":
            session, error = handler_auth(self)
            if error:
                json_response(self, {"ok": False, "error": error}, 401)
                return
            with connect_db() as conn:
                row = conn.execute("SELECT payload_json, updated_at, updated_by, reason FROM app_state WHERE key = ?", (STATE_KEY,)).fetchone()
            payload = sanitize_state_payload(json.loads(row[0])) if row else None
            json_response(self, {"ok": True, "payload": payload, "updatedAt": row[1] if row else None, "updatedBy": row[2] if row else None, "reason": row[3] if row else None})
            return
        if path == "/api/logs":
            session, error = handler_auth(self, admin=True)
            if error:
                json_response(self, {"ok": False, "error": error}, 403 if error == "admin-required" else 401)
                return
            with connect_db() as conn:
                rows = conn.execute("SELECT id, ts, actor, action, detail_json FROM logs ORDER BY id DESC LIMIT 100").fetchall()
            logs = [
                {"id": row[0], "ts": row[1], "actor": row[2], "action": row[3], "detail": json.loads(row[4] or "{}")}
                for row in rows
            ]
            json_response(self, {"ok": True, "logs": logs})
            return
        if path == "/api/snapshots":
            session, error = handler_auth(self, admin=True)
            if error:
                json_response(self, {"ok": False, "error": error}, 403 if error == "admin-required" else 401)
                return
            with connect_db() as conn:
                rows = conn.execute("SELECT id, ts, actor FROM snapshots ORDER BY id DESC LIMIT 50").fetchall()
            json_response(self, {"ok": True, "snapshots": [{"id": row[0], "ts": row[1], "actor": row[2]} for row in rows]})
            return
        if not static_file_path(self.path):
            json_response(self, {"ok": False, "error": "blocked"}, 403)
            return
        return super().do_GET()

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            if not is_allowed_host(self.headers.get("Host", "")):
                json_response(self, {"ok": False, "error": "host-blocked"}, 403)
                return
            client_ip = client_ip_from_headers({"REMOTE_ADDR": self.client_address[0] if self.client_address else ""})
            if not rate_limit_key(client_ip, path, RATE_LIMIT_LOGIN if path == "/api/auth/login" else RATE_LIMIT_DEFAULT):
                json_response(self, {"ok": False, "error": "rate-limit"}, 429)
                return
            if not request_origin_is_allowed(self):
                json_response(self, {"ok": False, "error": "origin-blocked"}, 403)
                return
            payload = read_json(self)
            if path == "/api/auth/login":
                user = find_auth_user(str(payload.get("email", "")), str(payload.get("password", "")))
                if not user:
                    json_response(self, {"ok": False, "error": "auth-required"}, 401)
                    return
                result = create_api_session(user)
                db_log(user["email"], "auth.api.login", {"role": user.get("role", "member")})
                json_response(self, {"ok": True, **result})
                return
            session, error = handler_auth(self, require_csrf=True, admin=path in {"/api/state", "/api/snapshot", "/api/docx/upload"})
            if error:
                json_response(self, {"ok": False, "error": error}, 403 if error in {"admin-required", "csrf-token-invalid"} else 401)
                return
            if path == "/api/log":
                db_log(session["email"], payload.get("action", "unknown"), payload.get("detail", {}))
                json_response(self, {"ok": True})
                return
            if path == "/api/state":
                with connect_db() as conn:
                    conn.execute(
                        """
                        INSERT INTO app_state (key, payload_json, updated_at, updated_by, reason)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(key) DO UPDATE SET
                            payload_json = excluded.payload_json,
                            updated_at = excluded.updated_at,
                            updated_by = excluded.updated_by,
                            reason = excluded.reason
                        """,
                        (
                            STATE_KEY,
                            json.dumps(sanitize_state_payload(payload.get("payload") or {}), ensure_ascii=False),
                            now_iso(),
                            session["email"],
                            payload.get("reason", "manual"),
                        ),
                    )
                db_log(session["email"], "state.saved", {"reason": payload.get("reason", "manual")})
                json_response(self, {"ok": True})
                return
            if path == "/api/snapshot":
                with connect_db() as conn:
                    cursor = conn.execute(
                        "INSERT INTO snapshots (ts, actor, payload_json) VALUES (?, ?, ?)",
                        (now_iso(), session["email"], json.dumps(sanitize_state_payload(payload.get("payload") or {}), ensure_ascii=False)),
                    )
                    snapshot_id = cursor.lastrowid
                db_log(session["email"], "snapshot.created", {"snapshotId": snapshot_id})
                json_response(self, {"ok": True, "snapshotId": snapshot_id})
                return
            if path == "/api/docx/check":
                source = template_path(payload.get("templateId"), payload.get("fileName"))
                ok = bool(source and zipfile.is_zipfile(source))
                json_response(
                    self,
                    {
                        "ok": ok,
                        "fileName": source.name if source else payload.get("fileName"),
                        "sha256": file_sha256(source) if ok and source else "",
                        "source": "uploaded" if source and source.parent == UPLOAD_DIR else "provided",
                    },
                )
                return
            if path == "/api/docx/upload":
                file_name = payload.get("fileName", "")
                if file_name not in KNOWN_TEMPLATES.values():
                    json_response(self, {"ok": False, "error": "unknown-template"}, 400)
                    return
                try:
                    data = base64.b64decode(payload.get("dataBase64", ""), validate=True)
                except (binascii.Error, ValueError):
                    json_response(self, {"ok": False, "error": "invalid-docx"}, 400)
                    return
                valid, validation_error = validate_docx_bytes(data)
                if not valid:
                    json_response(self, {"ok": False, "error": validation_error}, 400)
                    return
                target = UPLOAD_DIR / file_name
                target.write_bytes(data)
                digest = file_sha256(target)
                with connect_db() as conn:
                    conn.execute(
                        "INSERT INTO uploaded_templates (file_name, stored_path, sha256, uploaded_at, uploaded_by) VALUES (?, ?, ?, ?, ?)",
                        (file_name, str(target), digest, now_iso(), session["email"]),
                    )
                db_log(session["email"], "template.uploaded", {"fileName": file_name, "sha256": digest})
                json_response(self, {"ok": True, "sha256": digest})
                return
            if path == "/api/docx/export":
                data, source_name = filled_docx(payload)
                db_log(session["email"], "document.exported", {"template": source_name, "project": payload.get("projectName", "")})
                file_name = f"{payload.get('projectName', 'proje')}-{payload.get('title', 'belge')}.docx"
                safe_name = safe_download_name(file_name)
                self.send_response(200)
                self.send_header("Content-Type", DOCX_MIME)
                self.send_header("Content-Disposition", f'attachment; filename="{safe_name.encode("ascii", "ignore").decode("ascii") or "belge.docx"}"')
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            json_response(self, {"ok": False, "error": "not-found"}, 404)
        except ValueError as exc:
            json_response(self, {"ok": False, "error": safe_error(str(exc))}, 400)
        except Exception as exc:  # Keep local server debuggable for the admin screen.
            db_log("system", "server.error", {"path": path, "type": type(exc).__name__})
            json_response(self, {"ok": False, "error": "internal-error"}, 500)


def wsgi_status(code: int) -> str:
    labels = {
        200: "OK",
        204: "No Content",
        400: "Bad Request",
        403: "Forbidden",
        404: "Not Found",
        405: "Method Not Allowed",
        500: "Internal Server Error",
    }
    return f"{code} {labels.get(code, 'OK')}"


def wsgi_origin(environ: dict) -> str | None:
    origin = environ.get("HTTP_ORIGIN")
    host = environ.get("HTTP_HOST", "")
    return origin if origin in same_host_origins(host) else None


def wsgi_headers(environ: dict, content_type: str, length: int | None = None, extra: list[tuple[str, str]] | None = None) -> list[tuple[str, str]]:
    headers = [("Content-Type", content_type)]
    if length is not None:
        headers.append(("Content-Length", str(length)))
    origin = wsgi_origin(environ)
    if origin:
        headers.extend([("Access-Control-Allow-Origin", origin), ("Vary", "Origin")])
    headers.extend(
        [
            ("Access-Control-Allow-Methods", "GET, POST, OPTIONS"),
            ("Access-Control-Allow-Headers", "Content-Type, X-CSRF-Token"),
        ]
    )
    headers.extend(SECURITY_HEADERS)
    if extra:
        headers.extend(extra)
    return headers


def wsgi_json(environ: dict, start_response, payload: object, status: int = 200):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    start_response(wsgi_status(status), wsgi_headers(environ, JSON_MIME, len(data)))
    return [data]


def wsgi_read_json(environ: dict) -> dict:
    content_type = (environ.get("CONTENT_TYPE") or "").split(";", 1)[0].strip().lower()
    length = parse_content_length(environ.get("CONTENT_LENGTH"))
    if length and content_type != "application/json":
        raise ValueError("content-type-json-required")
    raw = environ["wsgi.input"].read(length) if length else b""
    if not raw:
        return {}
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("json-object-required")
    return payload


def wsgi_origin_is_allowed(environ: dict) -> bool:
    return bool(environ.get("HTTP_ORIGIN")) and bool(wsgi_origin(environ))


def wsgi_csrf_is_valid(environ: dict) -> bool:
    return environ.get("HTTP_X_CSRF_TOKEN") == CSRF_TOKEN


def ensure_wsgi_ready() -> None:
    global _WSGI_READY
    if not _WSGI_READY:
        init_db()
        _WSGI_READY = True


def wsgi_static(environ: dict, start_response, path: str):
    target = static_file_path(path)
    if not target:
        return wsgi_json(environ, start_response, {"ok": False, "error": "blocked"}, 403)
    if not target.exists() or not target.is_file():
        return wsgi_json(environ, start_response, {"ok": False, "error": "not-found"}, 404)
    data = target.read_bytes()
    content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
    start_response(wsgi_status(200), wsgi_headers(environ, content_type, len(data)))
    return [data]


def application(environ, start_response):
    """PythonAnywhere-compatible WSGI entrypoint."""
    ensure_wsgi_ready()
    method = environ.get("REQUEST_METHOD", "GET").upper()
    path = environ.get("PATH_INFO") or "/"
    try:
        if not is_allowed_host(environ.get("HTTP_HOST", "")):
            return wsgi_json(environ, start_response, {"ok": False, "error": "host-blocked"}, 403)
        if method == "OPTIONS":
            if not wsgi_origin_is_allowed(environ):
                return wsgi_json(environ, start_response, {"ok": False, "error": "origin-blocked"}, 403)
            start_response(wsgi_status(204), wsgi_headers(environ, JSON_MIME, 0))
            return [b""]
        if method == "GET":
            if path == "/api/health":
                session, _ = auth_from_headers(environ)
                return wsgi_json(environ, start_response, {"ok": True, "authenticated": bool(session)})
            if path == "/api/state":
                session, error = auth_from_headers(environ)
                if error:
                    return wsgi_json(environ, start_response, {"ok": False, "error": error}, 401)
                with connect_db() as conn:
                    row = conn.execute("SELECT payload_json, updated_at, updated_by, reason FROM app_state WHERE key = ?", (STATE_KEY,)).fetchone()
                payload = sanitize_state_payload(json.loads(row[0])) if row else None
                return wsgi_json(environ, start_response, {"ok": True, "payload": payload, "updatedAt": row[1] if row else None, "updatedBy": row[2] if row else None, "reason": row[3] if row else None})
            if path == "/api/logs":
                session, error = auth_from_headers(environ, admin=True)
                if error:
                    return wsgi_json(environ, start_response, {"ok": False, "error": error}, 403 if error == "admin-required" else 401)
                with connect_db() as conn:
                    rows = conn.execute("SELECT id, ts, actor, action, detail_json FROM logs ORDER BY id DESC LIMIT 100").fetchall()
                logs = [
                    {"id": row[0], "ts": row[1], "actor": row[2], "action": row[3], "detail": json.loads(row[4] or "{}")}
                    for row in rows
                ]
                return wsgi_json(environ, start_response, {"ok": True, "logs": logs})
            if path == "/api/snapshots":
                session, error = auth_from_headers(environ, admin=True)
                if error:
                    return wsgi_json(environ, start_response, {"ok": False, "error": error}, 403 if error == "admin-required" else 401)
                with connect_db() as conn:
                    rows = conn.execute("SELECT id, ts, actor FROM snapshots ORDER BY id DESC LIMIT 50").fetchall()
                return wsgi_json(environ, start_response, {"ok": True, "snapshots": [{"id": row[0], "ts": row[1], "actor": row[2]} for row in rows]})
            return wsgi_static(environ, start_response, path)
        if method == "POST":
            client_ip = client_ip_from_headers(environ)
            if not rate_limit_key(client_ip, path, RATE_LIMIT_LOGIN if path == "/api/auth/login" else RATE_LIMIT_DEFAULT):
                return wsgi_json(environ, start_response, {"ok": False, "error": "rate-limit"}, 429)
            if not wsgi_origin_is_allowed(environ):
                return wsgi_json(environ, start_response, {"ok": False, "error": "origin-blocked"}, 403)
            payload = wsgi_read_json(environ)
            if path == "/api/auth/login":
                user = find_auth_user(str(payload.get("email", "")), str(payload.get("password", "")))
                if not user:
                    return wsgi_json(environ, start_response, {"ok": False, "error": "auth-required"}, 401)
                result = create_api_session(user)
                db_log(user["email"], "auth.api.login", {"role": user.get("role", "member")})
                return wsgi_json(environ, start_response, {"ok": True, **result})
            session, error = auth_from_headers(environ, require_csrf=True, admin=path in {"/api/state", "/api/snapshot", "/api/docx/upload"})
            if error:
                return wsgi_json(environ, start_response, {"ok": False, "error": error}, 403 if error in {"admin-required", "csrf-token-invalid"} else 401)
            if path == "/api/log":
                db_log(session["email"], payload.get("action", "unknown"), payload.get("detail", {}))
                return wsgi_json(environ, start_response, {"ok": True})
            if path == "/api/state":
                with connect_db() as conn:
                    conn.execute(
                        """
                        INSERT INTO app_state (key, payload_json, updated_at, updated_by, reason)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(key) DO UPDATE SET
                            payload_json = excluded.payload_json,
                            updated_at = excluded.updated_at,
                            updated_by = excluded.updated_by,
                            reason = excluded.reason
                        """,
                        (
                            STATE_KEY,
                            json.dumps(sanitize_state_payload(payload.get("payload") or {}), ensure_ascii=False),
                            now_iso(),
                            session["email"],
                            payload.get("reason", "manual"),
                        ),
                    )
                db_log(session["email"], "state.saved", {"reason": payload.get("reason", "manual")})
                return wsgi_json(environ, start_response, {"ok": True})
            if path == "/api/snapshot":
                with connect_db() as conn:
                    cursor = conn.execute(
                        "INSERT INTO snapshots (ts, actor, payload_json) VALUES (?, ?, ?)",
                        (now_iso(), session["email"], json.dumps(sanitize_state_payload(payload.get("payload") or {}), ensure_ascii=False)),
                    )
                    snapshot_id = cursor.lastrowid
                db_log(session["email"], "snapshot.created", {"snapshotId": snapshot_id})
                return wsgi_json(environ, start_response, {"ok": True, "snapshotId": snapshot_id})
            if path == "/api/docx/check":
                source = template_path(payload.get("templateId"), payload.get("fileName"))
                ok = bool(source and zipfile.is_zipfile(source))
                return wsgi_json(
                    environ,
                    start_response,
                    {
                        "ok": ok,
                        "fileName": source.name if source else payload.get("fileName"),
                        "sha256": file_sha256(source) if ok and source else "",
                        "source": "uploaded" if source and source.parent == UPLOAD_DIR else "provided",
                    },
                )
            if path == "/api/docx/upload":
                file_name = payload.get("fileName", "")
                if file_name not in KNOWN_TEMPLATES.values():
                    return wsgi_json(environ, start_response, {"ok": False, "error": "unknown-template"}, 400)
                try:
                    data = base64.b64decode(payload.get("dataBase64", ""), validate=True)
                except (binascii.Error, ValueError):
                    return wsgi_json(environ, start_response, {"ok": False, "error": "invalid-docx"}, 400)
                valid, validation_error = validate_docx_bytes(data)
                if not valid:
                    return wsgi_json(environ, start_response, {"ok": False, "error": validation_error}, 400)
                target = UPLOAD_DIR / file_name
                target.write_bytes(data)
                digest = file_sha256(target)
                with connect_db() as conn:
                    conn.execute(
                        "INSERT INTO uploaded_templates (file_name, stored_path, sha256, uploaded_at, uploaded_by) VALUES (?, ?, ?, ?, ?)",
                        (file_name, str(target), digest, now_iso(), session["email"]),
                    )
                db_log(session["email"], "template.uploaded", {"fileName": file_name, "sha256": digest})
                return wsgi_json(environ, start_response, {"ok": True, "sha256": digest})
            if path == "/api/docx/export":
                data, source_name = filled_docx(payload)
                db_log(session["email"], "document.exported", {"template": source_name, "project": payload.get("projectName", "")})
                file_name = f"{payload.get('projectName', 'proje')}-{payload.get('title', 'belge')}.docx"
                safe_name = safe_download_name(file_name)
                headers = [("Content-Disposition", f'attachment; filename="{safe_name.encode("ascii", "ignore").decode("ascii") or "belge.docx"}"')]
                start_response(wsgi_status(200), wsgi_headers(environ, DOCX_MIME, len(data), headers))
                return [data]
            return wsgi_json(environ, start_response, {"ok": False, "error": "not-found"}, 404)
        return wsgi_json(environ, start_response, {"ok": False, "error": "method-not-allowed"}, 405)
    except ValueError as exc:
        return wsgi_json(environ, start_response, {"ok": False, "error": safe_error(str(exc))}, 400)
    except Exception as exc:
        db_log("system", "server.error", {"path": path, "type": type(exc).__name__})
        return wsgi_json(environ, start_response, {"ok": False, "error": "internal-error"}, 500)


def check_environment() -> int:
    init_db()
    missing = [name for name in KNOWN_TEMPLATES.values() if not (TEMPLATE_DIR / name).exists()]
    print(f"database={DB_PATH}")
    print(f"templates_ok={len(KNOWN_TEMPLATES) - len(missing)}/{len(KNOWN_TEMPLATES)}")
    if missing:
        print("missing_templates=" + ",".join(missing))
        return 1
    print("check=ok")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Proje Yönetimi yerel backend")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        return check_environment()
    init_db()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Proje Yönetimi açıldı: http://{args.host}:{args.port}")
    print("Kapatmak için Ctrl+C")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nKapatıldı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

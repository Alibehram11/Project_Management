from __future__ import annotations

import argparse
import base64
import hashlib
import json
import mimetypes
import secrets
import sqlite3
import sys
import zipfile
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "app_data.sqlite3"
TEMPLATE_DIR = ROOT / "proje_yonetimi_ogrenci_belgeleri_word"
UPLOAD_DIR = ROOT / "uploaded_templates"
STATE_KEY = "main"
MAX_UPLOAD_BYTES = 12 * 1024 * 1024
CSRF_TOKEN = secrets.token_urlsafe(32)

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


def init_db() -> None:
    UPLOAD_DIR.mkdir(exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
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
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO logs (ts, actor, action, detail_json) VALUES (?, ?, ?, ?)",
            (now_iso(), actor or "anonim", action, json.dumps(detail or {}, ensure_ascii=False)),
        )
        conn.execute(
            "DELETE FROM logs WHERE id NOT IN (SELECT id FROM logs ORDER BY id DESC LIMIT 1000)"
        )


def json_response(handler: SimpleHTTPRequestHandler, payload: object, status: int = 200) -> None:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def read_json(handler: SimpleHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length", "0") or "0")
    if length > MAX_UPLOAD_BYTES:
        raise ValueError("İstek çok büyük.")
    raw = handler.rfile.read(length)
    if not raw:
        return {}
    return json.loads(raw.decode("utf-8"))


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


def sanitize_state_payload(payload: object) -> object:
    if not isinstance(payload, dict):
        return {}
    clean = dict(payload)
    users = clean.get("users")
    if isinstance(users, list):
        clean["users"] = [
            {key: value for key, value in user.items() if key != "password"}
            for user in users
            if isinstance(user, dict)
        ]
    return clean


def allowed_origin(handler: SimpleHTTPRequestHandler) -> str | None:
    host = handler.headers.get("Host", "")
    return f"http://{host}" if host else None


def request_origin_is_allowed(handler: SimpleHTTPRequestHandler) -> bool:
    origin = handler.headers.get("Origin")
    if not origin:
        return True
    return origin == allowed_origin(handler)


def csrf_is_valid(handler: SimpleHTTPRequestHandler) -> bool:
    return handler.headers.get("X-CSRF-Token") == CSRF_TOKEN


class Handler(SimpleHTTPRequestHandler):
    server_version = "ProjeYonetimiLocal/1.0"

    def translate_path(self, path: str) -> str:
        parsed = urlparse(path)
        clean = unquote(parsed.path).lstrip("/")
        if not clean:
            clean = "index.html"
        return str((ROOT / clean).resolve())

    def end_headers(self) -> None:
        origin = self.headers.get("Origin")
        if origin and origin == allowed_origin(self):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-CSRF-Token")
        super().end_headers()

    def do_OPTIONS(self) -> None:
        if not request_origin_is_allowed(self):
            json_response(self, {"ok": False, "error": "origin-blocked"}, 403)
            return
        self.send_response(204)
        self.end_headers()

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        blocked = {"/app_data.sqlite3", "/server.py"}
        if path in blocked or path.startswith("/uploaded_templates/"):
            json_response(self, {"ok": False, "error": "blocked"}, 403)
            return
        if path == "/api/health":
            json_response(self, {"ok": True, "database": DB_PATH.name, "templateCount": len(KNOWN_TEMPLATES), "csrfToken": CSRF_TOKEN})
            return
        if path == "/api/state":
            with sqlite3.connect(DB_PATH) as conn:
                row = conn.execute("SELECT payload_json, updated_at, updated_by, reason FROM app_state WHERE key = ?", (STATE_KEY,)).fetchone()
            payload = sanitize_state_payload(json.loads(row[0])) if row else None
            json_response(self, {"ok": True, "payload": payload, "updatedAt": row[1] if row else None, "updatedBy": row[2] if row else None, "reason": row[3] if row else None})
            return
        if path == "/api/logs":
            with sqlite3.connect(DB_PATH) as conn:
                rows = conn.execute("SELECT id, ts, actor, action, detail_json FROM logs ORDER BY id DESC LIMIT 100").fetchall()
            logs = [
                {"id": row[0], "ts": row[1], "actor": row[2], "action": row[3], "detail": json.loads(row[4] or "{}")}
                for row in rows
            ]
            json_response(self, {"ok": True, "logs": logs})
            return
        if path == "/api/snapshots":
            with sqlite3.connect(DB_PATH) as conn:
                rows = conn.execute("SELECT id, ts, actor FROM snapshots ORDER BY id DESC LIMIT 50").fetchall()
            json_response(self, {"ok": True, "snapshots": [{"id": row[0], "ts": row[1], "actor": row[2]} for row in rows]})
            return
        return super().do_GET()

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            if not request_origin_is_allowed(self):
                json_response(self, {"ok": False, "error": "origin-blocked"}, 403)
                return
            if not csrf_is_valid(self):
                json_response(self, {"ok": False, "error": "csrf-token-invalid"}, 403)
                return
            payload = read_json(self)
            if path == "/api/log":
                db_log(payload.get("actor", "anonim"), payload.get("action", "unknown"), payload.get("detail", {}))
                json_response(self, {"ok": True})
                return
            if path == "/api/state":
                with sqlite3.connect(DB_PATH) as conn:
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
                            payload.get("actor", "anonim"),
                            payload.get("reason", "manual"),
                        ),
                    )
                db_log(payload.get("actor", "anonim"), "state.saved", {"reason": payload.get("reason", "manual")})
                json_response(self, {"ok": True})
                return
            if path == "/api/snapshot":
                with sqlite3.connect(DB_PATH) as conn:
                    cursor = conn.execute(
                        "INSERT INTO snapshots (ts, actor, payload_json) VALUES (?, ?, ?)",
                        (now_iso(), payload.get("actor", "anonim"), json.dumps(sanitize_state_payload(payload.get("payload") or {}), ensure_ascii=False)),
                    )
                    snapshot_id = cursor.lastrowid
                db_log(payload.get("actor", "anonim"), "snapshot.created", {"snapshotId": snapshot_id})
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
                data = base64.b64decode(payload.get("dataBase64", ""), validate=True)
                if len(data) > MAX_UPLOAD_BYTES:
                    json_response(self, {"ok": False, "error": "file-too-large"}, 400)
                    return
                target = UPLOAD_DIR / file_name
                target.write_bytes(data)
                if not zipfile.is_zipfile(target):
                    target.unlink(missing_ok=True)
                    json_response(self, {"ok": False, "error": "invalid-docx"}, 400)
                    return
                digest = file_sha256(target)
                with sqlite3.connect(DB_PATH) as conn:
                    conn.execute(
                        "INSERT INTO uploaded_templates (file_name, stored_path, sha256, uploaded_at, uploaded_by) VALUES (?, ?, ?, ?, ?)",
                        (file_name, str(target), digest, now_iso(), payload.get("actor", "anonim")),
                    )
                db_log(payload.get("actor", "anonim"), "template.uploaded", {"fileName": file_name, "sha256": digest})
                json_response(self, {"ok": True, "sha256": digest})
                return
            if path == "/api/docx/export":
                data, source_name = filled_docx(payload)
                db_log(payload.get("actor", "anonim"), "document.exported", {"template": source_name, "project": payload.get("projectName", "")})
                file_name = f"{payload.get('projectName', 'proje')}-{payload.get('title', 'belge')}.docx"
                safe_name = "".join("-" if char in '\\/:*?"<>|' else char for char in file_name)
                self.send_response(200)
                self.send_header("Content-Type", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
                self.send_header("Content-Disposition", f'attachment; filename="{safe_name.encode("ascii", "ignore").decode("ascii") or "belge.docx"}"')
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            json_response(self, {"ok": False, "error": "not-found"}, 404)
        except Exception as exc:  # Keep local server debuggable for the admin screen.
            json_response(self, {"ok": False, "error": str(exc)}, 500)


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

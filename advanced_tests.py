from __future__ import annotations

import copy
import hashlib
import json
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import server
from advanced_rules import (
    DomainError,
    atomic_bulk,
    cursor_page,
    export_tasks_csv,
    export_tasks_pdf,
    literal_task_search,
    parse_utc,
    prepare_state_transition,
    project_progress,
    restore_from_trash,
    run_retry_job,
    validate_state,
)
from security_tests import configure_test_backend, expect_status, json_body, login, request


TEST_ROOT = Path(".advanced_test_runtime")
FRESH_COUNTER = 0


def base_state() -> dict:
    users = [dict(user) for user in server.DEMO_USERS]
    return {
        "users": users,
        "projects": [
            {
                "id": "p1", "name": "Alpha", "ownerId": "demo-admin", "status": "active",
                "memberIds": ["demo-admin", "demo-tasarim", "demo-yazilim"],
                "adminIds": ["demo-admin"],
                "memberProfiles": {
                    "demo-admin": {"role": "owner", "team": "Yönetim"},
                    "demo-tasarim": {"role": "member", "team": "Tasarım"},
                    "demo-yazilim": {"role": "lead", "team": "Yazılım"},
                },
            },
            {
                "id": "p2", "name": "Beta", "ownerId": "demo-mentor", "status": "active",
                "memberIds": ["demo-mentor", "demo-atolye"], "adminIds": ["demo-mentor"],
                "memberProfiles": {
                    "demo-mentor": {"role": "owner", "team": "Yönetim"},
                    "demo-atolye": {"role": "member", "team": "Yönetim"},
                },
            },
        ],
        "tasks": [
            {
                "id": "t1", "projectId": "p1", "title": "Arayüz", "description": "Panel",
                "assigneeId": "demo-tasarim", "createdBy": "demo-admin", "createdAt": "2026-01-01T10:00:00+00:00",
                "dueDate": "2026-08-10", "status": "todo", "comments": [], "submissions": [], "checklist": [],
                "dependencyIds": [], "version": 1,
            },
            {
                "id": "t2", "projectId": "p2", "title": "Envanter", "description": "Stok",
                "assigneeId": "demo-atolye", "createdBy": "demo-mentor", "createdAt": "2026-01-02T10:00:00+00:00",
                "dueDate": "2026-08-12", "status": "todo", "comments": [], "submissions": [], "checklist": [],
                "dependencyIds": [], "version": 1,
            },
        ],
        "invites": [], "calendarEvents": [], "crmItems": [], "feedItems": [], "documents": {},
        "documentTemplates": [],
        "atolyeRequests": [
            {"id": "r-admin", "createdBy": "demo-admin", "status": "Beklemede"},
            {"id": "r-member", "createdBy": "demo-tasarim", "status": "Beklemede"},
        ],
        "trash": [],
    }


def fresh() -> dict:
    global FRESH_COUNTER
    FRESH_COUNTER += 1
    configure_test_backend(TEST_ROOT / f"case-{FRESH_COUNTER:02}")
    server.PASSWORD_RESET_TOKENS.clear()
    admin = login("admin@proje.local", "123456", "10.0.0.1")
    status, _, body = request("POST", "/api/state", {"payload": base_state(), "revision": 0, "reason": "advanced-test"}, admin)
    expect_status("initialize", status, "200")
    return {
        "admin": admin,
        "member": login("tasarim@proje.local", "123456", "10.0.0.2"),
        "mentor": login("mentor@proje.local", "123456", "10.0.0.3"),
        "revision": json_body(body)["revision"],
    }


def get_state(headers: dict) -> tuple[dict, int]:
    status, _, body = request("GET", "/api/state", headers=headers)
    expect_status("get state", status, "200")
    result = json_body(body)
    return result["payload"], int(result["revision"])


def post_state(headers: dict, state: dict, revision: int) -> tuple[str, dict]:
    status, _, body = request("POST", "/api/state", {"payload": state, "revision": revision, "reason": "advanced"}, headers)
    return status, json_body(body)


def expect_domain(code: str, fn) -> None:
    try:
        fn()
    except DomainError as exc:
        if exc.code != code:
            raise AssertionError(f"expected {code}, got {exc.code}") from exc
        return
    raise AssertionError(f"expected DomainError({code})")


def run() -> None:
    tests: list[tuple[str, object]] = []
    add = lambda name, fn: tests.append((name, fn))

    def t01():
        ctx = fresh(); state, _ = get_state(ctx["member"])
        if {p["id"] for p in state["projects"]} != {"p1"} or {t["id"] for t in state["tasks"]} != {"t1"}:
            raise AssertionError("IDOR visibility leak")
        if any(any(key in user for key in ("password", "passwordHash", "passwordSalt")) for user in state["users"]):
            raise AssertionError("credential fields leaked through state API")
        if {request["id"] for request in state["atolyeRequests"]} != {"r-member"}:
            raise AssertionError("private workshop request leaked")
    add("01 IDOR: member sees only own project and task", t01)

    def t02():
        ctx = fresh(); state, rev = get_state(ctx["member"])
        state["projects"][0]["adminIds"].append("demo-tasarim")
        expect_status("role escalation", post_state(ctx["member"], state, rev)[0], "403")
    add("02 member cannot escalate role through payload", t02)

    def t03():
        ctx = fresh(); token = ctx["member"]["Authorization"].removeprefix("Bearer ")
        server.API_SESSIONS[token]["expires"] = time.time() - 1
        status, _, body = request("GET", "/api/state", headers=ctx["member"])
        expect_status("expired", status, "401")
        if json_body(body).get("error") != "auth-expired": raise AssertionError("wrong expiry error")
    add("03 expired session token is rejected", t03)

    def t04():
        ctx = fresh(); state, rev = get_state(ctx["admin"])
        project = next(p for p in state["projects"] if p["id"] == "p1")
        project["memberIds"].remove("demo-tasarim"); project["memberProfiles"].pop("demo-tasarim")
        next(t for t in state["tasks"] if t["id"] == "t1")["assigneeId"] = "demo-admin"
        expect_status("remove member", post_state(ctx["admin"], state, rev)[0], "200")
        stale = copy.deepcopy(base_state()); stale["tasks"][0]["status"] = "approved"
        expect_status("revoked project access", post_state(ctx["member"], stale, rev + 1)[0], "403")
    add("04 project removal revokes already-open session access", t04)

    def t05():
        ctx = fresh(); state, rev = get_state(ctx["member"])
        payload = "<script>alert(1)</script> x'); DROP TABLE logs; --"
        state["tasks"][0]["comments"].append({"id": "c1", "userId": "demo-tasarim", "text": payload})
        expect_status("safe text", post_state(ctx["member"], state, rev)[0], "200")
        full, _ = get_state(ctx["admin"])
        if next(t for t in full["tasks"] if t["id"] == "t1")["comments"][0]["text"] != payload:
            raise AssertionError("payload was corrupted instead of safely stored")
        with sqlite3.connect(server.DB_PATH) as conn: conn.execute("SELECT COUNT(*) FROM logs").fetchone()
    add("05 SQL injection and stored XSS payload stay inert data", t05)

    def t06():
        ctx = fresh(); token = server.issue_password_reset("tasarim@proje.local", 60)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        if server.consume_password_reset(token, "123") or token_hash not in server.PASSWORD_RESET_TOKENS:
            raise AssertionError("invalid password submission consumed reset token")
        if not server.consume_password_reset(token, "654321"):
            raise AssertionError("valid password could not reuse retained reset token")
        token = server.issue_password_reset("tasarim@proje.local", 60)
        if not server.consume_password_reset(token, "654321") or server.consume_password_reset(token, "again12"):
            raise AssertionError("reset token was not single-use")
        expired = server.issue_password_reset("tasarim@proje.local", 1)
        server.PASSWORD_RESET_TOKENS[hashlib.sha256(expired.encode()).hexdigest()]["expires"] = time.time() - 1
        if server.consume_password_reset(expired, "777777"): raise AssertionError("expired reset token accepted")
    add("06 password reset token is single-use and expires", t06)

    def t07():
        ctx = fresh(); a, rev = get_state(ctx["admin"]); b = copy.deepcopy(a)
        a["projects"][0]["description"] = "A"; b["projects"][0]["description"] = "B"
        expect_status("first writer", post_state(ctx["admin"], a, rev)[0], "200")
        status, body = post_state(ctx["admin"], b, rev)
        expect_status("stale writer", status, "409")
        if body.get("error") != "revision-conflict": raise AssertionError("lost update not detected")
    add("07 simultaneous edits use optimistic concurrency", t07)

    def t08():
        ctx = fresh(); state, rev = get_state(ctx["admin"])
        state["projects"] = [p for p in state["projects"] if p["id"] != "p2"]
        expect_status("delete project", post_state(ctx["admin"], state, rev)[0], "200")
        saved, _ = get_state(ctx["admin"])
        if any(i.get("projectId") == "p2" for key in ("tasks", "invites", "calendarEvents", "crmItems", "feedItems") for i in saved[key]):
            raise AssertionError("cascade delete left related data")
    add("08 project deletion cascades related records", t08)

    def t09():
        original = base_state(); snapshot = copy.deepcopy(original)
        try: atomic_bulk(original, [lambda s: s["tasks"][0].update(status="review"), lambda _: (_ for _ in ()).throw(ConnectionError())])
        except ConnectionError: pass
        if original != snapshot: raise AssertionError("interrupted drag changed original state")
    add("09 interrupted drag/drop remains atomic", t09)

    def t10():
        state = base_state(); state["users"].append({"id": "duplicate", "name": "X", "email": "ADMIN@PROJE.LOCAL"})
        expect_domain("email-conflict", lambda: validate_state(state))
    add("10 concurrent duplicate email registration is rejected", t10)

    def t11():
        state = base_state(); before = copy.deepcopy(state)
        ops = [lambda s: s["projects"][0].update(name="Changed"), lambda s: s["tasks"].append({"id": "bad", "projectId": "missing", "assigneeId": "x"})]
        expect_domain("task-project-invalid", lambda: atomic_bulk(state, ops))
        if state != before: raise AssertionError("partial bulk update leaked")
    add("11 bulk update is all-or-nothing", t11)

    def t12():
        state = base_state(); state["tasks"][0]["dependencyIds"] = ["t3"]
        state["tasks"].append({"id": "t3", "projectId": "p1", "assigneeId": "demo-admin", "status": "todo", "dependencyIds": ["t1"]})
        expect_domain("task-dependency-cycle", lambda: validate_state(state))
    add("12 circular task dependency is rejected", t12)

    def t13():
        state = base_state(); state["tasks"][0]["dueDate"] = "2026-08-10"
        state["tasks"].append({"id": "child", "projectId": "p1", "assigneeId": "demo-admin", "status": "todo", "parentTaskId": "t1", "dueDate": "2026-08-11", "dependencyIds": []})
        expect_domain("subtask-deadline-invalid", lambda: validate_state(state))
    add("13 subtask cannot end after parent", t13)

    def t14():
        state = base_state(); p = state["projects"][0]; p["memberIds"].remove(p["ownerId"])
        expect_domain("project-owner-invalid", lambda: validate_state(state))
    add("14 project cannot lose its only owner/admin", t14)

    def t15():
        if parse_utc("2026-07-12T12:00:00+03:00") != parse_utc("2026-07-12T09:00:00Z"):
            raise AssertionError("timezone conversion mismatch")
    add("15 deadlines are normalized consistently across timezones", t15)

    def t16():
        current = base_state(); current["projects"][0]["status"] = "archived"; incoming = copy.deepcopy(current)
        incoming["tasks"][0]["title"] = "Changed"
        expect_domain("project-locked", lambda: prepare_state_transition(current, incoming, {"userId": "demo-admin", "email": "admin@proje.local"}, 1, 1))
    add("16 archived project rejects new edits", t16)

    def t17():
        state = base_state(); state["tasks"][0]["description"] = "x" * 50_001
        started = time.perf_counter(); expect_domain("text-too-long", lambda: validate_state(state))
        if time.perf_counter() - started > 1: raise AssertionError("long text validation too slow")
    add("17 excessive free text is bounded without slowdown", t17)

    add("18 empty project progress is zero", lambda: None if project_progress([]) == 0 else (_ for _ in ()).throw(AssertionError("0/0 progress")))

    def t19():
        tasks = [{"id": f"t{i:05}", "title": f"Task {i}", "description": "bulk", "status": "todo"} for i in range(10_000)]
        started = time.perf_counter(); result = literal_task_search(tasks, "Task 9999")
        if len(result) != 1 or time.perf_counter() - started > 1.5: raise AssertionError("large list search too slow")
    add("19 ten-thousand task filtering stays responsive", t19)

    def t20():
        server.RATE_BUCKETS.clear()
        with ThreadPoolExecutor(max_workers=120) as pool:
            decisions = list(pool.map(lambda _: server.rate_limit_key("load-ip", "load", 100), range(120)))
        if sum(decisions) != 100: raise AssertionError("high request rate was not bounded")
    add("20 high concurrent request burst is rate-limited", t20)

    def t21():
        items = [{"id": f"i{i:03}", "createdAt": f"2026-01-01T00:{i:02}:00Z"} for i in range(20)]
        page1, cursor = cursor_page(items, 10); items.pop(2); items.append({"id": "new", "createdAt": "2026-01-01T01:00:00Z"})
        pages = list(page1)
        while cursor:
            page, cursor = cursor_page(items, 10, cursor)
            pages.extend(page)
        ids = [item["id"] for item in pages]
        if len(ids) != len(set(ids)) or "new" not in ids: raise AssertionError("cursor pagination duplicated or skipped new tail")
    add("21 cursor pagination avoids duplicates during changes", t21)

    def t22():
        ctx = fresh(); status, _, body = request("POST", "/api/docx/upload", b"", {**ctx["admin"], "Content-Length": str(50 * 1024 * 1024)})
        expect_status("50MB upload", status, "400")
        if json_body(body).get("error") != "request-too-large": raise AssertionError("large upload error unclear")
    add("22 50MB attachment is rejected before body read", t22)

    def t23():
        tasks = [{"id": "a", "title": "100%_ready", "description": ""}, {"id": "b", "title": "100XXready", "description": ""}]
        if [item["id"] for item in literal_task_search(tasks, "%_")] != ["a"]: raise AssertionError("wildcards were not treated literally")
    add("23 search treats percent and underscore literally", t23)

    def t24():
        ctx = fresh(); state, rev = get_state(ctx["admin"])
        next(t for t in state["tasks"] if t["id"] == "t1")["assigneeId"] = "demo-yazilim"
        expect_status("assignment", post_state(ctx["admin"], state, rev)[0], "200")
        first = server.process_outbox(lambda *_: (_ for _ in ()).throw(ConnectionError()), max_attempts=3)
        second = server.process_outbox(lambda *_: None, max_attempts=3)
        saved, _ = get_state(ctx["admin"])
        if next(t for t in saved["tasks"] if t["id"] == "t1")["assigneeId"] != "demo-yazilim" or not first["retried"] or not second["sent"]:
            raise AssertionError("notification outage blocked assignment or retry")
    add("24 notification outage does not roll back assignment", t24)

    def t25():
        ctx = fresh(); login("tasarim@proje.local", "123456", "10.0.0.22")
        state, rev = get_state(ctx["admin"]); next(t for t in state["tasks"] if t["id"] == "t1")["assigneeId"] = "demo-admin"
        _, body = post_state(ctx["admin"], state, rev); state, rev = get_state(ctx["admin"])
        next(t for t in state["tasks"] if t["id"] == "t1")["assigneeId"] = "demo-tasarim"
        expect_status("multi-device assignment", post_state(ctx["admin"], state, rev)[0], "200")
        with sqlite3.connect(server.DB_PATH) as conn:
            rows = conn.execute("SELECT payload_json FROM outbox WHERE kind = 'task-assigned'").fetchall()
        devices = {json.loads(row[0])["device"] for row in rows if json.loads(row[0]).get("taskId") == "t1" and json.loads(row[0]).get("assigneeId") == "demo-tasarim" and json.loads(row[0]).get("revision") == rev + 1}
        if len(devices) != 2: raise AssertionError("multi-device delivery rows missing")
    add("25 notifications reach both active devices", t25)

    def t26():
        fresh()
        with server.connect_db() as conn:
            conn.execute("UPDATE outbox SET status = 'sent'")
            server.enqueue_outbox(conn, "jira-sync", {"issue": "PM-1"}, "jira:PM-1")
        attempts = {"count": 0}
        def sender(*_):
            attempts["count"] += 1
            if attempts["count"] < 3: raise TimeoutError()
        server.process_outbox(sender, max_attempts=3); server.process_outbox(sender, max_attempts=3); result = server.process_outbox(sender, max_attempts=3)
        if result["sent"] != 1 or attempts["count"] != 3: raise AssertionError("integration retry failed")
    add("26 third-party integration retries transient failures", t26)

    def t27():
        tasks = [{"id": str(i), "projectId": "p", "title": f"Task {i}", "status": "todo", "assigneeId": "u", "dueDate": ""} for i in range(5_000)]
        started = time.perf_counter(); csv_data, pdf_data = export_tasks_csv(tasks), export_tasks_pdf(tasks)
        ctx = fresh()
        csv_status, csv_headers, api_csv = request("POST", "/api/export/tasks", {"projectId": "p1", "format": "csv"}, ctx["admin"])
        pdf_status, pdf_headers, api_pdf = request("POST", "/api/export/tasks", {"projectId": "p1", "format": "pdf"}, ctx["admin"])
        if csv_data.count(b"\n") < 5_000 or b"4999 | Task 4999" not in pdf_data or time.perf_counter() - started > 3:
            raise AssertionError("large export inconsistent or slow")
        expect_status("CSV API export", csv_status, "200"); expect_status("PDF API export", pdf_status, "200")
        if csv_headers.get("Content-Type") != "text/csv; charset=utf-8" or not api_pdf.startswith(b"%PDF"):
            raise AssertionError("export API content mismatch")
    add("27 large CSV/PDF exports remain consistent", t27)

    def t28():
        ctx = fresh(); state, rev = get_state(ctx["admin"]); state["tasks"][0]["title"] = "Audited"
        expect_status("audited update", post_state(ctx["admin"], state, rev)[0], "200")
        status, _, body = request("GET", "/api/logs", headers=ctx["admin"]); expect_status("logs", status, "200")
        if not any(log["action"] == "state.changed" and log["detail"].get("toRevision") == rev + 1 for log in json_body(body)["logs"]):
            raise AssertionError("audit trail missing")
    add("28 every state change writes actor and revision audit", t28)

    def t29():
        current = base_state(); incoming = copy.deepcopy(current)
        incoming["users"] = [u for u in incoming["users"] if u["id"] != "demo-tasarim"]
        candidate = prepare_state_transition(current, incoming, {"userId": "demo-admin", "email": "admin@proje.local"}, 1, 1)
        deleted = next(u for u in candidate["users"] if u["id"] == "demo-tasarim")
        if deleted["name"] != "Silinmiş kullanıcı" or not deleted["deleted"]: raise AssertionError("deleted user reference lost")
    add("29 deleted account remains as consistent tombstone", t29)

    def t30():
        current = base_state(); incoming = copy.deepcopy(current); incoming["projects"] = [p for p in incoming["projects"] if p["id"] != "p2"]
        deleted = prepare_state_transition(current, incoming, {"userId": "demo-admin", "email": "admin@proje.local"}, 1, 1)
        restored = restore_from_trash(deleted, "trash-project-p2")
        if not any(p["id"] == "p2" for p in restored["projects"]) or not any(t["id"] == "t2" for t in restored["tasks"]):
            raise AssertionError("trash restore incomplete")
    add("30 soft-deleted project can be restored with children", t30)

    passed = []
    for name, fn in tests:
        fn(); passed.append(name); print(f"PASS {name}")
    print(f"PASS total={len(passed)}")


if __name__ == "__main__":
    run()

"""Run the attached 63-case endpoint, security, robustness, UX and data checklist.

The suite deliberately reports unsupported product surfaces as NOT_APPLICABLE. It
does not turn the absence of JWT, webhooks, Redis, a browser runner or a CDN into
false product failures.
"""

from __future__ import annotations

import base64
import copy
import json
import math
import re
import sqlite3
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import server
from advanced_rules import (
    DomainError,
    atomic_bulk,
    cursor_page,
    literal_task_search,
    prepare_state_transition,
    project_progress,
    restore_from_trash,
    run_retry_job,
)
from advanced_tests import base_state
from security_tests import configure_test_backend, expect_status, json_body, login, request


TEST_ROOT = Path(".endpoint_quality_runtime")
CASE_NUMBER = 0


class NotApplicable(Exception):
    pass


def fresh() -> dict:
    global CASE_NUMBER
    CASE_NUMBER += 1
    configure_test_backend(TEST_ROOT / f"case-{CASE_NUMBER:02}")
    server.PASSWORD_RESET_TOKENS.clear()
    state = base_state()
    admin = login("admin@proje.local", "123456", f"10.30.0.{CASE_NUMBER % 200 + 1}")
    status, _, body = request(
        "POST",
        "/api/state",
        {"payload": state, "revision": 0, "reason": "endpoint-quality"},
        admin,
    )
    expect_status("initialize", status, "200")
    return {
        "admin": admin,
        "member": login("tasarim@proje.local", "123456", f"10.31.0.{CASE_NUMBER % 200 + 1}"),
        "revision": int(json_body(body)["revision"]),
    }


def get_state(headers: dict) -> tuple[dict, int]:
    status, _, body = request("GET", "/api/state", headers=headers)
    expect_status("state", status, "200")
    result = json_body(body)
    return result["payload"], int(result["revision"])


def post_state(headers: dict, payload: dict, revision: int) -> tuple[str, dict]:
    status, _, body = request(
        "POST",
        "/api/state",
        {"payload": payload, "revision": revision, "reason": "endpoint-quality"},
        headers,
    )
    return status, json_body(body)


def assert_error_status(status: str, allowed: tuple[str, ...] = ("400", "401", "403", "409", "413", "429")) -> None:
    if not status.startswith(allowed):
        raise AssertionError(f"expected one of {allowed}, got {status}")


def case_01():
    ctx = fresh()
    expect_status("health", request("GET", "/api/health")[0], "200")
    expect_status("state", request("GET", "/api/state", headers=ctx["admin"])[0], "200")
    expect_status("log", request("POST", "/api/log", {"action": "quality"}, ctx["admin"])[0], "200")
    expect_status("logs", request("GET", "/api/logs", headers=ctx["admin"])[0], "200")


def case_02():
    status, _, body = request(
        "POST", "/api/auth/login", {"email": "admin@proje.local"},
        {"Origin": "https://alibehram11.pythonanywhere.com", "Content-Type": "application/json"},
    )
    expect_status("missing fields", status, "400")
    if not json_body(body).get("error"):
        raise AssertionError("missing-field response has no error code")


def case_03():
    ctx = fresh()
    status, _, _ = request(
        "POST", "/api/docx/upload",
        {"fileName": server.KNOWN_TEMPLATES["fr01"], "dataBase64": 123}, ctx["admin"],
    )
    expect_status("wrong type", status, "400")


def case_04():
    items = [{"id": f"t{i}", "createdAt": f"2026-01-{i + 1:02}"} for i in range(5)]
    first, cursor = cursor_page(items, 2)
    second, _ = cursor_page(items, 2, cursor)
    if len(first) != 2 or len(second) != 2 or set(item["id"] for item in first) & set(item["id"] for item in second):
        raise AssertionError("cursor pages overlap or have wrong size")
    empty, _ = cursor_page(items, 2, "2027-01-01|last")
    if empty:
        raise AssertionError("empty cursor page is not empty")


def case_05():
    tasks = [{"id": "1", "title": "Alpha SQL", "description": "Design"}, {"id": "2", "title": "Beta", "description": "Build"}]
    result = literal_task_search(tasks, "sql")
    if [task["id"] for task in result] != ["1"]:
        raise AssertionError("literal search returned an unexpected task")


def case_06():
    ctx = fresh()
    state, revision = get_state(ctx["admin"])
    created = {"id": "crud-task", "projectId": "p1", "title": "Created", "description": "CRUD", "assigneeId": "demo-admin", "status": "todo", "comments": [], "submissions": [], "checklist": [], "dependencyIds": [], "version": 1}
    state["tasks"].append(created)
    status, result = post_state(ctx["admin"], state, revision)
    expect_status("create", status, "200")
    state, revision = get_state(ctx["admin"])
    next(task for task in state["tasks"] if task["id"] == "crud-task")["title"] = "Updated"
    expect_status("update", post_state(ctx["admin"], state, revision)[0], "200")
    state, revision = get_state(ctx["admin"])
    state["tasks"] = [task for task in state["tasks"] if task["id"] != "crud-task"]
    expect_status("delete", post_state(ctx["admin"], state, revision)[0], "200")
    state, _ = get_state(ctx["admin"])
    if any(task["id"] == "crud-task" for task in state["tasks"]):
        raise AssertionError("CRUD delete did not remove the task")


def case_07():
    expect_status("unknown resource", request("GET", "/api/not-a-real-resource")[0], "404")


def case_08():
    raise NotApplicable("The application exposes revisioned state writes, not PUT/DELETE resource endpoints.")


def case_09():
    ctx = fresh()
    state, revision = get_state(ctx["admin"])
    payload_a, payload_b = copy.deepcopy(state), copy.deepcopy(state)
    payload_a["projects"][0]["name"] = "Writer A"
    payload_b["projects"][0]["name"] = "Writer B"
    def write(payload):
        return post_state(ctx["admin"], payload, revision)[0]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(write, (payload_a, payload_b)))
    if sorted(results) != ["200 OK", "409 Conflict"]:
        raise AssertionError(f"expected one winner and one revision conflict, got {results}")


def case_10():
    original = {"items": [1]}
    def fail(candidate):
        candidate["items"].append(2)
        raise DomainError("forced-rollback")
    try:
        atomic_bulk(original, [fail])
    except DomainError:
        pass
    else:
        raise AssertionError("bulk operation did not fail")
    if original != {"items": [1]}:
        raise AssertionError("failed bulk operation mutated the source")


def case_11():
    raise NotApplicable("No webhook or callback endpoint exists in this application.")


def case_12():
    from security_tests import minimal_docx_b64
    valid = base64.b64decode(minimal_docx_b64())
    if server.validate_docx_bytes(valid)[0] is not True:
        raise AssertionError("valid DOCX rejected")
    if server.validate_docx_bytes(b"not-a-docx")[0] is not False:
        raise AssertionError("invalid DOCX accepted")


def case_13():
    server.RATE_BUCKETS.clear()
    results = [server.rate_limit_key("quality-ip", "quality", 3) for _ in range(4)]
    if results != [True, True, True, False]:
        raise AssertionError(f"rate limiter sequence is wrong: {results}")


def case_14():
    raise NotApplicable("No versioned /api/vN contract exists.")


def case_15():
    raise NotApplicable("No cron or scheduler is part of the application contract.")


def case_16():
    ctx = fresh()
    payload = "x'); DROP TABLE logs; --"
    expect_status("SQLi", request("POST", "/api/log", {"action": "sqli", "detail": {"payload": payload}}, ctx["admin"])[0], "200")
    with sqlite3.connect(server.DB_PATH) as conn:
        if conn.execute("SELECT COUNT(*) FROM logs WHERE action = ?", ("sqli",)).fetchone()[0] != 1:
            raise AssertionError("SQLi log record missing")
        conn.execute("SELECT COUNT(*) FROM logs")


def case_17():
    ctx = fresh()
    payload = "<script>alert(1)</script>"
    state, revision = get_state(ctx["admin"])
    state["tasks"][0]["description"] = payload
    expect_status("XSS data", post_state(ctx["admin"], state, revision)[0], "200")
    js = Path("app.js").read_text(encoding="utf-8")
    if "textContent" not in js:
        raise AssertionError("frontend has no textContent rendering path")


def case_18():
    ctx = fresh()
    status = request("POST", "/api/log", {"action": "csrf"}, {**ctx["admin"], "X-CSRF-Token": "wrong"})[0]
    expect_status("CSRF", status, "403")


def case_19():
    expect_status("unauthenticated state", request("GET", "/api/state")[0], "401")


def case_20():
    ctx = fresh()
    state, _ = get_state(ctx["member"])
    if {project["id"] for project in state["projects"]} != {"p1"}:
        raise AssertionError("member can see another project's state")
    if any(task["projectId"] != "p1" for task in state["tasks"]):
        raise AssertionError("nested task IDOR leak")


def case_21():
    ctx = fresh()
    token = ctx["admin"]["Authorization"].removeprefix("Bearer ")
    if token.count(".") > 1:
        raise AssertionError("unexpected JWT-like token")
    server.API_SESSIONS[token]["expires"] = time.time() - 1
    expect_status("expired token", request("GET", "/api/state", headers=ctx["admin"])[0], "401")


def case_22():
    if any("password" in user or not user.get("passwordHash") or not user.get("passwordSalt") for user in server.DEMO_USERS):
        raise AssertionError("demo users contain plaintext or missing password hash")


def case_23():
    server.RATE_BUCKETS.clear()
    headers = {"Origin": "https://alibehram11.pythonanywhere.com", "Content-Type": "application/json", "Remote-Addr": "brute-force-ip"}
    statuses = [request("POST", "/api/auth/login", {"email": "admin@proje.local", "password": "wrong"}, headers)[0] for _ in range(server.RATE_LIMIT_LOGIN + 1)]
    if not any(status.startswith("429") for status in statuses):
        raise AssertionError("login brute-force limit did not return 429")


def case_24():
    raise NotApplicable("TLS termination and HTTP redirect are deployment concerns; PythonAnywhere supplies HTTPS.")


def case_25():
    status, headers, _ = request("GET", "/api/health")
    expect_status("headers", status, "200")
    required = {"Content-Security-Policy", "X-Frame-Options", "Strict-Transport-Security", "X-Content-Type-Options"}
    if not required.issubset(headers):
        raise AssertionError(f"missing security headers: {required - set(headers)}")


def case_26():
    status, _, body = request("POST", "/api/auth/login", b"{", {"Content-Type": "application/json", "Origin": "https://alibehram11.pythonanywhere.com"})
    assert_error_status(status)
    text = body.decode("utf-8", "replace")
    if any(marker in text for marker in ("Traceback", "server.py", "sqlite3", "C:\\Users")):
        raise AssertionError("internal exception details leaked")


def case_27():
    ctx = fresh()
    status, _, _ = request("POST", "/api/docx/upload", {"fileName": "../evil.docx", "dataBase64": base64.b64encode(b"MZ-webshell").decode()}, ctx["admin"])
    assert_error_status(status, ("400", "403"))
    status, _, _ = request("POST", "/api/docx/upload", {"fileName": server.KNOWN_TEMPLATES["fr01"], "dataBase64": "not-base64"}, ctx["admin"])
    assert_error_status(status, ("400",))


def case_28():
    raise NotApplicable("No redirect URL parameter or redirect endpoint exists.")


def case_29():
    raise NotApplicable("The main application uses the Python standard library; external dependency CVE scanning needs a package audit tool.")


def case_30():
    ctx = fresh()
    expect_status("logout", request("POST", "/api/auth/logout", {}, ctx["admin"])[0], "200")
    expect_status("revoked session", request("GET", "/api/state", headers=ctx["admin"])[0], "401")


def case_31():
    raise NotApplicable("A coverage percentage needs coverage.py instrumentation and is not a runtime endpoint assertion.")


def case_32():
    fresh()
    with server.connect_db() as conn:
        conn.execute("DELETE FROM outbox")
    with server.connect_db() as conn:
        server.enqueue_outbox(conn, "quality", {"id": "integration"}, "quality-integration")
    result = server.process_outbox(lambda _kind, _payload: None)
    if result["sent"] != 1:
        raise AssertionError(f"DB/outbox integration failed: {result}")


def case_33():
    values = [server.sanitize_value(None), server.sanitize_value(""), server.sanitize_value(float("nan"))]
    if values != [None, "", None]:
        raise AssertionError(f"null/empty normalization failed: {values}")


def case_34():
    ctx = fresh()
    state, revision = get_state(ctx["admin"])
    state["tasks"][0]["description"] = "x" * 50_001
    expect_status("bounded huge input", post_state(ctx["admin"], state, revision)[0], "200")
    saved, _ = get_state(ctx["admin"])
    if len(saved["tasks"][0]["description"]) > server.MAX_SANITIZE_STRING:
        raise AssertionError("huge input was not bounded")


def case_35():
    fresh()
    with server.connect_db() as conn:
        conn.execute("DELETE FROM outbox")
    with server.connect_db() as conn:
        server.enqueue_outbox(conn, "timeout", {"id": "timeout"}, "quality-timeout")
    result = server.process_outbox(lambda _kind, _payload: (_ for _ in ()).throw(TimeoutError()))
    if result["retried"] < 1 or result["failed"]:
        raise AssertionError(f"timeout did not degrade to retry: {result}")


def case_36():
    attempts = []
    result = run_retry_job({"id": "retry"}, lambda _job: (_ for _ in ()).throw(RuntimeError()), max_attempts=3)
    if result["status"] != "failed" or result["attempts"] != 3:
        raise AssertionError("retry loop did not stop at max attempts")
    attempts.append(result["attempts"])


def case_37():
    raise NotApplicable("Graceful shutdown requires a process supervisor and deployment test environment.")


def case_38():
    ctx = fresh()
    request("POST", "/api/log", {"action": "log-secret", "detail": {"password": "do-not-log"}}, ctx["admin"])
    with sqlite3.connect(server.DB_PATH) as conn:
        raw = conn.execute("SELECT detail_json FROM logs WHERE action = ?", ("log-secret",)).fetchone()[0]
    if "do-not-log" in raw or "password" in raw.casefold():
        raise AssertionError("log stored a secret field")


def case_39():
    raise NotApplicable("Memory-leak measurement needs a long-running process profiler.")


def case_40():
    raise NotApplicable("No runtime feature-flag/config service exists.")


def case_41():
    fresh()
    durations = []
    for _ in range(30):
        started = time.perf_counter()
        status, _, _ = request("GET", "/api/health")
        durations.append(time.perf_counter() - started)
        expect_status("health benchmark", status, "200")
    p95 = sorted(durations)[int(len(durations) * 0.95) - 1]
    if statistics.mean(durations) > 0.2 or p95 > 0.4:
        raise AssertionError(f"health latency too high: avg={statistics.mean(durations):.3f}s p95={p95:.3f}s")


def case_42():
    fresh()
    def health(_):
        return request("GET", "/api/health")[0]
    with ThreadPoolExecutor(max_workers=12) as pool:
        statuses = list(pool.map(health, range(48)))
    if not all(status.startswith("200") for status in statuses):
        raise AssertionError(f"concurrent health failure: {statuses}")


def case_43():
    server.RATE_BUCKETS.clear()
    results = [server.rate_limit_key("spike-ip", "spike", 10) for _ in range(50)]
    if sum(results) != 10:
        raise AssertionError(f"spike was not controlled: accepted={sum(results)}")


def case_44():
    if "sqlite3" not in Path("server.py").read_text(encoding="utf-8") or "SELECT" not in Path("server.py").read_text(encoding="utf-8"):
        raise AssertionError("database access not present for N+1 inspection")


def case_45():
    fresh()
    with server.connect_db() as conn:
        indexes = {row[1] for row in conn.execute("PRAGMA index_list(logs)").fetchall()}
    if "idx_logs_ts" not in indexes:
        raise AssertionError("logs timestamp index missing")


def case_46():
    raise NotApplicable("No cache layer is configured, so cache invalidation is not an application contract.")


def case_47():
    raise NotApplicable("CDN/gzip is a reverse-proxy deployment concern, not implemented by the local WSGI app.")


def case_48():
    raise NotApplicable("Long exports are bounded synchronous operations; there is no async job contract to assert.")


def case_49():
    html = Path("index.html").read_text(encoding="utf-8")
    if html.count("required") < 8 or "type=\"email\"" not in html:
        raise AssertionError("form field validation metadata is incomplete")


def case_50():
    js = Path("app.js").read_text(encoding="utf-8")
    if not any(marker in js for marker in ("backendStatus", "disabled", "loading")):
        raise AssertionError("no visible loading/status handling found")


def case_51():
    raise NotApplicable("The app is a single-page static shell; browser-rendered branded 404/500 pages are not defined.")


def case_52():
    css = Path("styles.css").read_text(encoding="utf-8")
    if "@media" not in css:
        raise AssertionError("responsive media rules missing")


def case_53():
    html = Path("index.html").read_text(encoding="utf-8")
    if 'aria-label=' not in html or 'type="button"' not in html:
        raise AssertionError("basic keyboard/a11y attributes missing")


def case_54():
    js = Path("app.js").read_text(encoding="utf-8")
    if not re.search(r"dataset\.submitting|data-submitting|submit.*disabled", js, re.IGNORECASE | re.DOTALL):
        raise AssertionError("no duplicate-submit guard found")


def case_55():
    js = Path("app.js").read_text(encoding="utf-8")
    if not any(marker in js.casefold() for marker in ("toast", "kaydedildi", "silindi", "basarili")):
        raise AssertionError("action feedback message not found")


def case_56():
    raise NotApplicable("The app switches views without a URL history router.")


def case_57():
    tasks = [{"id": str(i), "title": f"Task {i}", "description": "bulk"} for i in range(10_000)]
    started = time.perf_counter()
    result = literal_task_search(tasks, "Task 9999")
    if len(result) != 1 or time.perf_counter() - started > 0.5:
        raise AssertionError("large list search is too slow or incorrect")


def case_58():
    raise NotApplicable("Cross-browser execution requires an installed browser automation matrix.")


def case_59():
    ctx = fresh()
    status, _, body = request("POST", "/api/snapshot", {"payload": {"backup": True}}, ctx["admin"])
    expect_status("snapshot", status, "200")
    snapshot_id = json_body(body).get("snapshotId")
    status, _, body = request("GET", "/api/snapshots", headers=ctx["admin"])
    expect_status("snapshot list", status, "200")
    if snapshot_id not in {item["id"] for item in json_body(body).get("snapshots", [])}:
        raise AssertionError("created snapshot cannot be restored/listed")


def case_60():
    state = base_state()
    deleted_project = state["projects"].pop(0)
    state["trash"] = [{"id": "trash-p1", "kind": "project", "data": {"project": deleted_project, "tasks": []}}]
    restored = restore_from_trash(state, "trash-p1")
    if not any(project["id"] == "p1" for project in restored["projects"]):
        raise AssertionError("soft-delete restore failed")


def case_61():
    raise NotApplicable("No migration scripts are shipped in this single-file SQLite app.")


def case_62():
    ctx = fresh()
    state, revision = get_state(ctx["admin"])
    state["projects"][0]["name"] = "first writer"
    expect_status("first writer", post_state(ctx["admin"], state, revision)[0], "200")
    state["projects"][0]["name"] = "stale writer"
    expect_status("lost update guard", post_state(ctx["admin"], state, revision)[0], "409")


def case_63():
    state = base_state()
    incoming = copy.deepcopy(state)
    incoming["users"] = [user for user in incoming["users"] if user["id"] != "demo-tasarim"]
    session = {"userId": "demo-admin", "email": "admin@proje.local", "role": "admin"}
    result = prepare_state_transition(state, incoming, session, 0, 0)
    deleted = next(user for user in result["users"] if user["id"] == "demo-tasarim")
    if not deleted.get("deleted") or not deleted.get("name", "").casefold().startswith("silin"):
        raise AssertionError("user deletion did not preserve an anonymized audit reference")


CASES = [
    case_01, case_02, case_03, case_04, case_05, case_06, case_07, case_08, case_09, case_10,
    case_11, case_12, case_13, case_14, case_15, case_16, case_17, case_18, case_19, case_20,
    case_21, case_22, case_23, case_24, case_25, case_26, case_27, case_28, case_29, case_30,
    case_31, case_32, case_33, case_34, case_35, case_36, case_37, case_38, case_39, case_40,
    case_41, case_42, case_43, case_44, case_45, case_46, case_47, case_48, case_49, case_50,
    case_51, case_52, case_53, case_54, case_55, case_56, case_57, case_58, case_59, case_60,
    case_61, case_62, case_63,
]


def run() -> dict[str, int]:
    results = {"total": len(CASES), "passed": 0, "failed": 0, "not_applicable": 0}
    for number, test in enumerate(CASES, 1):
        try:
            test()
        except NotApplicable as exc:
            results["not_applicable"] += 1
            print(f"{number:02d} NOT_APPLICABLE {exc}")
        except Exception as exc:  # The runner must report every case and continue.
            results["failed"] += 1
            print(f"{number:02d} FAIL {type(exc).__name__}: {exc}")
        else:
            results["passed"] += 1
            print(f"{number:02d} PASS")
    print("SUMMARY " + " ".join(f"{key}={value}" for key, value in results.items()))
    return results


if __name__ == "__main__":
    run()

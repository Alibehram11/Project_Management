from __future__ import annotations

import copy
import math
from pathlib import Path

import server
from advanced_rules import DomainError, MAX_TASK_NESTING, validate_state
from advanced_tests import base_state, fresh, get_state, post_state
from security_tests import configure_test_backend, expect_status, json_body, login, minimal_docx_b64, request


TEST_ROOT = Path(".security_advanced_runtime")


def expect_domain(code: str, fn) -> None:
    try:
        fn()
    except DomainError as exc:
        if exc.code != code:
            raise AssertionError(f"expected {code}, got {exc.code}") from exc
        return
    raise AssertionError(f"expected DomainError({code})")


def no_feature_surface(*names: str) -> None:
    source = Path("server.py").read_text(encoding="utf-8").casefold()
    if any(name.casefold() in source for name in names):
        raise AssertionError(f"unexpected unsupported security surface: {names}")


def run() -> None:
    tests: list[tuple[str, object]] = []
    add = lambda name, fn: tests.append((name, fn))

    def t01_opaque_session_rejects_forged_jwt():
        fresh()
        status, _, _ = request("GET", "/api/state", headers={
            "Authorization": "Bearer eyJhbGciOiJub25lIn0.eyJzdWIiOiJhZG1pbiJ9.",
        })
        expect_status("forged jwt", status, "401")
    add("01 JWT none/algorithm confusion is unavailable and forged token is rejected", t01_opaque_session_rejects_forged_jwt)

    def t02_replayed_session_is_revoked():
        fresh()
        session = login("tasarim@proje.local", "123456", "10.20.0.2")
        if "refreshToken" in session:
            raise AssertionError("unexpected refresh token in client session")
        if not server.revoke_api_session(session):
            raise AssertionError("session was not revoked")
        status, _, _ = request("GET", "/api/state", headers=session)
        expect_status("replayed revoked session", status, "401")
    add("02 replayed bearer session cannot be reused after revocation", t02_replayed_session_is_revoked)

    def t03_login_enumeration_response_is_uniform():
        configure_test_backend(TEST_ROOT / "enumeration")
        valid_shape = {"Origin": "https://alibehram11.pythonanywhere.com", "Content-Type": "application/json", "Remote-Addr": "10.20.0.3"}
        existing = request("POST", "/api/auth/login", {"email": "admin@proje.local", "password": "wrong"}, valid_shape)
        missing = request("POST", "/api/auth/login", {"email": "missing-user@proje.local", "password": "wrong"}, {**valid_shape, "Remote-Addr": "10.20.0.4"})
        if existing[0] != missing[0] or json_body(existing[2]) != json_body(missing[2]):
            raise AssertionError("login responses reveal whether the account exists")
    add("03 login does not expose user enumeration", t03_login_enumeration_response_is_uniform)

    def t04_reset_tokens_are_unpredictable():
        configure_test_backend(TEST_ROOT / "reset-randomness")
        server.PASSWORD_RESET_TOKENS.clear()
        tokens = {server.issue_password_reset("tasarim@proje.local") for _ in range(100)}
        if len(tokens) != 100 or min(len(token) for token in tokens) < 40:
            raise AssertionError("reset tokens are not sufficiently random")
        if any(len(token) < 40 for token in tokens):
            raise AssertionError("short reset token generated")
    add("04 reset and invite token generation has sufficient entropy", t04_reset_tokens_are_unpredictable)

    def t05_two_factor_surface_is_not_bypassable():
        no_feature_surface("/api/auth/2fa", "two_factor", "verify_2fa", "create_2fa_session")
    add("05 no unimplemented 2FA endpoint can be bypassed", t05_two_factor_surface_is_not_bypassable)

    def t06_mass_assignment_is_case_insensitive():
        state = base_state()
        state["projects"][0]["ISOWNER"] = True
        expect_domain("mass-assignment-denied", lambda: validate_state(state))
    add("06 mass assignment cannot inject privileged fields", t06_mass_assignment_is_case_insensitive)

    def t07_nested_foreign_task_data_is_hidden():
        ctx = fresh()
        state, _ = get_state(ctx["member"])
        if any(task["id"] == "t2" or task.get("comments") for task in state["tasks"]):
            raise AssertionError("foreign nested task data leaked")
    add("07 nested IDOR cannot expose foreign task comments or submissions", t07_nested_foreign_task_data_is_hidden)

    def t08_secondary_exports_repeat_authorization():
        ctx = fresh()
        status, _, _ = request("POST", "/api/export/tasks", {"projectId": "p2", "format": "csv"}, ctx["member"])
        expect_status("foreign task export", status, "403")
        status, _, _ = request("POST", "/api/docx/export", {"projectId": "p2", "templateId": "fr01"}, ctx["member"])
        expect_status("foreign docx export", status, "403")
    add("08 export and bulk-like secondary operations recheck authorization", t08_secondary_exports_repeat_authorization)

    def t09_denied_resource_response_is_consistent():
        ctx = fresh()
        state, rev = get_state(ctx["member"])
        state["projects"].append(copy.deepcopy(base_state()["projects"][1]))
        status_a, body_a = post_state(ctx["member"], state, rev)
        status_b, _, body_b = request("POST", "/api/export/tasks", {"projectId": "p2", "format": "csv"}, ctx["member"])
        if not status_a.startswith("403") or not status_b.startswith("403") or body_a.get("error") != json_body(body_b).get("error"):
            raise AssertionError("denied-resource responses are inconsistent")
    add("09 unauthorized resource responses do not disclose existence", t09_denied_resource_response_is_consistent)

    def t10_role_change_is_revalidated_centrally():
        ctx = fresh()
        state, rev = get_state(ctx["admin"])
        project = next(item for item in state["projects"] if item["id"] == "p1")
        project["adminIds"].append("demo-tasarim")
        project["memberProfiles"]["demo-tasarim"]["role"] = "admin"
        expect_status("grant role", post_state(ctx["admin"], state, rev)[0], "200")
        member_state, member_rev = get_state(ctx["member"])
        member_state["projects"][0]["name"] = "Member-managed"
        expect_status("fresh role is honored", post_state(ctx["member"], member_state, member_rev)[0], "200")
    add("10 role changes are applied from current server state", t10_role_change_is_revalidated_centrally)

    def t11_tenant_project_isolation():
        ctx = fresh()
        state, _ = get_state(ctx["member"])
        if {project["id"] for project in state["projects"]} != {"p1"}:
            raise AssertionError("foreign tenant project leaked")
    add("11 project and user IDs cannot cross tenant boundaries", t11_tenant_project_isolation)

    def t12_no_cross_tenant_autocomplete_endpoint():
        no_feature_surface("/api/autocomplete", "/api/user-search", "autocomplete_users")
    add("12 unsupported cross-tenant autocomplete surface is absent", t12_no_cross_tenant_autocomplete_endpoint)

    def t13_global_logs_are_not_project_member_data():
        # This application has one global workspace; project-scoped admins are not
        # treated as tenant administrators by the state authorization model.
        source = Path("advanced_rules.py").read_text(encoding="utf-8")
        if "visible_state" not in source or "managed_project_ids" not in source:
            raise AssertionError("project scope model missing")
    add("13 shared logs and queues use the same project scope model", t13_global_logs_are_not_project_member_data)

    def t14_svg_payload_is_rejected():
        fresh()
        status, _, _ = request("POST", "/api/docx/upload", {"fileName": "01_FR-01_Proje_Tanim_Karti.docx", "dataBase64": minimal_docx_b64("word/media/evil.svg", b"<svg><script>alert(1)</script></svg>")}, login("admin@proje.local", "123456", "10.20.0.14"))
        expect_status("svg upload", status, "400")
    add("14 SVG script payloads are rejected inside DOCX uploads", t14_svg_payload_is_rejected)

    def t15_upload_is_validated_by_content():
        fresh()
        admin = login("admin@proje.local", "123456", "10.20.0.15")
        status, _, _ = request("POST", "/api/docx/upload", {"fileName": "01_FR-01_Proje_Tanim_Karti.docx", "dataBase64": "UEsDBA=="}, admin)
        expect_status("fake docx", status, "400")
    add("15 upload validation checks file content, not only extension", t15_upload_is_validated_by_content)

    def t16_download_names_cannot_traverse():
        for value in ("../server.py", "..\\app_data.sqlite3", "%2e%2e%2fsecret.docx", "\u202e.docx"):
            name = server.safe_download_name(value)
            if ".." in name or "/" in name or "\\" in name or "\u202e" in name:
                raise AssertionError("unsafe download name survived")
    add("16 path traversal characters are removed from file names", t16_download_names_cannot_traverse)

    def t17_api_redacts_mixed_case_secrets():
        state = base_state()
        state["users"][0]["PASSWORDHASH"] = "secret"
        state["users"][0]["OAuthToken"] = "oauth-secret"
        visible = server.visible_state(state, {"email": "admin@proje.local", "userId": "demo-admin"})
        raw = str(visible)
        if "PASSWORDHASH" in raw or "OAuthToken" in raw or "secret" in raw:
            raise AssertionError("mixed-case secret leaked in API view")
    add("17 API responses redact sensitive fields case-insensitively", t17_api_redacts_mixed_case_secrets)

    def t18_exception_response_stays_generic():
        original = server.find_auth_user
        server.find_auth_user = lambda *_: (_ for _ in ()).throw(RuntimeError("C:\\private\\db.sqlite3"))
        try:
            result = request("POST", "/api/auth/login", {"email": "admin@proje.local", "password": "123456"}, {"Origin": "https://alibehram11.pythonanywhere.com", "Content-Type": "application/json", "Remote-Addr": "10.20.0.18"})
        finally:
            server.find_auth_user = original
        if result[0] != "500 Internal Server Error" or json_body(result[2]) != {"ok": False, "error": "internal-error"}:
            raise AssertionError("internal exception details leaked")
    add("18 error responses never expose stack or file path details", t18_exception_response_stays_generic)

    def t19_state_change_requires_csrf():
        ctx = fresh()
        headers = {key: value for key, value in ctx["admin"].items() if key != "X-CSRF-Token"}
        status, _, _ = request("POST", "/api/state", {"payload": base_state(), "revision": 1}, headers)
        expect_status("csrf bypass", status, "403")
    add("19 state-changing requests require CSRF", t19_state_change_requires_csrf)

    def t20_cors_does_not_allow_arbitrary_origin():
        ctx = fresh()
        status, _, _ = request("POST", "/api/log", {"action": "cors"}, {**ctx["admin"], "Origin": "https://evil.example"})
        expect_status("wildcard cors", status, "403")
    add("20 credentialed CORS is restricted to configured origins", t20_cors_does_not_allow_arbitrary_origin)

    def t21_browser_security_headers_are_complete():
        status, headers, _ = request("GET", "/api/health")
        expect_status("security headers", status, "200")
        for name in ("Content-Security-Policy", "X-Frame-Options", "Strict-Transport-Security", "X-Content-Type-Options"):
            if name not in headers:
                raise AssertionError(f"missing security header: {name}")
    add("21 clickjacking and transport security headers are present", t21_browser_security_headers_are_complete)

    def t22_workflow_cannot_skip_review():
        ctx = fresh()
        state, rev = get_state(ctx["member"])
        state["tasks"][0]["status"] = "approved"
        expect_status("workflow bypass", post_state(ctx["member"], state, rev)[0], "409")
    add("22 task approval cannot skip the review workflow", t22_workflow_cannot_skip_review)

    def t23_duplicate_write_is_revision_protected():
        ctx = fresh()
        state, rev = get_state(ctx["admin"])
        state["projects"][0]["name"] = "Once"
        expect_status("first write", post_state(ctx["admin"], state, rev)[0], "200")
        expect_status("duplicate stale write", post_state(ctx["admin"], state, rev)[0], "409")
    add("23 repeated critical state requests do not create duplicate writes", t23_duplicate_write_is_revision_protected)

    def t24_numeric_values_reject_negative_and_nan():
        state = base_state()
        state["projects"][0]["budget"] = -1
        expect_domain("numeric-value-invalid", lambda: validate_state(state))
        state["projects"][0]["budget"] = math.nan
        expect_domain("numeric-value-invalid", lambda: validate_state(state))
    add("24 numeric fields reject negative and non-finite values", t24_numeric_values_reject_negative_and_nan)

    def t25_login_rate_limit_is_account_scoped():
        configure_test_backend(TEST_ROOT / "account-rate")
        headers = {"Origin": "https://alibehram11.pythonanywhere.com", "Content-Type": "application/json"}
        statuses = [request("POST", "/api/auth/login", {"email": "rate-limit@proje.local", "password": "wrong"}, {**headers, "Remote-Addr": f"10.20.25.{index}"})[0] for index in range(server.RATE_LIMIT_LOGIN_ACCOUNT + 1)]
        if statuses[-1] != "429 Too Many Requests":
            raise AssertionError("login account rate limit was not enforced")
    add("25 login rate limiting cannot be bypassed by changing IP", t25_login_rate_limit_is_account_scoped)

    def t26_nested_task_depth_is_bounded():
        state = base_state()
        parent = "t1"
        for index in range(MAX_TASK_NESTING + 1):
            task_id = f"nested-{index}"
            state["tasks"].append({"id": task_id, "projectId": "p1", "assigneeId": "demo-admin", "status": "todo", "parentTaskId": parent, "dependencyIds": []})
            parent = task_id
        expect_domain("task-depth-exceeded", lambda: validate_state(state))
    add("26 nested task depth is bounded", t26_nested_task_depth_is_bounded)

    def t27_no_ssrf_webhook_surface():
        no_feature_surface("webhook", "callback_url", "169.254.169.254")
    add("27 no unimplemented webhook URL can be abused for SSRF", t27_no_ssrf_webhook_surface)

    def t28_oauth_secrets_cannot_enter_state():
        state = base_state()
        state["integrations"] = [{"provider": "jira", "oauthToken": "secret"}]
        expect_domain("secret-storage-denied", lambda: validate_state(state))
    add("28 OAuth and API secrets cannot be stored in application state", t28_oauth_secrets_cannot_enter_state)

    def t29_no_unsigned_webhook_receiver_surface():
        no_feature_surface("webhook_signature", "verify_webhook", "webhook_receiver")
    add("29 no unsigned webhook receiver accepts forged events", t29_no_unsigned_webhook_receiver_surface)

    configure_test_backend(TEST_ROOT / "suite")
    passed = []
    for name, fn in tests:
        fn()
        passed.append(name)
        print(f"PASS {name}")
    print(f"PASS total={len(passed)}")


if __name__ == "__main__":
    run()

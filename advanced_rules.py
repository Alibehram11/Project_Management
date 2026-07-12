from __future__ import annotations

import copy
import csv
import io
import json
from datetime import datetime, timezone
from typing import Callable, Iterable


PROJECT_COLLECTIONS = ("tasks", "invites", "calendarEvents", "crmItems", "feedItems")
TASK_MEMBER_FIELDS = {"status", "comments", "submissions", "checklist", "updatedAt", "version"}
TEXT_LIMITS = {"title": 300, "description": 20_000, "text": 20_000, "note": 20_000}


class DomainError(ValueError):
    def __init__(self, code: str, status: int = 400):
        super().__init__(code)
        self.code = code
        self.status = status


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def item_map(items: object) -> dict[str, dict]:
    if not isinstance(items, list):
        return {}
    return {
        str(item.get("id")): item
        for item in items
        if isinstance(item, dict) and item.get("id")
    }


def is_system_admin(session: dict) -> bool:
    return str(session.get("email", "")).casefold() == "admin@proje.local"


def project_role(project: dict | None, user_id: str) -> str:
    if not project or not user_id or user_id not in (project.get("memberIds") or []):
        return "none"
    if project.get("ownerId") == user_id:
        return "owner"
    if user_id in (project.get("adminIds") or []):
        return "admin"
    return str((project.get("memberProfiles") or {}).get(user_id, {}).get("role") or "member")


def managed_project_ids(state: dict, session: dict) -> set[str]:
    if is_system_admin(session):
        return set(item_map(state.get("projects")).keys())
    user_id = str(session.get("userId") or "")
    return {
        project_id
        for project_id, project in item_map(state.get("projects")).items()
        if project_role(project, user_id) in {"owner", "admin"}
    }


def visible_state(state: dict, session: dict) -> dict:
    user_id = str(session.get("userId") or "")
    if is_system_admin(session):
        result = copy.deepcopy(state)
        projects = result.get("projects", [])
    else:
        projects = [
            copy.deepcopy(project)
            for project in state.get("projects", [])
            if isinstance(project, dict) and project_role(project, user_id) != "none"
        ]
        result = copy.deepcopy(state)
    project_ids = {str(project.get("id")) for project in projects}
    visible_user_ids = {user_id}
    for project in projects:
        visible_user_ids.update(str(value) for value in project.get("memberIds", []))
    result["projects"] = projects
    source_users = state.get("users", []) if not is_system_admin(session) else result.get("users", [])
    result["users"] = []
    for user in source_users:
        if not isinstance(user, dict) or (not is_system_admin(session) and str(user.get("id")) not in visible_user_ids):
            continue
        public_user = copy.deepcopy(user)
        for key in ("password", "passwordHash", "passwordSalt", "resetToken"):
            public_user.pop(key, None)
        result["users"].append(public_user)
    if is_system_admin(session):
        return result
    for key in PROJECT_COLLECTIONS:
        result[key] = [
            copy.deepcopy(item)
            for item in state.get(key, [])
            if isinstance(item, dict) and str(item.get("projectId")) in project_ids
        ]
    result["documents"] = {
        key: copy.deepcopy(value)
        for key, value in (state.get("documents") or {}).items()
        if any(str(key).startswith(f"{project_id}:") for project_id in project_ids)
    }
    if managed_project_ids(state, session):
        result["atolyeRequests"] = copy.deepcopy(state.get("atolyeRequests", []))
    else:
        result["atolyeRequests"] = [
            copy.deepcopy(request)
            for request in state.get("atolyeRequests", [])
            if isinstance(request, dict) and str(request.get("createdBy")) == user_id
        ]
    result["trash"] = []
    return result


def parse_utc(value: object) -> datetime:
    text = str(value or "").strip()
    if len(text) == 10:
        text = f"{text}T23:59:59+00:00"
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        raise DomainError("date-invalid") from None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _check_text_limits(value: object) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in TEXT_LIMITS and isinstance(item, str) and len(item) > TEXT_LIMITS[key]:
                raise DomainError("text-too-long")
            _check_text_limits(item)
    elif isinstance(value, list):
        for item in value:
            _check_text_limits(item)


def _validate_task_graph(tasks: list[dict]) -> None:
    tasks_by_id = item_map(tasks)
    graph: dict[str, list[str]] = {}
    for task_id, task in tasks_by_id.items():
        dependencies = [str(value) for value in task.get("dependencyIds", [])]
        if task_id in dependencies or any(value not in tasks_by_id for value in dependencies):
            raise DomainError("task-dependency-invalid")
        graph[task_id] = dependencies
        parent_id = str(task.get("parentTaskId") or "")
        if parent_id:
            parent = tasks_by_id.get(parent_id)
            if not parent or str(parent.get("projectId")) != str(task.get("projectId")):
                raise DomainError("parent-task-invalid")
            if task.get("dueDate") and parent.get("dueDate") and parse_utc(task["dueDate"]) > parse_utc(parent["dueDate"]):
                raise DomainError("subtask-deadline-invalid")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str) -> None:
        if task_id in visiting:
            raise DomainError("task-dependency-cycle")
        if task_id in visited:
            return
        visiting.add(task_id)
        for dependency_id in graph.get(task_id, []):
            visit(dependency_id)
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in graph:
        visit(task_id)


def validate_state(state: dict) -> dict:
    if not isinstance(state, dict):
        raise DomainError("state-invalid")
    _check_text_limits(state)
    users = item_map(state.get("users"))
    projects = item_map(state.get("projects"))
    emails: set[str] = set()
    for user in users.values():
        email = str(user.get("email") or "").strip().casefold()
        if not user.get("deleted"):
            if not email or email in emails:
                raise DomainError("email-conflict", 409)
            emails.add(email)

    for project_id, project in projects.items():
        members = {str(value) for value in project.get("memberIds", [])}
        owner_id = str(project.get("ownerId") or "")
        admins = {str(value) for value in project.get("adminIds", [])}
        if not owner_id or owner_id not in members or owner_id not in users:
            raise DomainError("project-owner-invalid")
        if not ({owner_id} | admins) & members:
            raise DomainError("project-admin-required")
        if any(member_id not in users or users[member_id].get("deleted") for member_id in members):
            raise DomainError("project-member-invalid")
        if any(admin_id not in members for admin_id in admins):
            raise DomainError("project-admin-invalid")

    tasks = [task for task in state.get("tasks", []) if isinstance(task, dict)]
    for task in tasks:
        project = projects.get(str(task.get("projectId")))
        if not project:
            raise DomainError("task-project-invalid")
        if str(task.get("assigneeId")) not in {str(value) for value in project.get("memberIds", [])}:
            raise DomainError("task-assignee-invalid")
    _validate_task_graph(tasks)
    return state


def _changed_fields(before: dict, after: dict) -> set[str]:
    return {key for key in set(before) | set(after) if before.get(key) != after.get(key)}


def _project_ids_changed(before: list, after: list) -> set[str]:
    old_map, new_map = item_map(before), item_map(after)
    changed = set(old_map) ^ set(new_map)
    changed.update(key for key in set(old_map) & set(new_map) if old_map[key] != new_map[key])
    return changed


def _project_of_item(item: dict | None) -> str:
    return str((item or {}).get("projectId") or "")


def _authorize_transition(current: dict, incoming: dict, session: dict) -> None:
    if is_system_admin(session):
        return
    user_id = str(session.get("userId") or "")
    current_projects = item_map(current.get("projects"))
    managed = managed_project_ids(current, session)
    for project_id in _project_ids_changed(current.get("projects", []), incoming.get("projects", [])):
        if project_id not in managed:
            raise DomainError("project-access-denied", 403)
        if project_id not in current_projects:
            raise DomainError("project-create-denied", 403)

    if current.get("users") != incoming.get("users") or current.get("documentTemplates") != incoming.get("documentTemplates"):
        raise DomainError("system-admin-required", 403)

    for key in PROJECT_COLLECTIONS:
        old_map, new_map = item_map(current.get(key)), item_map(incoming.get(key))
        changed_ids = set(old_map) ^ set(new_map)
        changed_ids.update(item_id for item_id in set(old_map) & set(new_map) if old_map[item_id] != new_map[item_id])
        for item_id in changed_ids:
            before, after = old_map.get(item_id), new_map.get(item_id)
            project_id = _project_of_item(before or after)
            if project_id in managed:
                continue
            if key != "tasks" or not before or not after:
                raise DomainError("project-access-denied", 403)
            project = current_projects.get(project_id)
            if project_role(project, user_id) == "none" or str(before.get("assigneeId")) != user_id:
                raise DomainError("project-access-denied", 403)
            if _changed_fields(before, after) - TASK_MEMBER_FIELDS:
                raise DomainError("task-field-denied", 403)

    if current.get("trash") != incoming.get("trash"):
        raise DomainError("project-access-denied", 403)

    if current.get("atolyeRequests") != incoming.get("atolyeRequests") and not managed:
        old_requests, new_requests = item_map(current.get("atolyeRequests")), item_map(incoming.get("atolyeRequests"))
        changed = set(old_requests) ^ set(new_requests)
        changed.update(key for key in set(old_requests) & set(new_requests) if old_requests[key] != new_requests[key])
        for request_id in changed:
            before, after = old_requests.get(request_id), new_requests.get(request_id)
            if before and not after:
                raise DomainError("project-access-denied", 403)
            if str((after or before or {}).get("createdBy")) != user_id:
                raise DomainError("project-access-denied", 403)
            if before and after and before != after:
                raise DomainError("project-access-denied", 403)


def _merge_scoped_input(current: dict, incoming: dict, session: dict) -> dict:
    if is_system_admin(session):
        return copy.deepcopy(incoming)
    user_id = str(session.get("userId") or "")
    current_projects = item_map(current.get("projects"))
    scope_ids = {
        project_id
        for project_id, project in current_projects.items()
        if project_role(project, user_id) != "none"
    }
    incoming_projects = item_map(incoming.get("projects"))
    if set(incoming_projects) - scope_ids:
        raise DomainError("project-access-denied", 403)
    candidate = copy.deepcopy(current)
    candidate["projects"] = [
        copy.deepcopy(project)
        for project_id, project in current_projects.items()
        if project_id not in scope_ids
    ] + [copy.deepcopy(project) for project in incoming.get("projects", []) if isinstance(project, dict)]
    for key in PROJECT_COLLECTIONS:
        candidate[key] = [
            copy.deepcopy(item)
            for item in current.get(key, [])
            if _project_of_item(item) not in scope_ids
        ] + [
            copy.deepcopy(item)
            for item in incoming.get(key, [])
            if isinstance(item, dict) and _project_of_item(item) in scope_ids
        ]
    candidate["documents"] = copy.deepcopy(current.get("documents") or {})
    for key, value in (incoming.get("documents") or {}).items():
        if any(str(key).startswith(f"{project_id}:") for project_id in scope_ids):
            candidate["documents"][key] = copy.deepcopy(value)
    if managed_project_ids(current, session):
        candidate["atolyeRequests"] = copy.deepcopy(incoming.get("atolyeRequests", []))
    else:
        incoming_requests = [
            copy.deepcopy(request)
            for request in incoming.get("atolyeRequests", [])
            if isinstance(request, dict) and str(request.get("createdBy")) == user_id
        ]
        if len(incoming_requests) != len(incoming.get("atolyeRequests", [])):
            raise DomainError("project-access-denied", 403)
        candidate["atolyeRequests"] = [
            copy.deepcopy(request)
            for request in current.get("atolyeRequests", [])
            if str(request.get("createdBy")) != user_id
        ] + incoming_requests
    return candidate


def _apply_archive_lock(current: dict, incoming: dict) -> None:
    old_projects = item_map(current.get("projects"))
    new_projects = item_map(incoming.get("projects"))
    for project_id, old_project in old_projects.items():
        if old_project.get("status") not in {"archived", "completed"}:
            continue
        if new_projects.get(project_id) != old_project:
            raise DomainError("project-locked", 409)
        for key in PROJECT_COLLECTIONS:
            old_items = [item for item in current.get(key, []) if _project_of_item(item) == project_id]
            new_items = [item for item in incoming.get(key, []) if _project_of_item(item) == project_id]
            if old_items != new_items:
                raise DomainError("project-locked", 409)


def _apply_cascade_and_trash(current: dict, incoming: dict, actor: str) -> None:
    old_projects = item_map(current.get("projects"))
    new_projects = item_map(incoming.get("projects"))
    removed_ids = set(old_projects) - set(new_projects)
    trash = list(incoming.get("trash") or current.get("trash") or [])
    for project_id in removed_ids:
        related = {
            key: copy.deepcopy([item for item in current.get(key, []) if _project_of_item(item) == project_id])
            for key in PROJECT_COLLECTIONS
        }
        trash.append({
            "id": f"trash-project-{project_id}",
            "kind": "project",
            "deletedAt": utc_now(),
            "deletedBy": actor,
            "data": {"project": copy.deepcopy(old_projects[project_id]), **related},
        })
        for key in PROJECT_COLLECTIONS:
            incoming[key] = [item for item in incoming.get(key, []) if _project_of_item(item) != project_id]
    incoming["trash"] = trash[-100:]


def _preserve_deleted_users(current: dict, incoming: dict) -> None:
    old_users, new_users = item_map(current.get("users")), item_map(incoming.get("users"))
    removed_ids = set(old_users) - set(new_users)
    for user_id in removed_ids:
        new_users[user_id] = {
            "id": user_id,
            "name": "Silinmiş kullanıcı",
            "email": str(old_users[user_id].get("email") or f"deleted+{user_id}@local.invalid"),
            "password": "",
            "deleted": True,
        }
        for project in incoming.get("projects", []):
            project["memberIds"] = [value for value in project.get("memberIds", []) if str(value) != user_id]
            project["adminIds"] = [value for value in project.get("adminIds", []) if str(value) != user_id]
            (project.get("memberProfiles") or {}).pop(user_id, None)
            fallback = str(project.get("ownerId") or "")
            for task in incoming.get("tasks", []):
                if str(task.get("projectId")) == str(project.get("id")) and str(task.get("assigneeId")) == user_id:
                    task["assigneeId"] = fallback
    incoming["users"] = list(new_users.values())


def prepare_state_transition(
    current: dict,
    incoming: dict,
    session: dict,
    expected_revision: int,
    current_revision: int,
) -> dict:
    if expected_revision != current_revision:
        raise DomainError("revision-conflict", 409)
    candidate = _merge_scoped_input(current, incoming, session)
    old_users = item_map(current.get("users"))
    for user in candidate.get("users", []):
        old_user = old_users.get(str(user.get("id")))
        if not old_user:
            continue
        for key in ("password", "passwordHash", "passwordSalt"):
            if key not in user and key in old_user:
                user[key] = old_user[key]
    _authorize_transition(current, candidate, session)
    _apply_archive_lock(current, candidate)
    _apply_cascade_and_trash(current, candidate, str(session.get("email") or "unknown"))
    _preserve_deleted_users(current, candidate)
    return validate_state(candidate)


def project_progress(tasks: Iterable[dict]) -> int:
    task_list = list(tasks)
    if not task_list:
        return 0
    complete = sum(1 for task in task_list if task.get("status") == "approved")
    return round(complete * 100 / len(task_list))


def literal_task_search(tasks: Iterable[dict], query: str) -> list[dict]:
    needle = query.casefold()
    return [
        task
        for task in tasks
        if needle in f"{task.get('title', '')} {task.get('description', '')}".casefold()
    ]


def cursor_page(items: Iterable[dict], limit: int = 50, after: str = "") -> tuple[list[dict], str]:
    safe_limit = max(1, min(int(limit), 200))
    ordered = sorted(items, key=lambda item: (str(item.get("createdAt") or ""), str(item.get("id") or "")))
    if after:
        try:
            after_time, after_id = after.split("|", 1)
        except ValueError:
            raise DomainError("cursor-invalid") from None
        ordered = [
            item
            for item in ordered
            if (str(item.get("createdAt") or ""), str(item.get("id") or "")) > (after_time, after_id)
        ]
    page = ordered[:safe_limit]
    next_cursor = ""
    if len(page) == safe_limit:
        next_cursor = f"{page[-1].get('createdAt', '')}|{page[-1].get('id', '')}"
    return page, next_cursor


def restore_from_trash(state: dict, trash_id: str) -> dict:
    candidate = copy.deepcopy(state)
    record = next((item for item in candidate.get("trash", []) if str(item.get("id")) == str(trash_id)), None)
    if not record or record.get("kind") != "project":
        raise DomainError("trash-item-not-found", 404)
    data = record.get("data") or {}
    project = data.get("project")
    if not isinstance(project, dict) or str(project.get("id")) in item_map(candidate.get("projects")):
        raise DomainError("trash-restore-conflict", 409)
    candidate.setdefault("projects", []).append(copy.deepcopy(project))
    for key in PROJECT_COLLECTIONS:
        candidate.setdefault(key, []).extend(copy.deepcopy(data.get(key) or []))
    candidate["trash"] = [item for item in candidate.get("trash", []) if item is not record]
    return validate_state(candidate)


def atomic_bulk(state: dict, operations: Iterable[Callable[[dict], None]]) -> dict:
    candidate = copy.deepcopy(state)
    for operation in operations:
        operation(candidate)
    validate_state(candidate)
    return candidate


def run_retry_job(job: dict, sender: Callable[[dict], None], max_attempts: int = 3) -> dict:
    result = copy.deepcopy(job)
    result.setdefault("attempts", 0)
    while result["attempts"] < max_attempts:
        result["attempts"] += 1
        try:
            sender(result)
            result["status"] = "sent"
            result["lastError"] = ""
            return result
        except Exception as exc:
            result["status"] = "retry" if result["attempts"] < max_attempts else "failed"
            result["lastError"] = type(exc).__name__
    return result


def export_tasks_csv(tasks: Iterable[dict]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=["id", "projectId", "title", "status", "assigneeId", "dueDate"])
    writer.writeheader()
    for task in tasks:
        writer.writerow({key: task.get(key, "") for key in writer.fieldnames})
    return output.getvalue().encode("utf-8-sig")


def export_tasks_pdf(tasks: Iterable[dict]) -> bytes:
    lines = [f"{task.get('id', '')} | {task.get('title', '')} | {task.get('status', '')}" for task in tasks]
    text = "\n".join(lines).replace("\\", "/").replace("(", "[").replace(")", "]")
    stream = f"BT /F1 9 Tf 40 800 Td ({text.replace(chr(10), ') Tj 0 -12 Td (')}) Tj ET".encode("latin-1", "replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode())
    pdf.extend(f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode())
    return bytes(pdf)


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

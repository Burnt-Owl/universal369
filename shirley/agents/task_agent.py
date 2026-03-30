"""Task management agent for Shirley.

Handles CRUD operations on tasks stored in data/tasks.json.
Each task has: id, title, description, status, priority, due_date, tags, recurring, timestamps.
"""
import json
from datetime import date, datetime

from shirley.config import TASKS_FILE, ensure_data_dirs


def _load():
    if TASKS_FILE.exists():
        return json.loads(TASKS_FILE.read_text())
    return {"version": 1, "tasks": []}


def _save(data):
    ensure_data_dirs()
    TASKS_FILE.write_text(json.dumps(data, indent=2))


def _next_id(tasks):
    today = date.today().strftime("%Y%m%d")
    prefix = f"t_{today}_"
    existing = [t["id"] for t in tasks if t["id"].startswith(prefix)]
    if not existing:
        return f"{prefix}001"
    nums = [int(tid.split("_")[-1]) for tid in existing]
    return f"{prefix}{max(nums) + 1:03d}"


def add_task(title, due_date=None, priority="medium", tags=None, description=""):
    """Add a new task. Returns the created task dict."""
    data = _load()
    task = {
        "id": _next_id(data["tasks"]),
        "title": title,
        "description": description,
        "status": "pending",
        "priority": priority,
        "due_date": due_date,
        "tags": tags or [],
        "recurring": None,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "completed_at": None,
    }
    data["tasks"].append(task)
    _save(data)
    return task


def list_tasks(status_filter=None, priority_filter=None, tag_filter=None):
    """List tasks with optional filters."""
    data = _load()
    tasks = data["tasks"]

    if status_filter:
        tasks = [t for t in tasks if t["status"] == status_filter]
    if priority_filter:
        tasks = [t for t in tasks if t["priority"] == priority_filter]
    if tag_filter:
        tasks = [t for t in tasks if tag_filter in t.get("tags", [])]

    return tasks


def complete_task(task_id):
    """Mark a task as done. Returns the updated task or None."""
    data = _load()
    for task in data["tasks"]:
        if task["id"] == task_id:
            task["status"] = "done"
            task["completed_at"] = datetime.utcnow().isoformat() + "Z"
            _save(data)
            return task
    return None


def update_task(task_id, **updates):
    """Update task fields. Returns the updated task or None."""
    allowed = {"title", "description", "status", "priority", "due_date", "tags", "recurring"}
    data = _load()
    for task in data["tasks"]:
        if task["id"] == task_id:
            for key, val in updates.items():
                if key in allowed:
                    task[key] = val
            _save(data)
            return task
    return None


def get_task(task_id):
    """Get a single task by ID."""
    data = _load()
    for task in data["tasks"]:
        if task["id"] == task_id:
            return task
    return None


def delete_task(task_id):
    """Remove a task entirely. Returns True if found and removed."""
    data = _load()
    original_len = len(data["tasks"])
    data["tasks"] = [t for t in data["tasks"] if t["id"] != task_id]
    if len(data["tasks"]) < original_len:
        _save(data)
        return True
    return False


def format_task(task):
    """Format a task for display."""
    status_icon = {"pending": "[ ]", "in_progress": "[~]", "done": "[x]", "cancelled": "[-]"}
    pri_label = {"urgent": "!!!", "high": "!! ", "medium": "!  ", "low": "   "}
    icon = status_icon.get(task["status"], "[ ]")
    pri = pri_label.get(task["priority"], "   ")
    due = f" (due: {task['due_date']})" if task.get("due_date") else ""
    tags = f" [{', '.join(task['tags'])}]" if task.get("tags") else ""
    return f"  {icon} {pri} {task['title']}{due}{tags}  ({task['id']})"

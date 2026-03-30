"""Shirley CLI — your AI office & life manager.

Usage:
    python -m shirley                          Interactive chat
    python -m shirley ask "question"           Ask Shirley something
    python -m shirley task add "title"         Add a task
    python -m shirley task list                List tasks
    python -m shirley task done <id>           Complete a task
    python -m shirley briefing                 Morning briefing
    python -m shirley schedule                 Show today's schedule
    python -m shirley schedule plan            AI-generate today's plan
    python -m shirley create "prompt"          Create content
"""
import argparse
import sys

from shirley.config import ensure_data_dirs


def cmd_ask(args):
    from shirley.brain import ask
    message = " ".join(args.message)
    print(ask(message))


def cmd_chat(args):
    from shirley.brain import ask
    print("Shirley here. What do you need? (type 'quit' to exit)\n")
    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nLater. -- Shirley")
            break
        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "bye"):
            print("\nLater. -- Shirley")
            break
        reply = ask(user_input)
        print(f"\nShirley: {reply}\n")


def cmd_task(args):
    from shirley.agents.task_agent import (
        add_task, list_tasks, complete_task, delete_task, format_task,
    )

    if args.task_action == "add":
        title = " ".join(args.title)
        task = add_task(
            title=title,
            due_date=args.due,
            priority=args.priority or "medium",
            tags=args.tags.split(",") if args.tags else [],
        )
        print(f"Added: {format_task(task)}")

    elif args.task_action == "list":
        tasks = list_tasks(
            status_filter=args.status,
            priority_filter=args.priority,
        )
        if not tasks:
            print("  No tasks found.")
            return
        print("Tasks:")
        for t in tasks:
            print(format_task(t))

    elif args.task_action == "done":
        task = complete_task(args.task_id)
        if task:
            print(f"Completed: {task['title']}")
        else:
            print(f"Task not found: {args.task_id}")

    elif args.task_action == "delete":
        if delete_task(args.task_id):
            print(f"Deleted: {args.task_id}")
        else:
            print(f"Task not found: {args.task_id}")


def cmd_briefing(args):
    from shirley.agents.task_agent import list_tasks, format_task
    from shirley.brain import ask

    pending = list_tasks(status_filter="pending") + list_tasks(status_filter="in_progress")
    if pending:
        task_summary = "\n".join(format_task(t) for t in pending)
        context = f"Here are the user's current tasks:\n{task_summary}"
    else:
        context = "The user has no pending tasks right now."

    reply = ask(
        "Generate my morning briefing. What's on my plate today? "
        "Summarize my tasks by priority, flag anything overdue, and "
        "give me a plan for the day.",
        extra_context=context,
    )
    print(reply)


def cmd_schedule(args):
    from shirley.agents.task_agent import list_tasks, format_task
    from shirley.brain import ask

    if args.schedule_action == "plan":
        pending = list_tasks(status_filter="pending") + list_tasks(status_filter="in_progress")
        if pending:
            task_summary = "\n".join(format_task(t) for t in pending)
            context = f"Current tasks:\n{task_summary}"
        else:
            context = "No pending tasks."

        reply = ask(
            "Create a time-blocked schedule for my day. "
            "Prioritize high/urgent tasks first. Include breaks. "
            "Format as a simple timeline.",
            extra_context=context,
        )
        print(reply)
    else:
        # Default: show today's schedule if it exists
        from datetime import date
        from shirley.config import SCHEDULE_DIR
        import json
        today_file = SCHEDULE_DIR / f"{date.today().isoformat()}.json"
        if today_file.exists():
            data = json.loads(today_file.read_text())
            for block in data.get("blocks", []):
                print(f"  {block['time']}  {block['title']} ({block['duration_min']}min)")
        else:
            print("No schedule for today. Run 'python -m shirley schedule plan' to create one.")


def cmd_create(args):
    from shirley.brain import ask
    from shirley.config import NOTES_DIR
    from datetime import datetime
    import re

    prompt = " ".join(args.prompt)
    reply = ask(
        f"Help me create the following: {prompt}\n\n"
        "Produce the content in clean markdown format.",
        extra_context="You are in creation mode. Help produce high-quality written content.",
    )
    print(reply)

    # Save to notes
    slug = re.sub(r"[^a-z0-9]+", "-", prompt.lower())[:40].strip("-")
    now = datetime.utcnow().strftime("%Y-%m-%d-%H-%M")
    filename = f"{now}-{slug}.md"
    filepath = NOTES_DIR / filename
    filepath.write_text(f"# {prompt}\n\n{reply}\n")
    print(f"\nSaved to: {filepath}")


def main():
    ensure_data_dirs()

    parser = argparse.ArgumentParser(
        prog="shirley",
        description="Shirley -- your AI office & life manager",
    )
    subparsers = parser.add_subparsers(dest="command")

    # ask
    ask_parser = subparsers.add_parser("ask", help="Ask Shirley a question")
    ask_parser.add_argument("message", nargs="+")

    # task
    task_parser = subparsers.add_parser("task", help="Manage tasks")
    task_sub = task_parser.add_subparsers(dest="task_action")

    task_add = task_sub.add_parser("add", help="Add a task")
    task_add.add_argument("title", nargs="+")
    task_add.add_argument("--due", help="Due date (YYYY-MM-DD)")
    task_add.add_argument("--priority", choices=["low", "medium", "high", "urgent"])
    task_add.add_argument("--tags", help="Comma-separated tags")

    task_list = task_sub.add_parser("list", help="List tasks")
    task_list.add_argument("--status", choices=["pending", "in_progress", "done", "cancelled"])
    task_list.add_argument("--priority", choices=["low", "medium", "high", "urgent"])

    task_done = task_sub.add_parser("done", help="Complete a task")
    task_done.add_argument("task_id")

    task_del = task_sub.add_parser("delete", help="Delete a task")
    task_del.add_argument("task_id")

    # briefing
    subparsers.add_parser("briefing", help="Morning briefing")

    # schedule
    sched_parser = subparsers.add_parser("schedule", help="Day schedule")
    sched_parser.add_argument("schedule_action", nargs="?", default="show",
                              choices=["show", "plan"])

    # create
    create_parser = subparsers.add_parser("create", help="Create content")
    create_parser.add_argument("prompt", nargs="+")

    args = parser.parse_args()

    if args.command is None:
        cmd_chat(args)
    elif args.command == "ask":
        cmd_ask(args)
    elif args.command == "task":
        if args.task_action is None:
            task_parser.print_help()
        else:
            cmd_task(args)
    elif args.command == "briefing":
        cmd_briefing(args)
    elif args.command == "schedule":
        cmd_schedule(args)
    elif args.command == "create":
        cmd_create(args)


if __name__ == "__main__":
    main()

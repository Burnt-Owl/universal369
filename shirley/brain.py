import json
from datetime import datetime, date

import anthropic

from shirley.config import (
    ANTHROPIC_API_KEY, CLAUDE_MODEL, HISTORY_FILE,
    TASKS_FILE, MAX_HISTORY_TURNS, ensure_data_dirs,
)

SYSTEM_PROMPT = """\
You are Shirley, a personal office and life manager AI assistant.

Personality:
- Organized, efficient, and genuinely helpful
- Slightly witty -- you're not a comedian, but you have a dry sense of humor
- You speak directly. No fluff, no corporate jargon.
- You sign off briefings with "-- Shirley"
- You remember context from the conversation and reference it naturally
- When something is overdue, you're gently firm about it

You help with:
- Scheduling and planning days
- Managing tasks and priorities
- Creating content and documents
- Keeping track of the user's projects (including Comedy Factory)

Rules:
- Be concise. Bullet points over paragraphs.
- When asked about tasks/schedule, always reference the actual data provided in context.
- If you don't know something, say so.
- Current date: {today}
"""


def _load_history():
    if HISTORY_FILE.exists():
        data = json.loads(HISTORY_FILE.read_text())
        return data.get("turns", [])
    return []


def _save_history(turns):
    ensure_data_dirs()
    trimmed = turns[-MAX_HISTORY_TURNS * 2:]
    HISTORY_FILE.write_text(json.dumps({"turns": trimmed}, indent=2))


def _load_tasks_context():
    if TASKS_FILE.exists():
        data = json.loads(TASKS_FILE.read_text())
        tasks = data.get("tasks", [])
        if tasks:
            pending = [t for t in tasks if t["status"] in ("pending", "in_progress")]
            if pending:
                lines = ["Current tasks:"]
                for t in pending:
                    pri = t.get("priority", "medium")
                    due = t.get("due_date", "no due date")
                    lines.append(f"  [{pri.upper()}] {t['title']} (due: {due}, status: {t['status']})")
                return "\n".join(lines)
    return "No tasks currently tracked."


def ask(user_message, extra_context=None):
    """Send a message to Shirley and get a response."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    today = date.today().strftime("%A, %B %d, %Y")
    system = SYSTEM_PROMPT.format(today=today)

    tasks_ctx = _load_tasks_context()
    system += f"\n\n{tasks_ctx}"

    if extra_context:
        system += f"\n\n{extra_context}"

    history = _load_history()
    messages = []
    for turn in history:
        messages.append({"role": turn["role"], "content": turn["content"]})

    messages.append({"role": "user", "content": user_message})

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        system=system,
        messages=messages,
    )

    reply = response.content[0].text

    now = datetime.utcnow().isoformat() + "Z"
    history.append({"timestamp": now, "role": "user", "content": user_message})
    history.append({"timestamp": now, "role": "assistant", "content": reply})
    _save_history(history)

    return reply


def ask_structured(user_message, schema_hint):
    """Ask Shirley for a JSON-structured response."""
    prompt = (
        f"{user_message}\n\n"
        f"Respond ONLY with valid JSON matching this structure:\n{schema_hint}"
    )

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    today = date.today().strftime("%A, %B %d, %Y")
    system = SYSTEM_PROMPT.format(today=today)

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    return json.loads(text)

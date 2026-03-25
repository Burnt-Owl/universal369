"""
Brief Agent — scores stories for comedy potential and selects the best one.
Output: runs/YYYY-MM-DD/selected-event.json
"""

import json
import anthropic
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL


SCORING_PROMPT = """You are the head writer for a comedy YouTube/TikTok series called "Raven & Jax" — a tattooed couple on their couch reacting to world events.

Given a list of today's news stories, score each one from 1-10 for comedy potential based on:
- Absurdity level (how weird or unbelievable it is)
- Relatability (can a normal couple have opinions on it?)
- Couple-reaction potential (can you imagine them arguing/discussing this?)
- Avoid tragedies, mass casualties, or events that aren't funny under any framing

Return a JSON array with this format for each story:
[
  {
    "index": 0,
    "score": 8,
    "comedy_angle": "One sentence on how to make this funny for a couple on a couch"
  }
]

Only return the JSON array. No other text."""


def score_stories(stories: list[dict]) -> list[dict]:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    stories_text = "\n\n".join(
        f"[{i}] {s['headline']}\n{s['summary']}"
        for i, s in enumerate(stories)
    )

    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        messages=[
            {"role": "user", "content": f"{SCORING_PROMPT}\n\nStories:\n{stories_text}"},
        ],
    )

    raw = message.content[0].text.strip()
    # Strip markdown code blocks if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw)


def run(run_dir: Path) -> Path:
    brief_file = run_dir / "daily-brief.json"
    brief = json.loads(brief_file.read_text())
    stories = brief["stories"]

    print(f"[brief_agent] Scoring {len(stories)} stories for comedy potential...")

    scores = score_stories(stories)
    scores_by_index = {s["index"]: s for s in scores}

    # Pick highest score, skip anything with score < 5
    best = max(
        (s for s in scores if s["score"] >= 5),
        key=lambda s: s["score"],
        default=None,
    )

    if not best:
        # Fallback: just pick highest score overall
        best = max(scores, key=lambda s: s["score"])

    selected_story = stories[best["index"]]
    selected_story["comedy_score"] = best["score"]
    selected_story["comedy_angle"] = best["comedy_angle"]

    output = {
        "date": brief["date"],
        "selected": selected_story,
        "all_scores": scores,
    }

    out_file = run_dir / "selected-event.json"
    out_file.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"[brief_agent] Selected: \"{selected_story['headline']}\" (score: {best['score']})")
    return out_file


if __name__ == "__main__":
    from datetime import date
    run_dir = Path(__file__).parent.parent / "runs" / date.today().isoformat()
    run(run_dir)

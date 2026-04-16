"""
SessionStart hook - injects knowledge base context into every conversation.

Two-tier context injection:
1. Always: meta-wiki index (process knowledge about building skills)
2. If applicable: current skill's wiki index (tool-specific knowledge)

The hook detects which skill is being worked on by checking the conversation
context or recent git activity, and injects that skill's references/index.md
alongside the process knowledge.

Configure in .claude/settings.json:
{
    "hooks": {
        "SessionStart": [{
            "matcher": "",
            "command": "uv run --directory claude-memory-compiler python hooks/session-start.py"
        }]
    }
}
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Paths relative to project root
ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = ROOT / "knowledge"
DAILY_DIR = ROOT / "daily"
INDEX_FILE = KNOWLEDGE_DIR / "index.md"
AGENTS_FILE = ROOT / "AGENTS.md"

# cli-me specific paths
CLI_ME_ROOT = ROOT.parent
SKILL_REPO_DIR = CLI_ME_ROOT / "skill-repo"
META_WIKI_DIR = CLI_ME_ROOT / ".claude" / "skills" / "cli-me-meta" / "references" / "meta-wiki"

MAX_CONTEXT_CHARS = 30_000
MAX_LOG_LINES = 30


def get_recent_log() -> str:
    """Read the most recent daily log (today or yesterday)."""
    today = datetime.now(timezone.utc).astimezone()

    for offset in range(2):
        date = today - timedelta(days=offset)
        log_path = DAILY_DIR / f"{date.strftime('%Y-%m-%d')}.md"
        if log_path.exists():
            lines = log_path.read_text(encoding="utf-8").splitlines()
            # Return last N lines to keep context small
            recent = lines[-MAX_LOG_LINES:] if len(lines) > MAX_LOG_LINES else lines
            return "\n".join(recent)

    return "(no recent daily log)"


def get_available_skills() -> list[str]:
    """List all skills in skill-repo/ that have references/index.md."""
    skills = []
    if SKILL_REPO_DIR.exists():
        for skill_dir in sorted(SKILL_REPO_DIR.iterdir()):
            if skill_dir.is_dir():
                index = skill_dir / "references" / "index.md"
                if index.exists():
                    skills.append(skill_dir.name)
    return skills


def build_context() -> str:
    """Assemble the context to inject into the conversation."""
    parts = []

    # Today's date
    today = datetime.now(timezone.utc).astimezone()
    parts.append(f"## Today\n{today.strftime('%A, %B %d, %Y')}")

    # AGENTS.md (the schema — tells the agent how to work with the wiki)
    if AGENTS_FILE.exists():
        agents_content = AGENTS_FILE.read_text(encoding="utf-8")
        parts.append(f"## Knowledge Base Schema\n\n{agents_content}")

    # Tier 1: Process knowledge index (always injected)
    if INDEX_FILE.exists():
        index_content = INDEX_FILE.read_text(encoding="utf-8")
        parts.append(f"## Process Knowledge Index\n\n{index_content}")
    else:
        parts.append("## Process Knowledge Index\n\n(empty - no articles compiled yet)")

    # Tier 2: Available skills for reference
    skills = get_available_skills()
    if skills:
        skill_list = ", ".join(skills)
        parts.append(
            f"## Available Skill Wikis\n\n"
            f"Skills with reference wikis: {skill_list}\n\n"
            f"To access a skill's wiki, read `skill-repo/<name>/references/index.md`."
        )

    # Recent daily log
    recent_log = get_recent_log()
    parts.append(f"## Recent Daily Log\n\n{recent_log}")

    context = "\n\n---\n\n".join(parts)

    # Truncate if too long
    if len(context) > MAX_CONTEXT_CHARS:
        context = context[:MAX_CONTEXT_CHARS] + "\n\n...(truncated)"

    return context


def main():
    context = build_context()

    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context,
        }
    }

    print(json.dumps(output))


if __name__ == "__main__":
    main()

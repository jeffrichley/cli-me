"""Path constants and configuration for the cli-me knowledge base."""

from pathlib import Path
from datetime import datetime, timezone

# -- Paths ------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent.parent
DAILY_DIR = ROOT_DIR / "daily"
KNOWLEDGE_DIR = ROOT_DIR / "knowledge"
CONCEPTS_DIR = KNOWLEDGE_DIR / "concepts"
CONNECTIONS_DIR = KNOWLEDGE_DIR / "connections"
PLAYBOOKS_DIR = KNOWLEDGE_DIR / "playbooks"
QA_DIR = KNOWLEDGE_DIR / "qa"
REPORTS_DIR = ROOT_DIR / "reports"
SCRIPTS_DIR = ROOT_DIR / "scripts"
HOOKS_DIR = ROOT_DIR / "hooks"
AGENTS_FILE = ROOT_DIR / "AGENTS.md"

INDEX_FILE = KNOWLEDGE_DIR / "index.md"
LOG_FILE = KNOWLEDGE_DIR / "log.md"
STATE_FILE = SCRIPTS_DIR / "state.json"

# -- cli-me specific paths -------------------------------------------------
# The parent cli-me repo root (one level up from claude-memory-compiler/)
CLI_ME_ROOT = ROOT_DIR.parent
SKILL_REPO_DIR = CLI_ME_ROOT / "skill-repo"
META_WIKI_DIR = CLI_ME_ROOT / ".claude" / "skills" / "cli-me-meta" / "references" / "meta-wiki"

# -- Timezone ---------------------------------------------------------------
TIMEZONE = "America/Chicago"


def now_iso() -> str:
    """Current time in ISO 8601 format."""
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def today_iso() -> str:
    """Current date in ISO 8601 format."""
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")

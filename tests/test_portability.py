"""
StockForge portability tests.

Verifies the repo is agent-cloneable:
  1. Required files (Makefile, AGENTS.md, SETUP.md, .env.example, requirements.txt)
  2. All scripts present
  3. Scripts import without errors
  4. No hardcoded /root or absolute paths to a user-specific location
  5. Helper modules present
  6. Watchlist / config files present

Run with:  pytest tests/ -v
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


# -----------------------------------------------------------------------------
# 1. Required files
# -----------------------------------------------------------------------------
@pytest.mark.parametrize("relpath", [
    "AGENTS.md",
    "SETUP.md",
    "Makefile",
    ".env.example",
    "requirements.txt",
    "README.md",
])
def test_required_files_exist(relpath: str):
    """Agent-cloneable means these top-level files are guaranteed to exist."""
    assert (ROOT / relpath).is_file(), f"Missing required file: {relpath}"


# -----------------------------------------------------------------------------
# 2. Scripts present
# -----------------------------------------------------------------------------
EXPECTED_SCRIPTS = [
    "scripts/daily_intelligence.py",
    "scripts/daily_top_picks.py",
    "scripts/analyze_stock.py",
    "scripts/screen_stocks.py",
    "scripts/llm_portfolio.py",
    "scripts/stock_pulse.py",
    "scripts/stock_risk_report.py",
    "scripts/test_alpha_zoo.py",
]


@pytest.mark.parametrize("relpath", EXPECTED_SCRIPTS)
def test_script_present(relpath: str):
    assert (ROOT / relpath).is_file(), f"Missing script: {relpath}"


# -----------------------------------------------------------------------------
# 3. Scripts import
# -----------------------------------------------------------------------------
@pytest.mark.parametrize("relpath", EXPECTED_SCRIPTS)
def test_script_parses(relpath: str):
    """All scripts must be syntactically valid Python."""
    path = ROOT / relpath
    source = path.read_text(encoding="utf-8")
    ast.parse(source, filename=str(path))


# -----------------------------------------------------------------------------
# 4. No hardcoded user-specific paths
# -----------------------------------------------------------------------------
# Patterns that indicate a non-portable hardcoded path.
# Allowed: __file__, Path(__file__), os.path.dirname(__file__), env vars
FORBIDDEN_PATH_PATTERNS = [
    re.compile(r"['\"]/root/StockForge"),                        # absolute install dir
    re.compile(r"['\"]/Users/[^'\"]*StockForge"),                # macOS user install
    re.compile(r"['\"]C:\\\\[^'\"]*StockForge"),                # Windows install
    re.compile(r"['\"]/home/\w+/StockForge"),                   # generic Linux user
]


def _python_files() -> list[Path]:
    return [
        p for p in ROOT.rglob("*.py")
        if ".venv" not in p.parts
        and "__pycache__" not in p.parts
        and ".codegraph" not in p.parts
        and ".pytest_cache" not in p.parts
    ]


def _shell_files() -> list[Path]:
    return [p for p in ROOT.rglob("*.sh") if ".venv" not in p.parts]


def test_no_hardcoded_paths_in_python():
    """No Python file should reference an absolute user-specific install path."""
    offenders = []
    for path in _python_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in FORBIDDEN_PATH_PATTERNS:
            for match in pattern.finditer(text):
                offenders.append((path.relative_to(ROOT), match.group(0)))
    assert not offenders, (
        f"Found hardcoded user paths in Python files. Use __file__ or env vars:\n"
        + "\n".join(f"  {p}: {m}" for p, m in offenders)
    )


def test_no_hardcoded_paths_in_shell():
    """No shell script should reference /root/StockForge or similar."""
    for path in _shell_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        # setup.sh and push.sh are allowed to cd to "$(dirname $0)" which is portable
        # We just check the body for absolute user paths.
        for pattern in FORBIDDEN_PATH_PATTERNS:
            assert not pattern.search(text), (
                f"{path.relative_to(ROOT)} contains hardcoded path: {pattern.pattern}"
            )


# -----------------------------------------------------------------------------
# 5. Helper modules present
# -----------------------------------------------------------------------------
HELPER_MODULES = [
    "analysis",
    "intelligence",
    "screeners",
    "portfolio",
    "risk",
    "config",
]


@pytest.mark.parametrize("relpath", HELPER_MODULES)
def test_helper_module_exists(relpath: str):
    assert (ROOT / relpath).is_dir(), f"Missing helper module: {relpath}/"


# -----------------------------------------------------------------------------
# 6. Config / watchlist present
# -----------------------------------------------------------------------------
def test_watchlist_present():
    assert (ROOT / "config" / "watchlist.txt").is_file(), "Missing config/watchlist.txt"


def test_screener_filters_present():
    assert (ROOT / "config" / "screener_filters.json").is_file(), (
        "Missing config/screener_filters.json"
    )


# -----------------------------------------------------------------------------
# 7. .env.example has at least one optional var documented
# -----------------------------------------------------------------------------
def test_env_example_documented():
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    # Should mention at least one key; the existing template has NEWSAPI_KEY
    assert "NEWSAPI_KEY" in text or "API_KEY" in text, (
        ".env.example should document at least one optional API key"
    )


# -----------------------------------------------------------------------------
# 8. Makefile has expected targets
# -----------------------------------------------------------------------------
def test_makefile_has_help_target():
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert "help:" in makefile, "Makefile must have a help target"
    assert "setup:" in makefile, "Makefile must have a setup target"
    assert "verify:" in makefile, "Makefile must have a verify target"

"""Tests: open-source hygiene — no leaks, privacy files present, ignore rules."""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Russian-specific Cyrillic letters are built via codepoints (no literals in this file)


def _tracked_files() -> list[str]:
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True)
    assert out.returncode == 0, "git ls-files failed — run inside the repo"
    return [line for line in out.stdout.splitlines() if line.strip()]


def test_no_private_paths_tokens_or_personal_data_in_tracked_files():
    forbidden = [r"G:\\", "G:/Projects", r"C:\\Users\\", "token ghp_", "ghp_",
                 "AKIA", "-----BEGIN", "api_key=", "password="]
    # the maintainer's public handle in LICENSE is intentional identity, not a leak
    allowed_handle_files = {"LICENSE"}
    handle = "".join(chr(c) for c in (0x62, 0x69, 0x67, 0x70, 0x69))  # avoid self-flagging
    # this test file necessarily contains the needle strings — skip it in its own scan
    skip_files = {"tests/test_oss_hygiene.py"}
    leaks = []
    for rel in _tracked_files():
        if rel in skip_files:
            continue
        path = ROOT / rel
        if path.stat().st_size > 2_000_000:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            continue
        for needle in forbidden:
            if needle.lower() in text.lower():
                leaks.append(f"{rel}: {needle!r}")
        if rel not in allowed_handle_files and handle in text.lower():
            leaks.append(f"{rel}: personal handle outside LICENSE")
    assert not leaks, f"privacy leaks found: {leaks}"


def test_no_russian_letters_in_tracked_text_files():
    """Policy: Ukrainian + English only. Russian-specific letters must not appear."""
    russian_only = [chr(c) for c in (0x044B, 0x044A, 0x044D, 0x0451, 0x042B, 0x042A, 0x042D, 0x0401)]
    offenders = []
    for rel in _tracked_files():
        if rel == "tests/test_oss_hygiene.py":  # this scanner defines the needles
            continue
        if not rel.endswith((".md", ".json", ".py", ".js", ".html", ".txt", ".toml", ".bat")):
            continue
        text = (ROOT / rel).read_text(encoding="utf-8", errors="ignore")
        for letter in russian_only:
            if letter in text:
                offenders.append(f"{rel}: {letter!r}")
    assert not offenders, f"Russian letters found: {offenders}"


def test_gitignore_covers_secrets_and_databases():
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".env" in ignore and "*.db" in ignore and "*.sqlite3" in ignore
    # no .env or db files are actually tracked
    tracked = _tracked_files()
    assert not any(f == ".env" or f.endswith(".db") for f in tracked)


def test_community_files_exist():
    for rel in ("CONTRIBUTING.md", "SECURITY.md", "LICENSE",
                ".github/ISSUE_TEMPLATE/bug_report.md",
                ".github/ISSUE_TEMPLATE/feature_request.md"):
        assert (ROOT / rel).exists(), f"missing community file {rel}"


def test_readme_has_contributing_section_and_topics():
    for readme in ("README.md", "README.en.md"):
        text = (ROOT / readme).read_text(encoding="utf-8")
        assert "CONTRIBUTING.md" in text and "SECURITY.md" in text
        for topic in ("habits", "gamification", "self-improvement", "fastapi", "pwa", "local-first"):
            assert topic in text, f"{readme} lacks topic {topic!r}"

"""Tests for the reusable checks' scripts."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import check_agent_instructions as agents  # noqa: E402
import check_external_wording_pr as wording  # noqa: E402


def repo(tmp_path: Path, files: dict[str, str]) -> Path:
    for rel, text in files.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return tmp_path


GOOD = "# Agents\n\nRun `make lint` and `make test`. Code is in `src/app.py`; see `docs/guide.md`.\n"


def base(tmp_path: Path, extra: dict[str, str] | None = None) -> Path:
    files = {
        "AGENTS.md": GOOD,
        "Makefile": "lint:\n\t@true\ntest:\n\t@true\n",
        "src/app.py": "x",
        "docs/guide.md": "g",
    }
    return repo(tmp_path, {**files, **(extra or {})})


def names(tmp_path: Path, extra: dict[str, str] | None = None) -> list[str]:
    base(tmp_path, extra)
    return agents.check(tmp_path)


def test_a_clean_repository_passes(tmp_path: Path) -> None:
    assert names(tmp_path) == []


def test_missing_or_empty_agents_file_fails(tmp_path: Path) -> None:
    assert any("missing" in p for p in agents.check(tmp_path))
    (tmp_path / "AGENTS.md").write_text("", encoding="utf-8")
    assert any("missing or empty" in p for p in agents.check(tmp_path))


def test_a_deliberate_cursorrules_addition_is_rejected(tmp_path: Path) -> None:
    problems = names(tmp_path, {".cursorrules": "rules"})
    assert any(".cursorrules" in p and "vendor-specific" in p for p in problems)


@pytest.mark.parametrize(
    "rel",
    [
        ".cursor/mcp.json",
        ".github/prompts/x.prompt.md",
        ".windsurfrules",
        ".aider.conf.yml",
        ".gemini/settings.json",
    ],
)
def test_other_vendor_files_are_rejected(tmp_path: Path, rel: str) -> None:
    assert names(tmp_path, {rel: "x"})


def test_pointer_files_must_be_short_and_point_at_agents(tmp_path: Path) -> None:
    assert names(tmp_path, {"CLAUDE.md": "@AGENTS.md\n"}) == []
    long_text = "\n".join(f"line {i}" for i in range(9)) + "\nAGENTS.md\n"
    assert any(
        "pointer files are at most" in p
        for p in names(tmp_path, {"GEMINI.md": long_text})
    )
    assert any(
        "does not point at AGENTS.md" in p
        for p in names(tmp_path, {".github/copilot-instructions.md": "Be nice.\n"})
    )


def test_a_make_target_that_does_not_exist_is_reported(tmp_path: Path) -> None:
    base(tmp_path)
    (tmp_path / "AGENTS.md").write_text(
        GOOD + "Also run `make pipeline`.\n", encoding="utf-8"
    )
    assert any("no target 'pipeline'" in p for p in agents.check(tmp_path))


def test_a_path_that_does_not_exist_is_reported_but_urls_and_placeholders_are_not(
    tmp_path: Path,
) -> None:
    base(tmp_path)
    (tmp_path / "AGENTS.md").write_text(
        GOOD
        + "See `docs/gone.md`, `https://example.com/a.md`, `~/x/y.md`, `src/<name>/a.py`, `src/*.py`, `/abs/p.md`.\n",
        encoding="utf-8",
    )
    problems = agents.check(tmp_path)
    assert problems == [
        "AGENTS.md mentions `docs/gone.md` which does not exist in the repository"
    ]


def test_oversized_agents_file_fails(tmp_path: Path) -> None:
    base(tmp_path)
    (tmp_path / "AGENTS.md").write_text("x" * (33 * 1024), encoding="utf-8")
    assert any("limit" in p for p in agents.check(tmp_path))


def test_cli_exit_codes(tmp_path: Path) -> None:
    base(tmp_path)

    def run(p):
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "check_agent_instructions.py"), str(p)],
            capture_output=True,
            text=True,
        )

    assert run(tmp_path).returncode == 0
    (tmp_path / ".cursorrules").write_text("x", encoding="utf-8")
    assert run(tmp_path).returncode == 1
    assert run(tmp_path / "nope").returncode == 2


# ---- wording check -------------------------------------------------------------------------------


def git(repo_dir: Path, *args: str) -> str:
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@t",
    }
    return subprocess.run(
        ["git", "-C", str(repo_dir), *args],
        capture_output=True,
        text=True,
        check=True,
        env=env,
    ).stdout.strip()


def pr_repo(tmp_path: Path, content: str, message: str):
    git(tmp_path, "init", "-q", "-b", "main")
    (tmp_path / "a.txt").write_text("base\n", encoding="utf-8")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "init")
    base_sha = git(tmp_path, "rev-parse", "HEAD")
    (tmp_path / "b.txt").write_text(content, encoding="utf-8")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", message)
    return base_sha, git(tmp_path, "rev-parse", "HEAD")


def run_check(
    tmp_path: Path, terms: str, title="Fine title", body="Fine body", sha=("", "")
):
    env = {
        **os.environ,
        "EXTERNAL_WORDING_TERMS": terms,
        "PR_TITLE": title,
        "PR_BODY": body,
        "BASE_SHA": sha[0],
        "HEAD_SHA": sha[1],
    }
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "check_external_wording_pr.py")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def test_no_terms_configured_passes_with_a_notice(tmp_path: Path) -> None:
    result = run_check(tmp_path, "")
    assert result.returncode == 0 and "NOTICE" in result.stdout


def test_clean_pull_request_passes(tmp_path: Path) -> None:
    sha = pr_repo(tmp_path, "hello\n", "docs: hello")
    assert run_check(tmp_path, "zebra", sha=sha).returncode == 0


@pytest.mark.parametrize("where", ["title", "body", "commit", "line"])
def test_each_place_is_checked_and_the_term_is_never_printed(
    tmp_path: Path, where: str
) -> None:
    secret = "zebracorn"
    sha = pr_repo(
        tmp_path,
        f"x\nthis has {secret} in it\n" if where == "line" else "x\n",
        f"feat: {secret}" if where == "commit" else "feat: ok",
    )
    result = run_check(
        tmp_path,
        f"# comment\n{secret}\n",
        title=f"t {secret}" if where == "title" else "t",
        body=f"b {secret}" if where == "body" else "b",
        sha=sha,
    )
    assert result.returncode == 1
    assert secret not in result.stdout + result.stderr, (
        "the term must never appear in CI logs"
    )
    assert "matches listed term #2" in result.stdout


def test_comma_lists_whole_words_and_case_insensitivity() -> None:
    terms = wording.parse_terms("alpha, word:bob")
    assert wording.first_hit("ALPHA", terms) == 1
    assert wording.first_hit("a bob ran", terms) == 2
    assert wording.first_hit("bobcat", terms) is None


def test_a_git_error_exits_two(tmp_path: Path) -> None:
    assert run_check(tmp_path, "zebra", sha=("deadbeef", "cafebabe")).returncode == 2

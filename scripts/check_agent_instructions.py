#!/usr/bin/env python3
"""Check that a repository keeps ONE generic agent-instructions file and only pointers for other clients.

Rules
  1. `AGENTS.md` exists at the repository root, is not empty and is at most 32 KB.
  2. Pointer files (`CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`), when present, have at most 5
     non-empty lines and mention `AGENTS.md`.
  3. No other vendor instruction files: `.cursorrules`, `.cursor/`, `.windsurfrules`, `.clinerules`, `.aider*`,
     `.continue/`, `.github/prompts/`, `.gemini/`.
  4. Accuracy: every `make <target>` written in backticks in `AGENTS.md` exists in the Makefile, and every relative
     path written in backticks exists in the repository (URLs, absolute and home paths, placeholders, globs, `owner/repo` slugs and
     action references are skipped).

Usage: check_agent_instructions.py [REPO_DIR]        Exit codes: 0 clean, 1 violations, 2 not a repository.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

POINTERS = ("CLAUDE.md", "GEMINI.md", ".github/copilot-instructions.md")
FORBIDDEN = (
    ".cursorrules",
    ".cursor",
    ".windsurfrules",
    ".clinerules",
    ".continue",
    ".github/prompts",
    ".gemini",
)
MAX_BYTES = 32 * 1024
POINTER_LINES = 5
PATH_EXT = (
    ".md",
    ".py",
    ".yml",
    ".yaml",
    ".toml",
    ".json",
    ".sh",
    ".cfg",
    ".ini",
    ".txt",
    ".mk",
)
TICKS = re.compile(r"`([^`\n]+)`")
MAKE_CALL = re.compile(r"^make\s+([A-Za-z0-9_.-]+)")


def makefile_targets(repo: Path) -> set[str]:
    path = repo / "Makefile"
    if not path.is_file():
        return set()
    return set(
        re.findall(
            r"^([A-Za-z0-9_.-]+)\s*:(?!=)",
            path.read_text(encoding="utf-8", errors="replace"),
            re.M,
        )
    )


# `owner/repo` slugs and action references name other repositories, not files in this one.
EXTERNAL_PREFIXES = ("PetroSa2/", "actions/", "docker/", "astral-sh/", "OWNER/")


def looks_like_path(token: str) -> bool:
    if any(c in token for c in "<>{}*$|=: ") or token.startswith(
        ("http", "/", "~", "-", "@", "#", "..") + EXTERNAL_PREFIXES
    ):
        return False
    token = token.split("#", 1)[0].rstrip(".,;:)")
    return bool(token) and ("/" in token or token.endswith(PATH_EXT))


def check(repo: Path) -> list[str]:
    problems: list[str] = []
    agents = repo / "AGENTS.md"
    if not agents.is_file() or agents.stat().st_size == 0:
        problems.append("AGENTS.md is missing or empty")
    elif agents.stat().st_size > MAX_BYTES:
        problems.append(
            f"AGENTS.md is {agents.stat().st_size} bytes (limit {MAX_BYTES})"
        )

    for rel in POINTERS:
        path = repo / rel
        if path.is_file():
            lines = [
                line
                for line in path.read_text(
                    encoding="utf-8", errors="replace"
                ).splitlines()
                if line.strip()
            ]
            if len(lines) > POINTER_LINES:
                problems.append(
                    f"{rel} has {len(lines)} lines: pointer files are at most {POINTER_LINES}"
                )
            if "AGENTS.md" not in "\n".join(lines):
                problems.append(f"{rel} does not point at AGENTS.md")

    for rel in FORBIDDEN:
        if (repo / rel).exists():
            problems.append(
                f"{rel} is a vendor-specific instruction file: merge it into AGENTS.md or docs and delete it"
            )
    for path in repo.glob(".aider*"):
        problems.append(f"{path.name} is a vendor-specific instruction file")

    if agents.is_file():
        text = agents.read_text(encoding="utf-8", errors="replace")
        targets = makefile_targets(repo)
        for token in TICKS.findall(text):
            token = token.strip()
            call = MAKE_CALL.match(token)
            if call and call.group(1) not in targets:
                problems.append(
                    f"AGENTS.md mentions `{token}` but the Makefile has no target '{call.group(1)}'"
                )
            elif looks_like_path(token):
                rel = token.split("#", 1)[0].rstrip(".,;:)")
                if not (repo / rel).exists():
                    problems.append(
                        f"AGENTS.md mentions `{token}` which does not exist in the repository"
                    )
    return problems


def main(argv: list[str]) -> int:
    repo = Path(argv[1]) if len(argv) > 1 else Path.cwd()
    if not repo.is_dir():
        sys.stderr.write(f"agent-instructions: ERROR: {repo} is not a directory\n")
        return 2
    problems = check(repo)
    for line in problems:
        sys.stderr.write(f"agent-instructions: {line}\n")
    if problems:
        sys.stderr.write(f"agent-instructions: FAILED, {len(problems)} problem(s)\n")
        return 1
    sys.stderr.write("agent-instructions: OK\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

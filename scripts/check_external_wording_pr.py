#!/usr/bin/env python3
"""Fail a pull request whose title, body, commit messages or added lines contain a listed term.

The term list comes from the organisation Actions variable `EXTERNAL_WORDING_TERMS` (passed in the environment
as EXTERNAL_WORDING_TERMS), so the terms never appear in public code. One term per line or comma-separated;
`word:term` matches a whole word, anything else is a case-insensitive substring. The terms are never printed:
a finding names the place (title, body, commit, file:line) and the index of the term only.

Environment: EXTERNAL_WORDING_TERMS, PR_TITLE, PR_BODY, BASE_SHA, HEAD_SHA (and a git checkout with history).
Exit codes: 0 clean or no terms configured (a notice says so), 1 violations, 2 git error.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys


def parse_terms(raw: str) -> list[tuple[int, re.Pattern[str]]]:
    terms: list[tuple[int, re.Pattern[str]]] = []
    for index, item in enumerate(t.strip() for t in re.split(r"[\n,]", raw or "")):
        if not item or item.startswith("#"):
            continue
        if item.lower().startswith("word:"):
            token = item[5:].strip()
            if token:
                terms.append(
                    (index + 1, re.compile(r"\b" + re.escape(token) + r"\b", re.I))
                )
        else:
            terms.append((index + 1, re.compile(re.escape(item), re.I)))
    return terms


def first_hit(text: str, terms: list[tuple[int, re.Pattern[str]]]) -> int | None:
    for index, pattern in terms:
        if pattern.search(text or ""):
            return index
    return None


def git(*args: str) -> str:
    out = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip() or "git failed")
    return out.stdout


def added_lines(diff: str):
    path, line_no = "", 0
    for line in diff.splitlines():
        if line.startswith("+++ "):
            path = line[6:] if line.startswith("+++ b/") else line[4:]
        elif line.startswith("@@"):
            m = re.search(r"\+(\d+)", line)
            line_no = int(m.group(1)) - 1 if m else 0
        elif line.startswith("+") and not line.startswith("+++"):
            line_no += 1
            yield path, line_no, line[1:]
        elif not line.startswith("-"):
            line_no += 1


def main() -> int:
    terms = parse_terms(os.environ.get("EXTERNAL_WORDING_TERMS", ""))
    if not terms:
        print(
            "external-wording: NOTICE: no terms configured (organisation variable EXTERNAL_WORDING_TERMS is empty); nothing checked"
        )
        return 0
    findings: list[str] = []
    for place, key in (("PR title", "PR_TITLE"), ("PR body", "PR_BODY")):
        hit = first_hit(os.environ.get(key, ""), terms)
        if hit:
            findings.append(f"{place} matches listed term #{hit}")
    base, head = os.environ.get("BASE_SHA", ""), os.environ.get("HEAD_SHA", "")
    try:
        if base and head:
            for sha, message in (
                block.split("\n", 1) if "\n" in block else (block, "")
                for block in git("log", "--format=%H%n%B%x00", f"{base}..{head}").split(
                    "\x00"
                )
                if block.strip()
            ):
                hit = first_hit(message, terms)
                if hit:
                    findings.append(
                        f"commit {sha.strip()[:10]} message matches listed term #{hit}"
                    )
            for path, line_no, text in added_lines(
                git("diff", "--unified=0", f"{base}...{head}")
            ):
                hit = first_hit(text, terms) or first_hit(path, terms)
                if hit:
                    findings.append(f"{path}:{line_no} matches listed term #{hit}")
    except RuntimeError as exc:
        sys.stderr.write(f"external-wording: ERROR: {exc}\n")
        return 2
    for finding in findings:
        print(f"external-wording: {finding}")
    if findings:
        print(
            "external-wording: FAILED. Reword generically (for example 'Agentic Developer', 'ticket orchestrator'). "
            "The listed terms are configured in the organisation, not in this repository."
        )
        return 1
    print(f"external-wording: OK ({len(terms)} term(s) checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

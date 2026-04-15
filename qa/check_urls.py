"""Deterministic URL checker for wiki technique pages.

Crawls every URL in every .md file under skill-repo/*/references/
and reports HTTP status. No LLM judgment — just status codes.

Usage:
    uv run qa/check_urls.py                    # check all skills
    uv run qa/check_urls.py ffmpeg             # check one skill
    uv run qa/check_urls.py ffmpeg --fix       # interactive: prompt to remove dead URLs
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import urllib.request
import urllib.error
import ssl


SKILL_REPO = Path(__file__).parent.parent / "skill-repo"
URL_PATTERN = re.compile(r'https?://[^\s\)>\]"\'`]+')

# Some sites block default Python UA
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; cli-me-url-checker/1.0)"
}

# Skip URLs known to block automated access
SKIP_DOMAINS = {
    "trac.ffmpeg.org",  # Anubis anti-bot wall
}

# Domains that block HEAD requests but work with GET
GET_ONLY_DOMAINS = {
    "support.google.com",  # Returns 404 on HEAD, 200 on GET
}

# SSL context that doesn't verify (some sites have bad certs)
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE


def extract_urls(text: str) -> list[str]:
    """Extract all HTTP(S) URLs from markdown text."""
    urls = URL_PATTERN.findall(text)
    # Clean trailing punctuation that's not part of the URL
    cleaned = []
    for url in urls:
        url = url.rstrip(".,;:!?")
        # Remove trailing ) if there's no matching ( in the URL
        while url.endswith(")") and url.count("(") < url.count(")"):
            url = url[:-1]
        cleaned.append(url)
    return list(dict.fromkeys(cleaned))  # dedupe, preserve order


def check_url(url: str, timeout: int = 15) -> tuple[int, str]:
    """Check a URL and return (status_code, description).

    Returns:
        (200, "OK")
        (301, "REDIRECT → <location>")
        (403, "FORBIDDEN")
        (404, "NOT FOUND")
        (0, "ERROR: <message>")
    """
    parsed = urlparse(url)
    if parsed.hostname in SKIP_DOMAINS:
        return (-1, "SKIPPED (known bot-blocker)")

    method = "GET" if parsed.hostname in GET_ONLY_DOMAINS else "HEAD"
    req = urllib.request.Request(url, headers=HEADERS, method=method)
    try:
        resp = urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX)
        return (resp.status, "OK")
    except urllib.error.HTTPError as e:
        if e.code in (301, 302, 307, 308):
            location = e.headers.get("Location", "unknown")
            return (e.code, f"REDIRECT → {location}")
        return (e.code, e.reason)
    except urllib.error.URLError as e:
        return (0, f"ERROR: {e.reason}")
    except Exception as e:
        return (0, f"ERROR: {e}")


def check_skill(skill_name: str) -> list[dict]:
    """Check all URLs in a skill's references directory."""
    refs_dir = SKILL_REPO / skill_name / "references"
    if not refs_dir.exists():
        print(f"No references directory for skill '{skill_name}'")
        return []

    results = []
    for md_file in sorted(refs_dir.rglob("*.md")):
        text = md_file.read_text(encoding="utf-8", errors="replace")
        urls = extract_urls(text)
        if not urls:
            continue

        rel_path = md_file.relative_to(SKILL_REPO / skill_name)
        for url in urls:
            status, desc = check_url(url)
            results.append({
                "file": str(rel_path),
                "url": url,
                "status": status,
                "description": desc,
            })
            # Rate limit
            time.sleep(0.3)

    return results


def main():
    skill_filter = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else None

    if skill_filter:
        skills = [skill_filter]
    else:
        skills = sorted(
            d.name for d in SKILL_REPO.iterdir()
            if d.is_dir() and (d / "SKILL.md").exists()
        )

    total_checked = 0
    total_dead = 0
    all_results = []

    for skill in skills:
        print(f"\n{'='*60}")
        print(f"Checking: {skill}")
        print(f"{'='*60}")

        results = check_skill(skill)
        all_results.extend(results)

        current_file = None
        for r in results:
            if r["file"] != current_file:
                current_file = r["file"]
                print(f"\n  {current_file}")

            total_checked += 1
            status = r["status"]
            url_short = r["url"][:80] + ("..." if len(r["url"]) > 80 else "")

            if status == 200:
                print(f"    ✓ {status} {url_short}")
            elif status == -1:
                print(f"    ⊘ SKIP {url_short} ({r['description']})")
            elif 300 <= status < 400:
                print(f"    → {status} {url_short} ({r['description']})")
                total_dead += 1
            else:
                print(f"    ✗ {status} {url_short} ({r['description']})")
                total_dead += 1

    # Summary
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"  URLs checked:  {total_checked}")
    print(f"  Live (200):    {sum(1 for r in all_results if r['status'] == 200)}")
    print(f"  Redirects:     {sum(1 for r in all_results if 300 <= r['status'] < 400)}")
    print(f"  Dead/Error:    {sum(1 for r in all_results if r['status'] != 200 and r['status'] != -1 and not (300 <= r['status'] < 400))}")
    print(f"  Skipped:       {sum(1 for r in all_results if r['status'] == -1)}")

    if total_dead > 0:
        print(f"\n  DEAD/REDIRECT URLs:")
        for r in all_results:
            if r["status"] != 200 and r["status"] != -1:
                print(f"    [{r['status']}] {r['file']}: {r['url']}")

    return 1 if total_dead > 0 else 0


if __name__ == "__main__":
    sys.exit(main())

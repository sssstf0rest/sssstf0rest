#!/usr/bin/env python3
"""Regenerate the Featured Gallery in README.md.

Renders a curated list of repos as a two-column table, ranked by stars, in the
same markup freestylefly/freestylefly uses: name, description, then a
"Stars · Forks · Updated" line. Stats come from the GitHub API, so they stay
current without hand-editing.

Standard library only, so CI needs no dependency install.

Env:
  GITHUB_TOKEN  optional, raises the API rate limit from 60/hr to 5000/hr
  USERNAME      repo owner (default: sssstf0rest)
"""

import html
import json
import os
import re
import sys
import urllib.error
import urllib.request

USERNAME = os.environ.get("USERNAME", "sssstf0rest")
README = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "README.md")

START = "<!-- FEATURED:START -->"
END = "<!-- FEATURED:END -->"

# The curated list. Order here doesn't matter — output is ranked by stars.
REPOS = [
    "Open-Bookmarks-in-New-Tab",
    "TabCloser",
    "YouTube-in-New-Tab",
    "Open-Rubato",
]

# Fallback blurbs for repos with no GitHub description. Setting the description
# on the repo itself is better: it shows up on GitHub too, and this dict can
# then be emptied.
DESCRIPTIONS = {
    "Open-Rubato": "TODO — add a description on the repo page and this line disappears.",
}


def rate_limit_note(e):
    """Turn a 403/429 into an actionable message instead of a traceback."""
    remaining = e.headers.get("x-ratelimit-remaining")
    reset = e.headers.get("x-ratelimit-reset")
    if remaining == "0":
        when = ""
        if reset:
            import datetime
            t = datetime.datetime.fromtimestamp(int(reset), datetime.timezone.utc)
            when = f" Resets at {t:%H:%M:%S} UTC."
        tok = "" if os.environ.get("GITHUB_TOKEN") else (
            " Set GITHUB_TOKEN to raise the limit from 60/hr to 5000/hr.")
        return f"GitHub API rate limit exceeded.{when}{tok}"
    return f"HTTP {e.code}: {e.reason}"


def api(url):
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{USERNAME}-profile-readme",
    })
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def fetch(name):
    try:
        d = api(f"https://api.github.com/repos/{USERNAME}/{name}")
    except urllib.error.HTTPError as e:
        print(f"  ! skipping {name}: {rate_limit_note(e)}", file=sys.stderr)
        return None
    except Exception as e:  # noqa: BLE001
        print(f"  ! skipping {name}: {e}", file=sys.stderr)
        return None

    desc = d.get("description") or DESCRIPTIONS.get(name) or "—"
    return {
        "name": d["name"],
        "url": d["html_url"],
        "desc": desc,
        "stars": d.get("stargazers_count", 0),
        "forks": d.get("forks_count", 0),
        "updated": (d.get("pushed_at") or "")[:10],
    }


def cell(r):
    name = html.escape(r["name"])
    url = html.escape(r["url"], quote=True)
    desc = html.escape(r["desc"])
    return (
        '<td width="50%" valign="top">\n'
        f'  <a href="{url}"><strong>{name}</strong></a><br>\n'
        f"  <sub>{desc}</sub><br><br>\n"
        f'  <sub>Stars: <strong>{r["stars"]:,}</strong> · '
        f'Forks: <strong>{r["forks"]:,}</strong> · '
        f'Updated: <strong>{r["updated"]}</strong></sub>\n'
        "</td>"
    )


def render(rows):
    if not rows:
        return "\n_No projects to show yet._\n"

    lines = ["", "<table>"]
    for i in range(0, len(rows), 2):
        lines.append("<tr>")
        pair = rows[i : i + 2]
        for r in pair:
            lines.append(cell(r))
        if len(pair) == 1:
            # Keep the table rectangular when the count is odd.
            lines.append('<td width="50%"></td>')
        lines.append("</tr>")
    lines.append("</table>")
    lines.append("")
    return "\n".join(lines)


def main():
    rows = [r for r in (fetch(n) for n in REPOS) if r]
    if not rows and REPOS:
        # Every lookup failed (rate limit, network). Leave the existing gallery
        # in place rather than replacing it with an empty-state message.
        print("error: no repos could be fetched; leaving README untouched", file=sys.stderr)
        return 1
    rows.sort(key=lambda r: (-r["stars"], -r["forks"], r["name"].lower()))
    print(f"fetched {len(rows)}/{len(REPOS)} repos")

    with open(README, encoding="utf-8") as f:
        readme = f.read()

    if START not in readme or END not in readme:
        print(f"markers not found in {README} — nothing to do", file=sys.stderr)
        return 1

    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
    updated = pattern.sub(START + render(rows) + END, readme)

    if updated == readme:
        print("no change")
        return 0

    with open(README, "w", encoding="utf-8") as f:
        f.write(updated)
    print(f"README.md updated with {len(rows)} projects")
    return 0


if __name__ == "__main__":
    sys.exit(main())

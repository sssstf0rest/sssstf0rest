#!/usr/bin/env python3
"""Regenerate the follower wall in README.md.

Fetches every follower, enriches each with their display name and follower
count, sorts by that count, and rewrites the block between the
START/END_SECTION:top-followers markers.

Standard library only, so CI needs no dependency install.

Env:
  GITHUB_TOKEN  optional, but raises the API rate limit from 60/hr to 5000/hr
  USERNAME      profile to read followers from (default: sssstf0rest)
  PER_ROW       avatars per table row (default: 6)
  MAX_SHOWN     cap on avatars rendered; 0 means no cap (default: 24)
"""

import html
import json
import os
import re
import sys
import urllib.error
import urllib.request

USERNAME = os.environ.get("USERNAME", "sssstf0rest")
PER_ROW = int(os.environ.get("PER_ROW", "6"))
MAX_SHOWN = int(os.environ.get("MAX_SHOWN", "24"))
README = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "README.md")

START = "<!--START_SECTION:top-followers-->"
END = "<!--END_SECTION:top-followers-->"

# Display names are user-controlled text from the GitHub API. They are escaped
# before being written into the table, never interpolated raw.
NAME_MAX = 22


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
        return json.load(resp), resp.headers


def fetch_followers():
    """All followers, following pagination."""
    out, page = [], 1
    while True:
        batch, _ = api(
            f"https://api.github.com/users/{USERNAME}/followers?per_page=100&page={page}"
        )
        if not batch:
            break
        out.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return out


def enrich(followers):
    """Add each follower's own follower count and display name."""
    rows = []
    for u in followers:
        login = u["login"]
        try:
            p, _ = api(u["url"])
            rows.append({
                "login": login,
                "name": p.get("name") or login,
                "avatar": p.get("avatar_url") or u.get("avatar_url", ""),
                "followers": p.get("followers", 0),
            })
        except urllib.error.HTTPError as e:
            # A suspended or renamed account shouldn't sink the whole run.
            print(f"  ! skipping {login}: HTTP {e.code}", file=sys.stderr)
        except Exception as e:  # noqa: BLE001
            print(f"  ! skipping {login}: {e}", file=sys.stderr)
    rows.sort(key=lambda r: (-r["followers"], r["login"].lower()))
    return rows


def truncate(name):
    name = " ".join(name.split())
    return name if len(name) <= NAME_MAX else name[: NAME_MAX - 1] + "…"


def render(rows):
    if not rows:
        return "\n_No followers to show yet._\n"

    shown = rows[:MAX_SHOWN] if MAX_SHOWN else rows
    lines = ["", "<table>"]
    for i in range(0, len(shown), PER_ROW):
        lines.append("  <tr>")
        for r in shown[i : i + PER_ROW]:
            login = html.escape(r["login"], quote=True)
            name = html.escape(truncate(r["name"]), quote=True)
            avatar = html.escape(r["avatar"], quote=True)
            lines.append(
                f'    <td align="center">\n'
                f'      <a href="https://github.com/{login}">\n'
                f'        <img src="{avatar}&s=100" width="80" alt="{login}" />\n'
                f"      </a>\n"
                f"      <br />\n"
                f'      <a href="https://github.com/{login}"><sub><b>{name}</b></sub></a>\n'
                f"    </td>"
            )
        lines.append("  </tr>")
    lines.append("</table>")

    total = len(rows)
    if MAX_SHOWN and total > MAX_SHOWN:
        lines.append(f"\n<sub>Showing {MAX_SHOWN} of {total} followers.</sub>")
    lines.append("")
    return "\n".join(lines)


def main():
    try:
        followers = fetch_followers()
    except urllib.error.HTTPError as e:
        print(f"error: {rate_limit_note(e)}", file=sys.stderr)
        return 1
    except Exception as e:  # noqa: BLE001
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(f"fetched {len(followers)} followers for {USERNAME}")
    rows = enrich(followers)
    print(f"enriched {len(rows)}")

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
    print(f"README.md updated with {min(len(rows), MAX_SHOWN or len(rows))} avatars")
    return 0


if __name__ == "__main__":
    sys.exit(main())

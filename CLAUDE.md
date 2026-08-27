# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

This is a GitHub **profile repository** (`sssstf0rest/sssstf0rest` — the repo name matches the username, so the root `README.md` renders on the user's GitHub profile page). It contains no application code, no build system, no tests, and no dependencies.

There are exactly two kinds of content:

1. **`README.md` (root)** — hand-maintained. It embeds a few of the generated cards via `raw.githubusercontent.com` URLs. This is the only file a human normally edits.
2. **`profile-summary-card-output/`** — fully machine-generated, committed by CI. Never hand-edit anything under it.

## The generation pipeline

`.github/workflows/profile-summary-cards.yml` runs the third-party action [`vn7n24fzkq/github-profile-summary-cards@release`](https://github.com/vn7n24fzkq/github-profile-summary-cards) on `create`, on `push`, on a daily-ish cron, and on manual dispatch. The action queries the GitHub API for `github.repository_owner`, renders the cards, and commits them back to `master` (hence `permissions: contents: write` and the wall of identical `Generate profile summary cards` commits in the history).

Output layout — one directory per theme (~66 of them: `default`, `dracula`, `nord_dark`, `vue`, …), each containing the same five SVGs plus a per-theme `README.md` with copy-paste embed snippets:

```
profile-summary-card-output/<theme>/
  0-profile-details.svg
  1-repos-per-language.svg
  2-most-commit-language.svg
  3-stats.svg
  4-productive-time.svg
  README.md
```

The theme set, the SVG contents, and the per-theme READMEs are all owned by the upstream action. To change what the cards look like, change the action's inputs in the workflow (or the action version) — not the SVGs. Committing edits to generated files just guarantees they get clobbered on the next run.

## Working in this repo

- There is nothing to build, lint, or test. Changes are verified by pushing and letting the workflow run, or by triggering it from the Actions tab (`workflow_dispatch`).
- Regenerating locally is not set up; the action is the only supported path.
- Any diff that touches hundreds of SVGs is CI's, not yours. Keep hand-written commits scoped to `README.md` and `.github/workflows/`.

## Known problems in the current state

Both are pre-existing; mention them rather than silently working around them.

**1. A GitHub personal access token is committed in plaintext.** `.github/workflows/profile-summary-cards-haoshen.yml` writes the token literal into the secret *name*:

```yaml
GITHUB_TOKEN: ${{ secrets.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 }}
```

This does not work as intended (it dereferences a secret that doesn't exist, yielding an empty string) *and* it leaks the token into git history and any fork or clone. The token must be revoked on GitHub, and the reference replaced with `${{ secrets.GITHUB_TOKEN }}` as the sibling workflow already does.

**2. `profile-summary-cards-haoshen.yml` is invalid YAML.** Its `jobs:` key has an empty value and `build:` sits at column 0 as a sibling top-level key, so GitHub Actions rejects the file. Only `profile-summary-cards.yml` actually runs. The two workflows are otherwise near-duplicates with the same `name:`; the broken one is most likely meant to be deleted rather than fixed.

**3. Root `README.md` points at the wrong repo.** Its embed URLs use `sssstf0rest/test_repo`, but the remote is `sssstf0rest/sssstf0rest` (which is what the generated per-theme READMEs correctly use), so the profile images resolve to a repo that isn't this one.

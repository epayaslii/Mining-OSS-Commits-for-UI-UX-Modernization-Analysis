"""
Phase 2: Commit-Level Mining (refined)

This script mines commits from repositories and identifies UI-related commits using:
1. Keyword matching with word-boundary regex (UI, accessibility, visual, theme, etc.)
2. Tiered file-type detection (Tier 1: stylesheets, Tier 2: components in UI directories,
   plus package.json diffs against a known UI-library list)
3. Date filtering (commits after June 26, 2024)
4. Prefix/bot exclusion (automated chore/deps/release commits, dependabot/renovate/CI bots)

Refined from the original keyword-substring version to cut false positives: adds bot-author
exclusion, regex word-boundary keyword matching (so "ui" doesn't match inside "build"),
directory-aware component detection, and a durable per-commit file cache so re-runs never
re-fetch a commit's file list from the GitHub API.

Output: ui_commits_checkpoint_final.csv with all mined UI commits
"""

import os
import re
import time
import requests
import concurrent.futures
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')

# ============================================================================
# Configuration
# ============================================================================

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "your_token_here")
SESSION = requests.Session()
SESSION.headers.update({
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
})

INPUT_CSV = "repositories_filtered.csv"
OUTPUT_CSV = "ui_commits_checkpoint_final.csv"
FILECACHE = "commit_files_cache.csv"   # sha -> filenames (durable across runs)
DONEFILE = "done_repos.txt"            # fully-processed repos

CUTOFF_DATE = "2024-06-26"
SAVE_INTERVAL = 10  # Save checkpoint every 10 repos

# ============================================================================
# Keywords & Filters
# ============================================================================

UI_SURFACE = (
    "ui:", "(ui)", "[ui]", "fix(ui)", "feat(ui)", "chore(ui)",
    "style(ui)", "refactor(ui)", "user interface"
)
UI_WORD_RE = re.compile(
    r"\b(ui|visual|usability|accessibility|a11y|theme|responsive|dark\s*mode|design\s*system)\b",
    re.I
)

EXCLUDE_PREFIXES = (
    "chore(deps", "chore(release", "chore: bump", "chore: release", "chore: version",
    "chore: update dep", "chore: update all", "chore: update lock", "chore: lock",
    "fix(deps", "build(deps", "deps:", "bump ", "release:", "merge ", "ci:",
    "test:", "build:", "docs:", "meta:", "refactor(docs", "fix lint", "fix: lint",
    "fix linter", "revert",
)
VERSION_ONLY_RE = re.compile(r"^v?\d+\.\d+(\.\d+)?", re.I)
BOT_RE = re.compile(r"(dependabot|renovate|github-actions|weblate)", re.I)

# Tier 1: stylesheets (always UI). Tier 2: components, only if inside a UI directory.
TIER1_STYLE = (".css", ".scss", ".sass", ".less", ".styl")
TIER2_COMP = (".tsx", ".jsx", ".vue", ".svelte")
UI_DIRS = (
    "/components/", "/component/", "/ui/", "/views/", "/view/", "/layouts/",
    "/pages/", "/theme/", "/themes/", "/styles/", "/style/", "/assets/",
    "/design/", "/widgets/"
)
TEST_RE = re.compile(r"(__tests__|\.test\.|\.spec\.|/tests?/|/e2e/|\.stories\.)", re.I)
UI_LIBS = (
    "react", "vue", "@angular/core", "svelte", "next", "nuxt", "gatsby",
    "antd", "@ant-design", "@mui/", "@material-ui", "@chakra-ui", "@mantine/",
    "tailwindcss", "styled-components", "@emotion/", "bootstrap", "@radix-ui",
    "shadcn", "primereact", "element-plus"
)

# ============================================================================
# GitHub API Functions
# ============================================================================

def has_ui_keyword(msg):
    """Word-boundary keyword match, so substrings like 'build' don't match 'ui'."""
    if not isinstance(msg, str):
        return False
    return any(s in f" {msg.lower()} " for s in UI_SURFACE) or bool(UI_WORD_RE.search(msg))


def is_excluded(msg):
    """True for automated/bot-style commits (deps bumps, releases, version-only, lint)."""
    if not isinstance(msg, str):
        return True
    m = msg.lower().strip()
    return m.startswith(EXCLUDE_PREFIXES) or bool(VERSION_ONLY_RE.match(m)) or "version packages" in m


def ui_file_hit(f):
    """Tiered file classification: stylesheets always count; components only in UI dirs;
    package.json only counts if the diff touches a known UI library."""
    name = (f.get("filename") or "").lower()
    if not name or TEST_RE.search(name):
        return False
    if name.endswith(TIER1_STYLE):
        return True
    if name.endswith(TIER2_COMP):
        return any(d in f"/{name}" for d in UI_DIRS)
    if name.endswith("package.json"):
        patch = f.get("patch") or ""
        chg = [ln for ln in patch.splitlines() if ln[:1] in "+-"]
        return any(lib in ln.lower() for ln in chg for lib in UI_LIBS)
    return False


def gh_get(url, params=None, tries=4):
    """Rate-limit-aware GET with per-request timeouts (avoids hangs)."""
    for i in range(tries):
        try:
            r = SESSION.get(url, params=params, timeout=(5, 12))
        except requests.RequestException:
            time.sleep(2 ** i)
            continue
        if r.status_code == 200:
            return r.json()
        if r.status_code in (403, 429):
            reset = int(r.headers.get("X-RateLimit-Reset", time.time() + 30))
            wait = max(5, min(reset - int(time.time()) + 1, 300))
            print(f"    rate limited, sleeping {wait}s", flush=True)
            time.sleep(wait)
        elif r.status_code in (404, 409, 422, 451):
            return None
        else:
            time.sleep(2 ** i)
    return None


def list_commits(repo, page):
    return gh_get(f"https://api.github.com/repos/{repo}/commits",
                  params={"per_page": 100, "page": page}) or []


# Durable per-commit file cache: loaded once, appended to immediately on every fetch
# so an interrupted run never re-fetches a commit's files from the API.
_cache = {}
if os.path.exists(FILECACHE):
    _cache = dict(zip(*[pd.read_csv(FILECACHE).fillna("")[c] for c in ("sha", "filenames")]))
    print(f"file cache: {len(_cache)} commits")
_cache_fh = open(FILECACHE, "a")
if not os.path.exists(FILECACHE) or os.path.getsize(FILECACHE) == 0:
    _cache_fh.write("sha,filenames\n")
    _cache_fh.flush()


def fetch_files(repo, sha):
    """Return (filenames_str, ui_hit). Cached per sha; each fetch persisted immediately."""
    if sha in _cache:
        names = _cache[sha]
        hit = any(
            n.lower().endswith(TIER1_STYLE) or
            (n.lower().endswith(TIER2_COMP) and any(d in f"/{n.lower()}" for d in UI_DIRS))
            for n in names.split("|") if n and not TEST_RE.search(n)
        )
        return names, hit

    data = gh_get(f"https://api.github.com/repos/{repo}/commits/{sha}")
    files = (data or {}).get("files", [])
    names = "|".join((f.get("filename") or "") for f in files)[:1000]
    hit = any(ui_file_hit(f) for f in files)
    _cache[sha] = names
    _cache_fh.write(f'{sha},"{names}"\n')
    _cache_fh.flush()
    return names, hit


def process_repo(repo):
    """Mine commits from a single repository."""
    out, stop = [], False

    for page in (1, 2):  # Max 200 commits per repo
        if stop:
            break
        commits = list_commits(repo, page)
        if not isinstance(commits, list) or not commits:
            break

        cands = []
        for c in commits:
            sha = c.get("sha", "")
            author = (c.get("author") or {}).get("login") or \
                c.get("commit", {}).get("author", {}).get("name", "")
            msg = c.get("commit", {}).get("message", "")
            date = c.get("commit", {}).get("author", {}).get("date", "")

            if date and date[:10] < CUTOFF_DATE:
                stop = True
                break
            if BOT_RE.search(author or ""):
                continue
            if has_ui_keyword(msg):
                cands.append((sha, msg, date, True))
            elif is_excluded(msg):
                continue
            else:
                cands.append((sha, msg, date, False))

        def work(item):
            sha, msg, date, kw = item
            names, hit = fetch_files(repo, sha)
            return sha, msg, date, kw, hit, names

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            for sha, msg, date, kw, hit, names in executor.map(work, cands):
                if hit or (kw and names):
                    out.append({
                        "repo": repo, "sha": sha, "message": msg[:300], "date": date,
                        "keyword_match": kw, "file_match": hit, "filenames": names
                    })

    return out


# ============================================================================
# Main Mining Loop
# ============================================================================

def mine_commits():
    """Mine UI-related commits from all repositories, resumable across runs."""
    df_repos = pd.read_csv(INPUT_CSV)
    rows = pd.read_csv(OUTPUT_CSV).to_dict("records") if os.path.exists(OUTPUT_CSV) else []
    done = set(open(DONEFILE).read().split()) if os.path.exists(DONEFILE) else set()
    print(f"resuming: {len(done)} repos done, {len(rows)} rows")

    for idx, row in df_repos.iterrows():
        repo = row["name"]
        if repo in done:
            continue
        print(f"[{idx+1}/{len(df_repos)}] Mining {repo}...", flush=True)
        try:
            results = process_repo(repo)
            rows.extend(results)
            print(f"    +{len(results)}", flush=True)
            done.add(repo)  # mark done ONLY on success
            if (idx + 1) % SAVE_INTERVAL == 0:
                pd.DataFrame(rows).to_csv(OUTPUT_CSV, index=False)
                open(DONEFILE, "w").write("\n".join(sorted(done)))
                print("    >>> Checkpoint saved.")
        except Exception as e:
            print(f"    error: {e} (will retry next run)", flush=True)  # not marked done

    pd.DataFrame(rows).to_csv(OUTPUT_CSV, index=False)
    open(DONEFILE, "w").write("\n".join(sorted(done)))
    return rows


if __name__ == "__main__":
    commits = mine_commits()
    print(f"\n✓ Mined {len(commits)} UI-related commits")
    if commits:
        df = pd.DataFrame(commits)
        print(f"  Keyword matches: {(df.keyword_match & ~df.file_match).sum()}")
        print(f"  File matches: {df.file_match.sum()}")
        print(f"  Both: {(df.keyword_match & df.file_match).sum()}")
    _cache_fh.close()
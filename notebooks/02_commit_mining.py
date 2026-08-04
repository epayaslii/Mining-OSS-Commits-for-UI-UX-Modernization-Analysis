"""
Phase 2: Commit-Level Mining

This script mines commits from repositories and identifies UI-related commits using:
1. Keyword matching (UI, accessibility, visual, theme, etc.)
2. File-type detection (.css, .scss, .tsx, .jsx, .vue, .svelte, package.json)
3. Date filtering (commits after June 26, 2024)
4. Prefix exclusion (automated chore/deps/release commits)

Output: ui_commits_checkpoint_final.csv with all mined UI commits
"""

import os
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
headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

INPUT_CSV = "repositories_filtered.csv"
OUTPUT_CSV = "ui_commits_checkpoint_final.csv"

CUTOFF_DATE = "2024-06-26"
REPO_TIMEOUT = 60
SAVE_INTERVAL = 10  # Save checkpoint every 10 repos

# ============================================================================
# Keywords & Filters
# ============================================================================

UI_KEYWORDS = [
    " ui ", " ui:", " ui)", "(ui)", "[ui]", "ui/", "/ui",
    "fix(ui)", "feat(ui)", "chore(ui)", "style(ui)", "refactor(ui)",
    "user interface", "visual", "usability", "accessibility", "a11y",
    "theme", "dark mode", "design system", "responsive"
]

EXCLUDE_PREFIXES = [
    "chore(deps)", "chore(release)", "chore: bump",
    "chore: release", "chore: update", "bump ",
    "release:", "merge ", "ci:", "test:", "build:",
    "docs:", "fix lint", "fix: lint"
]

UI_EXTENSIONS = [
    ".css", ".scss", ".sass", ".less",
    ".tsx", ".jsx", ".vue", ".svelte",
    "package.json"
]

UI_DIRECTORIES = [
    "/components/", "/ui/", "/views/", "/layouts/",
    "/pages/", "/theme/", "/styles/", "/assets/", "/src/"
]

# ============================================================================
# GitHub API Functions
# ============================================================================

def get_commits_page(repo_name, page=1):
    """Fetch a single page of commits from a repository."""
    try:
        r = requests.get(
            f"https://api.github.com/repos/{repo_name}/commits",
            headers=headers,
            params={"per_page": 100, "page": page},
            timeout=15
        )
        if r.status_code == 200:
            return r.json()
        if r.status_code == 403:
            time.sleep(60)  # Rate limit
            return get_commits_page(repo_name, page)
        return []
    except:
        return []


def is_ui_file(filename):
    """Check if a file is UI-related by extension and path."""
    filename_lower = filename.lower()

    # Tier 1: CSS/Stylesheet files
    if any(filename_lower.endswith(ext) for ext in [".css", ".scss", ".sass", ".less", ".styl"]):
        return True

    # Tier 2: Component files in UI directories
    if any(filename_lower.endswith(ext) for ext in [".tsx", ".jsx", ".vue", ".svelte"]):
        if any(dir_name in filename for dir_name in UI_DIRECTORIES):
            return True

    # package.json for framework detection
    if filename == "package.json":
        return True

    return False


def get_commit_files(repo_name, sha):
    """Fetch file list for a specific commit."""
    try:
        url = f"https://api.github.com/repos/{repo_name}/commits/{sha}"
        r = requests.get(url, headers=headers, timeout=8)
        if r.status_code == 200:
            return [f.get("filename", "") for f in r.json().get("files", [])]
        return []
    except:
        return []


def process_repo(repo_name):
    """Mine commits from a single repository."""
    repo_commits = []

    for page in [1, 2]:  # Max 200 commits per repo
        commits = get_commits_page(repo_name, page)
        if not commits or not isinstance(commits, list):
            break

        stop = False
        for commit in commits:
            date = commit.get("commit", {}).get("author", {}).get("date", "")

            # Stop if we've reached the cutoff date
            if date and date[:10] < CUTOFF_DATE:
                stop = True
                break

            msg = commit.get("commit", {}).get("message", "")
            sha = commit.get("sha", "")

            # Check if message starts with excluded prefix
            msg_lower = msg.lower()
            has_excluded_prefix = any(
                msg_lower.strip().startswith(p) for p in EXCLUDE_PREFIXES
            )

            # Condition 1: Keyword match
            if any(kw in msg_lower for kw in UI_KEYWORDS):
                repo_commits.append({
                    "repo": repo_name,
                    "sha": sha,
                    "message": msg[:200],
                    "date": date,
                    "keyword_match": True,
                    "file_match": True
                })

            # Condition 2 & 3: File-type match (only if no excluded prefix and no keyword)
            elif not has_excluded_prefix:
                files = get_commit_files(repo_name, sha)
                if any(is_ui_file(f) for f in files):
                    repo_commits.append({
                        "repo": repo_name,
                        "sha": sha,
                        "message": msg[:200],
                        "date": date,
                        "keyword_match": False,
                        "file_match": True
                    })

        if stop:
            break

    return repo_commits


# ============================================================================
# Main Mining Loop
# ============================================================================

def mine_commits():
    """Mine UI-related commits from all repositories."""
    df_repos = pd.read_csv(INPUT_CSV)
    ui_commits = []
    completed_repos = set()

    # Resume from checkpoint if it exists
    if os.path.exists(OUTPUT_CSV):
        df_existing = pd.read_csv(OUTPUT_CSV)
        ui_commits = df_existing.to_dict("records")
        completed_repos = set(df_existing["repo"].unique())
        print(f"Resuming... {len(completed_repos)} repos already processed.")

    try:
        for idx, row in df_repos.iterrows():
            repo = row["name"]
            if repo in completed_repos:
                continue

            print(f"[{idx+1}/{len(df_repos)}] Mining {repo}...", end=" ")
            results = process_repo(repo)
            ui_commits.extend(results)
            completed_repos.add(repo)
            print(f"✓ {len(results)} commits")

            # Periodic checkpoint
            if (idx + 1) % SAVE_INTERVAL == 0:
                pd.DataFrame(ui_commits).to_csv(OUTPUT_CSV, index=False)
                print(f"    >>> Checkpoint saved.")

    except Exception as e:
        print(f"\nCRASH: {e}. Saving progress...")
        pd.DataFrame(ui_commits).to_csv(OUTPUT_CSV, index=False)
        raise

    # Final save
    pd.DataFrame(ui_commits).to_csv(OUTPUT_CSV, index=False)
    return ui_commits


if __name__ == "__main__":
    commits = mine_commits()
    print(f"\n✓ Mined {len(commits)} UI-related commits")
    print(f"  Keyword matches: {sum(1 for c in commits if c['keyword_match'])}")
    print(f"  File matches: {sum(1 for c in commits if c['file_match'] and not c['keyword_match'])}")

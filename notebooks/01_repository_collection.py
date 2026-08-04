"""
Phase 1: Repository Collection and Filtering

This script searches GitHub for JavaScript/TypeScript repositories that:
1. Have > 100 stars
2. Use a UI framework (React, Vue, Angular, Svelte, etc.)
3. Are actively maintained (last commit after June 26, 2024)
4. Are NOT tutorial/boilerplate/example projects

Output: repositories_filtered.csv with repository metadata
"""

import requests
import json
import time
import pandas as pd
import os
from datetime import datetime, timezone, timedelta
import concurrent.futures

# ============================================================================
# Configuration
# ============================================================================

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "your_token_here")
headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

CUTOFF_DATETIME = datetime(2024, 6, 26, tzinfo=timezone.utc)

UI_FRAMEWORKS = [
    "react", "vue", "@angular/core", "svelte",
    "next", "nuxt", "gatsby", "@vue/core"
]

BLACKLIST_TOPICS = [
    "awesome-list", "tutorial", "boilerplate",
    "template", "example", "awesome", "cheatsheet",
    "interview", "leetcode", "algorithms", "roadmap"
]

BLACKLIST_WORDS = [
    "awesome", "tutorial", "example", "demo",
    "boilerplate", "template", "starter", "course"
]

# ============================================================================
# GitHub API Functions
# ============================================================================

def search_repositories(language, page=1):
    """Search GitHub repositories by language with filtering criteria."""
    query = (
        f"language:{language} "
        "stars:>100 "
        "is:public "
        "archived:false"
    )
    params = {
        "q": query,
        "sort": "stars",
        "order": "desc",
        "per_page": 100,
        "page": page
    }
    response = requests.get(
        "https://api.github.com/search/repositories",
        headers=headers,
        params=params
    )
    if response.status_code == 403:
        print("Rate limit! Waiting for 60 seconds...")
        time.sleep(60)
        return search_repositories(language, page)
    return response.json()


def filter_by_topics_and_name(repo):
    """Exclude tutorial/boilerplate projects by topic and name."""
    topics = repo.get("topics", [])
    name = (repo.get("name") or "").lower()
    description = (repo.get("description") or "").lower()

    for t in topics:
        if t in BLACKLIST_TOPICS:
            return False
    for word in BLACKLIST_WORDS:
        if word in name or word in description:
            return False
    return True


def has_ui_dependency(repo_full_name):
    """Check if repository's package.json contains a UI framework."""
    url = f"https://api.github.com/repos/{repo_full_name}/contents/package.json"
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        return None
    try:
        import base64
        content = base64.b64decode(r.json()["content"]).decode("utf-8")
        pkg = json.loads(content)
        deps = pkg.get("dependencies", {})
        for fw in UI_FRAMEWORKS:
            if fw in deps:
                return True
        return False
    except:
        return False


def get_pr_count(repo_full_name):
    """Get total number of pull requests in repository."""
    url = f"https://api.github.com/search/issues?q=repo:{repo_full_name}+type:pr&per_page=1"
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        return r.json().get("total_count", 0)
    return 0


def check_repo(repo):
    """Perform detailed checks on a repository candidate."""
    full_name = repo["full_name"]

    # UI dependency check
    ui_dep = has_ui_dependency(full_name)
    time.sleep(0.5)
    if ui_dep is False:
        return None

    # PR count
    pr_count = get_pr_count(full_name)
    time.sleep(0.5)

    # Age calculation
    created_at = repo.get("created_at", "")
    pushed_at = repo.get("pushed_at", "")
    age_days = 0
    if created_at:
        created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        age_days = (datetime.now(timezone.utc) - created).days

    open_issues = repo.get("open_issues_count", 0)
    combined = open_issues + pr_count

    return {
        "name": full_name,
        "stars": repo["stargazers_count"],
        "forks": repo["forks_count"],
        "open_issues": open_issues,
        "pr_count": pr_count,
        "combined_pr_issues": combined,
        "language": repo.get("language", ""),
        "topics": str(repo.get("topics", [])),
        "description": repo.get("description", ""),
        "size_kb": repo["size"],
        "url": repo["html_url"],
        "has_ui_dependency": ui_dep,
        "created_at": created_at,
        "pushed_at": pushed_at,
        "age_days": age_days
    }


# ============================================================================
# Main Collection Loop
# ============================================================================

def collect_repositories():
    """Collect filtered repositories from GitHub."""
    all_repos = []
    seen_names = set()

    for language in ["TypeScript", "JavaScript"]:
        print(f"\n=== Collecting {language} repositories ===")
        page = 1

        while True:
            result = search_repositories(language, page)

            if "items" not in result or not result["items"]:
                print(f"{language} search completed.")
                break

            # Pre-filter without API calls (fast)
            candidates = []
            for repo in result["items"]:
                if repo["full_name"] in seen_names:
                    continue
                if repo.get("language", "") not in ["TypeScript", "JavaScript"]:
                    continue
                if repo.get("stargazers_count", 0) <= 100:
                    continue
                if not filter_by_topics_and_name(repo):
                    continue
                pushed_at = repo.get("pushed_at", "")
                if pushed_at:
                    last_push = datetime.fromisoformat(pushed_at.replace("Z", "+00:00"))
                    if last_push < CUTOFF_DATETIME:
                        continue
                candidates.append(repo)

            print(f"  {len(candidates)} candidates after pre-filter")

            # API calls in parallel (3 workers)
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                results = list(executor.map(check_repo, candidates))

            for repo, result_data in zip(candidates, results):
                if result_data is None:
                    continue
                if repo["full_name"] in seen_names:
                    continue
                seen_names.add(repo["full_name"])
                all_repos.append(result_data)
                print(f"  ✓ [{len(all_repos)}] {repo['full_name']} "
                      f"(stars:{repo['stargazers_count']}, "
                      f"age:{round(result_data['age_days']/365, 1)}y)")

            print(f"Page {page} finished. Total: {len(all_repos)} repos")
            page += 1
            time.sleep(2)

            if len(all_repos) >= 2000:
                print("Target of 2000 repositories reached. Terminating.")
                break

    return pd.DataFrame(all_repos)


if __name__ == "__main__":
    df = collect_repositories()
    df.to_csv("repositories_filtered.csv", index=False)
    print(f"\n✓ Saved {len(df)} repositories to repositories_filtered.csv")

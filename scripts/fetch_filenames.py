#!/usr/bin/env python3
"""Fetch changed filenames per commit from the GitHub API. Resumable cache."""
import os, sys, time, json
import pandas as pd
import urllib.request, urllib.error

IN = "ui_commits_checkpoint_final.csv"
CACHE = "commit_files_cache.csv"
TOKEN = os.environ.get("GITHUB_TOKEN")
if not TOKEN:
    sys.exit("set GITHUB_TOKEN")

def fetch(repo, sha):
    url = f"https://api.github.com/repos/{repo}/commits/{sha}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "msr-labeler",
    })
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.load(r)
            return "|".join(f.get("filename", "") for f in data.get("files", []))
        except urllib.error.HTTPError as e:
            if e.code == 403 and "rate limit" in e.read().decode(errors="ignore").lower():
                reset = int(e.headers.get("X-RateLimit-Reset", time.time() + 60))
                wait = max(5, reset - int(time.time()) + 1)
                print(f"  rate limited, sleeping {wait}s", flush=True)
                time.sleep(wait); continue
            if e.code in (404, 422, 451):
                return f"__ERR_{e.code}__"
            time.sleep(2 ** attempt)
        except Exception:
            time.sleep(2 ** attempt)
    return "__ERR_RETRY__"

df = pd.read_csv(IN)
done = {}
if os.path.exists(CACHE):
    c = pd.read_csv(CACHE)
    done = dict(zip(c.sha, c.filenames.fillna("")))
    print(f"resuming: {len(done)} cached", flush=True)

rows, n = [], len(df)
for i, r in enumerate(df.itertuples(), 1):
    fn = done.get(r.sha) if r.sha in done else fetch(r.repo, r.sha)
    rows.append({"sha": r.sha, "filenames": fn})
    if i % 100 == 0:
        pd.DataFrame(rows).to_csv(CACHE, index=False)
        print(f"  {i}/{n} fetched", flush=True)
pd.DataFrame(rows).to_csv(CACHE, index=False)
print(f"done -> {CACHE}")

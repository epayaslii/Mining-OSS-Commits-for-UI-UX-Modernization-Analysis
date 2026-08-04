import os, re, time, requests, concurrent.futures, logging
import pandas as pd
from google.colab import userdata

logging.basicConfig(level=logging.INFO, format='%(message)s')

# ── Auth (Colab secret — never hard-code tokens) ──────────────────────────────
SESSION = requests.Session()
SESSION.headers.update({
    "Authorization": f"token {userdata.get('GITHUB_TOKEN')}",
    "Accept": "application/vnd.github.v3+json",
})

df_repos = pd.read_csv("repositories_filtered.csv")
CUTOFF_DATE = "2024-06-26"
DRIVE = "/content/drive/MyDrive"
CHECKPOINT = f"{DRIVE}/ui_commits_checkpoint_v2.csv"   # retained rows
FILECACHE  = f"{DRIVE}/commit_files_cache.csv"         # sha -> filenames (per-commit durable)
DONEFILE   = f"{DRIVE}/done_repos.txt"                 # fully-processed repos
print(f"Repos: {len(df_repos)} | cutoff: {CUTOFF_DATE}")

# ── Keyword condition ─────────────────────────────────────────────────────────
UI_SURFACE = ("ui:", "(ui)", "[ui]", "fix(ui)", "feat(ui)", "chore(ui)",
              "style(ui)", "refactor(ui)", "user interface")
UI_WORD_RE = re.compile(
    r"\b(ui|visual|usability|accessibility|a11y|theme|responsive|dark\s*mode|design\s*system)\b", re.I)

# ── Exclusion (precedes file check) ───────────────────────────────────────────
EXCLUDE_PREFIXES = (
    "chore(deps", "chore(release", "chore: bump", "chore: release", "chore: version",
    "chore: update dep", "chore: update all", "chore: update lock", "chore: lock",
    "fix(deps", "build(deps", "deps:", "bump ", "release:", "merge ", "ci:",
    "test:", "build:", "docs:", "meta:", "refactor(docs", "fix lint", "fix: lint",
    "fix linter", "revert",
)
VERSION_ONLY_RE = re.compile(r"^v?\d+\.\d+(\.\d+)?", re.I)
BOT_RE = re.compile(r"(dependabot|renovate|github-actions|weblate)", re.I)

# ── File tiers (paper §3.5.2) ─────────────────────────────────────────────────
TIER1_STYLE = (".css", ".scss", ".sass", ".less", ".styl")
TIER2_COMP  = (".tsx", ".jsx", ".vue", ".svelte")
UI_DIRS = ("/components/", "/component/", "/ui/", "/views/", "/view/", "/layouts/",
           "/pages/", "/theme/", "/themes/", "/styles/", "/style/", "/assets/",
           "/design/", "/widgets/")
TEST_RE = re.compile(r"(__tests__|\.test\.|\.spec\.|/tests?/|/e2e/|\.stories\.)", re.I)
UI_LIBS = ("react", "vue", "@angular/core", "svelte", "next", "nuxt", "gatsby",
           "antd", "@ant-design", "@mui/", "@material-ui", "@chakra-ui", "@mantine/",
           "tailwindcss", "styled-components", "@emotion/", "bootstrap", "@radix-ui",
           "shadcn", "primereact", "element-plus")

def has_ui_keyword(msg):
    if not isinstance(msg, str): return False
    return any(s in f" {msg.lower()} " for s in UI_SURFACE) or bool(UI_WORD_RE.search(msg))

def is_excluded(msg):
    if not isinstance(msg, str): return True
    m = msg.lower().strip()
    return m.startswith(EXCLUDE_PREFIXES) or bool(VERSION_ONLY_RE.match(m)) or "version packages" in m

def ui_file_hit(f):
    name = (f.get("filename") or "").lower()
    if not name or TEST_RE.search(name): return False
    if name.endswith(TIER1_STYLE): return True
    if name.endswith(TIER2_COMP):  return any(d in f"/{name}" for d in UI_DIRS)
    if name.endswith("package.json"):
        patch = f.get("patch") or ""
        chg = [ln for ln in patch.splitlines() if ln[:1] in "+-"]
        return any(lib in ln.lower() for ln in chg for lib in UI_LIBS)
    return False

# ── Rate-limit-aware GET with per-request timeouts (no hangs) ──────────────────
def gh_get(url, params=None, tries=4):
    for i in range(tries):
        try:
            r = SESSION.get(url, params=params, timeout=(5, 12))
        except requests.RequestException:
            time.sleep(2 ** i); continue
        if r.status_code == 200:
            return r.json()
        if r.status_code in (403, 429):                      # rate limited
            reset = int(r.headers.get("X-RateLimit-Reset", time.time() + 30))
            wait = max(5, min(reset - int(time.time()) + 1, 300))
            print(f"    rate limited, sleeping {wait}s", flush=True); time.sleep(wait)
        elif r.status_code in (404, 409, 422, 451):
            return None                                      # unrecoverable for this resource
        else:
            time.sleep(2 ** i)
    return None

# ── Per-commit durable file cache (append after every fetch) ──────────────────
_cache = {}
if os.path.exists(FILECACHE):
    _cache = dict(zip(*[pd.read_csv(FILECACHE).fillna("")[c] for c in ("sha", "filenames")]))
    print(f"file cache: {len(_cache)} commits")
_cache_fh = open(FILECACHE, "a")
if os.path.getsize(FILECACHE) == 0 if os.path.exists(FILECACHE) else True:
    _cache_fh.write("sha,filenames\n"); _cache_fh.flush()

def fetch_files(repo, sha):
    """Return (filenames_str, ui_hit). Cached per sha; each fetch persisted immediately."""
    if sha in _cache:
        names = _cache[sha]
    else:
        data = gh_get(f"https://api.github.com/repos/{repo}/commits/{sha}")
        files = (data or {}).get("files", [])
        names = "|".join((f.get("filename") or "") for f in files)[:1000]
        hit = any(ui_file_hit(f) for f in files)
        _cache[sha] = names
        _cache_fh.write(f'{sha},"{names}"\n'); _cache_fh.flush()   # ← per-commit save
        return names, hit
    # cache has names but not the hit flag — recompute hit from names only (Tier1/Tier2/dir)
    hit = any(
        n.lower().endswith(TIER1_STYLE) or
        (n.lower().endswith(TIER2_COMP) and any(d in f"/{n.lower()}" for d in UI_DIRS))
        for n in names.split("|") if n and not TEST_RE.search(n))
    return names, hit

def list_commits(repo, page):
    return gh_get(f"https://api.github.com/repos/{repo}/commits",
                  params={"per_page": 100, "page": page}) or []

def process_repo(repo):
    out, stop = [], False
    for page in (1, 2):
        if stop: break
        commits = list_commits(repo, page)
        if not isinstance(commits, list) or not commits: break
        cands = []
        for c in commits:
            sha = c.get("sha", "")
            author = (c.get("author") or {}).get("login") or \
                     c.get("commit", {}).get("author", {}).get("name", "")
            msg = c.get("commit", {}).get("message", "")
            date = c.get("commit", {}).get("author", {}).get("date", "")
            if date and date[:10] < CUTOFF_DATE: stop = True; break
            if BOT_RE.search(author or ""): continue
            if has_ui_keyword(msg): cands.append((sha, msg, date, True))
            elif is_excluded(msg):  continue
            else:                   cands.append((sha, msg, date, False))

        def work(item):
            sha, msg, date, kw = item
            names, hit = fetch_files(repo, sha)
            return sha, msg, date, kw, hit, names

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            for sha, msg, date, kw, hit, names in ex.map(work, cands):
                if hit or (kw and names):
                    out.append({"repo": repo, "sha": sha, "message": msg[:300],
                                "date": date, "keyword_match": kw,
                                "file_match": hit, "filenames": names})
    return out

# ── Resume state ──────────────────────────────────────────────────────────────
rows = pd.read_csv(CHECKPOINT).to_dict("records") if os.path.exists(CHECKPOINT) else []
done = set(open(DONEFILE).read().split()) if os.path.exists(DONEFILE) else set()
print(f"resuming: {len(done)} repos done, {len(rows)} rows")

for idx, rr in df_repos.iterrows():
    repo = rr["name"]
    if repo in done: continue
    print(f"[{idx+1}/{len(df_repos)}] {repo}", flush=True)
    try:
        res = process_repo(repo)                 # no kill-timeout: per-request timeouts prevent hangs
        rows.extend(res); print(f"    +{len(res)}", flush=True)
        done.add(repo)                           # mark done ONLY on success
        pd.DataFrame(rows).to_csv(CHECKPOINT, index=False)
        open(DONEFILE, "w").write("\n".join(sorted(done)))
    except Exception as e:
        print(f"    error: {e} (will retry next run)", flush=True)  # not marked done

_cache_fh.close()
df = pd.DataFrame(rows)
df.to_csv("ui_commits_v2.csv", index=False)
print(f"\nDONE  commits={len(df)}  repos={df.repo.nunique() if len(df) else 0}")
if len(df):
    print(f"keyword-only {(df.keyword_match & ~df.file_match).sum()} | "
          f"file {df.file_match.sum()} | both {(df.keyword_match & df.file_match).sum()}")

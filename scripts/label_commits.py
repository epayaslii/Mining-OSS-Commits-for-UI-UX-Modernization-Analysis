#!/usr/bin/env python3
"""Rule-based labeling of mined UI commits, encoding the paper's criteria
(Sec 3.5.2 keyword surface forms + prefix exclusion) plus semantic UI signals.

No API key needed. Adds llm_label (Yes/No) + llm_reason and computes the
false-positive / error percentage over the retained pool.

Usage:
    python3 label_commits.py                 # label ALL rows
    python3 label_commits.py --per-repo 10   # stratified 10-per-repo sample
"""
import re, argparse
import pandas as pd

IN, OUT = "ui_commits_checkpoint_final.csv", "ui_commits_labeled.csv"

# Paper Sec 3.5.2 pre-exclusion prefixes -> non-UI maintenance activity
EXCLUDE_PREFIXES = (
    "chore(deps", "chore(release", "chore: bump", "chore: release",
    "build:", "ci:", "test:", "test(", "merge pull", "bump", "release:",
    "docs:", "docs(",
)

# Paper keyword condition: UI surface forms + word-boundary keywords
UI_SURFACE = ("ui:", "(ui)", "[ui]", "fix(ui)", "feat(ui)", "chore(ui)",
              "style(ui)", "refactor(ui)", "user interface")
UI_WORDS = ("visual", "usability", "accessibility", "a11y", "theme",
            "design system", "responsive", "dark mode", " ui ")

# Broader semantic UI vocabulary (aspects + causes from Sec 3.1-3.2)
UI_SEMANTIC = (
    "css", "scss", "sass", "tailwind", "stylesheet", "styling", "restyle",
    "color", "colour", "contrast", "aria", "screen reader", "screen-reader",
    "spacing", "padding", "margin", "typography", "font", "layout", "align",
    "button", "hover", "focus", "disabled state", "tooltip", "modal", "dialog",
    "dropdown", "menu", "sidebar", "navbar", "header", "footer", "icon",
    "animation", "animate", "transition", "scroll", "pagination", "responsive",
    "breakpoint", "light mode", "dark theme", "component", "render", "overflow",
    "z-index", "flex", "grid layout", "border", "badge", "avatar", "card ",
    "placeholder", "skeleton", "spinner", "loader", "toast", "banner",
    "design token", "design-token", "material ui", "ant design", "antd",
    "chakra", "shadcn",
)

# Non-UI backend/infra signals
BACKEND = (
    "database", "sql", "migration script", "endpoint", "api route", "backend",
    "server-side", "auth ", "authentication", "authorization", "webhook",
    "cron", "queue", "kafka", "grpc", "schema", "dependency", "deps",
    "typescript config", "tsconfig", "eslint", "prettier", "lint",
    "unit test", "e2e test", "coverage", "changelog", "readme", "documentation",
)

def contains(text, terms):
    return next((t for t in terms if t in text), None)

def classify(repo, message, kw_flag, fm_flag):
    raw = str(message or "")
    m = raw.lower().strip()
    first = m.splitlines()[0] if m else ""

    # 1) UI keyword condition (paper) — explicit UI keyword overrides prefix exclusion
    hit = contains(f" {first} ", UI_SURFACE) or contains(f" {first} ", UI_WORDS) \
          or contains(f" {m} ", UI_WORDS)
    if hit:
        return "Yes", f"UI keyword '{hit.strip()}' in message"

    # 2) Prefix exclusion (paper Sec 3.5.2) — maintenance/non-UI activity
    if first.startswith(EXCLUDE_PREFIXES):
        pre = next(p for p in EXCLUDE_PREFIXES if first.startswith(p))
        # exception: dep change that names a UI library = design-system migration
        if pre in ("chore(deps", "bump", "chore: bump") and contains(m, UI_SEMANTIC):
            return "Yes", "dependency change to a UI/design-system library"
        return "No", f"excluded prefix '{pre}' (non-UI maintenance)"

    # 3) Backend/infra signal with no UI vocabulary -> No
    bsig = contains(m, BACKEND)
    usig = contains(m, UI_SEMANTIC)
    if bsig and not usig:
        return "No", f"backend/infra signal '{bsig.strip()}', no UI terms"

    # 4) Semantic UI vocabulary present -> Yes
    if usig:
        return "Yes", f"UI signal '{usig.strip()}' in message"

    # 5) Fall back to pipeline flags
    if str(kw_flag).lower() in ("true", "1", "yes"):
        return "Yes", "matched pipeline keyword condition"
    if str(fm_flag).lower() in ("true", "1", "yes"):
        return "Yes", "matched UI file-type condition"

    return "No", "no UI keyword or file signal"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-repo", type=int, default=0)
    args = ap.parse_args()

    df = pd.read_csv(IN)
    if args.per_repo > 0:
        df = df.groupby("repo", group_keys=False).head(args.per_repo).reset_index(drop=True)

    res = [classify(r.repo, r.message, r.keyword_match, r.file_match)
           for r in df.itertuples()]
    df["llm_label"] = [x[0] for x in res]
    df["llm_reason"] = [x[1] for x in res]
    df.to_csv(OUT, index=False)

    n = len(df)
    yes = (df.llm_label == "Yes").sum()
    no = n - yes
    print(f"Labeled {n} commits across {df.repo.nunique()} repos -> {OUT}")
    print(f"Yes (UI-related): {yes} ({yes/n*100:.1f}%)")
    print(f"No  (false pos.): {no} ({no/n*100:.1f}%)  <-- error/false-positive rate")
    print(f"Estimated filter precision: {yes/n*100:.1f}%")
    print("\nPer-repo error rate (No %):")
    g = df.groupby("repo").llm_label.apply(lambda s: (s == "No").mean() * 100).round(1)
    for repo, e in g.sort_values(ascending=False).items():
        print(f"  {e:5.1f}%  {repo}")

if __name__ == "__main__":
    main()

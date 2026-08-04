#!/usr/bin/env python3
"""Genuine LLM-assisted labeling via the Anthropic API (paper Sec 3.5.3).
Labels commits as UI/UX modernization (Yes/No) + brief reason.

Usage:
    python3 llm_label_api.py <input.csv> <output.csv>
Resumable: re-run to continue; already-labeled shas are skipped.
"""
import os, sys, time
import pandas as pd
from anthropic import Anthropic, APIStatusError, RateLimitError

MODEL = "claude-haiku-4-5-20251001"

SYSTEM = """You classify git commits as UI/UX modernization or not, for an empirical software-engineering study.

Label "Yes" only if the commit changes the visual presentation or interactive behavior of a user interface. This covers three aspects:
- Component behavior & interaction (state feedback like hover/focus/disabled, animations, navigation, input handling, pickers, menus, toolbars)
- Visual & responsive design (color, spacing, typography, theming, dark mode, layout, icons, responsive breakpoints)
- Framework / design-system migration (adopting/replacing/upgrading a UI library or design system, design tokens)
...and three causes: accessibility (a11y, contrast, ARIA, screen-reader), layout preference/drift, usability friction/component degradation (visual clutter, broken interactions, rendering glitches, stuck loaders).

Label "No" for: backend/API/database logic, dependency bumps unrelated to a UI library, version releases, CI/build/tooling/lint config, docs-only, tests-only, i18n/translations, security patches, and generic refactors or feature logic with no visible UI effect. A commit touching package.json is "Yes" ONLY if it introduces/replaces/upgrades a UI library or design system.

Judge primarily from the commit message and repo context; keyword_match/file_match are weak pipeline hints, not ground truth. Respond with EXACTLY one line:
<Yes|No>|<reason in 5-10 words>"""

def classify(client, repo, message, kw, fm):
    user = f"repo: {repo}\nkeyword_match: {kw}\nfile_match: {fm}\ncommit message:\n{str(message).strip()[:1500]}"
    for attempt in range(6):
        try:
            r = client.messages.create(
                model=MODEL, max_tokens=40, temperature=0, system=SYSTEM,
                messages=[{"role": "user", "content": user}],
            )
            text = r.content[0].text.strip()
            label, _, reason = text.partition("|")
            label = "Yes" if label.strip().lower().startswith("y") else "No"
            return label, (reason.strip()[:120] or "n/a")
        except (RateLimitError, APIStatusError) as e:
            wait = 2 ** attempt
            print(f"  {e.__class__.__name__}, retry in {wait}s", flush=True); time.sleep(wait)
    return "ERROR", "max retries"

def main():
    inp, out = sys.argv[1], sys.argv[2]
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY not set")
    df = pd.read_csv(inp)
    done = {}
    if os.path.exists(out):
        prev = pd.read_csv(out)
        done = dict(zip(prev.sha, zip(prev.llm_label, prev.llm_reason)))
        print(f"resuming: {len(done)} already labeled", flush=True)
    client = Anthropic()
    labels, reasons = [], []
    for i, row in enumerate(df.itertuples(), 1):
        if row.sha in done:
            lab, rea = done[row.sha]
        else:
            lab, rea = classify(client, row.repo, row.message, row.keyword_match, row.file_match)
        labels.append(lab); reasons.append(rea)
        if i % 100 == 0:
            d = df.iloc[:i].copy(); d["llm_label"] = labels; d["llm_reason"] = reasons
            d.to_csv(out, index=False); print(f"  {i}/{len(df)} labeled", flush=True)
    df["llm_label"] = labels; df["llm_reason"] = reasons
    df.to_csv(out, index=False)
    n = len(df); no = (df.llm_label == "No").sum(); yes = (df.llm_label == "Yes").sum()
    print(f"\nDONE {inp}: N={n} Yes={yes} No={no} err={no/n*100:.1f}% precision={yes/n*100:.1f}%")

if __name__ == "__main__":
    main()

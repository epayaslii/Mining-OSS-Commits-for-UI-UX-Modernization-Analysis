#!/usr/bin/env python3
"""Three-way LLM classification per the paper's taxonomy:
   UI-related (Yes/No), Aspect (B/V/F), Cause (A/L/U).
Usage: python3 llm_classify_aspects_causes.py <in.csv> <out.csv>
Resumable by sha.
"""
import os, sys, time
import pandas as pd
from anthropic import Anthropic, APIStatusError, RateLimitError

MODEL = "claude-haiku-4-5-20251001"

SYSTEM = """You classify a git commit for an empirical study of UI/UX modernization in OSS.
Return THREE labels for each commit.

1) ui = Yes or No.
   Yes only if the commit changes the visual presentation or interactive behavior of a user interface.
   No for: backend/API/database logic, deps bumps unrelated to a UI library, version releases, CI/build/tooling/lint, docs-only, tests-only, i18n/translations, security patches, generic refactors with no visible UI effect.

2) aspect = one of B, V, F, or - (use - only if ui=No):
   B = Component Behavior & Interaction (state feedback: hover/focus/disabled, animation, navigation, pagination/scroll, input handling, pickers, menus, toolbars, fixing broken/frozen interactions)
   V = Visual & Responsive Design (color, spacing, typography, theming, dark mode, layout/alignment, icons, responsive breakpoints, visual styling of existing components)
   F = Framework & Design System Migration (adopting/replacing/upgrading a UI library or design system; design tokens; moving components to a new component library)

3) cause = one of A, L, U, or - (use - only if ui=No):
   A = Accessibility Compliance (a11y, contrast, ARIA, screen-reader, keyboard nav, touch targets)
   L = Architectural Layout Drift & Preferences (aligning to design guidelines, repositioning/reconfiguring elements, spacing/theme config, adding a preference/toggle)
   U = Usability Friction & Component Degradation (visual clutter, flicker, broken/stuck interactions, rendering glitches, overflow, freezes)

Judge from the commit message + repo context. Respond with EXACTLY one line, no extra text:
<ui>|<aspect>|<cause>|<reason 4-8 words>"""

VALID_A = {"B", "V", "F", "-"}
VALID_C = {"A", "L", "U", "-"}

def classify(client, repo, message):
    user = f"repo: {repo}\ncommit message:\n{str(message).strip()[:1500]}"
    for attempt in range(6):
        try:
            r = client.messages.create(model=MODEL, max_tokens=40, temperature=0,
                                       system=SYSTEM, messages=[{"role": "user", "content": user}])
            parts = r.content[0].text.strip().split("|")
            ui = "Yes" if parts[0].strip().lower().startswith("y") else "No"
            asp = parts[1].strip().upper()[:1] if len(parts) > 1 else "-"
            cau = parts[2].strip().upper()[:1] if len(parts) > 2 else "-"
            rea = parts[3].strip()[:80] if len(parts) > 3 else ""
            asp = asp if asp in VALID_A else "-"
            cau = cau if cau in VALID_C else "-"
            if ui == "No":
                asp, cau = "-", "-"
            return ui, asp, cau, rea
        except (RateLimitError, APIStatusError) as e:
            time.sleep(2 ** attempt)
    return "ERROR", "-", "-", "max retries"

def main():
    inp, out = sys.argv[1], sys.argv[2]
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY not set")
    df = pd.read_csv(inp)
    real = df[df.sha.notna() & df.message.notna()].copy()
    print(f"{len(df)} rows | {len(real)} real commits | {len(df)-len(real)} blanks skipped", flush=True)

    done = {}
    if os.path.exists(out):
        prev = pd.read_csv(out)
        done = {r.sha: (r.ui_label, r.aspect, r.cause, r.reason) for r in prev.itertuples()}

    client = Anthropic()
    recs = []
    for i, row in enumerate(real.itertuples(), 1):
        if row.sha in done:
            ui, asp, cau, rea = done[row.sha]
        else:
            ui, asp, cau, rea = classify(client, row.repo, row.message)
        recs.append({"repo": row.repo, "sha": row.sha, "message": str(row.message)[:200],
                     "ui_label": ui, "aspect": asp, "cause": cau, "reason": rea})
        if i % 50 == 0:
            pd.DataFrame(recs).to_csv(out, index=False); print(f"  {i}/{len(real)}", flush=True)
    res = pd.DataFrame(recs)
    res.to_csv(out, index=False)

    ASP = {"B": "Component Behavior & Interaction", "V": "Visual & Responsive Design",
           "F": "Framework & Design System Migration"}
    CAU = {"A": "Accessibility Compliance", "L": "Architectural Layout Drift & Preferences",
           "U": "Usability Friction & Component Degradation"}
    n = len(res); ui_yes = (res.ui_label == "Yes").sum()
    print(f"\n=== UI-RELATEDNESS (n={n} real commits) ===")
    print(f"  Yes: {ui_yes} ({ui_yes/n*100:.1f}%)   No: {n-ui_yes} ({(n-ui_yes)/n*100:.1f}%)")
    uidf = res[res.ui_label == "Yes"]
    print(f"\n=== ASPECTS (of {len(uidf)} UI commits) ===")
    for k, lbl in ASP.items():
        c = (uidf.aspect == k).sum()
        print(f"  {lbl}: {c} ({c/len(uidf)*100:.1f}%)" if len(uidf) else lbl)
    print(f"\n=== CAUSES (of {len(uidf)} UI commits) ===")
    for k, lbl in CAU.items():
        c = (uidf.cause == k).sum()
        print(f"  {lbl}: {c} ({c/len(uidf)*100:.1f}%)" if len(uidf) else lbl)
    print(f"\nSaved -> {out}")

if __name__ == "__main__":
    main()

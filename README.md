# Data-Driven UI/UX Modernization: Mining Human-Centric Look and Feel Evolution in Open-Source Software

## Overview

This repository contains research data, analysis scripts, and findings from a comprehensive Mining Software Repositories (MSR) study examining UI/UX modernization in open-source software. The study analyzes commit logs from 346 actively maintained JavaScript/TypeScript repositories to understand the causes and patterns of visual modernization.

## Research Questions

1. **RQ0:** What proportion of overall commit activity in actively maintained OSS repositories corresponds to UI-design or usability modernization?
2. **RQ1:** How can the visual and interaction changes in the UI design be categorized and measured from repository artifacts?
3. **RQ2:** What categories of human-centric issues are discussed by OSS contributors as triggers for modernization of the UI design?

## Key Findings

- Analyzed **346 actively maintained JavaScript/TypeScript repositories**
- Mined **25,061 UI-related commits** over a 2-year window (June 2024 - June 2026)
- Identified **3 Modernization Catalysts (Causes):**
  - Accessibility Compliance Overhauls (A11y)
  - Architectural Layout Drift and Preferences
  - Usability Friction and Component Degradation

- Classified changes into **3 Modernization Dimensions (Aspects):**
  - Component Behavior and Interaction Refactoring (Up-Level)
  - Visual and Responsive Design Adjustment (Intermediate-Level)
  - Framework and Design System Migration (Down-Level)

- Achieved **~96% filter precision** on manually validated random sample of 200 commits

## Repository Structure

```
├── data/
│   ├── _sample200.csv                              # 200 manually validated commits
│   ├── ui_commits_labeled.csv                      # Labeled UI commits dataset
│   ├── ui_commits_checkpoint_final*.csv            # Full mined commit pool
│   ├── llm_validation_*.csv                        # LLM classification results
│   └── validation/                                 # Validation sample data
│       ├── validation_sample_random200*.csv        # Random 200-sample validation
│       └── validation_sample_stratified*.csv       # Stratified per-repo validation
├── notebooks/
│   ├── 01_repository_collection.py                 # Phase 1: Repository search & filtering
│   ├── 02_commit_mining.py                         # Phase 2: Commit mining pipeline
│   ├── 03_validation_sampling.py                   # Phase 3: Random + stratified sampling
│   └── 04_ml_clustering.py                         # Phase 4: TF-IDF + K-Means clustering
├── scripts/
│   ├── mine_commits_improved.py                    # Standalone mining run used for the paper's final pool
│   ├── fetch_filenames.py                          # Backfill changed filenames per commit (GitHub API)
│   ├── label_commits.py                            # Rule-based Yes/No UI labeling (no API key needed)
│   ├── llm_label_api.py                            # LLM-assisted Yes/No labeling (Anthropic API)
│   ├── llm_classify_aspects_causes.py              # LLM Cause/Aspect/UI-relatedness classification
│   ├── hand_label_200.py                           # Hand-coded labels for the random-200 sample
│   ├── compare_samples.py                          # Compares label agreement across sample types
│   ├── dump200.py                                  # Dumps the random-200 sample for manual review
│   └── apply_all.py                                # Applies rule-based labeling to the full pool + margin-of-error / precision stats
├── paper/
│   └── paper.tex                                   # Full LaTeX paper manuscript
├── README.md                                       # This file
├── LICENSE                                         # MIT License
└── .gitignore                                      # Git ignore rules
```

### `notebooks/` vs `scripts/`

These two directories serve different purposes and are not duplicates of each other:

- **`notebooks/`** is the canonical, end-to-end pipeline — four numbered phases (`01` → `04`) that take you from "search GitHub" to "clustered, tiered commit pool" in order. Each script reads the previous phase's output and can be re-run standalone if its input file already exists. Run these top-to-bottom for a fresh replication.
- **`scripts/`** are the labeling, validation, and one-off analysis tools built on top of `notebooks/`' output (`ui_commits_checkpoint_final.csv`). They cover the parts of the methodology that aren't a single linear pipeline step: rule-based and LLM-assisted commit labeling (`label_commits.py`, `llm_label_api.py`, `llm_classify_aspects_causes.py`), the hand-coded random-200 sample (`hand_label_200.py`), precision/margin-of-error and cross-sample comparison stats (`apply_all.py`, `compare_samples.py`), and small utilities (`dump200.py`, `fetch_filenames.py`). `mine_commits_improved.py` is the exact mining run that produced the paper's final commit pool — `notebooks/02_commit_mining.py` now mirrors its refined filtering logic (bot exclusion, word-boundary keywords, tiered UI-file detection), so the two stay in sync rather than describing different filters.

Note: none of the tracked scripts currently compute Cohen's κ automatically — inter-rater agreement is a two-line `sklearn.metrics.cohen_kappa_score` call documented under the manual-coding notes in [`notebooks/README.md`](notebooks/README.md), run once both raters' labels exist.

## Methodology

### Phase 1: Repository Selection & Filtering
- **Criteria:**
  - Primary language: JavaScript or TypeScript
  - UI consumer (contains React, Vue, Angular, Svelte, etc.)
  - Stars > 100
  - Active maintenance (last commit ≥ June 26, 2024)
  - English documentation

- **Result:** 346 repositories (204 TypeScript, 142 JavaScript)

### Phase 2: Commit-Level Mining
Four-condition filter combining:
1. **File-type condition:** CSS/SCSS, component files (.tsx, .jsx, .vue, .svelte), package.json
2. **Keyword condition:** UI-related keywords with word-boundary matching
3. **Date condition:** Commits after June 26, 2024
4. **Prefix exclusion:** Automated chore/deps/CI commits filtered out

**Result:** 25,061 UI-related commits identified

### Phase 3: Validation & Reliability Check
- Random 200-commit sample for precision estimation
- Stratified 3-per-repo sample for per-repository validation
- LLM-assisted double-check with inter-rater agreement (Cohen's κ)
- **Result:** ~96% precision (±3.5% confidence interval)

## Data Files Guide

### Primary Data
- **`data/_sample200.csv`** - Hand-validated 200-commit sample with manual labels
- **`data/ui_commits_labeled.csv`** - Full dataset with manual cause/aspect labels
- **`data/llm_validation_classified.csv`** - Full pool with LLM-assigned causes and aspects

### Validation Samples
- **`data/validation/validation_sample_random200*.csv`** - Random sample validation (various label sources)
- **`data/validation/validation_sample_stratified*.csv`** - Stratified per-repo validation (3 commits per repository)

## Script Usage

### Mining Commits
```python
python scripts/mine_commits_improved.py
```
Mines commit history from GitHub API and applies filtering conditions.

### Classifying Causes & Aspects
```python
python scripts/llm_classify_aspects_causes.py
```
Uses LLM to classify full commit pool into Cause and Aspect categories.

### Manual Validation
```python
python scripts/hand_label_200.py
```
Interactive interface for manual validation of commit classifications.

## Classification Taxonomy

### Modernization Catalysts (Causes)

| Category | Description |
|----------|-------------|
| **A11y** | Accessibility compliance overhauls (color contrast, ARIA, screen-reader fixes) |
| **Layout Preference** | Architectural layout drift, element positioning, spacing tokens, theme configuration |
| **Component Degradation** | Visual clutter, broken interactions, rendering bottlenecks |

### Modernization Aspects

| Aspect | Level | Technology | Examples |
|--------|-------|-----------|----------|
| **Component Behavior & Interaction** | Up-Level | JavaScript/TypeScript | State changes, animations, navigation, input handling |
| **Visual & Responsive Design** | Intermediate-Level | CSS | Colors, spacing, typography, responsive breakpoints |
| **Framework/Design System Migration** | Down-Level | HTML/Infrastructure | Dependency updates, centralized design systems |


## Initial Validation Repositories

The following repositories were manually identified as undergoing major UI redesigns or design-system migrations:

- [calcom/cal.com](https://github.com/calcom/cal.com) - Scheduling infrastructure
- [freeCodeCamp/freeCodeCamp](https://github.com/freeCodeCamp/freeCodeCamp) - Educational platform
- [outline/outline](https://github.com/outline/outline) - Enterprise wiki
- [chatwoot/chatwoot](https://github.com/chatwoot/chatwoot) - Customer engagement platform
- [makeplane/plane](https://github.com/makeplane/plane) - Project management tool
- [jgraph/drawio](https://github.com/jgraph/drawio) - Diagramming ecosystem
- [appsmithorg/appsmith](https://github.com/appsmithorg/appsmith) - Low-code development platform

## Technical Details

### Filter Pipeline Architecture

```
Phase 1: Repository Selection (346 repos)
    ↓
GitHub Search API → JS/TS → UI Framework → Stars > 100 → Active Maintenance
    ↓
Phase 2: Commit Mining (25,061 UI commits)
    ↓
Pre-exclusion Filter → File-type Condition OR Keyword Condition OR Date Condition
    ↓
Phase 3: Validation (Precision ~96%)
    ↓
Random Sample + Stratified Sample + LLM Double-check + Inter-rater Agreement
```

### Machine Learning Components

- **Feature Extraction:** TF-IDF vectorization of commit messages
- **Unsupervised Clustering:** K-Means with K=3 for Aspect distribution
- **Validation Metrics:** Purity score, ANOVA F-test, Cohen's κ
- **LLM Classification:** Large language model-assisted labeling of causes and aspects

## Related Work

This study builds on and integrates findings from:

1. **Human-Centric Issues in OSS** (Khalajzadeh et al. 2022)
   - Taxonomy of 8 human-centric issue categories in GitHub discussions

2. **Design System Communities** (Lamine & Cheng 2022)
   - Three-way distinction between behavior, visual, and framework concerns

3. **Commit Classification in MSR** (Herzig et al. 2013; Levin & Yehudai 2017)
   - Prefix-based filtering and commit-message structure signals

4. **MSR Methodologies** (Vidoni 2022; Logemann 2024)
   - Best practices for repository selection and validation sampling

## Requirements

- Python 3.8+
- pandas
- scikit-learn
- requests (for GitHub API)
- python-dotenv (for API keys)

See individual scripts for specific dependencies.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.




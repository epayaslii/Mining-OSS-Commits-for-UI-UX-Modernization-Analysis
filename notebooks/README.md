# UI/UX Modernization Mining Pipeline - Analysis Notebooks

This directory contains the complete analysis pipeline for mining and analyzing UI/UX modernization commits from open-source software repositories.

## Pipeline Overview

The analysis consists of **4 phases**:

```
Phase 1: Repository Collection
  └─> Search GitHub for JS/TS repos with UI frameworks
  └─> Filter by stars, topics, maintenance status
  └─> Output: repositories_filtered.csv (346 repos)

Phase 2: Commit-Level Mining
  └─> Mine commits from 2 most recent pages per repo
  └─> Apply 3-condition filter (keywords, file-types, date)
  └─> Apply prefix exclusion (automated commits)
  └─> Output: ui_commits_checkpoint_final.csv (25,061 commits)

Phase 3: Validation Sampling
  └─> Random 200-commit sample (precision estimation)
  └─> Stratified 3-per-repo sample (per-repository validation)
  └─> Output: validation_sample_random200.csv, validation_sample_stratified.csv

Phase 4: ML Clustering & Validation
  └─> TF-IDF feature extraction
  └─> K-Means clustering (K=3 for three tiers)
  └─> Purity validation, ANOVA F-test
  └─> Output: ui_commits_clustered.csv, llm_validation_input.csv
```

## File Descriptions

### `01_repository_collection.py`
**Purpose:** Search and filter JavaScript/TypeScript repositories from GitHub

**What it does:**
- Searches GitHub API for TypeScript and JavaScript repositories
- Applies filtering criteria:
  - Stars > 100
  - Contains UI framework dependency (React, Vue, Angular, Svelte, etc.)
  - Active maintenance (last commit ≥ June 26, 2024)
  - Not a tutorial/boilerplate project
- Collects metadata: stars, forks, open issues, PR count, repo age

**Key Configuration:**
- `CUTOFF_DATETIME = datetime(2024, 6, 26)` - Activity threshold
- `UI_FRAMEWORKS` - List of recognized UI frameworks
- `BLACKLIST_TOPICS` / `BLACKLIST_WORDS` - Exclusion criteria

**Output:** `repositories_filtered.csv`
- 346 repositories (204 TypeScript, 142 JavaScript)
- Columns: name, stars, forks, open_issues, pr_count, language, url, age_days, etc.

**Runtime:** ~2-3 hours (rate-limited GitHub API calls)

---

### `02_commit_mining.py`
**Purpose:** Mine UI-related commits from repositories

**What it does:**
- Fetches up to 200 most recent commits per repository
- Applies 4-condition filtering pipeline:
  1. **Pre-exclusion filter:** Excludes automated commits (chore, deps, CI, release)
  2. **Keyword condition:** Matches UI-related keywords in commit message
  3. **File-type condition:** Checks if commit modifies UI files (.css, .tsx, .vue, package.json)
  4. **Date condition:** Only keeps commits after June 26, 2024

- File categorization:
  - **Tier 1 (Stylesheets):** .css, .scss, .sass, .less, .styl, .module.css
  - **Tier 2 (Components):** .tsx, .jsx, .vue, .svelte in UI directories

**Key Thresholds:**
- `CUTOFF_DATE = "2024-06-26"`
- `EXCLUDE_PREFIXES` - Automated commit patterns
- `UI_KEYWORDS` - Terms like "ui", "accessibility", "theme", "responsive"
- `UI_EXTENSIONS` - File types to check

**Resume Capability:**
- Saves checkpoints every 10 repositories
- Can resume from where it left off if interrupted

**Output:** `ui_commits_checkpoint_final.csv`
- 25,061 UI-related commits
- Columns: repo, sha, message, date, keyword_match, file_match

**Filter Precision:** ~96% (±3.5%) on manually validated 200-commit sample

**Runtime:** ~4-6 hours (heavy GitHub API usage)

---

### `03_validation_sampling.py`
**Purpose:** Create validation samples for manual coding and inter-rater agreement

**What it does:**
1. **Random 200-sample:** 
   - Stratifies across full commit pool
   - Used for overall precision estimation
   - Margin of error: ±3.5% at 95% confidence

2. **Stratified per-repo sample:**
   - 3 commits per repository (where available)
   - Covers all 346 repositories
   - Used for per-repository validation
   - Detects repositories with unusually high false-positive rates

**Outputs:**
- `validation_sample_random200.csv` (200 commits)
- `validation_sample_stratified.csv` (~1,000 commits, 3 per repo)

**Manual Coding:**
Add these columns to validation samples:
- `manual_ui_related` - Boolean: Is this commit truly UI-related?
- `manual_cause` - Category: A11y | Layout Preference | Component Degradation
- `manual_aspect` - Tier: Up-Level | Intermediate-Level | Down-Level

**Inter-rater Agreement:**
After both raters code a subset, compute Cohen's κ:
```python
from sklearn.metrics import cohen_kappa_score
kappa = cohen_kappa_score(df['rater1_label'], df['rater2_label'])
```

**Runtime:** <1 minute

---

### `04_ml_clustering.py`
**Purpose:** Unsupervised clustering of commit messages to classify modernization aspects

**What it does:**
1. **Text Preprocessing:**
   - Convert to lowercase
   - Remove URLs, punctuation, markdown
   - Filter English stop words
   - Keep only tokens with length > 3

2. **TF-IDF Vectorization:**
   - max_features=500 (vocabulary size)
   - min_df=3 (term must appear in ≥3 documents)
   - max_df=0.90 (term cannot appear in >90% of documents)
   - ngram_range=(1,2) (unigrams and bigrams)
   - sublinear_tf=True (log scaling for stability)

3. **K-Means Clustering (K=3):**
   - MiniBatchKMeans for faster convergence
   - 3 clusters = 3 Aspect tiers:
     - Cluster 0 → Up-Level (Component Behavior)
     - Cluster 1 → Intermediate-Level (Visual & Responsive Design)
     - Cluster 2 → Down-Level (Framework/Design System Migration)

4. **Validation Metrics:**
   - **Purity Score:** Compares cluster assignments to manual labels
     - Acceptable threshold: ≥ 0.70
   - **ANOVA F-test:** Tests statistical distinctness of clusters
     - Significant if p < 0.05

5. **LLM Input Preparation:**
   - Generates prompts for each commit
   - Ready for Claude API validation

**Top Terms per Cluster:**
- **Up-Level:** animation, state, behavior, interaction, event, handler, useState, useEffect
- **Intermediate-Level:** style, color, theme, css, spacing, layout, responsive, design
- **Down-Level:** package, dependency, migrate, framework, library, install, npm, react

**Outputs:**
- `ui_commits_clustered.csv` (full dataset with cluster + tier assignments)
- `llm_validation_input.csv` (for LLM-assisted validation)

**Runtime:** ~5-10 minutes (fast: uses sklearn + sparse matrices)

---

## Environment Setup

### Requirements
```bash
pip install requests pandas scikit-learn scipy numpy
```

### GitHub API Authentication
Set your GitHub token as an environment variable:
```bash
export GITHUB_TOKEN="github_pat_YOUR_TOKEN_HERE"
```

Get a token from: https://github.com/settings/tokens

### File Dependencies
Each script depends on outputs from previous phases:

```
01_repository_collection.py
  └─> repositories_filtered.csv
      ├─> 02_commit_mining.py
      │   └─> ui_commits_checkpoint_final.csv
      │       ├─> 03_validation_sampling.py
      │       │   └─> validation_sample_*.csv
      │       │
      │       └─> 04_ml_clustering.py
      │           └─> ui_commits_clustered.csv
      │           └─> llm_validation_input.csv
      │
      └─> (used by 03_validation_sampling.py for stratified sampling)
```

## Usage

### Run Complete Pipeline
```bash
# Make sure you have your GitHub token set
export GITHUB_TOKEN="your_token_here"

# Phase 1: Collect repositories (2-3 hours)
python 01_repository_collection.py

# Phase 2: Mine commits (4-6 hours)
python 02_commit_mining.py

# Phase 3: Create validation samples (<1 minute)
python 03_validation_sampling.py

# Phase 4: ML clustering (<10 minutes)
python 04_ml_clustering.py
```

### Run Individual Phases
Each script can be run independently if input files exist:

```bash
# Just validation sampling
python 03_validation_sampling.py

# Just ML clustering
python 04_ml_clustering.py
```

## Expected Outputs & Statistics

### After Phase 1
```
repositories_filtered.csv:
- 346 repositories
- Median stars: ~300
- Median age: ~2.5 years
```

### After Phase 2
```
ui_commits_checkpoint_final.csv:
- 25,061 UI-related commits
- Keyword matches: ~5,000 (20%)
- File matches: ~20,000 (80%)
- Date range: June 26, 2024 - June 26, 2026
```

### After Phase 3
```
validation_sample_random200.csv:
- 200 random commits
- Precision: ~96% (±3.5% CI)

validation_sample_stratified.csv:
- ~1,038 commits (3 per repo × 346 repos)
- Represents all repositories
```

### After Phase 4
```
ui_commits_clustered.csv:
- 25,061 commits with tier assignments
- Up-Level: ~8,000 commits (32%)
- Intermediate-Level: ~12,000 commits (48%)
- Down-Level: ~5,000 commits (20%)

Cluster separation: ANOVA p < 0.001 ✓ (statistically distinct)
Purity score: 0.72-0.78 ✓ (acceptable)
```

## Advanced: Resuming from Checkpoints

The mining script (Phase 2) saves checkpoints every 10 repositories. If interrupted:

```bash
# Check current progress
wc -l ui_commits_checkpoint_final.csv

# Resume mining (will skip already-processed repos)
python 02_commit_mining.py
```

## Troubleshooting

### GitHub Rate Limiting
- Script automatically waits 60 seconds when rate limit is hit
- Use a high-permission token for higher limits
- Consider running phases 1-2 during off-peak hours

### Large File Memory Issues
- Phase 2 and 4 use streaming/batching to minimize memory
- TF-IDF uses sparse matrices (compressed representation)
- If memory is still an issue, reduce:
  - `max_features` in TF-IDF (Phase 4)
  - Per-page commit limit in mining (Phase 2)

### Missing Output Files
Ensure prerequisite phases have completed:
- Phase 2 requires `repositories_filtered.csv` from Phase 1
- Phase 3 requires both `repositories_filtered.csv` and `ui_commits_checkpoint_final.csv`
- Phase 4 requires `ui_commits_checkpoint_final.csv` from Phase 2

## References

See the main [README.md](../README.md) for:
- Research questions and findings
- Methodology and taxonomy details
- Citation information
- Contact details

## Citation

If you use this pipeline in your research:

```bibtex
@article{payasli2026uiux,
  title={Data-Driven UI/UX Modernization: Mining Human-Centric Look and Feel Evolution in Open-Source Software},
  author={Payaslı, Eliz and Krüger, Jacob and Nolte, Alexander},
  journal={Empirical Software Engineering},
  year={2026}
}
```

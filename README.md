# Data-Driven UI/UX Modernization: Mining Human-Centric Look and Feel Evolution in Open-Source Software

**Authors:** Eliz Payaslı, Jacob Krüger, Alexander Nolte  
**Date:** July 2026  
**Affiliation:** Eindhoven University of Technology, Software Engineering & Technology (SET) Group

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
├── scripts/
│   ├── mine_commits_improved.py                    # Phase 2: Commit mining pipeline
│   ├── llm_classify_aspects_causes.py              # Cause/Aspect classification
│   ├── llm_label_api.py                            # LLM integration utilities
│   ├── hand_label_200.py                           # Manual validation interface
│   ├── label_commits.py                            # Commit classification
│   ├── fetch_filenames.py                          # GitHub API utilities
│   └── apply_all.py                                # Batch processing
├── paper/
│   ├── paper.tex                                   # Full LaTeX paper manuscript
│   ├── aspects_causes_chart.tex                    # Cause/Aspect visualizations
│   └── full_pool_charts.tex                        # Full dataset visualizations
├── README.md                                       # This file
├── LICENSE                                         # MIT License
└── .gitignore                                      # Git ignore rules
```

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

## Citation

If you use this dataset or findings in your research, please cite:

```bibtex
@article{payasli2026uiux,
  title={Data-Driven {UI}/{UX} Modernization: Mining Human-Centric Look and Feel Evolution in Open-Source Software},
  author={Payaslı, Eliz and Krüger, Jacob and Nolte, Alexander},
  journal={Empirical Software Engineering},
  year={2026},
  publisher={Springer}
}
```

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

## Contact

For questions, feedback, or collaboration inquiries:
- **Eliz Payaslı** - elizpayasli.ep@gmail.com
- **Jacob Krüger** - Eindhoven University of Technology
- **Alexander Nolte** - Eindhoven University of Technology

---

**Last Updated:** August 4, 2026

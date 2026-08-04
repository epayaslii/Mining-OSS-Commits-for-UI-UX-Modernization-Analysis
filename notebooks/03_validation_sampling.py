"""
Phase 3: Validation & Reliability Check

This script creates validation samples for manual labeling:
1. Random 200-commit sample (precision estimation)
2. Stratified per-repository sample (3 commits per repo)

These samples are used for:
- Manual validation by researchers
- Computing filter precision and inter-rater agreement (Cohen's κ)
- LLM validation cross-checks

Output:
- validation_sample_random200.csv
- validation_sample_stratified.csv
"""

import pandas as pd
import os

# ============================================================================
# Configuration
# ============================================================================

INPUT_CSV = "ui_commits_checkpoint_final.csv"
RANDOM_SAMPLE_SIZE = 200
STRATIFIED_PER_REPO = 3

# ============================================================================
# Random Sample Validation
# ============================================================================

def create_random_sample():
    """Create random 200-commit sample for manual validation."""
    df_commits = pd.read_csv(INPUT_CSV)

    print(f"Total UI commits available: {len(df_commits)}")
    print(f"Generating random {RANDOM_SAMPLE_SIZE}-commit sample...")

    random_sample = df_commits.sample(n=RANDOM_SAMPLE_SIZE, random_state=42)
    random_sample.to_csv("validation_sample_random200.csv", index=False)

    kw_count = random_sample['keyword_match'].sum()
    file_count = (~random_sample['keyword_match'] & random_sample['file_match']).sum()

    print(f"\n✓ Random sample saved: {len(random_sample)} commits")
    print(f"   🔤 Keyword Matches: {kw_count} ({kw_count/RANDOM_SAMPLE_SIZE:.1%})")
    print(f"   📄 File Matches Only: {file_count} ({file_count/RANDOM_SAMPLE_SIZE:.1%})")
    print(f"   Unique repos in sample: {random_sample['repo'].nunique()}")

    return random_sample


# ============================================================================
# Stratified Sample Validation
# ============================================================================

def create_stratified_sample():
    """Create stratified 3-per-repo sample for per-repository validation."""
    df_commits = pd.read_csv(INPUT_CSV)
    df_repos = pd.read_csv("repositories_filtered.csv")

    print(f"\nTotal repositories to process: {len(df_repos)}")
    print(f"Generating stratified sample ({STRATIFIED_PER_REPO} per repo)...")

    stratified_samples = []
    repos_covered = 0

    for repo_name in df_repos["name"].unique():
        repo_commits = df_commits[df_commits["repo"] == repo_name]
        n = min(STRATIFIED_PER_REPO, len(repo_commits))

        if n > 0:
            sample = repo_commits.sample(n=n, random_state=42)
            stratified_samples.append(sample)
            repos_covered += 1

    stratified_sample = pd.concat(stratified_samples, ignore_index=True)
    stratified_sample.to_csv("validation_sample_stratified.csv", index=False)

    total_strat = len(stratified_sample)
    kw_count_strat = stratified_sample['keyword_match'].sum()
    file_count_strat = (~stratified_sample['keyword_match'] & stratified_sample['file_match']).sum()

    print(f"\n✓ Stratified sample saved: {total_strat} commits")
    print(f"   Repositories represented: {repos_covered} / {len(df_repos)}")
    print(f"   🔤 Keyword Matches: {kw_count_strat} ({kw_count_strat/total_strat:.1%})")
    print(f"   📄 File Matches Only: {file_count_strat} ({file_count_strat/total_strat:.1%})")
    print(f"   Avg commits per repo: {total_strat/repos_covered:.2f}")

    return stratified_sample


# ============================================================================
# Preview for Manual Labeling
# ============================================================================

def preview_sample(df, sample_name, num_preview=5):
    """Print preview of commits for manual labeling."""
    print(f"\n{'='*70}")
    print(f"Preview: First {num_preview} commits from {sample_name}")
    print(f"{'='*70}")

    for i, (idx, row) in enumerate(df.head(num_preview).iterrows()):
        print(f"\n[{i+1}] Repository: {row['repo']}")
        print(f"    SHA: {row['sha']}")
        print(f"    Message: {row['message'][:150]}...")
        print(f"    Match: {'🔤 Keyword' if row['keyword_match'] else '📄 File'}")
        print(f"    GitHub: https://github.com/{row['repo']}/commit/{row['sha']}")
        print(f"    Date: {row['date']}")


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("Phase 3: Validation Sample Creation")
    print("="*70)

    # Create samples
    random_sample = create_random_sample()
    stratified_sample = create_stratified_sample()

    # Show previews
    preview_sample(random_sample, "Random 200-Sample", num_preview=3)
    preview_sample(stratified_sample, "Stratified Sample", num_preview=3)

    print(f"\n{'='*70}")
    print("✓ Validation samples ready for manual coding!")
    print("="*70)
    print("\nNext steps:")
    print("1. Open 'validation_sample_random200.csv' in a spreadsheet")
    print("2. Add columns: 'manual_ui_related', 'manual_cause', 'manual_aspect'")
    print("3. Code 200 commits for precision estimation")
    print("4. Open 'validation_sample_stratified.csv' for per-repo validation")
    print("5. Calculate inter-rater agreement (Cohen's κ)")

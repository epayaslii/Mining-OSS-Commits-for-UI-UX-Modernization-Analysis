"""
Phase 4: ML Pipeline - TF-IDF Clustering & Tier Classification

This script performs unsupervised clustering of commit messages to classify
modernization aspects (Tier levels) across the full commit pool:

1. Feature Extraction: TF-IDF vectorization of cleaned commit messages
2. Clustering: MiniBatchKMeans with K=3 (Up-Level, Intermediate-Level, Down-Level)
3. Validation: Purity score, ANOVA F-test for statistical significance
4. LLM Input Prep: Generates prompts for LLM-assisted validation

Output:
- ui_commits_clustered.csv (with cluster and tier assignments)
- llm_validation_input.csv (for LLM classification)
"""

import pandas as pd
import numpy as np
import re
import warnings
warnings.filterwarnings('ignore')

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import MiniBatchKMeans
from sklearn.metrics import pairwise_distances_argmin_min, cohen_kappa_score
from sklearn.preprocessing import normalize
from scipy.stats import f_oneway

# ============================================================================
# Configuration
# ============================================================================

INPUT_CSV = "ui_commits_checkpoint_final.csv"
OUTPUT_CLUSTERED = "ui_commits_clustered.csv"
OUTPUT_LLM = "llm_validation_input.csv"

RANDOM_STATE = 42
N_CLUSTERS = 3
MIN_TOKEN_LENGTH = 3
MIN_MESSAGE_LENGTH = 5

# ============================================================================
# Text Preprocessing
# ============================================================================

STOP_WORDS = frozenset({
    'the', 'a', 'an', 'is', 'it', 'in', 'on', 'at', 'to', 'for', 'of', 'and', 'or',
    'but', 'not', 'with', 'this', 'that', 'was', 'are', 'be', 'as', 'by', 'from',
    'have', 'has', 'had', 'do', 'did', 'will', 'would', 'could', 'should', 'may',
    'fix', 'fixes', 'fixed', 'add', 'adds', 'added', 'update', 'updates', 'updated',
    'change', 'changes', 'changed', 'remove', 'removes', 'removed', 'merge', 'merged'
})

URL_RE = re.compile(r'https?://\S+')
NON_ALNUM_RE = re.compile(r'[^a-z0-9\s]')
MULTI_SPACE_RE = re.compile(r'\s+')


def clean_text(text):
    """Clean and preprocess commit message text."""
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = URL_RE.sub('', text)  # Remove URLs
    text = NON_ALNUM_RE.sub(' ', text)  # Keep only alphanumeric + space
    text = MULTI_SPACE_RE.sub(' ', text).strip()  # Normalize whitespace
    # Filter stop words and short tokens
    return ' '.join(
        w for w in text.split()
        if w not in STOP_WORDS and len(w) > MIN_TOKEN_LENGTH
    )


# ============================================================================
# Feature Extraction & Clustering
# ============================================================================

def run_ml_pipeline():
    """Run complete ML clustering pipeline."""
    print("="*70)
    print("Phase 4: ML Clustering Pipeline")
    print("="*70)

    # Load data
    print("\n1. Loading data...")
    df_commits = pd.read_csv(INPUT_CSV)
    print(f"   Total UI commits: {len(df_commits)}")

    # Preprocess
    print("\n2. Preprocessing messages...")
    df_commits['clean_message'] = df_commits['message'].apply(clean_text)
    df_commits = df_commits[
        df_commits['clean_message'].str.len() > MIN_MESSAGE_LENGTH
    ].reset_index(drop=True)
    print(f"   After cleaning: {len(df_commits)} commits")

    # TF-IDF
    print("\n3. Computing TF-IDF vectors...")
    vectorizer = TfidfVectorizer(
        max_features=500,
        min_df=3,
        max_df=0.90,
        ngram_range=(1, 2),
        sublinear_tf=True,
        dtype=np.float32
    )
    X = vectorizer.fit_transform(df_commits['clean_message'])
    print(f"   TF-IDF matrix shape: {X.shape}")

    # Clustering
    print("\n4. Clustering with MiniBatchKMeans...")
    kmeans = MiniBatchKMeans(
        n_clusters=N_CLUSTERS,
        random_state=RANDOM_STATE,
        batch_size=1024,
        n_init=5,
        max_iter=100
    )
    df_commits['cluster'] = kmeans.fit_predict(X)

    # Interpret clusters
    feature_names = vectorizer.get_feature_names_out()
    print("\n5. Top terms per cluster:")
    for cid in range(N_CLUSTERS):
        top_idx = kmeans.cluster_centers_[cid].argsort()[-12:][::-1]
        top_terms = [feature_names[i] for i in top_idx]
        print(f"   Cluster {cid}: {top_terms}")

    # Map clusters to tiers
    CLUSTER_TO_TIER = {
        0: "Up-Level",
        1: "Intermediate-Level",
        2: "Down-Level"
    }
    df_commits['tier'] = df_commits['cluster'].map(CLUSTER_TO_TIER)

    print(f"\n6. Cluster distribution:")
    print(df_commits['tier'].value_counts())

    # Purity validation (if validation samples exist)
    print("\n7. Purity validation (if available):")
    for sample_file, label in [
        ("validation_sample_random200.csv", "Random 200"),
        ("validation_sample_stratified.csv", "Stratified")
    ]:
        try:
            sample = pd.read_csv(sample_file)
            if 'manual_tier' not in sample.columns:
                print(f"   {label}: 'manual_tier' column not found (not yet coded)")
                continue
            merged = sample.merge(
                df_commits[['sha', 'cluster']],
                on='sha',
                how='inner'
            )
            if len(merged) == 0:
                continue
            purity = (
                merged.groupby('cluster')['manual_tier']
                .agg(lambda x: x.value_counts().iloc[0])
                .sum() / len(merged)
            )
            print(f"   {label}: Purity = {purity:.3f} (n={len(merged)})")
        except FileNotFoundError:
            print(f"   {label}: File not found")

    # ANOVA F-test
    print("\n8. ANOVA F-test (cluster separation):")
    X_norm = normalize(X, norm='l2', copy=False)
    centers_norm = normalize(kmeans.cluster_centers_, norm='l2')
    _, dists_all = pairwise_distances_argmin_min(X_norm, centers_norm, metric='cosine')
    distances = [
        dists_all[df_commits['cluster'].values == cid]
        for cid in range(N_CLUSTERS)
    ]
    f_stat, p_value = f_oneway(*distances)
    print(f"   F-statistic: {f_stat:.4f}")
    print(f"   p-value: {p_value:.6g}")
    print(f"   {'✓' if p_value < 0.05 else '✗'} Clusters are {'statistically distinct' if p_value < 0.05 else 'NOT distinct'}")

    # Save clustered results
    print("\n9. Saving results...")
    df_commits.to_csv(OUTPUT_CLUSTERED, index=False)
    print(f"   ✓ Saved: {OUTPUT_CLUSTERED}")

    # Prepare LLM validation input
    print("\n10. Preparing LLM validation input...")
    llm_input = df_commits[['sha', 'repo', 'message', 'date', 'keyword_match', 'file_match', 'tier']].copy()
    llm_input['prompt'] = (
        "Repository: " + llm_input['repo'].astype(str) +
        "\nCommit message: " + llm_input['message'].astype(str) +
        "\nIs this UI-related modernization? Respond: Yes or No"
    )
    llm_input.to_csv(OUTPUT_LLM, index=False)
    print(f"   ✓ Saved: {OUTPUT_LLM}")

    # Summary statistics
    print("\n" + "="*70)
    print("Summary Statistics")
    print("="*70)
    summary = df_commits.groupby('tier').agg(
        count=('sha', 'count'),
        keyword_match_pct=('keyword_match', 'mean'),
        file_match_pct=('file_match', 'mean')
    )
    summary['volume_pct'] = (summary['count'] / len(df_commits) * 100).round(1)
    summary[['keyword_match_pct', 'file_match_pct']] = summary[
        ['keyword_match_pct', 'file_match_pct']
    ].round(3)
    print(summary)

    return df_commits


if __name__ == "__main__":
    df = run_ml_pipeline()
    print(f"\n✓ ML pipeline complete!")
    print(f"  Total commits clustered: {len(df)}")

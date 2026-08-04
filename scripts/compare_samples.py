import pandas as pd
from label_commits import classify

df = pd.read_csv("ui_commits_checkpoint_final.csv")
def label(d):
    r=[classify(x.repo,x.message,x.keyword_match,x.file_match) for x in d.itertuples()]
    d=d.copy(); d["llm_label"]=[a for a,_ in r]; return d
def pct(d):
    n=len(d); no=(d.llm_label=="No").sum(); return n,(n-no),no,no/n*100

full=label(df)
rand=label(df.sample(n=200, random_state=42))
strat=label(df.groupby("repo",group_keys=False).head(10))

print(f"{'Sample':<22}{'N':>6}{'Yes':>7}{'No':>6}{'Error%':>9}{'Prec%':>8}")
for name,d in [("Full dataset",full),("Random 200 (seed42)",rand),("Stratified 10/repo",strat)]:
    n,y,no,e=pct(d)
    print(f"{name:<22}{n:>6}{y:>7}{no:>6}{e:>8.1f}%{100-e:>7.1f}%")

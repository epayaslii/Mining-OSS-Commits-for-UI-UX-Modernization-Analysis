import pandas as pd, math
from label_commits import classify

df = pd.read_csv("ui_commits_checkpoint_final.csv")

def label(d):
    r=[classify(x.repo,x.message,x.keyword_match,x.file_match) for x in d.itertuples()]
    d=d.copy(); d["llm_label"]=[a for a,_ in r]; d["llm_reason"]=[b for _,b in r]
    return d

def moe(p,n,N=None):  # 95% margin of error, optional finite-pop correction
    se=math.sqrt(p*(1-p)/n)
    if N: se*=math.sqrt((N-n)/(N-1))
    return 1.96*se*100

N=len(df)
full  = label(df)
rand  = label(df.sample(n=200, random_state=42))
strat = label(df.groupby("repo",group_keys=False).head(10))

full.to_csv("ui_commits_checkpoint_final_labeled.csv", index=False)
rand.to_csv("validation_sample_random200_labeled.csv", index=False)
strat.to_csv("validation_sample_stratified_labeled.csv", index=False)

print(f"{'Sample':<24}{'N':>6}{'Yes':>6}{'No':>5}{'Error%':>9}{'±MoE':>9}{'  95% CI'}")
for name,d,fpc in [("Full (census)",full,False),
                   ("Random 200 (seed42)",rand,True),
                   ("Stratified 10/repo",strat,True)]:
    n=len(d); no=(d.llm_label=="No").sum(); p=no/n; e=p*100
    m=0.0 if name.startswith("Full") else moe(p,n,N if fpc else None)
    ci=f"[{max(0,e-m):.1f}%, {e+m:.1f}%]" if m else "(no sampling error)"
    print(f"{name:<24}{n:>6}{n-no:>6}{no:>5}{e:>8.1f}%{m:>8.1f}%  {ci}")

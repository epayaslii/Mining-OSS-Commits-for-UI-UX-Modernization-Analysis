import pandas as pd
df = pd.read_csv("ui_commits_checkpoint_final.csv")
s = df.sample(n=200, random_state=42).reset_index(drop=True)
s.to_csv("_sample200.csv", index=False)
for i,r in s.iterrows():
    msg = " ".join(str(r.message).split())[:180]
    print(f"{i}\t{r.repo}\t{msg}")

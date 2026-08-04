import pandas as pd, math

# My (LLM) judgments for the seed-42 random-200 sample: idx -> (label, reason)
J = {
0:("Yes","music item style patch"),1:("Yes","event resizing interaction in component"),
2:("No","database NOT NULL schema logic"),3:("Yes","restore page scrolling behavior"),
4:("No","docs and examples only"),5:("No","backend sandbox/architecture removal"),
6:("Yes","edits chat-panel UI component"),7:("No","backend worker/server version check"),
8:("No","backend diagnostic noise reduction"),9:("No","lint config dependency fix"),
10:("Yes","color control UI feature for docs"),11:("No","vague, no UI signal"),
12:("Yes","UI routing correction"),13:("No","filter option persistence logic"),
14:("Yes","polish of UI workspace"),15:("Yes","pie panel chart rendering fix"),
16:("Yes","ui-tagged canvas save/load feature"),17:("No","backend env loading (BE ticket)"),
18:("No","admin feature-flag/backend"),19:("No","version number bump"),
20:("No","docs only"),21:("No","compatibility list/docs"),
22:("No","docs sections"),23:("Yes","heatmap button styling"),
24:("No","backend JSON-merge action"),25:("Yes","user disk-allocation warning UI"),
26:("No","thumbnail selection validation logic"),27:("Yes","gridlines prop on calendar views"),
28:("Yes","adds resource kind icons to table"),29:("No","CLI arg parsing"),
30:("Yes","removes banner, streamlines layout/sidebar"),31:("No","multiuser data isolation feature"),
32:("No","infra cluster port config"),33:("Yes","responsive PDF scaling on mobile"),
34:("No","version bump"),35:("No","backend downloader refactor"),
36:("Yes","sticky header scroll behavior"),37:("Yes","adds config selectors/controls"),
38:("No","backend webrtc/ios fixes"),39:("Yes","notification UI island"),
40:("Yes","overlay display fix"),41:("No","vague event bug"),
42:("Yes","DatePicker fullWidth prop/layout"),43:("No","TS return-type change"),
44:("No","angular v22 tooling support"),45:("Yes","card viewlet UI setting fix"),
46:("No","sentry package bump"),47:("No","backend manager refactor"),
48:("No","vague code todos"),49:("No","core upgrade process logic"),
50:("No","backend queue/concurrency engine"),51:("No","version release"),
52:("Yes","channel banner display behavior"),53:("Yes","timeline animation + layout"),
54:("Yes","adds actions to cards UI"),55:("No","backend gpu stats feature"),
56:("No","referral URL/sponsor config"),57:("Yes","component prop handling fix"),
58:("No","backend server for workers"),59:("Yes","menu type-ahead interaction"),
60:("Yes","dropdown badge alignment styling"),61:("No","vague sync update"),
62:("No","widget id-generation logic"),63:("Yes","UI/UX tweaks"),
64:("No","backend detector fixes"),65:("No","backend scrape format"),
66:("No","backend conversation isolation"),67:("Yes","heatmap viewport + tooltips polish"),
68:("Yes","progress bar UI"),69:("No","Electron framework upgrade"),
70:("Yes","slide navigation behavior"),71:("No","backend webdav type fix"),
72:("Yes","adds ENSBadge UI component"),73:("Yes","adds UI buttons/feature"),
74:("No","dependency version bump"),75:("No","guest permissions backend"),
76:("Yes","dialog button layout/UI tweaks"),77:("No","storybook stories only"),
78:("No","backend port manager overhaul"),79:("Yes","visual contrast for themes"),
80:("Yes","tooltip on setting"),81:("Yes","align banner and search field"),
82:("No","mask feature refactor"),83:("No","admin stats backend"),
84:("No","security/deps audit"),85:("No","Oracle DB import support"),
86:("No","deps/version bump"),87:("No","image basepath path logic"),
88:("No","lint tooling switch"),89:("No","editor parsing correctness"),
90:("Yes","settings revamp + mic button"),91:("Yes","field icon sizing"),
92:("No","dependency upgrade"),93:("No","backend plugin integration"),
94:("No","backend excluded-urls config"),95:("No","eslint rule"),
96:("Yes","drag-and-drop upload interaction"),97:("No","dependency update"),
98:("No","dependency bump (renovate)"),99:("No","nx tooling migration"),
100:("No","demo content tweak"),101:("No","react dependency bump"),
102:("No","test timing change"),103:("No","vague version feature"),
104:("No","list dedup data fix"),105:("No","changesets version release"),
106:("No","vague version feature"),107:("No","backend AI providers"),
108:("No","vague 'editor feedback'"),109:("No","prereq check/backend"),
110:("Yes","long-turn UX visibility/feedback"),111:("Yes","model icon fix"),
112:("No","trial/billing logic"),113:("Yes","adds reset button"),
114:("Yes","branch label refresh"),115:("No","routing/legacy cleanup"),
116:("No","internal filter-registration plumbing"),117:("No","backend API body limit"),
118:("Yes","icon picker interaction"),119:("No","animation helper code refactor"),
120:("No","code ASI/refactor logic"),121:("No","backend port manager removal"),
122:("No","feature/logic removal"),123:("No","translations/i18n"),
124:("No","backend SMS scoping feature"),125:("Yes","adds CTA on error screen"),
126:("Yes","collapse/fold interaction"),127:("Yes","chat UI polish/compact display"),
128:("No","macOS app launch/build fix"),129:("No","billing system feature"),
130:("Yes","cosmetic UI (lipstick emoji)"),131:("No","filter/sort data feature"),
132:("Yes","file menu fix"),133:("No","backend emulation/mouse"),
134:("No","TS type-safety cleanup"),135:("No","backend state framework"),
136:("No","security/deps audit"),137:("No","version release"),
138:("Yes","panel error display UI"),139:("Yes","theme dialog layout fix"),
140:("No","mentions feature logic"),141:("No","form draft persistence logic"),
142:("No","redirect link update"),143:("Yes","editor readonly support behavior"),
144:("Yes","flyout shows chart UI"),145:("No","package updates"),
146:("No","React Native framework upgrade"),147:("Yes","adds license preview/diff view"),
148:("No","backend fs routes"),149:("No","undefined-data guard"),
150:("Yes","theme methods change"),151:("Yes","TimePicker input behavior"),
152:("No","version publish"),153:("No","docs rebake"),
154:("Yes","clipboard paste + image previews"),155:("Yes","autocomplete input assist"),
156:("No","column dedup data logic"),157:("No","deps-dev bump"),
158:("No","docker build fix"),159:("No","backend feature flag"),
160:("Yes","fixes endless loading state"),161:("No","backend agent tool"),
162:("No","backend manager refactor"),163:("No","analytics tracking"),
164:("Yes","ui-tagged DOM render guard"),165:("No","backend Workday actions"),
166:("No","version bump"),167:("Yes","adds keyframe graphs button"),
168:("No","security dep upgrade"),169:("Yes","surfaces failures to user"),
170:("No","version release"),171:("Yes","mini-player size adjustment"),
172:("Yes","padding fix on settings page"),173:("No","hot-reload dev fix"),
174:("No","file relocation"),175:("Yes","block toolbar behavior"),
176:("No","search/pinning data feature"),177:("No","broken url fix"),
178:("No","backend cron/metadata flows"),179:("No","backend CORS security"),
180:("No","backend integration service"),181:("No","editor scale-lock logic"),
182:("No","trade-amount validation"),183:("No","backend json util"),
184:("Yes","replaces submenu icon"),185:("No","security fixes"),
186:("Yes","chat window display timing"),187:("Yes","dark-mode styles"),
188:("No","backend language header"),189:("No","deps/backend genai"),
190:("No","frontend listener cleanup refactor"),191:("Yes","menu item enable behavior"),
192:("Yes","node alignment visual"),193:("No","backend model loader"),
194:("No","version release"),195:("No","backend role logic"),
196:("Yes","topic drawer layout align"),197:("Yes","dark mode fix"),
198:("No","version tracking config"),199:("Yes","dark mode text color fix"),
}

df = pd.read_csv("_sample200.csv")
assert len(df)==200
df["llm_label"]=[J[i][0] for i in range(200)]
df["llm_reason"]=[J[i][1] for i in range(200)]
df.to_csv("validation_sample_random200_HANDLABELED.csv", index=False)

n=200; no=(df.llm_label=="No").sum(); p=no/n
se=math.sqrt(p*(1-p)/n)*math.sqrt((3727-200)/(3727-1)); m=1.96*se*100
print("Genuine LLM hand-labeling of random-200 (seed42):")
print(f"  Yes(UI): {n-no}  No(not UI): {no}")
print(f"  Error/false-positive rate: {p*100:.1f}%  +/-{m:.1f}%  -> 95% CI [{p*100-m:.1f}%, {p*100+m:.1f}%]")
print(f"  Precision: {(1-p)*100:.1f}%")

from label_commits import classify
rb=[classify(x.repo,x.message,x.keyword_match,x.file_match)[0] for x in df.itertuples()]
rb_no=sum(1 for l in rb if l=="No")
agree=sum(1 for i in range(200) if rb[i]==df.llm_label.iloc[i])
print(f"\nRule-based on same 200: No={rb_no} ({rb_no/2:.1f}% error)")
print(f"Agreement rule-based vs hand: {agree}/200 = {agree/2:.1f}%")

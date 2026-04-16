# Japan AI Meeting Notes SaaS Concept Test — Demo

> B2B SaaS. Japan market. 3 positioning concepts for enterprise buyers.
> 10 AI personas across Japanese industries. Natural language commands.

---

## The Scenario

You are a product team at an AI meeting notes startup preparing to enter the
Japanese enterprise market. Before investing in localization and sales
materials, you want directional signal on which positioning resonates with
potential buyers across different industries and company sizes.

**Three positioning concepts:**

**Concept A: Save Time** — AI meeting notes software that records meetings,
writes summaries, and captures action items automatically so teams spend less
time on admin work.

**Concept B: Better Follow Through** — An AI meeting assistant that helps
teams remember decisions, track next steps, and make sure important follow-ups
do not get lost after meetings.

**Concept C: Cleaner CRM and Team Visibility** — AI meeting notes software
that turns conversations into structured notes and gives managers better
visibility into customer calls, team activity, and pipeline discussions.

---

## What Makes This Demo Different

1. **B2B SaaS** — Unlike consumer product demos, these personas evaluate
   software through enterprise buying lenses: IT security review, compliance
   requirements, procurement approval cycles (ringi), and ROI justification.
   Hesitations are organizational, not personal.

2. **Japan market** — Setting the market to Japan produces personas with
   Japanese names and Japanese companies (NTT Data, Sumitomo Mitsui, Daiichi
   Sankyo). Their responses then surfaced Japan-specific enterprise dynamics
   — keigo-aware NLP requirements, data residency concerns, nemawashi-style
   approval, and multi-month IT security review timelines — that emerged
   organically without being specified in the generate prompt.

---

## 3-Step Workflow

### Step 1: Build Panel

```
/persona generate 10 Potential buyers of AI meeting notes software in Japan
```

10 personas generated across diverse B2B buyer segments:

| # | Name | Age | Occupation | Segment |
|---|------|-----|------------|---------|
| 1 | Kenji Yamamoto | 34 | IT Project Manager, NTT Data | Efficiency-Obsessed Manager |
| 2 | Masahiro Ito | 56 | Manufacturing Division GM | Analog Traditionalist |
| 3 | Yuki Tanabe | 28 | COO & Co-founder, FlowBoard Inc. | Startup Juggler |
| 4 | Rina Ogawa | 43 | Corporate Planning, Sumitomo Mitsui Trust Bank | Overwhelmed Section Chief |
| 5 | Takeshi Morimoto | 47 | IT Director, Nihon Sogo Consulting | Skeptical IT Gatekeeper |
| 6 | Ayaka Nishimura | 32 | Freelance UX Designer, Fukuoka | Remote Creative Freelancer |
| 7 | Sachiko Harada | 53 | Managing Director, Tax Accounting Office | Cost-Conscious SMB Owner |
| 8 | Shota Kimura | 26 | Medical Representative, Daiichi Sankyo | Young Field Rep |
| 9 | Noboru Watanabe | 61 | Section Chief, Nara Prefectural Government | Government Bureaucrat |
| 10 | Haruka Fujimoto | 36 | DX Promotion Lead, Lion Corporation | Innovation Champion |

The panel spans enterprise (NTT Data, Sumitomo Mitsui), startup (FlowBoard),
SMB (tax office), government (Nara Prefecture), pharma (Daiichi Sankyo), and
freelance — covering the full spectrum of B2B buyer types in Japan.

### Step 2: Explore Motivations

```
/persona ask What would make you interested in trying AI meeting notes software, and what would make you hesitate before buying it?
```

Top themes surfaced:
- **Japanese language accuracy** — 8/10 personas cite keigo, code-switching, and industry terminology as critical
- **Data residency** — 7/10 require Japan-region hosting; overseas-only data routing is a dealbreaker for finance, pharma, government
- **IT/compliance approval gates** — Enterprise buyers face 4-6 month security review timelines
- **Human review before circulation** — AI-generated meeting records must be reviewed before distribution
- **Pricing transparency** — SMB and freelance buyers fear subscription creep; startups need free tiers
- **ROI proof** — Skeptics demand concrete numbers from comparable Japanese companies

### Step 3: Run Concept Test

```
/persona concept-test

Concept A: Save Time
AI meeting notes software that records meetings, writes summaries, and captures action items automatically so teams spend less time on admin work.

Concept B: Better Follow Through
An AI meeting assistant that helps teams remember decisions, track next steps, and make sure important follow ups do not get lost after meetings.

Concept C: Cleaner CRM and Team Visibility
AI meeting notes software that turns conversations into structured notes and gives managers better visibility into customer calls, team activity, and pipeline discussions.
```

### Results

- **B: Better Follow Through** — 9/10 (90%) first choice
- **A: Save Time** — 1/10 (10%) first choice
- **C: Cleaner CRM** — 0/10 (0%) first choice
- **Purchase likelihood**: mean 3.1/5, range 2–4

Concept B won decisively. The panel's message is clear: **automated
transcription is "table stakes," not differentiation.** The real pain point
in Japanese enterprise is decisions evaporating after meetings — follow-through
is what buyers will pay for.

**The lone A voter** — Shota Kimura (Young Field Rep) — spends 2 hours every
night writing visit reports. For him, time savings is the acute problem.
Everyone else already sees transcription as commodity functionality.

**Concept C received zero votes.** CRM integration and manager visibility
felt too narrow (sales-team-specific) and raised surveillance concerns in
a culture that values consensus over top-down monitoring.

**Key Japan-specific blockers surfaced across all concepts:**
- Data residency (Japan-region hosting or on-premise)
- Japanese NLP accuracy (keigo, code-switching, industry jargon)
- Human review workflows before automated distribution
- Procurement timelines (ringi approval, IT security checklists)

[Summary](concept-test/results/summary.json) |
[Results JSON](concept-test/results/results.json) |
[Ask Results](ask/results/results.json)

---

### View pre-generated results (no API calls needed)

Results are already committed. Browse `concept-test/results/` and `ask/results/`.

---

## What's in the Box

```
demo/japan-meeting-ai/
├── README.md                          <- You are here
├── personas/                          <- 10-persona panel (Japan)
│   ├── manifest.json
│   └── 10 persona JSON files
├── ask/
│   └── results/
│       ├── results.json, report.md, summary.json
│       └── results.csv, persona_comparison.csv, run_metadata.json
└── concept-test/
    ├── config.json                    <- 3 AI meeting notes concepts (A/B/C)
    └── results/
        ├── results.json, report.md, summary.json
        ├── results.csv, persona_comparison.csv
        ├── run_metadata.json
        └── chart_overall.png, chart_purchase_likelihood.png
```

---

## Caveats

- Virtual panel of 10 AI personas; directional only
- Not statistically representative; use for hypothesis generation
- AI-generated responses may exhibit positivity bias
- Each segment is represented by a single persona; treat segment-level observations as illustrative, not proportional

# Directory Structure

```
claude-persona/
├── SKILL.md                    # Skill orchestration logic (Claude Code skill entry point)
├── README.md                   # User-facing documentation
├── CLAUDE.md                   # Developer guidance for Claude Code
├── requirements.txt            # Python dependencies (analysis only)
├── references/
│   ├── simulation-prompt.md            # Core simulation prompt (loaded at runtime)
│   ├── adherence-check-prompt.md       # Adherence scoring (loaded at runtime)
│   ├── persona-schema.md               # Persona JSON schema
│   ├── persona-generation-prompt.md    # Segment-driven generation template
│   ├── persona-generation-prompt-topiconly.md  # Topic-driven generation template
│   ├── segment-inference-prompt.md     # Topic → segments inference prompt
│   ├── topic-only-generation-flow.md   # 4-step topic-only generation flow
│   ├── report-template.md             # One-pager report template & rules
│   ├── command-details.md             # Detailed input/output per command
│   ├── directory-structure.md         # This file
│   └── test-cases.md                  # Trigger & functional test suite
├── scripts/
│   ├── simulate_survey.py      # Agent-separated survey engine (claude -p CLI)
│   ├── analyze_results.py      # Python analysis & visualization
│   └── llm_backends.py         # Shared backend adapters (claude-cli, codex-cli)
├── templates/
│   └── concept_test.md         # Concept test survey template (primary)
├── demo/
│   └── running-shoes/          # Concept test demo (15 personas, full results)
│       ├── README.md
│       ├── concept-test/       # Config + results
│       └── personas/           # 15 pre-generated personas + manifest.json
├── personas/                   # Generated persona panels (per survey run)
│   └── _archive/               # Historical panels (git-ignored)
├── tests/                      # Unit tests (34 cases)
└── outputs/                    # Survey results (date-organized, git-ignored)
    └── {YYYY-MM-DD}/{HHMMSS}/{survey_type}/
```

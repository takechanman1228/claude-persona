# Installation

`claude-persona` can be installed either as a Claude Code plugin or as a local
skill copied into `~/.claude/skills/persona/`.

## Prerequisites

| Requirement | Version | Purpose |
|-------------|---------|---------|
| Claude Code | latest | Runs `/persona` commands |
| Python | 3.10+ | Simulation and analysis scripts |
| git | latest | Clone or install script |
| pip | latest | Optional dependency install for analysis |

`simulate_survey.py` and `analyze_results.py` expect Python 3.10+.
For the analysis pipeline, install:

```bash
python3 -m pip install --user -r requirements.txt
```

## Plugin Install

```bash
/plugin marketplace add takechanman1228/claude-persona
/plugin install claude-persona@claude-persona
```

Restart Claude Code after installation.

If your Claude Code build namespaces plugin commands, run:

```bash
/claude-persona:persona concept-test Running shoes: 3 concepts
```

Otherwise use the standard command:

```bash
/persona concept-test Running shoes: 3 concepts
```

## One-Command Install

```bash
curl -fsSL https://raw.githubusercontent.com/takechanman1228/claude-persona/main/install.sh | bash
```

This copies the skill into `~/.claude/skills/persona/` and attempts a best-effort
dependency install.

## Clone and Install

```bash
git clone https://github.com/takechanman1228/claude-persona.git
bash claude-persona/install.sh
```

## Manual Install

```bash
mkdir -p ~/.claude/skills/persona
cp skills/persona/SKILL.md ~/.claude/skills/persona/SKILL.md
cp CLAUDE.md ~/.claude/skills/persona/CLAUDE.md
cp requirements.txt ~/.claude/skills/persona/requirements.txt
cp -R scripts references templates demo docs assets ~/.claude/skills/persona/
```

Then restart Claude Code.

## Verify

```bash
ls ~/.claude/skills/persona/SKILL.md
ls ~/.claude/skills/persona/scripts/simulate_survey.py
ls ~/.claude/skills/persona/demo/running-shoes/concept-test/results/report.md
```

Optional sanity checks:

```bash
python3 -m py_compile scripts/*.py
python3 -m unittest discover -s tests -v
```

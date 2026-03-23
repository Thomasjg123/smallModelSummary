# Context Refinement Debug CLI

Tools in this repo are for running and inspecting chunked summarization tests.  
Your main entry point is `debug_cli.py`.

## What Is Included

- `debug_cli.py`: step-by-step debug workflow for one config
- `run_debug.sh`: non-interactive wrapper for quick debug runs
- `run_tests.py`: batch runs across configs
- `dashboard.py` / `dashboard_v2.py`: view run/test results
- `config.py`: test definitions + model config
- `db.py`: SQLite schema and persistence
- `articles/`: cached article text
- `runs/`: run artifacts/output
- `data/context_tests.db`: SQLite database

## Quick Start

1. Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. (Optional) Override model/database settings via env vars:

```bash
export DEBUGCLI_SMALL_MODEL_BASE_URL="http://localhost:8080/v1"
export DEBUGCLI_BIG_MODEL_BASE_URL="http://localhost:8000/v1"
export DEBUGCLI_DB_PATH="data/context_tests.db"
```

4. Run debug CLI:

```bash
python3 debug_cli.py
```

5. Run a specific config with a chunk limit:

```bash
python3 debug_cli.py 03 2
```

## Environment Variables

Canonical templates:

- JSON template: `env/environment.example.json`
- Text template: `env/ENV_VARS.txt`

Current supported variables:

- `DEBUGCLI_SMALL_MODEL_BASE_URL`
- `DEBUGCLI_SMALL_MODEL_NAME`
- `DEBUGCLI_SMALL_MODEL_DISPLAY_NAME`
- `DEBUGCLI_SMALL_MODEL_TEMPERATURE`
- `DEBUGCLI_SMALL_MODEL_MAX_TOKENS`
- `DEBUGCLI_SMALL_MODEL_TIMEOUT`
- `DEBUGCLI_BIG_MODEL_BASE_URL`
- `DEBUGCLI_BIG_MODEL_NAME`
- `DEBUGCLI_BIG_MODEL_DISPLAY_NAME`
- `DEBUGCLI_BIG_MODEL_TEMPERATURE`
- `DEBUGCLI_BIG_MODEL_MAX_TOKENS`
- `DEBUGCLI_BIG_MODEL_TIMEOUT`
- `DEBUGCLI_DB_PATH`

## Common Commands

Run batch tests:

```bash
python3 run_tests.py
```

Start dashboard:

```bash
python3 dashboard_v2.py
```

Non-interactive debug run:

```bash
./run_debug.sh 12 2
```

## Git Setup

If this is a fresh clone/folder:

```bash
git init
git add .
git commit -m "Initial project setup"
```

## Notes

- `config.py` now supports env var overrides for model settings.
- `db.py` supports overriding the SQLite path with `DEBUGCLI_DB_PATH`.
- If model endpoints are unreachable, debug runs will fail at request time.

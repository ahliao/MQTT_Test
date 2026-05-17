# uv Workflow

## What uv Is

`uv` is a fast Python project and package manager. In this project, it should handle the jobs that are often split across `python -m venv`, `pip`, `pip-tools`, and manual command running.

For this project, `uv` will be used to:

- Create and manage the virtual environment
- Add runtime and development dependencies
- Run Python commands inside the project environment
- Create a lockfile so installs are reproducible

## Why Use uv Here

This project is meant to be educational and runnable on Linux. `uv` helps because the setup steps are explicit and repeatable.

Benefits:

- Fast dependency installation
- One main tool for environment setup and command execution
- Lockfile support through `uv.lock`
- Good fit for modern `pyproject.toml` Python projects
- Avoids needing to manually activate a virtual environment for every command

Tradeoff:

- It is one more tool to learn if you already know `pip`.

## Project Files uv Will Use

Expected files after implementation:

```text
pyproject.toml
uv.lock
.python-version
```

`pyproject.toml` describes the project, dependencies, scripts, and development tools.

`uv.lock` records exact dependency versions. This makes the project more reproducible across computers.

`.python-version` records the Python version the project expects.

## Common Commands

Initialize or sync the environment:

```bash
uv sync
```

Run the sensor service:

```bash
uv run python -m sensor_platform.sensor
```

Run the processor service:

```bash
uv run python -m sensor_platform.processor
```

Run the CLI monitor:

```bash
uv run python -m sensor_platform.monitor_cli
```

Run tests:

```bash
uv run pytest
```

Add a runtime dependency:

```bash
uv add paho-mqtt
```

Add a development dependency:

```bash
uv add --dev pytest
```

## Mental Model

Without `uv`, you might do this:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m sensor_platform.sensor
```

With `uv`, the workflow becomes:

```bash
uv sync
uv run python -m sensor_platform.sensor
```

`uv run` makes sure the command runs inside the project environment.

## Protobuf Generation With uv

The project should include an automatic protobuf generation command. The exact command will be finalized during implementation, but the intended usage is:

```bash
uv run generate-protobuf
```

That command should:

- Read `proto/sensor_platform.proto`
- Generate Python protobuf code
- Write generated files under `src/sensor_platform/generated/`

Run the generation command any time the `.proto` file changes.

## Recommended Learning Path

1. Use `uv sync` to prepare the environment.
2. Use `uv run ...` instead of activating the virtual environment manually.
3. Use `uv add ...` when the project needs a new dependency.
4. Commit `pyproject.toml` and `uv.lock` so the dependency set is reproducible.

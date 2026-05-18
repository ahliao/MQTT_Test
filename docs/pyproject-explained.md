# pyproject.toml Explained

## What This File Is

`pyproject.toml` is the main configuration file for many modern Python projects.

In this project, it answers questions like:

- What is this project called?
- What Python version does it need?
- What packages does it depend on?
- What command-line scripts should be available?
- How should the project be built and installed?
- Where are the tests?
- How should the linter behave?

Older Python projects often used files such as `setup.py`, `setup.cfg`, `requirements.txt`, and tool-specific config files. Modern projects often collect much of that configuration in `pyproject.toml`.

## What TOML Is

TOML stands for Tom's Obvious Minimal Language. It is a configuration file format.

It is meant to be easier to read than formats like JSON for human-edited configuration.

Basic TOML examples:

```toml
name = "sensor-platform-test"
version = "0.1.0"
requires-python = ">=3.11"
```

Each line is a key/value pair:

```text
key = value
```

Strings use quotes:

```toml
description = "Educational MQTT and protobuf sensor platform demo."
```

Lists use square brackets:

```toml
dependencies = [
    "paho-mqtt>=2.1.0",
    "protobuf>=5.29.0",
]
```

Sections use headers in square brackets:

```toml
[project]
```

Everything after that header belongs to that section until the next section starts.

## This Project's pyproject.toml

The current file is:

```toml
[project]
name = "sensor-platform-test"
version = "0.1.0"
description = "Educational MQTT and protobuf sensor platform demo for Linux embedded computers."
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "paho-mqtt>=2.1.0",
    "pyqtgraph>=0.13.7",
    "PySide6>=6.8.0",
    "protobuf>=5.29.0",
]

[project.scripts]
generate-protobuf = "sensor_platform.tools.generate_protobuf:main"
sensor-platform-sensor = "sensor_platform.sensors.sensor:main"
sensor-platform-high-rate-sensor = "sensor_platform.sensors.high_rate_sensor:main"
sensor-platform-processor = "sensor_platform.processors.processor:main"
sensor-platform-high-rate-processor = "sensor_platform.processors.high_rate_processor:main"
sensor-platform-monitor = "sensor_platform.monitors.monitor_cli:main"
sensor-platform-monitor-gui = "sensor_platform.gui.monitor_qt:main"

[dependency-groups]
dev = [
    "grpcio-tools>=1.68.0",
    "pytest>=8.3.0",
    "ruff>=0.8.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/sensor_platform"]

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py311"
```

## The project Section

```toml
[project]
```

This section describes the Python package itself.

### name

```toml
name = "sensor-platform-test"
```

This is the package name. It is the name packaging tools use when installing or building the project.

This is not necessarily the same as the Python import name.

Package name:

```text
sensor-platform-test
```

Python import name:

```python
import sensor_platform
```

Python package names often use underscores in code, while installable package names often use hyphens.

### version

```toml
version = "0.1.0"
```

This is the project version.

For a learning project, `0.1.0` means an early initial version.

### description

```toml
description = "Educational MQTT and protobuf sensor platform demo for Linux embedded computers."
```

This is a short human-readable description of the project.

### readme

```toml
readme = "README.md"
```

This tells packaging tools that `README.md` is the main long-form project description.

### requires-python

```toml
requires-python = ">=3.11"
```

This means the project requires Python 3.11 or newer.

The `>=` means "greater than or equal to."

So this is allowed:

```text
Python 3.11
Python 3.12
Python 3.13
```

This is not allowed:

```text
Python 3.10
Python 3.9
```

## Runtime Dependencies

```toml
dependencies = [
    "paho-mqtt>=2.1.0",
    "pyqtgraph>=0.13.7",
    "PySide6>=6.8.0",
    "protobuf>=5.29.0",
]
```

These are packages needed when running the application.

They are installed by:

```bash
uv sync
```

What each dependency does:

- `paho-mqtt`: MQTT client library used by the sensor, processor, CLI monitor, and GUI monitor.
- `pyqtgraph`: plotting library used by the GUI monitor.
- `PySide6`: Qt GUI framework used by the GUI monitor.
- `protobuf`: protobuf runtime used to serialize and deserialize messages.

The version syntax means "install at least this version."

Example:

```toml
"paho-mqtt>=2.1.0"
```

Means:

```text
Use paho-mqtt version 2.1.0 or newer.
```

## The project.scripts Section

```toml
[project.scripts]
```

This section creates command-line commands for the project.

Example:

```toml
sensor-platform-sensor = "sensor_platform.sensors.sensor:main"
```

This means:

```text
Create a command called sensor-platform-sensor.
When it runs, import `sensor_platform.sensors.sensor` and call its `main()` function.
```

So this command:

```bash
uv run sensor-platform-sensor
```

Runs this Python function:

```python
sensor_platform.sensors.sensor.main()
```

The project scripts are:

- `generate-protobuf`: generate Python protobuf files from the `.proto` schema.
- `sensor-platform-sensor`: run the simulated ADC sensor publisher.
- `sensor-platform-high-rate-sensor`: run the batched high-rate sensor publisher.
- `sensor-platform-processor`: run the processor service.
- `sensor-platform-high-rate-processor`: run the batched high-rate processor service.
- `sensor-platform-monitor`: run the CLI monitor.
- `sensor-platform-monitor-gui`: run the PySide6 GUI monitor.

The script format is:

```text
command-name = "python.module.path:function_name"
```

## The dependency-groups Section

```toml
[dependency-groups]
dev = [
    "grpcio-tools>=1.68.0",
    "pytest>=8.3.0",
    "ruff>=0.8.0",
]
```

This section defines dependencies used for development but not necessarily needed by the application at runtime.

Development dependencies in this project:

- `grpcio-tools`: provides the protobuf compiler used to generate Python files.
- `pytest`: runs the test suite.
- `ruff`: checks Python code quality.

These tools help build and verify the project, but the running sensor platform does not directly use all of them.

## The build-system Section

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

This tells Python packaging tools how to build and install this project.

`hatchling` is the build backend. It is not part of the sensor platform logic. It is packaging infrastructure.

This section means:

```text
If this project needs to be built, use hatchling to build it.
```

This matters because this project uses a `src/` layout and command-line scripts.

## The tool.hatch Section

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/sensor_platform"]
```

This configures Hatchling.

It tells Hatchling where the Python package lives.

The project code is here:

```text
src/sensor_platform/
```

Without this setting, the build tool may not know which directory should become the installed Python package.

## The tool.pytest Section

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
```

This configures `pytest`.

It tells pytest to look for tests in the `tests/` directory.

So when you run:

```bash
uv run pytest
```

pytest knows the project tests are here:

```text
tests/
```

## The tool.ruff Section

```toml
[tool.ruff]
line-length = 100
target-version = "py311"
```

This configures Ruff.

Ruff is a Python code quality tool.

This section means:

- `line-length = 100`: prefer lines to stay within 100 characters.
- `target-version = "py311"`: check code as Python 3.11 code.

Run Ruff with:

```bash
uv run ruff check .
```

Ruff does not run the application. It checks the source code for likely mistakes and style issues.

## How uv Uses This File

`uv` reads `pyproject.toml` to understand the project.

When you run:

```bash
uv sync
```

`uv` will:

- Read the project metadata.
- Create or update `.venv/`.
- Install runtime dependencies.
- Install development dependencies.
- Install this project as a local package.
- Update `uv.lock` if needed.

When you run:

```bash
uv run sensor-platform-monitor-gui
```

`uv` will:

- Use the project environment.
- Find the `sensor-platform-monitor-gui` script from `[project.scripts]`.
- Run `sensor_platform.gui.monitor_qt:main`.

## pyproject.toml vs uv.lock

These two files work together, but they have different jobs.

`pyproject.toml` says what the project wants:

```text
protobuf >= 5.29.0
```

`uv.lock` records exactly what was installed:

```text
protobuf 6.33.6
```

Think of it this way:

- `pyproject.toml`: the recipe
- `uv.lock`: the exact grocery receipt

You usually edit `pyproject.toml` directly only when changing project configuration.

You usually let `uv` update `uv.lock`.

## Common Changes

Add a runtime dependency:

```bash
uv add some-package
```

This updates `pyproject.toml` and `uv.lock`.

Add a development dependency:

```bash
uv add --dev some-dev-tool
```

Add a new command-line script by editing `[project.scripts]`:

```toml
my-command = "sensor_platform.some_module:main"
```

Then run it with:

```bash
uv run my-command
```

## Key Takeaways

- `pyproject.toml` is the main Python project configuration file.
- TOML is a readable config format made of sections and key/value pairs.
- `[project]` describes the package and runtime dependencies.
- `[project.scripts]` creates command-line commands.
- `[dependency-groups]` lists development tools.
- `[build-system]` tells Python how to build/install the project.
- `[tool.pytest.ini_options]` configures tests.
- `[tool.ruff]` configures linting.
- `uv` reads this file to install dependencies and run project commands.

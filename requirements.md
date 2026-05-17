# Requirements: configsloader

## Overview

### Problem

Applications need to load configuration from multiple sources (CLI flags, environment variables, config files, defaults) with a deterministic resolution order. Existing Python solutions either lack multi-source layering, require excessive boilerplate, or do not support the specific resolution semantics required by the C++ ConfigsLoader library that this package must mirror.

### Why

A Python-idiomatic implementation of ConfigsLoader enables Python services and tools to share configuration semantics with C++ counterparts. Teams using both languages get consistent behavior (resolution order, verification, error messages, help output) without maintaining ad-hoc glue code.

### Users

- Python developers building CLI tools or services that require multi-source configuration
- Teams maintaining polyglot (C++/Python) systems that need identical config resolution semantics
- Guild framework users who consume configsloader as a dependency

---

## Definitions

- **Section / Group**: These terms refer to the SAME concept. A `section` is declared per-field via the `section` attribute in `Field()`. A `group` is the same concept as used in help output organization and CLI dot-notation prefixes. For example, a field with `section="backend.db"` belongs to group `backend.db`, appears under that group in `--help` output, and uses `--backend.db.<field>` as its CLI flag prefix.

---

## Functional Requirements

### FR-01: Declarative Field Definition

The library SHALL provide a `Field()` descriptor that declares a configuration field with the following optional attributes: `default`, `flags`, `env`, `section`, `description`, `required`, `validator`.

### FR-02: Resolution Order

When resolving a field's value, the library SHALL apply sources in the following precedence (highest to lowest): CLI flags > environment variables > preset file > config file(s) > field default.

### FR-03: CLI Flag Parsing

The library SHALL parse command-line arguments matching each field's declared `flags` list (e.g., `["--model", "-m"]`) and use the parsed value as the highest-precedence source.

### FR-04: Environment Variable Lookup `[PYTHON EXTENSION]`

The library SHALL read the environment variable named by a field's `env` attribute and use its value as the second-highest-precedence source.

### FR-05: Config File Loading (TOML) `[PYTHON EXTENSION]`

The library SHALL load TOML config files using Python 3.11's `tomllib` standard library module.

### FR-06: Config File Loading (JSON) `[PYTHON EXTENSION]`

The library SHALL load JSON config files using the `json` standard library module.

### FR-07: Config File Format Auto-Detection

When format is set to `"auto"` (the default), the library SHALL detect the file format from the file extension (`.toml` for TOML, `.json` for JSON).

### FR-08: Explicit Format Override

The library SHALL accept an explicit `format` parameter (in class Meta or at load time) that overrides auto-detection.

### FR-09: Multi-File Hierarchy with Layering `[PYTHON EXTENSION]`

The library SHALL support loading multiple config files in a defined order, where values in later files override values from earlier files.

### FR-10: Config File Locations in Meta `[PYTHON EXTENSION]`

The library SHALL allow config file paths to be defined in a class-level `Meta.files` list, representing the layering order (first = lowest priority, last = highest priority).

### FR-11: Config File Override at Load Time

The library SHALL allow the `Meta.files` list to be overridden by passing a `files` argument to the `.load()` method.

### FR-12: Type Coercion — Primitive Types

The library SHALL coerce string-sourced values (CLI, env vars) to the field's annotated type for: `str`, `int`, `float`, and `bool`.

### FR-13: Type Coercion — Bool Semantics

For `bool` fields, the library SHALL accept `"true"`, `"1"`, `"yes"` (case-insensitive) as `True`; all other string values SHALL resolve to `False`. `[PYTHON EXTENSION]`: The C++ version accepts only `"true"` and `"1"` (case-sensitive). The Python version extends this to accept `"yes"` and to be case-insensitive for all accepted values.

### FR-14: Type Coercion — Enum Types `[PYTHON EXTENSION]`

The library SHALL coerce string values to Enum types including `str`-based Enum (`StrEnum`), `IntEnum`, plain `Enum`, and `Flag` by auto-detecting and matching the member name (case-insensitive) or value. NOTE: The C++ version requires explicit parser functions for enum coercion; the Python version auto-detects enum members by name/value without requiring explicit parsers.

### FR-15: Required Field Validation

When a field is marked `required=True` and no value is provided by any source (CLI, env, config files, default), the library SHALL raise an error identifying the missing field.

### FR-16: Custom Validators

The library SHALL support a per-field `validator` callable that receives the resolved value as its single argument (signature: `validator(value) -> bool`) and returns a boolean indicating validity. A return of `False` SHALL be treated as a validation failure.

### FR-17: Validation Error Collection

The library SHALL collect ALL validation errors (required fields, per-field validators, type coercion failures) and report them TOGETHER rather than failing fast on the first error. The error format SHALL be: `"Configuration validation failed with N error(s):\n  * <error 1>\n  * <error 2>\n  ..."`.

### FR-18: Validation Timing

Validation SHALL run AFTER all sources have been applied, so that validators see the final resolved value for their field.

### FR-19: Cross-Field Validation `[PYTHON EXTENSION]`

The library SHALL support cross-field validators that receive two arguments: `(value, config)` where `value` is the field's resolved value and `config` is the fully resolved configuration object providing access to all other field values. This enables cross-field validation logic. NOTE: Simple per-field validators (FR-16) receive only `(value)`. Cross-field validators are distinguished by accepting two parameters. This is a PYTHON EXTENSION beyond the C++ implementation, which only supports per-field verification.

### FR-20: Auto-Generated Help Output — Interactive Modes

The library SHALL support the following help invocations:
- `--help` (bare): shows navigation/overview of available groups and usage
- `--help all`: shows all fields across all groups
- `--help required`: shows only required fields
- `--help <group>`: shows fields in the specified group
- `--help groups`: shows the group hierarchy tree

### FR-21: Help Output — Colored ANSI Display

The help output SHALL use ANSI color codes (toggleable via environment or API):
- BOLD for section/group headers
- CYAN for flag names
- YELLOW for type names
- RED for `[Required]` markers
- GREEN for group names
- GRAY for default values

### FR-22: Help Output — Per-Field Format

Each field in help output SHALL be displayed in the format: `[Required] <flags> <type> <description> (default: <value>)`. When a field's current value differs from its default, the format SHALL be: `[Required] <flags> <type> <description> (current: <value>, default: <value>)`.

### FR-23: Help Output — Usage Line

The help output SHALL include a usage line showing required flags with their types (e.g., `Usage: app --host <string> --port <int>`).

### FR-24: Help Output — String Quoting and Type Names

String default values SHALL be quoted in display (e.g., `(default: "localhost")`). Type names displayed SHALL be: `string`, `int`, `bool`, `float`, `enum`.

### FR-25: Help Output Grouped by Section

The auto-generated help output SHALL group fields by their declared `section`, displaying the section name as a header with 2 spaces of indentation per nesting level for nested groups.

### FR-26: Help Output Content

For each field, the help output SHALL display: flag names, type, description, and default/current value.

### FR-27: Per-Field Section Declaration `[PYTHON EXTENSION]`

Each field SHALL declare which config file section it belongs to via the `section` attribute, mapping to a TOML table or JSON object key.

### FR-28: Global Section Fallback `[PYTHON EXTENSION]`

When a field does not declare a `section`, the library SHALL read it from the top-level (root) of the config file.

### FR-29: Hierarchical / Nested Config Structures

The library SHALL support nested configuration structures using dot notation in CLI flags (e.g., `--backend.db.host`) mapping to nested TOML tables or JSON objects. Prefix accumulation SHALL follow the group hierarchy (e.g., group `backend` containing subgroup `db` containing field `host` produces flag `--backend.db.host`).

### FR-30: Preset File — Reserved Flag

The library SHALL reserve `--preset <path>` as a built-in CLI flag. The preset flag loads a single file whose format is auto-detected by extension. The preset is applied BEFORE CLI arguments in the resolution order (i.e., CLI wins over preset). Key lookup in the preset file uses the field's first declared flag name stripped of leading dashes (e.g., `--host` maps to key `host`). For multi-flag fields, the first flag in the `flags` list is used. For dotted flags like `--backend.db.host`, the preset key is `backend.db.host`.

### FR-31: Preset File Resolution

Preset files SHALL be resolved from a configurable directory (defined in Meta or at load time) by appending the preset name and expected extension.

### FR-32: Config File Auto-Discovery

The library SHALL attempt to load config files from the paths specified in `Meta.files`, silently skipping paths that do not exist.

### FR-33: Unknown Flag Handling — Three Modes

The library SHALL support three modes for handling unknown CLI flags: Error, Warn, Ignore. The mode SHALL be configurable as a class-level setting (in Meta) or at load time. The default mode SHALL be Error.

### FR-34: Unknown Flag Handling — Error Mode

When unknown CLI flags are encountered and the handling mode is Error, the library SHALL print a list of all unknown flags and raise an error.

### FR-35: Unknown Flag Handling — Warn Mode

When unknown CLI flags are encountered and the handling mode is Warn, the library SHALL print a warning listing the unknown flags and continue loading.

### FR-36: Unknown Flag Handling — Ignore Mode

When unknown CLI flags are encountered and the handling mode is Ignore, the library SHALL silently discard them.

### FR-37: Print Config — Reserved Flags

The library SHALL reserve `--print-config` and `--print-config-verbose` as built-in CLI flags:
- `--print-config`: dumps only fields whose values differ from their defaults, in TOML format, then exits.
- `--print-config-verbose`: dumps ALL field values in TOML format, then exits.

### FR-38: Reserved Flag Validation

The library SHALL reserve the following CLI flags: `--help`/`-h`, `--preset`, `--print-config`, `--print-config-verbose`. If a user-defined field declares any of these as its flags, the library SHALL raise an error at class definition or load time.

### FR-39: is_set Tracking

Each field SHALL track whether it was explicitly set by any source (CLI, env, preset, config file) versus still holding its default value. This information SHALL be accessible via an API such as `config.is_set("field_name")` returning a boolean.

### FR-40: Zero-Config Usage

The library SHALL work with zero configuration beyond field declarations: calling `.load()` with no arguments SHALL resolve values from CLI, env, and defaults without requiring any config files to exist.

### FR-41: Type Coercion Failure Handling

When a field annotated with a numeric type (e.g., `int`, `float`) receives a non-numeric string value from any source (CLI, env var, preset, config file), the library SHALL raise a `ValueError`. Coercion errors SHALL be collected together with other validation errors per FR-17 and reported in the same aggregate error message.

### FR-42: Duplicate Flag Detection

If two or more fields declare the same CLI flag (e.g., both use `--host`), the library SHALL raise an error at class definition time (during metaclass validation) identifying the conflicting fields and the duplicated flag.

### FR-43: Repeated CLI Flag Behavior

When the same CLI flag appears multiple times in `sys.argv` (e.g., `--host a --host b`), the last occurrence SHALL win and its value SHALL be used.

### FR-44: Nested Group Declaration in Python

Nested configuration groups SHALL be declarable using either of two patterns:
1. Nested `ConfigsLoader` subclasses as class attributes (compositional pattern)
2. Dotted `section` names in `Field()` (e.g., `section="backend.db"`)

Both patterns produce equivalent behavior in resolution, CLI flag generation, and help output.

### FR-45: Boolean Switch Behavior `[PYTHON EXTENSION]`

Bool fields with CLI flags SHALL act as argument-less switches (store_true). If `--verbose` appears alone (no following value), the resolved value is `True`. Optionally, an explicit value may follow the flag: `--verbose false` resolves to `False`. NOTE: The C++ version does NOT support bare boolean flags (if `--verbose` has no following value, it is silently skipped). The Python version adds this as a convention expected by Python users (argparse behavior).

---

## Non-Functional Requirements

### NFR-01: Python Version

The library SHALL support Python 3.11 and above.

### NFR-02: Idiomatic Python API

The public API SHALL use Python idioms: metaclass-based class definition, type annotations, descriptor protocol, and dataclass-like ergonomics.

### NFR-03: Minimal Required Dependencies

The library SHALL minimize required third-party dependencies. TOML parsing SHALL use `tomllib` from the standard library (Python 3.11+). TOML serialization (required for `--print-config` output per FR-37) SHALL use `tomli-w` or equivalent as a dependency, OR the library SHALL output a simple `key = value` TOML-compatible format that does not require a full serializer.

### NFR-04: Trivial Deployment

The library SHALL be installable via `pip install` with no native extensions or complex build steps.

### NFR-05: Semantic Parity with C++ Version

Semantic parity with C++ ConfigsLoader for shared features (CLI parsing, presets, help output, unknown flags, validation, enums). The Python version EXTENDS the C++ with: environment variables, config file loading, multi-file layering, section-based mapping, and cross-field validation. These extensions are marked with `[PYTHON EXTENSION]` in their FRs.

### NFR-06: Startup Performance

Configuration loading is not performance-critical. The library need not optimize beyond reasonable single-pass loading (configuration is loaded once at process startup).

### NFR-07: Package Naming

The importable package name SHALL be `configsloader`. The repository name SHALL be `configs_loader_python`.

### NFR-08: Testability

All functional requirements SHALL be verifiable through automated unit and integration tests without requiring external services.

### NFR-09: Thread Safety

ConfigsLoader is not thread-safe. `.load()` should be called once at startup. Concurrent access to the resolved config object (read-only) is safe.

---

## Constraints

| ID | Constraint |
|----|-----------|
| C-01 | Python 3.11+ minimum (leverages `tomllib` from stdlib) |
| C-02 | Package import name is `configsloader` |
| C-03 | Library is decoupled from Guild (no Guild imports or runtime dependency) |
| C-04 | Mixed file formats across layered files is supported (e.g., `global.toml` + `project.json`) |
| C-05 | Optional dependencies are permitted for backward compatibility or extended features |

---

## Acceptance Criteria

### AC-01: Declarative Field Definition

**AC-01.1**: Given a class with `model: str = Field(default="gemma4", flags=["--model", "-m"], env="APP_MODEL", section="provider", description="LLM model to use")`, when the class is introspected, then all attributes are retrievable from the field descriptor.

**AC-01.2**: Given a class with a `Field()` that omits optional attributes, when the class is defined, then no error is raised and omitted attributes default to `None` / empty.

**AC-01.3**: Given a class with `required=True` on a field, when the field descriptor is introspected, then `required` is `True`.

### AC-02: Resolution Order

**AC-02.1**: Given `--model cli_val` on CLI, `APP_MODEL=env_val` in environment, `model = "file_val"` in config, a preset with `model = "preset_val"`, and `default="def_val"`, when `.load()` is called, then `config.model == "cli_val"`.

**AC-02.2**: Given no CLI flag, `APP_MODEL=env_val` in environment, a preset with `model = "preset_val"`, `model = "file_val"` in config, and `default="def_val"`, when `.load()` is called, then `config.model == "env_val"`.

**AC-02.3**: Given no CLI flag, no env var, a preset with `model = "preset_val"`, `model = "file_val"` in config, and `default="def_val"`, when `.load()` is called, then `config.model == "preset_val"`.

**AC-02.4**: Given no CLI flag, no env var, no preset, `model = "file_val"` in config, and `default="def_val"`, when `.load()` is called, then `config.model == "file_val"`.

### AC-03: CLI Flag Parsing

**AC-03.1**: Given `flags=["--model", "-m"]` and `sys.argv` contains `["-m", "gpt4"]`, when `.load()` is called, then `config.model == "gpt4"`.

**AC-03.2**: Given `flags=["--verbose"]` on a `bool` field and `sys.argv` contains `["--verbose"]`, when `.load()` is called, then `config.verbose is True`.

### AC-04: Environment Variable Lookup

**AC-04.1**: Given `env="APP_PORT"` and `os.environ["APP_PORT"] = "8080"` with type annotation `int`, when `.load()` is called, then `config.port == 8080`.

**AC-04.2**: Given `env="APP_PORT"` and `APP_PORT` is not set and no CLI flag is provided, when `.load()` is called, then the config file or default value is used.

### AC-05: Config File Loading (TOML)

**AC-05.1**: Given a file `config.toml` containing `[provider]\nmodel = "llama3"`, when `.load(files=["config.toml"])` is called, then `config.model == "llama3"`.

**AC-05.2**: Given a syntactically invalid TOML file, when `.load()` is called, then a descriptive error is raised identifying the file and parse issue.

### AC-06: Config File Loading (JSON)

**AC-06.1**: Given a file `config.json` containing `{"provider": {"model": "llama3"}}`, when `.load(files=["config.json"])` is called, then `config.model == "llama3"`.

**AC-06.2**: Given a syntactically invalid JSON file, when `.load()` is called, then a descriptive error is raised identifying the file and parse issue.

### AC-07: Config File Format Auto-Detection

**AC-07.1**: Given `Meta.format = "auto"` and a file named `app.toml`, when `.load()` is called, then the file is parsed as TOML.

**AC-07.2**: Given `Meta.format = "auto"` and a file named `app.json`, when `.load()` is called, then the file is parsed as JSON.

**AC-07.3**: Given `Meta.format = "auto"` and a file with an unrecognized extension `.yaml`, when `.load()` is called, then an error is raised indicating unsupported format.

### AC-08: Explicit Format Override

**AC-08.1**: Given a file named `config.txt` and `format="toml"` specified, when `.load()` is called, then the file is parsed as TOML regardless of extension.

### AC-09: Multi-File Hierarchy with Layering

**AC-09.1**: Given `Meta.files = ["base.toml", "override.toml"]` where `base.toml` has `model = "base"` and `override.toml` has `model = "override"`, when `.load()` is called, then `config.model == "override"`.

**AC-09.2**: Given three files in order where only the first and third define a field, when `.load()` is called, then the third file's value wins.

### AC-10: Config File Locations in Meta

**AC-10.1**: Given `class Meta: files = ["~/.config/app.toml", "./app.toml"]`, when `.load()` is called, then both paths are attempted with `~` expanded.

**AC-10.2**: Given `Meta.files` contains a path that does not exist, when `.load()` is called, then no error is raised and that path is skipped.

### AC-11: Config File Override at Load Time

**AC-11.1**: Given `Meta.files = ["a.toml"]` and `.load(files=["b.toml"])` is called, then only `b.toml` is loaded and `a.toml` is ignored.

### AC-12: Type Coercion — Primitive Types

**AC-12.1**: Given a field annotated as `int` and CLI value `"42"`, when `.load()` is called, then the resolved value is `42` (int).

**AC-12.2**: Given a field annotated as `float` and env var value `"3.14"`, when `.load()` is called, then the resolved value is `3.14` (float).

**AC-12.3**: Given a field annotated as `str` and config file value `"hello"`, when `.load()` is called, then the resolved value is `"hello"` (str).

### AC-13: Type Coercion — Bool Semantics

**AC-13.1**: Given a `bool` field and env var value `"yes"`, when `.load()` is called, then the resolved value is `True`.

**AC-13.2**: Given a `bool` field and CLI value `"0"`, when `.load()` is called, then the resolved value is `False`.

**AC-13.3**: Given a `bool` field and env var value `"TRUE"`, when `.load()` is called, then the resolved value is `True`.

**AC-13.4**: Given a `bool` field and env var value `"nope"`, when `.load()` is called, then the resolved value is `False`.

### AC-14: Type Coercion — Enum Types

**AC-14.1**: Given a `StrEnum` field with member `FAST = "fast"` and CLI value `"fast"`, when `.load()` is called, then the resolved value is the `FAST` enum member.

**AC-14.2**: Given an `IntEnum` field with member `HIGH = 3` and config value `"HIGH"`, when `.load()` is called, then the resolved value is the `HIGH` enum member.

**AC-14.3**: Given a `Flag` field with members `READ = 1, WRITE = 2` and CLI value `"READ|WRITE"`, when `.load()` is called, then the resolved value is `READ | WRITE`.

### AC-15: Required Field Validation

**AC-15.1**: Given a field with `required=True` and no value from any source, when `.load()` is called, then an error is raised naming the missing field.

**AC-15.2**: Given a field with `required=True` and a value provided via env var, when `.load()` is called, then no error is raised.

### AC-16: Custom Validators

**AC-16.1**: Given `validator=lambda v: v > 0` on an `int` field and resolved value `-1`, when `.load()` is called, then a validation error is raised.

**AC-16.2**: Given a validator that returns `True`, when `.load()` is called, then loading succeeds.

### AC-17: Validation Error Collection

**AC-17.1**: Given two fields both failing validation (one required and missing, one failing its validator), when `.load()` is called, then a single error is raised with message format `"Configuration validation failed with 2 error(s):\n  * ...\n  * ..."` listing both failures.

**AC-17.2**: Given three fields where two fail validation and one succeeds, when `.load()` is called, then the error message reports exactly 2 errors and includes details for both failing fields.

### AC-18: Validation Timing

**AC-18.1**: Given a field set via CLI that overrides a config file value, when the validator runs, then it receives the CLI value (the final resolved value), not the config file value.

### AC-19: Cross-Field Validation (Python Extension)

**AC-19.1**: Given a validator on field `max_val` that checks `max_val > config.min_val`, and resolved values `max_val=5, min_val=10`, when `.load()` is called, then a validation error is raised.

**AC-19.2**: Given cross-field validator with valid values `max_val=10, min_val=5`, when `.load()` is called, then loading succeeds.

### AC-20: Auto-Generated Help Output — Interactive Modes

**AC-20.1**: Given `sys.argv` contains `["--help"]` (bare), when `.load()` is called, then help text is printed containing at minimum: a "Usage:" line showing required flags, a list of available groups/sections, and an instruction to use `--help <group>` for group-specific help or `--help all` for full output. `SystemExit` is raised after printing.

**AC-20.2**: Given `sys.argv` contains `["-h"]`, when `.load()` is called, then the same help output behavior occurs as `--help`.

**AC-20.3**: Given `sys.argv` contains `["--help", "all"]`, when `.load()` is called, then ALL fields across all groups are displayed and `SystemExit` is raised.

**AC-20.4**: Given `sys.argv` contains `["--help", "required"]`, when `.load()` is called, then only fields with `required=True` are displayed and `SystemExit` is raised.

**AC-20.5**: Given `sys.argv` contains `["--help", "provider"]` where `provider` is a defined group/section, when `.load()` is called, then only fields in that group are displayed and `SystemExit` is raised.

**AC-20.6**: Given `sys.argv` contains `["--help", "groups"]`, when `.load()` is called, then the group hierarchy tree is displayed showing group names and their contained fields, and `SystemExit` is raised.

### AC-21: Help Output — Colored Display

**AC-21.1**: Given ANSI color output is enabled, when `--help all` is invoked, then flag names appear with CYAN escape codes, type names with YELLOW, and `[Required]` markers with RED.

**AC-21.2**: Given ANSI color output is disabled (e.g., `NO_COLOR=1`), when `--help` is invoked, then no ANSI escape codes appear in the output.

### AC-22: Help Output — Per-Field Format

**AC-22.1**: Given a required field with `flags=["--host"]`, type `str`, description `"Server host"`, and default `"localhost"`, when `--help all` is invoked, then the output contains `[Required] --host string Server host (default: "localhost")`.

**AC-22.2**: Given a field with default `"localhost"` that has been set to `"prod-server"` via config file, when `--help all` is invoked, then the output shows `(current: "prod-server", default: "localhost")`.

### AC-23: Help Output — Usage Line

**AC-23.1**: Given required fields `--host <string>` and `--port <int>`, when `--help` is invoked, then the output includes a usage line containing `--host <string>` and `--port <int>`.

### AC-24: Help Output — String Quoting and Type Names

**AC-24.1**: Given a field with type `str` and default `"localhost"`, when displayed in help, then the default appears as `(default: "localhost")` with quotes around the string value.

**AC-24.2**: Given fields of types `str`, `int`, `bool`, `float`, and an `Enum`, when displayed in help, then type names shown are `string`, `int`, `bool`, `float`, and `enum` respectively.

### AC-25: Help Output Grouped by Section

**AC-25.1**: Given fields in sections `"provider"` and `"logging"`, when `--help all` is invoked, then the output contains section headers grouping their respective fields with 2 spaces of indentation per nesting level.

**AC-25.2**: Given fields with no section, when `--help all` is invoked, then those fields appear under a general/global group.

### AC-26: Help Output Content

**AC-26.1**: Given a field with `flags=["--model", "-m"]`, `default="gemma4"`, type `str`, `description="LLM model to use"`, when `--help all` is invoked, then the output contains all of: `--model`, `-m`, `"gemma4"`, `string`, `LLM model to use`.

### AC-27: Per-Field Section Declaration

**AC-27.1**: Given a field with `section="database"` and TOML content `[database]\nhost = "localhost"`, when `.load()` is called, then the field resolves to `"localhost"`.

**AC-27.2**: Given a field with `section="database"` and JSON content `{"database": {"host": "localhost"}}`, when `.load()` is called, then the field resolves to `"localhost"`.

### AC-28: Global Section Fallback

**AC-28.1**: Given a field with no `section` and TOML content `host = "localhost"` at the root level, when `.load()` is called, then the field resolves to `"localhost"`.

**AC-28.2**: Given a field with no `section` and JSON content `{"host": "localhost"}` at root, when `.load()` is called, then the field resolves to `"localhost"`.

### AC-29: Hierarchical / Nested Config Structures

**AC-29.1**: Given a nested section path `section="database.primary"` and TOML content `[database.primary]\nhost = "db1"`, when `.load()` is called, then the field resolves to `"db1"`.

**AC-29.2**: Given nested JSON `{"database": {"primary": {"host": "db1"}}}` and a field with `section="database.primary"`, when `.load()` is called, then the field resolves to `"db1"`.

**AC-29.3**: Given a nested config group `backend` with subgroup `db` containing field `host`, when parsed from CLI `--backend.db.host myhost`, when `.load()` is called, then `config.backend.db.host == "myhost"`.

### AC-30: Preset File — Reserved Flag

**AC-30.1**: Given `--preset production.toml` on CLI and a preset file `production.toml` with `host = "prod-server"`, when `.load()` is called, then `config.host == "prod-server"` (assuming no higher-priority source overrides it).

**AC-30.2**: Given `--preset production.toml` and `--host cli-host` on CLI, when `.load()` is called, then `config.host == "cli-host"` (CLI wins over preset).

**AC-30.3**: Given `--preset nonexistent.toml`, when `.load()` is called, then an error is raised indicating the preset file was not found.

**AC-30.4**: Given a preset file with key `host` and a field with flag `--host`, when the preset is loaded, then the key `host` (flag name stripped of dashes) maps to the field correctly.

**AC-30.5**: Given a field with `flags=["--backend.db.host", "-H"]` and a preset file containing key `backend.db.host`, when the preset is loaded, then the key maps to the field correctly (first flag stripped of `--` prefix).

### AC-31: Preset File Resolution

**AC-31.1**: Given `Meta.preset_dir = "./presets"` and `--preset dev`, when `.load()` resolves the preset, then it looks for `./presets/dev.toml` (or `.json`).

### AC-32: Config File Auto-Discovery

**AC-32.1**: Given `Meta.files = ["~/.config/app.toml", "/etc/app.toml", "./app.toml"]` where only `./app.toml` exists, when `.load()` is called, then only `./app.toml` is loaded and no error is raised for missing files.

### AC-33: Unknown Flag Handling — Error Mode

**AC-33.1**: Given `Meta.unknown_flags = "error"` and CLI contains `["--unknown-flag", "val"]`, when `.load()` is called, then an error is raised listing `--unknown-flag`.

**AC-33.2**: Given `Meta.unknown_flags = "error"` and CLI contains only known flags, when `.load()` is called, then no error is raised.

**AC-33.3**: Given `Meta.unknown_flags = "error"` and CLI contains `["--unknown-one", "--unknown-two"]`, when `.load()` is called, then the error message lists both `--unknown-one` and `--unknown-two`.

### AC-34: Unknown Flag Handling — Warn Mode

**AC-34.1**: Given `Meta.unknown_flags = "warn"` and CLI contains `["--unknown-flag"]`, when `.load()` is called, then a warning is emitted listing the unknown flags and loading succeeds.

### AC-35: Unknown Flag Handling — Ignore Mode

**AC-35.1**: Given `Meta.unknown_flags = "ignore"` and CLI contains `["--unknown-flag"]`, when `.load()` is called, then loading succeeds with no warning or error.

### AC-36: Print Config

**AC-36.1**: Given `sys.argv` contains `["--print-config"]` and fields `host` (changed to `"prod"`) and `port` (still default `8080`), when `.load()` is called, then only `host = "prod"` is printed in TOML format and `SystemExit` is raised.

**AC-36.2**: Given `sys.argv` contains `["--print-config-verbose"]` and fields `host = "prod"` and `port = 8080`, when `.load()` is called, then both `host = "prod"` and `port = 8080` are printed in TOML format and `SystemExit` is raised.

### AC-37: Reserved Flag Validation

**AC-37.1**: Given a user-defined field with `flags=["--help"]`, when the class is defined or `.load()` is called, then an error is raised indicating that `--help` is a reserved flag.

**AC-37.2**: Given a user-defined field with `flags=["--print-config"]`, when the class is defined or `.load()` is called, then an error is raised indicating that `--print-config` is a reserved flag.

### AC-38: is_set Tracking

**AC-38.1**: Given a field with `default="localhost"` that receives no value from CLI, env, preset, or config file, when `.load()` completes, then `config.is_set("host")` returns `False`.

**AC-38.2**: Given a field with `default="localhost"` that receives value `"localhost"` from a config file (same as default), when `.load()` completes, then `config.is_set("host")` returns `True` (it was explicitly set, even though the value matches the default).

### AC-39: Zero-Config Usage

**AC-39.1**: Given a class with fields having only defaults and no `Meta.files`, when `.load()` is called with no arguments and no config files exist, then loading succeeds using defaults.

**AC-39.2**: Given a class with a field having `env="APP_X"` and `os.environ["APP_X"] = "val"` and no config files, when `.load()` is called, then `config.x == "val"`.

### AC-40: Type Coercion Failure Handling

**AC-40.1**: Given a field annotated as `int` with `flags=["--port"]` and CLI input `--port abc`, when `.load()` is called, then a `ValueError` is raised with a message identifying the field and the invalid value `"abc"`.

**AC-40.2**: Given a field annotated as `int` with `flags=["--port"]` and CLI input `--port abc`, AND a second field that is required but missing, when `.load()` is called, then both errors are reported together in a single aggregate error message per FR-17.

### AC-41: Duplicate Flag Detection

**AC-41.1**: Given two fields both declaring `flags=["--host"]`, when the class is defined (metaclass validation), then an error is raised identifying both fields and the duplicated flag `--host`.

**AC-41.2**: Given two fields where one declares `flags=["--host", "-H"]` and another declares `flags=["--server", "-H"]`, when the class is defined, then an error is raised identifying the duplicate short flag `-H`.

### AC-42: Repeated CLI Flag Behavior

**AC-42.1**: Given a field with `flags=["--host"]` and `sys.argv` contains `["--host", "first", "--host", "second"]`, when `.load()` is called, then `config.host == "second"` (last value wins).

### AC-43: Nested Group Declaration in Python

**AC-43.1**: Given a nested class pattern:
```python
class AppConfig(ConfigsLoader):
    class backend(ConfigsLoader):
        class db(ConfigsLoader):
            host: str = Field(default="localhost", flags=["--backend.db.host"])
```
when `.load()` is called with `--backend.db.host myhost`, then `config.backend.db.host == "myhost"`.

**AC-43.2**: Given a flat pattern with dotted section:
```python
class AppConfig(ConfigsLoader):
    db_host: str = Field(default="localhost", flags=["--backend.db.host"], section="backend.db")
```
when `.load()` is called with `--backend.db.host myhost`, then `config.db_host == "myhost"`.

### AC-44: Boolean Switch Behavior

**AC-44.1**: Given a `bool` field with `flags=["--verbose"]` and `sys.argv` contains `["--verbose"]` (no following value), when `.load()` is called, then `config.verbose is True`.

**AC-44.2**: Given a `bool` field with `flags=["--verbose"]` and `sys.argv` contains `["--verbose", "false"]`, when `.load()` is called, then `config.verbose is False`.

**AC-44.3**: Given a `bool` field with `flags=["--verbose"]` and `sys.argv` contains `["--verbose", "--other-flag"]` (next token is another flag), when `.load()` is called, then `config.verbose is True` (bare switch, `--other-flag` is not consumed as its value).

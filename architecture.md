# Architecture: configsloader

## 1. System Overview

**What this is**: A declarative, multi-source configuration library for Python. Users define config fields once (type, flags, env var, section, default) and the library resolves values from CLI, environment, preset files, config files, and defaults in a deterministic priority order.

**Key design principles**:
- Single declaration per field (no duplication across sources)
- Deterministic multi-source resolution (CLI > env > preset > config files > default)
- Idiomatic Python (metaclass, type annotations, descriptor protocol)
- Fail-together (collect all errors, report at once)

**Why this architecture**: Separating each source into its own module makes them independently testable and swappable. The loader orchestrates resolution without sources knowing about each other, enabling new sources (YAML, HTTP) without touching existing code.

## 2. Component Architecture

```
src/configsloader/
├── __init__.py
├── field.py
├── meta.py
├── loader.py
├── sources/
│   ├── __init__.py
│   ├── cli.py
│   ├── env.py
│   ├── file.py
│   └── preset.py
├── validation.py
├── coercion.py
├── help.py
├── serialization.py
└── hierarchy.py
```

| Module | Responsibility |
|--------|---------------|
| `__init__.py` | Public API surface: exports `ConfigsLoader` base class and `Field` constructor. |
| `field.py` | `Field()` factory function and `FieldDescriptor` dataclass holding all field metadata (flags, env, section, default, required, validator, type annotation). |
| `meta.py` | `ConfigsLoaderMeta` metaclass that collects `FieldDescriptor` instances at class-definition time, validates reserved/duplicate flags, and resolves nested class groups. |
| `loader.py` | The `.load()` method implementation: orchestrates source resolution, coercion, validation, help/print-config handling, and returns the populated instance. |
| `sources/cli.py` | Parses `sys.argv` against declared flags. Handles bool switches, repeated flags (last wins), and unknown flag detection. |
| `sources/env.py` | Reads `os.environ` for each field's declared `env` key. Returns raw string values. |
| `sources/file.py` | Loads TOML/JSON config files with format auto-detection. Supports multi-file layering and section-based key lookup. |
| `sources/preset.py` | Loads a single preset file (from `--preset` flag), resolves path from preset_dir, maps keys to fields via first-flag stripping. |
| `validation.py` | Runs required-field checks, per-field validators, and cross-field validators. Collects errors into an aggregate message. |
| `coercion.py` | Converts string values to annotated types: str, int, float, bool (with extended semantics), Enum/StrEnum/IntEnum/Flag. |
| `help.py` | Generates `--help` output in all modes (bare, all, required, group, groups). Handles ANSI coloring, field formatting, usage line, and group tree display. |
| `serialization.py` | Implements `--print-config` and `--print-config-verbose` output in TOML format. |
| `hierarchy.py` | Resolves nested groups from both nested-class declarations and dotted `section` attributes. Builds the group tree used by help output and section-based file lookups. |

## 3. Boundaries and Dependency Direction

```
                  __init__.py (public API)
                       │
                       ▼
                   loader.py  ◄── orchestrator
                  /  |  |  \  \
                 ▼   ▼  ▼   ▼  ▼
          sources/  coercion  validation  help  serialization
          (cli, env,    │         │
           file, preset)│         │
                        ▼         ▼
                     field.py  field.py
                        ▲         ▲
                        │         │
                     meta.py ──► hierarchy.py
```

**Dependency rules**:
- `loader.py` imports from all other modules (it is the orchestrator).
- `sources/*` modules import only from `field.py` (to read field metadata). They do NOT import from each other, from `help.py`, or from `validation.py`.
- `validation.py` imports from `field.py` only.
- `coercion.py` imports from `field.py` only.
- `help.py` imports from `field.py` and `hierarchy.py`.
- `meta.py` imports from `field.py` and `hierarchy.py`.
- `hierarchy.py` imports from `field.py` only.
- No circular dependencies. Data flows upward through `loader.py`.

**What CANNOT talk to what**:
- `sources/*` must not import `help.py`, `serialization.py`, or `validation.py`.
- `coercion.py` must not import `sources/*` or `validation.py`.
- `help.py` must not import `sources/*` or `loader.py`.

## 4. Test Seams

**Unit tests** (mock boundaries):
- `sources/cli.py`: patch `sys.argv`, test in isolation.
- `sources/env.py`: patch `os.environ`, test in isolation.
- `sources/file.py`: pass file content via `tmp_path` fixtures.
- `sources/preset.py`: same as file, with mock preset directory.
- `coercion.py`: pure functions, no mocking needed.
- `validation.py`: pass pre-resolved values, test error collection.
- `help.py`: capture stdout, verify formatting.

**Integration tests** (real components):
- `loader.py` + all sources together: set up real `sys.argv`, env vars, and temp config files; call `.load()` and verify final resolved values.
- Multi-file layering: real TOML + JSON files in priority order.

**E2E boundary**:
- Test exclusively through `ConfigsLoader.load()` public API.
- Verify resolution order by providing conflicting values across all sources.

## 5. Extension Points

**Adding a new source** (e.g., YAML, HTTP endpoint):
- Create `sources/yaml.py` implementing the same interface as `sources/file.py`.
- Register it in `loader.py`'s resolution sequence at the appropriate priority level.
- No changes to `field.py`, `validation.py`, or `coercion.py`.

**Adding a new coercion type** (e.g., `Path`, `datetime`):
- Add a handler in `coercion.py`'s type dispatch (match on the field's annotation).
- No changes to sources or loader.

**Adding a new help format** (e.g., JSON schema output):
- Add a function in `help.py` (or a new `help_json.py` module).
- Hook it into `loader.py`'s help-mode dispatch (e.g., `--help json-schema`).
- No changes to sources, validation, or coercion.

## 6. Key Design Decisions

**Why metaclass over decorator approach?**
A metaclass intercepts class creation, enabling automatic field collection, reserved-flag validation, and duplicate-flag detection at definition time (not at first `.load()` call). It also naturally supports nested-class group declarations and class inheritance of fields.

**Why sources as separate modules vs a monolithic resolver?**
Each source has distinct I/O (argv, environ, filesystem) and distinct parsing rules (bool switches in CLI vs string lookup in env). Separating them makes each independently testable, replaceable, and readable. The monolithic alternative would grow linearly with every new source.

**How does the `section` attribute work at the implementation level?**
During file loading, `sources/file.py` uses a field's `section` string (e.g., `"backend.db"`) to traverse nested dicts: `data["backend"]["db"][field_name]`. If `section` is None, the field is read from the root dict. The `hierarchy.py` module splits dotted sections into path segments and builds a tree for help grouping.

**How does nested group declaration translate to internal representation?**
The metaclass detects inner classes that inherit from `ConfigsLoader`. It flattens their fields into the parent's field registry, prepending the class name(s) as the section path. So `class backend: class db: host = Field(...)` produces a field with effective `section="backend.db"` and flag prefix `--backend.db.`. Both nested-class and dotted-section patterns produce identical `FieldDescriptor` entries.

## 7. Resolution Flow

When `.load()` is called, execution proceeds in this order:

```
 1. Validate reserved flags (--help, --preset, --print-config, --print-config-verbose)
    against user-declared fields. Raise immediately on conflict.
 2. Parse CLI args via sources/cli.py
    - Detect --help, --preset, --print-config flags (set aside for later)
    - Resolve field values from argv (last occurrence wins)
    - Collect unknown flags per configured mode (error/warn/ignore)
 3. Load env vars via sources/env.py
    - For each field with an `env` attribute, check os.environ
 4. Load preset file via sources/preset.py (if --preset was provided)
    - Resolve preset path from preset_dir
    - Parse file, map keys to fields via first-flag name
 5. Load config file(s) via sources/file.py
    - Use files= arg if provided, else Meta.files
    - Layer files in order (later overrides earlier)
    - Look up each field by name within its section
 6. For each field: resolve value from sources in priority order
    - CLI > env > preset > config files > default
    - Track is_set for any field receiving a non-default value
 7. Coerce types via coercion.py
    - Convert string values to annotated types
    - Collect coercion failures as errors
 8. Handle --help (if flag was present)
    - Generate and print help output, raise SystemExit
 9. Handle --print-config / --print-config-verbose (if flag was present)
    - Serialize and print config, raise SystemExit
10. Run validators via validation.py
    - Required-field checks
    - Per-field validators (value)
    - Cross-field validators (value, config)
    - Collect all failures
11. Report errors (if any accumulated)
    - Format aggregate error message, raise ValueError
12. Return populated instance with all fields set
```

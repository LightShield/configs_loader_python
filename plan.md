# Implementation Plan

## 1. File Creation Order (dependencies first)

1. `src/configsloader/field.py` — Field descriptor and FieldDescriptor dataclass
2. `src/configsloader/meta.py` — Metaclass: field collection, reserved/duplicate flag validation
3. `src/configsloader/hierarchy.py` — Dotted-section parsing, group tree building
4. `src/configsloader/sources/__init__.py` — Empty init
5. `src/configsloader/sources/cli.py` — argv parsing, bool switches, unknown flag detection
6. `src/configsloader/sources/env.py` — os.environ lookup per field
7. `src/configsloader/sources/file.py` — TOML/JSON loading, auto-detect, layering, section traversal
8. `src/configsloader/sources/preset.py` — Preset file resolution and key mapping
9. `src/configsloader/coercion.py` — Type conversion (str/int/float/bool/enum/flag)
10. `src/configsloader/validation.py` — Required checks, per-field and cross-field validators, error collection
11. `src/configsloader/help.py` — All --help modes, ANSI coloring, usage line, group tree
12. `src/configsloader/serialization.py` — --print-config / --print-config-verbose TOML output
13. `src/configsloader/loader.py` — Orchestrator: .load() method, resolution flow
14. `src/configsloader/__init__.py` — Public API: export ConfigsLoader, Field

## 2. Requirement to Module Mapping

| Module | FRs Covered |
|--------|-------------|
| field.py | FR-01, FR-27, FR-28, FR-39 |
| meta.py | FR-38, FR-42, FR-44 |
| hierarchy.py | FR-29, FR-44 |
| sources/cli.py | FR-03, FR-33-36, FR-43, FR-45 |
| sources/env.py | FR-04 |
| sources/file.py | FR-05-11, FR-32 |
| sources/preset.py | FR-30, FR-31 |
| coercion.py | FR-12-14, FR-41 |
| validation.py | FR-15-19 |
| help.py | FR-20-26 |
| serialization.py | FR-37 |
| loader.py | FR-02, FR-40 |

## 3. Test Strategy

**Unit tests** (`tests/test_<module>.py`):
- `test_field.py` — AC-01.1, AC-01.2, AC-01.3
- `test_meta.py` — AC-37.1, AC-37.2, AC-41.1, AC-41.2
- `test_cli.py` — AC-03.1, AC-03.2, AC-42.1, AC-44.1-44.3, AC-33.1-33.3, AC-34.1, AC-35.1
- `test_env.py` — AC-04.1, AC-04.2
- `test_file.py` — AC-05.1, AC-05.2, AC-06.1, AC-06.2, AC-07.1-07.3, AC-08.1, AC-10.2, AC-27.1, AC-27.2, AC-28.1, AC-28.2, AC-29.1, AC-29.2
- `test_preset.py` — AC-30.3, AC-30.4, AC-30.5, AC-31.1
- `test_coercion.py` — AC-12.1-12.3, AC-13.1-13.4, AC-14.1-14.3, AC-40.1
- `test_validation.py` — AC-15.1, AC-15.2, AC-16.1, AC-16.2, AC-17.1, AC-17.2, AC-19.1, AC-19.2
- `test_help.py` — AC-20.1-20.6, AC-21.1, AC-21.2, AC-22.1, AC-22.2, AC-23.1, AC-24.1, AC-24.2, AC-25.1, AC-25.2, AC-26.1
- `test_serialization.py` — AC-36.1, AC-36.2

**Integration tests** (`tests/test_integration.py`):
- AC-09.1, AC-09.2, AC-10.1, AC-11.1, AC-32.1 (multi-file layering)
- AC-30.1, AC-30.2 (preset + CLI interaction)
- AC-40.2 (coercion + validation error aggregation)

**E2E tests** (`tests/test_e2e.py`):
- AC-02.1-02.4 (full resolution order via .load())
- AC-18.1 (validation timing)
- AC-29.3, AC-43.1, AC-43.2 (nested groups end-to-end)
- AC-38.1, AC-38.2 (is_set tracking)
- AC-39.1, AC-39.2 (zero-config usage)

## 4. Implementation Notes

- Start with `field.py` and `meta.py` (no deps on other modules)
- Then sources (each independent, import only field.py)
- Then `coercion.py` and `validation.py` (depend on field.py)
- Then `loader.py` (orchestrates everything)
- Then `help.py` and `serialization.py` (depend on field.py + loader context)
- Finally `hierarchy.py` can be built early (imports only field.py) but is wired into meta.py last
- Cross-field validators distinguished by inspecting callable signature (1 param vs 2)
- Bool switch detection: peek at next argv token; if absent or starts with `-`, treat as bare switch
- `tomli-w` optional dep for serialization; fall back to manual TOML formatting

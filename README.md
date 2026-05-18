# ConfigsLoader Python

Configuration is scattered everywhere: argparse flags in one place, env-var
lookups in another, file-parsing logic in a third, and defaults sprinkled
throughout. Every new field means touching all of them. ConfigsLoader fixes
this: **one declaration per field, all sources resolved automatically.**

## What It Is

A unified, multi-source configuration loader for Python applications.
You declare each config field once and ConfigsLoader resolves its value from a
strict priority chain:

**CLI flag > environment variable > preset file > config file > default**

## How It Differs

| Property | ConfigsLoader | Typical approach |
|----------|--------------|-----------------|
| Declarations | Single per field | Duplicated across argparse, env, file parser |
| Priority chain | Built-in (CLI > env > preset > file > default) | Manual layering |
| Type safety | Automatic coercion with validation | Per-source casting |
| Runtime dependencies | Zero | Often pulls in Click, pydantic-settings, etc. |
| Help generation | Auto-generated from field metadata | Manual duplication |

## Features

- Declarative fields with defaults, CLI flags, env vars, and descriptions
- Resolution order: CLI > env var > preset file > config file > default
- Type coercion (str, int, float, bool, Enum, List, Optional)
- Required field validation
- Custom validators (single-field and cross-field)
- Auto-generated `--help` output
- TOML config file support with per-field section declarations
- Global section fallback for simple configs
- Preset file support (named configuration profiles)
- Config file auto-discovery (walk up directories)
- Multiple config files with layering (global -> project)
- Enum support with string conversion
- Unknown flag handling (error/warn/ignore modes)
- Hierarchical/nested config support
- 236 tests with 100% branch coverage

## Quick Usage

```python
from configsloader import ConfigsLoader, Field

class AppConfig(ConfigsLoader):
    # Fields declare which TOML section they live in
    model: str = Field(
        default="gemma4-4b",
        flags=["--model", "-m"],
        env="APP_MODEL",
        section="provider",
        description="LLM model to use",
    )
    temperature: float = Field(
        default=0.7,
        flags=["--temperature", "-t"],
        section="provider",
        description="Sampling temperature",
    )
    max_workers: int = Field(
        default=1,
        section="app",
        description="Max concurrent workers",
    )
    verbose: bool = Field(
        default=False,
        flags=["--verbose", "-v"],
        description="Enable verbose output",
    )

# Load from all sources (CLI > env > file > default)
config = AppConfig.load(
    args=sys.argv[1:],        # CLI arguments
    file="config.toml",       # TOML config file (optional)
)

print(config.model)        # from [provider] section, CLI, or env
print(config.max_workers)  # from [app] section or default
```

With `config.toml`:
```toml
[provider]
model = "gemma4-26b"
temperature = 0.5

[app]
max_workers = 4
```

## Install

```bash
pip install -e .
```

## Requirements

- Python 3.11+
- No runtime dependencies

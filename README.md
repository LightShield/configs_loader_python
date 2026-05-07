# ConfigsLoader Python

> **⚠️ TEMPORARY IMPLEMENTATION — API ONLY ⚠️**
>
> This is a **minimal stub** implementing only the public API surface needed by
> [guild](https://github.com/LightShield/guild). The internals are trivial
> (tomllib + sys.argv) and will be replaced with a proper implementation later.
>
> **Do not treat this as production-ready.** It exists to unblock Guild from
> duplicating config declarations between Pydantic models and Typer CLI flags.
>
> The real implementation will follow the design philosophy of
> [configs_loader_cpp](https://github.com/LightShield/configs_loader_cpp):
> single declaration per field, type-safe, high-performance reads, auto-generated help.

## What It Does

One declaration per config field. Value resolved from: **CLI flag > env var > config file > default**.

```python
from configsloader import ConfigsLoader, Field

class AppConfig(ConfigsLoader):
    model: str = Field(
        default="gemma4-4b",
        flags=["--model", "-m"],
        env="GUILD_MODEL",
        description="LLM model to use",
    )
    temperature: float = Field(
        default=0.7,
        flags=["--temperature", "-t"],
        description="Sampling temperature",
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
    section="provider",       # Section within the TOML file
)

print(config.model)        # resolved value
print(config.temperature)  # resolved value
```

## Features (Current)

- [x] Declarative fields with defaults, CLI flags, env vars, descriptions
- [x] Resolution order: CLI > env var > config file > default
- [x] Type coercion (str, int, float, bool)
- [x] Required field validation
- [x] Auto-generated `--help`
- [x] TOML config file support
- [x] Section-scoped config file loading

## Missing (Future)

- [ ] Hierarchical/nested configs
- [ ] Preset files
- [ ] Custom validators beyond type coercion
- [ ] Config file auto-discovery (walk up directories)
- [ ] Multiple config files with layering (global → project)
- [ ] Enum support with string conversion
- [ ] Unknown flag handling (error/warn/ignore)
- [ ] Performance optimization

## Install

```bash
pip install -e .
```

## Requirements

- Python 3.11+
- No external dependencies

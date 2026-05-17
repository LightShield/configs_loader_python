"""ConfigsLoader — unified config from CLI, env, file, defaults.

⚠️  TEMPORARY STUB IMPLEMENTATION — API surface only.
    Internals will be rewritten. Do not depend on internal behavior.
"""

from configsloader.field import Field, FieldDescriptor
from configsloader.meta import _ConfigMeta
from configsloader.coercion import coerce
from configsloader.core import ConfigsLoader

__version__ = "0.1.0"

__all__ = ["ConfigsLoader", "Field", "FieldDescriptor", "coerce", "__version__"]

"""Settings overrides for pre-commit pytest hook.

Inherit from dev settings but force the SQLite test database to be
in-memory to avoid creating files in the working tree during hooks.
"""

from .dev import *  # noqa: F401,F403

# Use in-memory SQLite for tests executed via pre-commit
DATABASES["default"]["TEST"] = {"NAME": ":memory:"}  # type: ignore[name-defined]  # noqa: F405

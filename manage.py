#!/usr/bin/env python
"""
Django management utility for Courpera.

This entrypoint enables administrative tasks such as running the server,
creating migrations, and applying them. It assumes a local development
configuration; production settings are introduced in later stages.
"""

import os
import sys


def main() -> None:
    """Run administrative tasks for the Courpera project.

    In development, we default to `config.settings` until the settings
    split is introduced in the next stage.
    """
    # Default to development settings; production overrides with env var.
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        # Provide a clear hint if Django is not installed in the environment.
        raise ImportError("Django is not installed or not available on the PYTHONPATH.") from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()

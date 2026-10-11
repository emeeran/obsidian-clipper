#!/usr/bin/env python3
"""Entry point for running obsidian_clipper as a module."""

import sys

from .cli.main import main

if __name__ == "__main__":
    sys.exit(main())

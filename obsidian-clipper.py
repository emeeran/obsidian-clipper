#!/usr/bin/env python3
"""
Obsidian Clipper - Legacy entry point wrapper.

This script provides backward compatibility with the old clipper.py entry point.
For new installations, use: python -m obsidian_clipper
"""

import os
import sys

# Add parent directory to path for development installs
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from obsidian_clipper.clipper import main

if __name__ == "__main__":
    sys.exit(main())

# Shim for tools that still call setup.py. Dependencies and metadata live in pyproject.toml only
# (2026-10-05: this file declared numpy and scipy while pyproject.toml declared four packages).
from setuptools import setup

setup()

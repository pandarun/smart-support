"""
CLI commands for Smart Support system.

This module provides command-line tools for:
- Migrating FAQ embeddings to persistent storage
- Managing storage backends
- Validating storage integrity
"""

from src.cli.migrate_embeddings import migrate

__all__ = ['migrate']

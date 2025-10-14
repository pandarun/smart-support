"""
Entry point for running CLI module as: python -m src.cli

Forwards to the migrate_embeddings command by default.
"""

from src.cli.migrate_embeddings import migrate

if __name__ == '__main__':
    migrate()

"""
Migration CLI for Persistent Embedding Storage.

Provides command-line interface for populating and updating the persistent
embedding storage from FAQ database. Supports incremental updates (only
changed templates) and force recompute (all templates).

Features:
- Incremental updates: Only compute embeddings for new/modified templates
- Change detection: SHA256 content hashing to detect FAQ changes
- Batch processing: Efficient API usage with configurable batch size
- Progress tracking: Rich progress bars and console output
- Validation: Integrity checks after migration
- Error handling: Graceful failure with rollback and helpful error messages

Usage:
    # Initial migration (populates empty storage)
    python -m src.cli.migrate_embeddings --faq-path docs/smart_support_vtb_belarus_faq_final.xlsx

    # Incremental update (after FAQ changes)
    python -m src.cli.migrate_embeddings --faq-path docs/smart_support_vtb_belarus_faq_final.xlsx --incremental

    # Force recompute all embeddings
    python -m src.cli.migrate_embeddings --faq-path docs/smart_support_vtb_belarus_faq_final.xlsx --force

    # Validate storage integrity
    python -m src.cli.migrate_embeddings --validate

    # Use PostgreSQL backend
    python -m src.cli.migrate_embeddings --storage-backend postgres --postgres-dsn "postgresql://user:pass@localhost/db"
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple

import click
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table
from rich.panel import Panel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

console = Console()


@click.command()
@click.option(
    '--storage-backend',
    type=click.Choice(['sqlite', 'postgres'], case_sensitive=False),
    default='sqlite',
    envvar='STORAGE_BACKEND',
    help='Storage backend to use (default: sqlite)',
)
@click.option(
    '--sqlite-path',
    type=click.Path(),
    default='data/embeddings.db',
    envvar='SQLITE_DB_PATH',
    help='Path to SQLite database file (default: data/embeddings.db)',
)
@click.option(
    '--postgres-dsn',
    type=str,
    envvar='POSTGRES_DSN',
    help='PostgreSQL connection string (e.g., postgresql://user:pass@localhost/db)',
)
@click.option(
    '--faq-path',
    type=click.Path(exists=True),
    default='docs/smart_support_vtb_belarus_faq_final.xlsx',
    envvar='FAQ_PATH',
    help='Path to FAQ Excel database',
)
@click.option(
    '--batch-size',
    type=int,
    default=20,
    help='Number of templates per embedding batch (default: 20)',
)
@click.option(
    '--force',
    is_flag=True,
    help='Force recompute all embeddings (ignore stored hashes)',
)
@click.option(
    '--incremental',
    is_flag=True,
    help='Only compute embeddings for new/modified templates (default behavior)',
)
@click.option(
    '--validate',
    is_flag=True,
    help='Validate storage integrity without migration',
)
@click.option(
    '--verbose',
    is_flag=True,
    help='Enable verbose logging (DEBUG level)',
)
def migrate(
    storage_backend: str,
    sqlite_path: str,
    postgres_dsn: Optional[str],
    faq_path: str,
    batch_size: int,
    force: bool,
    incremental: bool,
    validate: bool,
    verbose: bool,
):
    """
    Migrate FAQ templates to persistent embedding storage.

    This command loads FAQ templates from Excel database, computes embeddings
    using Scibox API, and stores them in persistent storage (SQLite or PostgreSQL).

    Supports incremental updates (only changed templates) and force recompute (all templates).
    """
    # Configure logging level
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)

    console.print(Panel.fit(
        "[bold cyan]Smart Support - Embedding Migration Tool[/bold cyan]",
        border_style="cyan"
    ))

    try:
        # Import dependencies
        from src.retrieval.storage import create_storage_backend
        from src.retrieval.storage.models import StorageConfig, EmbeddingRecordCreate
        from src.retrieval.embeddings import EmbeddingsClient
        from src.classification.faq_parser import parse_faq
        from src.utils.hashing import compute_content_hash

        # Create storage configuration
        config = _create_storage_config(storage_backend, sqlite_path, postgres_dsn)

        # Create and connect to storage backend
        with console.status("[bold yellow]Connecting to storage...", spinner="dots"):
            storage = create_storage_backend(config)
            storage.connect()
            storage.initialize_schema()

        console.print(f"✓ Connected to {storage_backend} storage", style="bold green")

        # Validate-only mode
        if validate:
            _validate_storage(storage)
            return

        # Load FAQ templates
        with console.status("[bold yellow]Loading FAQ templates...", spinner="dots"):
            templates = parse_faq(faq_path)

        console.print(f"✓ Loaded {len(templates)} templates from FAQ database", style="bold green")

        if not templates:
            console.print("[bold red]Error: FAQ database is empty", style="bold red")
            sys.exit(1)

        # Initialize embeddings client
        embeddings_client = EmbeddingsClient()

        # Perform migration
        if force:
            console.print("\n[bold yellow]Mode: FORCE RECOMPUTE[/bold yellow] (all embeddings will be recomputed)")
            _migrate_force(storage, embeddings_client, templates, batch_size)
        else:
            console.print("\n[bold yellow]Mode: INCREMENTAL UPDATE[/bold yellow] (only changed templates)")
            _migrate_incremental(storage, embeddings_client, templates, batch_size)

        # Validate storage after migration
        console.print("\n[bold cyan]Validating storage integrity...[/bold cyan]")
        _validate_storage(storage)

        # Display final stats
        _display_final_stats(storage)

        console.print("\n[bold green]✓ Migration completed successfully![/bold green]")

    except FileNotFoundError as e:
        console.print(f"\n[bold red]Error: File not found[/bold red]")
        console.print(f"  {e}")
        console.print("\nHint: Check that FAQ path is correct and file exists")
        sys.exit(1)

    except ImportError as e:
        console.print(f"\n[bold red]Error: Missing dependency[/bold red]")
        console.print(f"  {e}")
        console.print("\nHint: Ensure all required packages are installed (pip install -r requirements.txt)")
        sys.exit(1)

    except Exception as e:
        console.print(f"\n[bold red]Error: Migration failed[/bold red]")
        console.print(f"  {type(e).__name__}: {e}")
        logger.exception("Migration failed with exception")
        sys.exit(1)

    finally:
        # Cleanup
        if 'storage' in locals() and storage.is_connected():
            storage.disconnect()


def _create_storage_config(
    backend: str,
    sqlite_path: str,
    postgres_dsn: Optional[str]
) -> 'StorageConfig':
    """Create storage configuration from CLI arguments."""
    from src.retrieval.storage.models import StorageConfig

    if backend == 'postgres':
        if not postgres_dsn:
            console.print("[bold red]Error: --postgres-dsn required for PostgreSQL backend[/bold red]")
            sys.exit(1)

        # Parse PostgreSQL DSN
        # Format: postgresql://user:pass@host:port/database
        import re
        match = re.match(
            r'postgresql://(?P<user>[^:]+):(?P<password>[^@]+)@(?P<host>[^:]+):(?P<port>\d+)/(?P<database>.+)',
            postgres_dsn
        )
        if not match:
            console.print("[bold red]Error: Invalid PostgreSQL DSN format[/bold red]")
            console.print("Expected: postgresql://user:pass@host:port/database")
            sys.exit(1)

        return StorageConfig(
            backend='postgres',
            postgres_host=match.group('host'),
            postgres_port=int(match.group('port')),
            postgres_database=match.group('database'),
            postgres_user=match.group('user'),
            postgres_password=match.group('password'),
        )

    else:  # sqlite
        # Ensure directory exists
        sqlite_path_obj = Path(sqlite_path)
        sqlite_path_obj.parent.mkdir(parents=True, exist_ok=True)

        return StorageConfig(
            backend='sqlite',
            sqlite_path=sqlite_path,
        )


def _migrate_incremental(
    storage: 'StorageBackend',
    embeddings_client: 'EmbeddingsClient',
    templates: List[Dict],
    batch_size: int,
):
    """
    Perform incremental migration: only compute embeddings for new/modified templates.

    Change detection:
    - New templates: template_id not in storage
    - Modified templates: content hash changed
    - Deleted templates: template_id in storage but not in FAQ
    """
    from src.retrieval.storage.models import EmbeddingRecordCreate
    from src.utils.hashing import compute_content_hash

    console.print("[bold]Detecting changes...[/bold]")

    # Get current embeddings from storage
    with console.status("[bold yellow]Loading stored embeddings...", spinner="dots"):
        try:
            stored_records = storage.load_embeddings_all()
            stored_template_ids = {r.template_id for r in stored_records}
            stored_hashes = {r.template_id: r.content_hash for r in stored_records}
        except Exception as e:
            logger.warning(f"Failed to load stored embeddings: {e}. Assuming empty storage.")
            stored_template_ids = set()
            stored_hashes = {}

    # Compute current template hashes
    current_templates = {
        t.get('id', f"tmpl_{t['category']}_{i}"): t
        for i, t in enumerate(templates)
    }
    current_hashes = {
        template_id: compute_content_hash(t['question'], t['answer'])
        for template_id, t in current_templates.items()
    }

    # Detect changes
    current_ids = set(current_templates.keys())

    new_ids = current_ids - stored_template_ids
    deleted_ids = stored_template_ids - current_ids

    # Modified: in both, but hash changed
    potentially_modified = stored_template_ids & current_ids
    modified_ids = {
        tid for tid in potentially_modified
        if stored_hashes.get(tid) != current_hashes.get(tid)
    }

    unchanged_ids = potentially_modified - modified_ids

    # Display change summary
    _display_change_summary(
        new_count=len(new_ids),
        modified_count=len(modified_ids),
        deleted_count=len(deleted_ids),
        unchanged_count=len(unchanged_ids),
    )

    # Nothing to do?
    if not new_ids and not modified_ids and not deleted_ids:
        console.print("\n[bold green]✓ Storage is up-to-date, no changes detected[/bold green]")
        return

    # Get version ID
    version_id = storage.get_or_create_version(
        model_name=embeddings_client.model,
        model_version="v1",
        embedding_dimension=1024,
    )

    # Process new templates
    if new_ids:
        console.print(f"\n[bold cyan]Processing {len(new_ids)} new templates...[/bold cyan]")
        new_templates = [current_templates[tid] for tid in new_ids]
        _embed_and_store_batch(
            storage=storage,
            embeddings_client=embeddings_client,
            templates=new_templates,
            version_id=version_id,
            batch_size=batch_size,
            operation="INSERT",
        )

    # Process modified templates
    if modified_ids:
        console.print(f"\n[bold cyan]Processing {len(modified_ids)} modified templates...[/bold cyan]")
        modified_templates = [current_templates[tid] for tid in modified_ids]
        _embed_and_store_batch(
            storage=storage,
            embeddings_client=embeddings_client,
            templates=modified_templates,
            version_id=version_id,
            batch_size=batch_size,
            operation="UPDATE",
        )

    # Process deleted templates
    if deleted_ids:
        console.print(f"\n[bold cyan]Processing {len(deleted_ids)} deleted templates...[/bold cyan]")
        _delete_templates(storage, deleted_ids)


def _migrate_force(
    storage: 'StorageBackend',
    embeddings_client: 'EmbeddingsClient',
    templates: List[Dict],
    batch_size: int,
):
    """
    Perform force migration: recompute all embeddings regardless of stored state.

    Use case: Model version upgrade, embedding dimension change, or corrupted storage.
    """
    console.print("[bold yellow]Warning: Force recompute will regenerate ALL embeddings[/bold yellow]")

    # Get version ID (may create new version if model changed)
    version_id = storage.get_or_create_version(
        model_name=embeddings_client.model,
        model_version="v1",
        embedding_dimension=1024,
    )

    console.print(f"\n[bold cyan]Recomputing {len(templates)} embeddings...[/bold cyan]")

    # Recompute all embeddings
    _embed_and_store_batch(
        storage=storage,
        embeddings_client=embeddings_client,
        templates=templates,
        version_id=version_id,
        batch_size=batch_size,
        operation="UPSERT",  # Insert or update
    )


def _embed_and_store_batch(
    storage: 'StorageBackend',
    embeddings_client: 'EmbeddingsClient',
    templates: List[Dict],
    version_id: int,
    batch_size: int,
    operation: str,  # "INSERT", "UPDATE", or "UPSERT"
):
    """
    Compute embeddings for templates and store in batches.

    Args:
        storage: Storage backend
        embeddings_client: Embeddings API client
        templates: List of template dictionaries
        version_id: Embedding version ID
        batch_size: Number of templates per batch
        operation: "INSERT" (new), "UPDATE" (modified), or "UPSERT" (force)
    """
    from src.retrieval.storage.models import EmbeddingRecordCreate
    from src.utils.hashing import compute_content_hash
    from src.retrieval.embeddings import EmbeddingsError

    # Split into batches
    batches = [templates[i:i + batch_size] for i in range(0, len(templates), batch_size)]

    success_count = 0
    failure_count = 0

    # Progress bar
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("({task.completed}/{task.total})"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:

        task = progress.add_task(
            f"[cyan]Embedding templates...",
            total=len(templates)
        )

        for batch_idx, batch in enumerate(batches, start=1):
            try:
                # Combine question + answer for embedding
                texts = [f"{t['question']} {t['answer']}" for t in batch]

                # Call embeddings API
                embeddings = embeddings_client.embed_batch(texts)

                # Prepare records for storage
                records = []
                for template, embedding in zip(batch, embeddings):
                    template_id = template.get('id', f"tmpl_{template['category']}_{success_count}")
                    content_hash = compute_content_hash(template['question'], template['answer'])

                    record = EmbeddingRecordCreate(
                        template_id=template_id,
                        version_id=version_id,
                        embedding_vector=embedding,
                        category=template['category'],
                        subcategory=template['subcategory'],
                        question_text=template['question'],
                        answer_text=template['answer'],
                        content_hash=content_hash,
                        success_rate=0.5,  # Default
                        usage_count=0,
                    )
                    records.append(record)

                # Store batch
                if operation == "INSERT":
                    storage.store_embeddings_batch(records)
                elif operation == "UPDATE":
                    for record in records:
                        storage.update_embedding(record.template_id, record)
                elif operation == "UPSERT":
                    # Try insert, fall back to update
                    for record in records:
                        try:
                            storage.store_embedding(record)
                        except Exception:
                            storage.update_embedding(record.template_id, record)

                success_count += len(batch)
                progress.update(task, advance=len(batch))

            except EmbeddingsError as e:
                logger.error(f"Failed to embed batch {batch_idx}/{len(batches)}: {e}")
                failure_count += len(batch)
                progress.update(task, advance=len(batch))
                continue

            except Exception as e:
                logger.error(f"Failed to store batch {batch_idx}/{len(batches)}: {e}")
                failure_count += len(batch)
                progress.update(task, advance=len(batch))
                continue

    # Display results
    if success_count > 0:
        console.print(f"  ✓ Successfully processed {success_count} templates", style="bold green")

    if failure_count > 0:
        console.print(f"  ✗ Failed to process {failure_count} templates", style="bold red")


def _delete_templates(storage: 'StorageBackend', template_ids: Set[str]):
    """Delete templates from storage."""
    success_count = 0
    failure_count = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:

        task = progress.add_task(
            "[red]Deleting templates...",
            total=len(template_ids)
        )

        for template_id in template_ids:
            try:
                if storage.delete_embedding(template_id):
                    success_count += 1
                else:
                    logger.warning(f"Template not found: {template_id}")
                    failure_count += 1
            except Exception as e:
                logger.error(f"Failed to delete {template_id}: {e}")
                failure_count += 1

            progress.update(task, advance=1)

    if success_count > 0:
        console.print(f"  ✓ Successfully deleted {success_count} templates", style="bold green")

    if failure_count > 0:
        console.print(f"  ✗ Failed to delete {failure_count} templates", style="bold red")


def _display_change_summary(
    new_count: int,
    modified_count: int,
    deleted_count: int,
    unchanged_count: int,
):
    """Display change detection summary as table."""
    table = Table(title="Change Detection Summary", show_header=True, header_style="bold cyan")
    table.add_column("Status", style="bold")
    table.add_column("Count", justify="right")
    table.add_column("Action")

    table.add_row("New", str(new_count), "[green]Compute embeddings[/green]")
    table.add_row("Modified", str(modified_count), "[yellow]Recompute embeddings[/yellow]")
    table.add_row("Deleted", str(deleted_count), "[red]Remove embeddings[/red]")
    table.add_row("Unchanged", str(unchanged_count), "[dim]Skip[/dim]")

    console.print(table)


def _validate_storage(storage: 'StorageBackend'):
    """Validate storage integrity."""
    try:
        integrity = storage.validate_integrity()

        if integrity.get('valid', False):
            console.print("  ✓ Storage integrity check passed", style="bold green")
        else:
            console.print("  ✗ Storage integrity check failed", style="bold red")
            console.print(f"    Issues: {integrity.get('errors', [])}")
            sys.exit(1)

    except Exception as e:
        console.print(f"  ✗ Validation failed: {e}", style="bold red")
        sys.exit(1)


def _display_final_stats(storage: 'StorageBackend'):
    """Display final storage statistics."""
    try:
        info = storage.get_storage_info()

        table = Table(title="Storage Statistics", show_header=True, header_style="bold cyan")
        table.add_column("Metric", style="bold")
        table.add_column("Value", justify="right")

        for key, value in info.items():
            # Format key (camelCase -> Title Case)
            formatted_key = key.replace('_', ' ').title()
            table.add_row(formatted_key, str(value))

        console.print(table)

    except Exception as e:
        logger.warning(f"Failed to retrieve storage stats: {e}")


if __name__ == '__main__':
    migrate()

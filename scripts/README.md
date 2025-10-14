# Scripts Directory

Helper scripts for Smart Support system setup and maintenance.

## populate_database.sh

**Purpose:** Automates database population with FAQ embeddings for MVP deployment.

**Features:**
- ✅ Checks all prerequisites (Python, API key, FAQ file, dependencies)
- ✅ Creates data directory automatically
- ✅ Runs migration with optimal settings
- ✅ Validates database integrity
- ✅ Displays comprehensive statistics
- ✅ Handles errors gracefully with helpful messages

### Quick Start

```bash
# Initial database population (first time setup)
./scripts/populate_database.sh
```

This will:
1. Check for Scibox API key in `.env`
2. Verify FAQ Excel file exists
3. Install missing Python dependencies
4. Create SQLite database at `data/embeddings.db`
5. Compute embeddings for all FAQ templates (~210)
6. Validate database integrity
7. Display summary statistics

**Time:** ~1-2 minutes for ~210 templates (depends on API speed)

### Options

```bash
# Show help
./scripts/populate_database.sh --help

# Incremental update (only new/modified templates)
./scripts/populate_database.sh --incremental

# Force recompute all embeddings
./scripts/populate_database.sh --force

# Custom batch size (default: 20)
./scripts/populate_database.sh --batch-size 50

# Verbose logging
./scripts/populate_database.sh --verbose

# Combine options
./scripts/populate_database.sh --incremental --verbose
```

### Prerequisites

The script automatically checks for:

- **Python 3.8+** (required)
- **.env file** with `SCIBOX_API_KEY` (required)
- **FAQ Excel file** at `docs/smart_support_vtb_belarus_faq_final.xlsx` (required)
- **Python packages** (auto-installs if missing):
  - `openai` - Scibox API client
  - `openpyxl` - Excel file parsing
  - `pydantic` - Data validation
  - `click` - CLI framework
  - `rich` - Beautiful terminal output

### Example Output

```
╔════════════════════════════════════════════════════════════╗
║     Smart Support - Database Population Script            ║
║     Prepopulates SQLite with FAQ Embeddings                ║
╚════════════════════════════════════════════════════════════╝

[1/5] Checking prerequisites...
✓ Python found: Python 3.12.2
✓ Scibox API key configured
✓ FAQ file found: docs/smart_support_vtb_belarus_faq_final.xlsx
✓ All Python dependencies available

[2/5] Preparing data directory...
✓ Created data/ directory
ℹ Database will be created: data/embeddings.db

[3/5] Analyzing FAQ database...
✓ Found 210 templates in FAQ database
ℹ Estimated migration time: ~11 minutes
ℹ Batch size: 20 templates/batch

[4/5] Running database migration...
Mode: INCREMENTAL UPDATE (only new/modified)

Smart Support - Embedding Migration Tool
✓ Connected to sqlite storage
✓ Loaded 210 templates from FAQ database

Processing 210 new templates...
Embedding templates... ████████████ 100% (210/210) 00:42
  ✓ Successfully processed 210 templates

✓ Migration completed successfully!

[5/5] Validating database...
✓ Database integrity check passed
✓ Database contains 210 embeddings

╔════════════════════════════════════════════════════════════╗
║                 🎉 SUCCESS! 🎉                             ║
║     Database populated and ready for use                   ║
╚════════════════════════════════════════════════════════════╝

Database location: data/embeddings.db
Database size: 2.4M
Total embeddings: 210

Next steps:
  1. Test retrieval:  python -m src.cli.retrieve "Как открыть счет?"
  2. Run tests:       pytest tests/integration/retrieval/
  3. Start web UI:    python -m src.web.app (when available)
```

### Troubleshooting

**"Python not found"**
```bash
# Install Python 3.8+ from https://python.org
# Or use pyenv/conda
```

**"SCIBOX_API_KEY not set in .env"**
```bash
# Edit .env file
echo "SCIBOX_API_KEY=your_key_here" >> .env
```

**"FAQ file not found"**
```bash
# Verify file exists
ls -la docs/smart_support_vtb_belarus_faq_final.xlsx
```

**"Migration failed"**
```bash
# Run with verbose mode for detailed logs
./scripts/populate_database.sh --verbose
```

### When to Run

**Initial Setup:**
- First time deployment
- After cloning repository
- Fresh database needed

**Incremental Updates:**
- After FAQ content changes
- After adding new templates
- Regular maintenance

**Force Recompute:**
- After model upgrade
- Database corruption
- Embedding dimension change

### Manual Migration

If you prefer manual control:

```bash
# Direct CLI usage (without script)
python -m src.cli.migrate_embeddings \
    --faq-path docs/smart_support_vtb_belarus_faq_final.xlsx \
    --sqlite-path data/embeddings.db \
    --batch-size 20 \
    --incremental
```

See `python -m src.cli.migrate_embeddings --help` for all options.

## validate_mvp.sh

Validates MVP implementation against requirements (existing script).

## run_validation_v2.py

Runs classification validation tests (existing script).

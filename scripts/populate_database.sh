#!/bin/bash
#
# Smart Support - Database Population Script
#
# Automatically populates the SQLite database with FAQ embeddings.
# This script handles all prerequisites, runs the migration, and validates results.
#
# Usage:
#   ./scripts/populate_database.sh [OPTIONS]
#
# Options:
#   --force         Force recompute all embeddings (ignore cache)
#   --incremental   Only process new/modified templates (default)
#   --batch-size N  Number of templates per batch (default: 20)
#   --verbose       Enable verbose logging
#   --help          Show this help message
#

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Default values
FORCE_MODE=false
INCREMENTAL_MODE=false
BATCH_SIZE=20
VERBOSE_MODE=false
FAQ_PATH="docs/smart_support_vtb_belarus_faq_final.xlsx"
SQLITE_PATH="data/embeddings.db"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --force)
            FORCE_MODE=true
            shift
            ;;
        --incremental)
            INCREMENTAL_MODE=true
            shift
            ;;
        --batch-size)
            BATCH_SIZE="$2"
            shift 2
            ;;
        --verbose)
            VERBOSE_MODE=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --force         Force recompute all embeddings"
            echo "  --incremental   Only process new/modified templates"
            echo "  --batch-size N  Templates per batch (default: 20)"
            echo "  --verbose       Enable verbose logging"
            echo "  --help          Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Error: Unknown option $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Print header
echo -e "${CYAN}${BOLD}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║     Smart Support - Database Population Script            ║"
echo "║     Prepopulates SQLite with FAQ Embeddings                ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Step 1: Check prerequisites
echo -e "${BLUE}${BOLD}[1/5] Checking prerequisites...${NC}"

# Check if Python is available
if ! command -v python &> /dev/null; then
    echo -e "${RED}✗ Python not found${NC}"
    echo "Please install Python 3.8+ and try again"
    exit 1
fi
echo -e "${GREEN}✓ Python found: $(python --version)${NC}"

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠ .env file not found${NC}"
    echo "Creating .env from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${GREEN}✓ Created .env file${NC}"
        echo -e "${YELLOW}⚠ Please edit .env and add your SCIBOX_API_KEY${NC}"
    else
        echo -e "${RED}✗ .env.example not found${NC}"
        exit 1
    fi
fi

# Check if API key is set
if ! grep -q "SCIBOX_API_KEY=sk-" .env 2>/dev/null; then
    echo -e "${RED}✗ SCIBOX_API_KEY not set in .env${NC}"
    echo "Please edit .env and add your Scibox API key:"
    echo "  SCIBOX_API_KEY=your_key_here"
    exit 1
fi
echo -e "${GREEN}✓ Scibox API key configured${NC}"

# Check if FAQ file exists
if [ ! -f "$FAQ_PATH" ]; then
    echo -e "${RED}✗ FAQ file not found: $FAQ_PATH${NC}"
    echo "Please ensure the FAQ Excel file exists"
    exit 1
fi
echo -e "${GREEN}✓ FAQ file found: $FAQ_PATH${NC}"

# Check required Python packages
echo -e "${BLUE}Checking Python dependencies...${NC}"
python -c "import openai, openpyxl, pydantic, click, rich" 2>/dev/null || {
    echo -e "${YELLOW}⚠ Missing dependencies detected${NC}"
    echo "Installing required packages..."
    pip install -q openai openpyxl pydantic click rich
    echo -e "${GREEN}✓ Dependencies installed${NC}"
}
echo -e "${GREEN}✓ All Python dependencies available${NC}"

# Step 2: Create data directory
echo -e "\n${BLUE}${BOLD}[2/5] Preparing data directory...${NC}"

if [ ! -d "data" ]; then
    mkdir -p data
    echo -e "${GREEN}✓ Created data/ directory${NC}"
else
    echo -e "${GREEN}✓ data/ directory exists${NC}"
fi

# Check if database already exists
if [ -f "$SQLITE_PATH" ]; then
    SIZE=$(du -h "$SQLITE_PATH" | cut -f1)
    echo -e "${YELLOW}⚠ Database already exists: $SQLITE_PATH (Size: $SIZE)${NC}"

    if [ "$FORCE_MODE" = false ] && [ "$INCREMENTAL_MODE" = false ]; then
        echo -e "${YELLOW}Switching to incremental mode to preserve existing data${NC}"
        INCREMENTAL_MODE=true
    fi
else
    echo -e "${CYAN}ℹ Database will be created: $SQLITE_PATH${NC}"
fi

# Step 3: Count FAQ templates
echo -e "\n${BLUE}${BOLD}[3/5] Analyzing FAQ database...${NC}"

TEMPLATE_COUNT=$(python -c "
from src.classification.faq_parser import parse_faq
templates = parse_faq('$FAQ_PATH')
print(len(templates))
" 2>/dev/null || echo "0")

if [ "$TEMPLATE_COUNT" -eq 0 ]; then
    echo -e "${RED}✗ Failed to parse FAQ database${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Found $TEMPLATE_COUNT templates in FAQ database${NC}"

# Estimate time and cost
ESTIMATED_TIME=$((TEMPLATE_COUNT / BATCH_SIZE + 1))
echo -e "${CYAN}ℹ Estimated migration time: ~${ESTIMATED_TIME} minutes${NC}"
echo -e "${CYAN}ℹ Batch size: $BATCH_SIZE templates/batch${NC}"

# Step 4: Run migration
echo -e "\n${BLUE}${BOLD}[4/5] Running database migration...${NC}"

# Load environment variables from .env file
if [ -f .env ]; then
    export $(grep -v '^#' .env | grep -v '^$' | xargs)
fi

# Build migration command
MIGRATION_CMD="python -m src.cli.migrate_embeddings"
MIGRATION_CMD="$MIGRATION_CMD --faq-path $FAQ_PATH"
MIGRATION_CMD="$MIGRATION_CMD --sqlite-path $SQLITE_PATH"
MIGRATION_CMD="$MIGRATION_CMD --batch-size $BATCH_SIZE"

if [ "$FORCE_MODE" = true ]; then
    MIGRATION_CMD="$MIGRATION_CMD --force"
    echo -e "${YELLOW}Mode: FORCE RECOMPUTE (all embeddings)${NC}"
elif [ "$INCREMENTAL_MODE" = true ]; then
    MIGRATION_CMD="$MIGRATION_CMD --incremental"
    echo -e "${CYAN}Mode: INCREMENTAL UPDATE (only new/modified)${NC}"
fi

if [ "$VERBOSE_MODE" = true ]; then
    MIGRATION_CMD="$MIGRATION_CMD --verbose"
fi

echo -e "${CYAN}Running: $MIGRATION_CMD${NC}\n"

# Run migration
if $MIGRATION_CMD; then
    echo -e "\n${GREEN}${BOLD}✓ Migration completed successfully!${NC}"
else
    echo -e "\n${RED}${BOLD}✗ Migration failed${NC}"
    echo "Check the error messages above for details"
    exit 1
fi

# Step 5: Validate and display statistics
echo -e "\n${BLUE}${BOLD}[5/5] Validating database...${NC}"

# Validate database
python -c "
from src.retrieval.storage import create_storage_backend
from src.retrieval.storage.models import StorageConfig

config = StorageConfig(backend='sqlite', sqlite_path='$SQLITE_PATH')
storage = create_storage_backend(config)
storage.connect()

# Validate integrity
integrity = storage.validate_integrity()
if integrity.get('valid', False):
    print('${GREEN}✓ Database integrity check passed${NC}')
else:
    print('${RED}✗ Database integrity check failed${NC}')
    print(f'  Errors: {integrity.get(\"errors\", [])}')
    exit(1)

# Get statistics
count = storage.count()
info = storage.get_storage_info()

storage.disconnect()

print(f'${GREEN}✓ Database contains {count} embeddings${NC}')
" || exit 1

# Display final summary
echo -e "\n${GREEN}${BOLD}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                 🎉 SUCCESS! 🎉                             ║"
echo "║     Database populated and ready for use                   ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Display database info
if [ -f "$SQLITE_PATH" ]; then
    DB_SIZE=$(du -h "$SQLITE_PATH" | cut -f1)
    echo -e "${CYAN}Database location:${NC} $SQLITE_PATH"
    echo -e "${CYAN}Database size:${NC} $DB_SIZE"
    echo -e "${CYAN}Total embeddings:${NC} $TEMPLATE_COUNT"
fi

# Next steps
echo -e "\n${BOLD}Next steps:${NC}"
echo "  1. Test retrieval:  ${CYAN}python -m src.cli.retrieve \"Как открыть счет?\"${NC}"
echo "  2. Run tests:       ${CYAN}pytest tests/integration/retrieval/${NC}"
echo "  3. Start web UI:    ${CYAN}python -m src.web.app${NC} (when available)"

echo -e "\n${BOLD}To update the database later:${NC}"
echo "  Incremental:  ${CYAN}./scripts/populate_database.sh --incremental${NC}"
echo "  Force:        ${CYAN}./scripts/populate_database.sh --force${NC}"

echo ""

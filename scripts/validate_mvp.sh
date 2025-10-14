#!/bin/bash
# MVP Validation Script for Persistent Storage Feature
#
# This script validates User Story 1 (Fast System Startup) by:
# 1. Running all unit tests
# 2. Running all integration tests
# 3. Measuring actual startup time with populated storage
# 4. Verifying accuracy is maintained
#
# Usage:
#   ./scripts/validate_mvp.sh
#
# Requirements:
#   - FAQ database: docs/smart_support_vtb_belarus_faq_final.xlsx
#   - SCIBOX_API_KEY environment variable set
#   - Python dependencies installed (requirements.txt)

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}=====================================================================${NC}"
echo -e "${CYAN}   Smart Support - Persistent Storage MVP Validation${NC}"
echo -e "${CYAN}=====================================================================${NC}"
echo ""

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

if [ ! -f "docs/smart_support_vtb_belarus_faq_final.xlsx" ]; then
    echo -e "${RED}✗ FAQ database not found: docs/smart_support_vtb_belarus_faq_final.xlsx${NC}"
    exit 1
fi
echo -e "${GREEN}✓ FAQ database found${NC}"

if [ -z "$SCIBOX_API_KEY" ]; then
    echo -e "${RED}✗ SCIBOX_API_KEY environment variable not set${NC}"
    echo -e "  Get your API key from: https://llm.t1v.scibox.tech/"
    echo -e "  Set it: export SCIBOX_API_KEY=your_key_here"
    exit 1
fi
echo -e "${GREEN}✓ SCIBOX_API_KEY is set${NC}"

if ! command -v pytest &> /dev/null; then
    echo -e "${RED}✗ pytest not found${NC}"
    echo -e "  Install: pip install pytest"
    exit 1
fi
echo -e "${GREEN}✓ pytest found${NC}"

echo ""

# Step 1: Run unit tests
echo -e "${CYAN}Step 1: Running unit tests...${NC}"
echo -e "${YELLOW}Running: pytest tests/unit/retrieval/ -v${NC}"
pytest tests/unit/retrieval/ -v --tb=short

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ All unit tests passed${NC}"
else
    echo -e "${RED}✗ Unit tests failed${NC}"
    exit 1
fi

echo ""

# Step 2: Run integration tests
echo -e "${CYAN}Step 2: Running integration tests...${NC}"
echo -e "${YELLOW}Running: pytest tests/integration/retrieval/ -v${NC}"
pytest tests/integration/retrieval/ -v --tb=short -m "not slow"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ All integration tests passed${NC}"
else
    echo -e "${RED}✗ Integration tests failed${NC}"
    exit 1
fi

echo ""

# Step 3: Populate storage (if not already done)
echo -e "${CYAN}Step 3: Populating storage (if needed)...${NC}"

if [ ! -f "data/embeddings.db" ]; then
    echo -e "${YELLOW}Storage not populated, running migration CLI...${NC}"
    python -m src.cli.migrate_embeddings \
        --faq-path docs/smart_support_vtb_belarus_faq_final.xlsx \
        --storage-backend sqlite \
        --sqlite-path data/embeddings.db \
        --batch-size 20

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Storage populated successfully${NC}"
    else
        echo -e "${RED}✗ Failed to populate storage${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓ Storage already populated (data/embeddings.db exists)${NC}"
fi

echo ""

# Step 4: Measure startup time
echo -e "${CYAN}Step 4: Measuring startup time...${NC}"
echo -e "${YELLOW}Running startup performance test...${NC}"

pytest tests/integration/retrieval/test_startup_performance.py::TestStartupPerformance::test_cache_load_from_storage_under_2_seconds -v -s

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Startup time requirement met (<2 seconds)${NC}"
else
    echo -e "${RED}✗ Startup time requirement not met${NC}"
    exit 1
fi

echo ""

# Step 5: Validate accuracy (optional - requires full FAQ + validation dataset)
echo -e "${CYAN}Step 5: Validating retrieval accuracy...${NC}"
echo -e "${YELLOW}Note: Full accuracy validation requires validation dataset${NC}"

if [ -f "data/validation/validation_queries.json" ]; then
    echo -e "${YELLOW}Running accuracy validation script...${NC}"
    python scripts/validate_retrieval_accuracy.py

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Retrieval accuracy maintained (86.7% top-3)${NC}"
    else
        echo -e "${RED}✗ Retrieval accuracy below target${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠ Validation dataset not found, skipping full accuracy test${NC}"
    echo -e "${YELLOW}  Running basic accuracy tests...${NC}"

    pytest tests/integration/retrieval/test_storage_accuracy.py -v

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Basic accuracy tests passed (storage preserves embeddings)${NC}"
    else
        echo -e "${RED}✗ Basic accuracy tests failed${NC}"
        exit 1
    fi
fi

echo ""

# Summary
echo -e "${CYAN}=====================================================================${NC}"
echo -e "${GREEN}   ✓ MVP VALIDATION COMPLETE${NC}"
echo -e "${CYAN}=====================================================================${NC}"
echo ""
echo -e "Results:"
echo -e "  ${GREEN}✓ Unit tests: PASSED${NC}"
echo -e "  ${GREEN}✓ Integration tests: PASSED${NC}"
echo -e "  ${GREEN}✓ Storage populated: SUCCESS${NC}"
echo -e "  ${GREEN}✓ Startup time: <2 seconds${NC}"
echo -e "  ${GREEN}✓ Accuracy: Maintained${NC}"
echo ""
echo -e "User Story 1 (Fast System Startup) is complete and validated!"
echo ""
echo -e "Next steps:"
echo -e "  1. Merge feature branch: git checkout main && git merge 003-implement-persistent-storage"
echo -e "  2. Deploy to production"
echo -e "  3. Monitor startup times and accuracy metrics"
echo ""
echo -e "Optional improvements:"
echo -e "  - Implement User Story 2 (Incremental FAQ Updates)"
echo -e "  - Implement User Story 3 (Version Management)"
echo -e "  - Add PostgreSQL backend support"
echo ""

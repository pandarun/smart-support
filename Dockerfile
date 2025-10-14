# Smart Support - Intelligent Customer Support System
# Includes Classification Module + Template Retrieval Module
# Python 3.11 base image for production deployment

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Default paths
    FAQ_PATH=/app/docs/smart_support_vtb_belarus_faq_final.xlsx \
    LOG_LEVEL=INFO

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY docs/ ./docs/
COPY data/ ./data/

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Health check - verifies FAQ parser is working (shared by both modules)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "from src.classification.faq_parser import get_faq_parser; get_faq_parser()" || exit 1

# Default entry point: Python module runner
# Override with -m flag to run different modules:
#   docker run smart-support -m src.cli.classify <args>
#   docker run smart-support -m src.cli.retrieve <args>
ENTRYPOINT ["python"]

# Default: show classification CLI help
CMD ["-m", "src.cli.classify", "--help"]

# Usage examples:
#
# Classification:
#   docker run -e SCIBOX_API_KEY=$SCIBOX_API_KEY smart-support \
#       -m src.cli.classify "Как открыть счет?"
#
# Retrieval:
#   docker run -e SCIBOX_API_KEY=$SCIBOX_API_KEY smart-support \
#       -m src.cli.retrieve "Как открыть счет?" \
#       --category "Счета и вклады" --subcategory "Открытие счета"
#
# Validation:
#   docker run -e SCIBOX_API_KEY=$SCIBOX_API_KEY smart-support \
#       -m src.cli.classify --validate /app/data/validation/validation_dataset.json
#   docker run -e SCIBOX_API_KEY=$SCIBOX_API_KEY smart-support \
#       -m src.cli.retrieve --validate /app/data/validation/retrieval_validation_dataset.json

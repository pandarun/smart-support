# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Smart Support is an intelligent technical support system built for the Minsk Hackathon. The system uses AI/ML technologies to transform customer support operations by automatically classifying customer inquiries and providing relevant template responses to support operators.

**Core Capabilities:**
- Automatic classification of customer inquiries into product categories and subcategories
- Intelligent ranking and retrieval of relevant template responses from knowledge base
- Integration with Scibox platform for LLM-powered analysis
- Web interface for support operators to interact with the system

**Technical Stack:**
- LLM Integration: Scibox API (https://llm.t1v.scibox.tech/v1)
- Available Models:
  - `Qwen2.5-72B-Instruct-AWQ` (chat/classification)
  - `bge-m3` (embeddings for semantic search)

## API Integration

### Scibox LLM Service
The project integrates with Scibox's OpenAI-compatible API. Key endpoints:

**Chat Completions (for classification and response generation):**
```bash
POST https://llm.t1v.scibox.tech/v1/chat/completions
Headers: Authorization: Bearer $SCIBOX_API_KEY
```

**Embeddings (for semantic search in knowledge base):**
```bash
POST https://llm.t1v.scibox.tech/v1/embeddings
Model: bge-m3
```

### Python Client Usage
Use OpenAI Python client (v1.0+) with custom base URL:
```python
from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("SCIBOX_API_KEY"),
    base_url="https://llm.t1v.scibox.tech/v1"
)
```

## Data Assets

**Knowledge Base Location:** `docs/smart_support_vtb_belarus_faq_final.xlsx`
- Contains structured template responses for VTB Belarus customer support
- Includes categories, subcategories, and predefined answers

**Documentation:**
- `docs/Инструкция SciBox.md` - Complete SciBox API documentation with examples
- `docs/Полный кейс Smart Support МИНСК.txt` - Full hackathon case description and requirements

## System Architecture

The system should implement three core modules:

1. **Classification Module**
   - Analyzes incoming customer inquiry text
   - Determines product category and subcategory
   - Uses LLM for intelligent classification (10 points per correct classification in validation)

2. **Ranking/Retrieval Module**
   - Searches through template responses database
   - Ranks results by relevance to the inquiry
   - Considers successful resolution history
   - Uses embeddings (bge-m3) for semantic similarity

3. **Operator Interface**
   - Web-based UI for support operators
   - Displays classification results and ranked template responses
   - Allows quick editing and sending of responses
   - Should be fast and intuitive (20 points for UI/UX in evaluation)

## Evaluation Criteria

The system is evaluated on:
- **Classification Quality (30 points):** 10 points per correctly classified inquiry from validation set
- **Recommendation Relevance (30 points):** 10 points per correctly suggested template response
- **UI/UX (20 points):** Interface quality (10) + speed and navigation (10)
- **Presentation (20 points):** Demo quality (10) + business logic depth (10)

## Development Guidelines

### Environment Setup
- Store API key in `.env` file as `SCIBOX_API_KEY`
- `.env` is gitignored to prevent credential leaks

### Recommended Development Approach
1. Start with classification module - test against validation questions
2. Import and structure the FAQ database from Excel file
3. Implement semantic search using bge-m3 embeddings
4. Build operator interface with real-time classification and ranking
5. Test full pipeline with validation dataset

### Docker Deployment
The solution should include Docker setup for easy deployment across different operating systems (required for submission).

## Hackathon Checkpoints

- **Checkpoint 1:** Scibox integration, request classification, FAQ database import
- **Checkpoint 2:** Recommendation system implementation, correct classification on test cases
- **Checkpoint 3:** Full operator interface, quality evaluation on real data, demo and presentation ready

## Submission Requirements

1. Public repository with complete source code
2. Easy launch instructions (Docker recommended)
3. Demo video showing: inquiry → classification → recommendations → operator response
4. Technical presentation describing the system

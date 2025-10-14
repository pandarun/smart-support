# Feature Specification: Template Retrieval Module

**Feature Branch**: `002-create-template-retrieval`
**Created**: 2025-10-14
**Status**: Draft
**Input**: User description: "Create Template Retrieval Module that implements hybrid embeddings-based architecture for ranking and retrieving relevant FAQ template responses. Core Functionality: Precompute embeddings for all FAQ templates using Scibox bge-m3 embeddings model, accept user query text + Classification Module output (category/subcategory), filter templates to the classified category to narrow search space, compute query embedding and calculate cosine similarity against template embeddings, rank templates by semantic similarity score (primary ranking factor), return top-K (default 5) most relevant templates with confidence scores, support optional historical success rate weighting for ranking refinement. Performance Requirements: Template retrieval must complete in <1 second for top-5 results, precomputation of all template embeddings should complete in <60 seconds on startup, support concurrent retrieval requests without degradation. Integration: Consume Classification Module output (category, subcategory, confidence), use Scibox API bge-m3 model for embeddings, store precomputed embeddings in memory or lightweight cache, expose retrieval function callable from CLI and API. Quality Requirements: Top-3 templates must include correct answer for ≥80% of validation queries (hackathon scoring: 10 points per correct recommendation × 3 queries = 30 points), semantic similarity scores should correlate with operator selection, handle edge cases (no templates in category, query too short, all similarities below threshold). Evaluation Criteria: Hackathon awards 30 points for recommendation relevance, system should return top-5 ranked templates for operator review. Technical Constraints: Must use Scibox bge-m3 embeddings API, follow constitution principles (modular architecture, API-first, data-driven validation), include testcontainers integration tests and Chrome DevTools e2e tests, deploy via Docker with existing classification module. User Stories: 1) Operator receives classified inquiry and needs top-5 relevant template responses ranked by relevance 2) System administrator precomputes embeddings on startup/FAQ update and validates embedding coverage 3) QA team validates retrieval quality against test dataset of query-template pairs. Success Metrics: ≥80% of validation queries have correct template in top-3 results, retrieval latency <1 second for 95th percentile, embedding precomputation completes in <60 seconds for ~100-200 templates"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Retrieve Relevant Templates for Classified Inquiry (Priority: P1)

A support operator has received a customer inquiry that has been automatically classified (category and subcategory determined by the Classification Module). The operator needs to quickly see the top 5 most relevant template responses from the knowledge base, ranked by semantic similarity to the customer's actual question, so they can select the best answer with minimal editing.

**Why this priority**: This is the core functionality worth 30 points in hackathon evaluation (10 points per correctly recommended template × 3 validation queries). Without accurate template retrieval, operators cannot efficiently respond to customers. This directly impacts the UI/UX scoring (20 points) by determining how quickly operators can find and send appropriate responses.

**Independent Test**: Can be fully tested by providing a customer query text and classification result (e.g., category="Счета и вклады", subcategory="Открытие счета"), verifying that the system returns 5 ranked template responses within 1 second, and confirming that at least one of the top-3 templates is semantically relevant to the query when compared against a validation dataset.

**Acceptance Scenarios**:

1. **Given** a customer inquiry "Как открыть накопительный счет в мобильном приложении?" and classification result (category="Счета и вклады", subcategory="Открытие счета"), **When** the operator requests template retrieval, **Then** the system returns 5 ranked templates from the "Открытие счета" subcategory within 1 second, with similarity scores indicating relevance
2. **Given** a customer inquiry about a specific product feature and correct classification, **When** the operator views retrieved templates, **Then** the top-ranked template addresses the specific feature mentioned in the inquiry (not just generic category information)
3. **Given** multiple similar templates in the same subcategory, **When** the operator requests retrieval, **Then** templates are ranked by semantic similarity to the query (most relevant first), with similarity scores differentiating between near-duplicate templates

---

### User Story 2 - Precompute and Validate Embeddings on Startup (Priority: P2)

A system administrator deploys the Template Retrieval Module or updates the FAQ knowledge base. The system must automatically precompute semantic embeddings for all FAQ templates during initialization, validate that all templates have valid embeddings, and report readiness before accepting retrieval requests.

**Why this priority**: Embedding precomputation is a prerequisite for retrieval functionality. Without precomputed embeddings, retrieval cannot function. This ensures system reliability and provides visibility into embedding coverage for troubleshooting. Validates that the knowledge base is properly indexed before operators depend on it.

**Independent Test**: Can be fully tested by starting the system with the FAQ database containing 100-200 templates, measuring the time to complete embedding precomputation (must be <60 seconds), verifying that all templates have valid embedding vectors stored, and confirming the system reports "ready" status only after precomputation completes successfully.

**Acceptance Scenarios**:

1. **Given** the system starts with a FAQ database of 150 templates, **When** initialization runs, **Then** all 150 templates have embeddings computed via Scibox bge-m3 API within 60 seconds and the system reports "ready" status
2. **Given** embedding precomputation is in progress, **When** an operator attempts to retrieve templates, **Then** the system returns a clear "not ready" message indicating embeddings are still being computed
3. **Given** a template fails to generate an embedding (API error or invalid text), **When** precomputation completes, **Then** the system logs the failed template details and marks it as unavailable for retrieval, without blocking other templates

---

### User Story 3 - Validate Retrieval Quality Against Test Dataset (Priority: P3)

A QA team member needs to validate that the Template Retrieval Module meets the 80% accuracy requirement by running it against a test dataset of query-template pairs with known correct answers. The system generates a validation report showing which queries had the correct template in the top-3 results, overall accuracy percentage, and per-category breakdown.

**Why this priority**: Hackathon scoring awards 10 points per correctly recommended template (30 points total for 3 validation queries). This validation capability proves the system meets quality requirements and provides measurable metrics for the presentation. Enables continuous quality monitoring and identifies retrieval accuracy issues before operator use.

**Independent Test**: Can be fully tested by running the validation script with a dataset of 10+ query-template pairs (each with ground truth "correct template ID"), generating a validation report showing top-3 accuracy percentage (≥80% required), per-query results (correct/incorrect), and similarity score distributions for correct vs. incorrect retrievals.

**Acceptance Scenarios**:

1. **Given** a validation dataset with 10 queries and known correct template IDs, **When** validation runs, **Then** at least 8 of 10 queries (80%) have the correct template in the top-3 retrieved results
2. **Given** validation results for all queries, **When** the report is generated, **Then** it includes overall accuracy percentage, per-query breakdown (query text, correct template ID, retrieved templates with ranks, correct/incorrect status), and average similarity scores for correct vs. incorrect matches
3. **Given** a validation query where the correct template is not in the top-3, **When** reviewing results, **Then** the report shows the rank and similarity score of the correct template (if retrieved at all) to help diagnose ranking issues

---

### Edge Cases

- What happens when the classified category/subcategory has zero templates in the knowledge base? System should return an empty result set with a message indicating no templates available for this category, allowing the operator to escalate or manually search
- What happens when the customer query is too short or generic (e.g., "Помогите" / "Help")? System should still retrieve templates based on the classified category, but similarity scores will be low; operator should be notified that the query lacks specificity
- What happens when all template similarity scores are below a minimum threshold (e.g., <0.3 cosine similarity)? System should return the top-5 ranked templates but flag them as "low confidence matches" to warn the operator that manual review is needed
- What happens when the Scibox embeddings API is unavailable or times out during retrieval? System should return an error message indicating embeddings could not be computed for the query, suggest retry, and log the failure for monitoring
- What happens when the Scibox embeddings API fails during precomputation startup? System should retry failed templates with exponential backoff, log failures, and mark the system as "partially ready" if some templates have embeddings, or "not ready" if no embeddings could be computed
- What happens when multiple operators request template retrieval simultaneously for different queries? System should handle concurrent requests without performance degradation, serving each request within the <1 second target
- What happens when the FAQ knowledge base is updated (templates added/removed/edited) after the system is running? System should provide a way to trigger re-precomputation of embeddings for changed templates without requiring full system restart

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST precompute semantic embeddings for all FAQ templates using Scibox bge-m3 embeddings API on startup or when the knowledge base is updated
- **FR-002**: System MUST accept customer query text and Classification Module output (category, subcategory, confidence score) as input for retrieval
- **FR-003**: System MUST filter the FAQ knowledge base to templates matching the classified category and subcategory before computing similarity
- **FR-004**: System MUST compute a semantic embedding for the customer query using Scibox bge-m3 embeddings API at retrieval time
- **FR-005**: System MUST calculate cosine similarity between the query embedding and all filtered template embeddings
- **FR-006**: System MUST rank templates by similarity score in descending order (highest similarity first)
- **FR-007**: System MUST return the top-K templates (default K=5, configurable) with similarity scores for each result
- **FR-008**: System MUST complete template retrieval within 1 second (95th percentile) for top-5 results
- **FR-009**: System MUST handle concurrent retrieval requests from multiple operators without performance degradation
- **FR-010**: System MUST store precomputed template embeddings in memory or lightweight persistent cache (in-memory preferred for performance, SQLite acceptable for persistence)
- **FR-011**: System MUST report "ready" status only after all template embeddings have been successfully precomputed and stored
- **FR-012**: System MUST log each retrieval request with timestamp, query text (truncated if necessary), classified category/subcategory, number of templates retrieved, top similarity score, and processing time
- **FR-013**: System MUST provide a validation mode that accepts a test dataset of query-template pairs with ground truth template IDs and generates an accuracy report
- **FR-014**: System MUST expose retrieval functionality via CLI interface and programmatic API (callable from operator interface)
- **FR-015**: System MUST use Scibox API endpoint (https://llm.t1v.scibox.tech/v1/embeddings) with bge-m3 model for all embedding generation
- **FR-016**: System MUST handle API authentication using SCIBOX_API_KEY environment variable for Scibox embeddings API
- **FR-017**: System MUST return meaningful error messages for edge cases (no templates in category, API failures, timeout scenarios, low similarity scores)
- **FR-018**: System SHOULD support optional historical success rate weighting in ranking formula (e.g., 0.7 × similarity + 0.3 × historical_usage), with similarity-only ranking as default

### Performance Requirements

- **PR-001**: Template retrieval MUST complete within 1 second for top-5 results (95th percentile response time)
- **PR-002**: Embedding precomputation for 100-200 templates MUST complete within 60 seconds on system startup
- **PR-003**: System MUST handle at least 10 concurrent retrieval requests without exceeding the 1-second response time target

### Quality Requirements

- **QR-001**: Top-3 retrieved templates MUST include the correct/relevant template for at least 80% of validation queries
- **QR-002**: Similarity scores MUST correlate with retrieval relevance (templates with higher similarity scores should be more relevant to the query when manually reviewed)
- **QR-003**: Embedding precomputation MUST achieve 100% coverage (all templates have valid embeddings) or clearly report failed templates

### Key Entities

- **FAQ Template**: A predefined answer from the knowledge base, including template ID, category, subcategory, question text, answer text, and precomputed embedding vector (generated from question + answer text)
- **Query**: Customer inquiry text submitted by the operator, including the original text and runtime-generated embedding vector
- **Classification Result**: Output from the Classification Module containing predicted category, predicted subcategory, and confidence score
- **Retrieval Result**: A single retrieved template with metadata, including template ID, template text (question + answer), similarity score (cosine similarity between query and template embeddings), rank (position in sorted results), and category/subcategory
- **Similarity Score**: A numeric value (0.0 to 1.0) representing cosine similarity between query embedding and template embedding, where higher scores indicate greater semantic relevance
- **Validation Record**: A test case pairing a customer query with the ground truth correct template ID, used for quality validation
- **Embedding Vector**: A high-dimensional numeric representation (vector) of text generated by the bge-m3 model, used for semantic similarity comparison

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Template retrieval correctly places the relevant template in the top-3 results for at least 80% of validation dataset queries (minimum 8 out of 10 test cases)
- **SC-002**: 95% of retrieval requests complete within 1 second when tested with representative customer queries and concurrent load
- **SC-003**: Embedding precomputation for the full FAQ database (100-200 templates) completes within 60 seconds on system startup
- **SC-004**: Validation report shows positive correlation between similarity scores and retrieval relevance (templates with similarity >0.7 have >90% relevance when manually reviewed, templates with similarity <0.5 have <50% relevance)
- **SC-005**: Module can be integrated and tested independently without requiring the operator UI to be implemented (CLI interface provides full retrieval functionality)
- **SC-006**: System handles 10 concurrent retrieval requests with all responses completing within 1 second (no performance degradation under concurrent load)

### Business Value

- **BV-001**: Earns 30 points in hackathon evaluation through accurate template recommendations (10 points per correct recommendation × 3 validation queries)
- **BV-002**: Enables operators to find relevant template responses instantly (<1 second), reducing average customer response time by 70% compared to manual knowledge base search
- **BV-003**: Provides measurable quality metrics (top-3 accuracy percentage, similarity score correlation) demonstrating semantic search value for hackathon presentation
- **BV-004**: Integrates with existing Classification Module output to deliver complete inquiry-to-response workflow for Checkpoint 2 demo

## Assumptions

- Validation dataset with query-template pairs and ground truth template IDs will be created for testing (similar to Classification Module validation approach)
- FAQ templates contain sufficient text content (question + answer) for meaningful embeddings (minimum 10 words per template)
- Scibox bge-m3 embeddings API has sufficient quota/rate limits to support embedding precomputation and real-time retrieval during validation and demo
- Template embeddings remain valid for the duration of the hackathon (no need for periodic re-embedding unless templates change)
- Cosine similarity is an appropriate metric for semantic relevance in the Russian language banking FAQ domain (standard approach for bge-m3 model)
- Classification Module accuracy (90% achieved) is sufficient that retrieval can assume category/subcategory filtering will reduce false positive template matches
- Operators will provide feedback on template relevance (for future historical success rate weighting), but this is optional for MVP
- In-memory embedding storage is acceptable for ~100-200 templates (estimated ~100MB memory footprint for 768-dimensional embeddings)

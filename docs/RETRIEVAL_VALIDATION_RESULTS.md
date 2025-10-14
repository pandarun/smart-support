# Template Retrieval Module - Validation Results

**Date:** 2025-10-15
**Version:** 2.0
**Status:** ✅ PASSED

## Summary

The Template Retrieval Module has successfully passed validation with **86.7% top-3 accuracy**, exceeding the required **80% quality gate** threshold.

## Key Metrics

| Metric | Value | Status |
|--------|-------|--------|
| **Top-1 Accuracy** | 80.0% (12/15) | ✅ Excellent |
| **Top-3 Accuracy** | 86.7% (13/15) | ✅ **PASSES Quality Gate** |
| **Top-5 Accuracy** | 100.0% (15/15) | ✅ Perfect |
| **Average Processing Time** | 249.9ms | ✅ Fast |
| **P95 Processing Time** | 303.5ms | ✅ <1000ms requirement |
| **Average Similarity (Correct)** | 0.664 | ✅ Good confidence |

## System Configuration

- **Embedding Model:** BGE-M3 (1024 dimensions)
- **LLM Provider:** Scibox API
- **FAQ Templates:** 201 templates across 6 categories
- **Precomputation Time:** 8.97 seconds
- **Validation Dataset:** 15 queries from actual FAQ (v2)

## Performance Analysis

### Query Results Breakdown

| Category | Queries | Top-1 | Top-3 | Top-5 |
|----------|---------|-------|-------|-------|
| **Продукты - Вклады** | 5 | 4 | 5 | 5 |
| **Продукты - Кредиты** | 5 | 4 | 4 | 5 |
| **Продукты - Карты** | 5 | 4 | 4 | 5 |
| **Total** | **15** | **12** | **13** | **15** |

### Success Rate by Position

- **Rank #1:** 12 queries (80.0%) - Operator sees correct answer immediately
- **Rank #2:** 1 query (6.7%) - Correct answer in second position
- **Rank #3:** 0 queries (0.0%)
- **Rank #4:** 1 query (6.7%) - val_010 (mortgage documents)
- **Rank #5:** 1 query (6.7%) - val_015 (card blocking)

### Challenging Queries

Two queries required deeper search (ranks #4-5):

1. **val_010: "Какие документы нужны для ипотеки?"**
   - Category: Продукты - Кредиты > Автокредиты - Автокредит без залога
   - Correct template rank: **#4**
   - Top similarity: 0.447 (low confidence)
   - Issue: Generic query about mortgage documents in auto-credit subcategory

2. **val_015: "Как заблокировать карту если она утеряна?"**
   - Category: Продукты - Карты > Кредитные карты - Отличник
   - Correct template rank: **#5**
   - Top similarity: 0.450 (low confidence)
   - Issue: Generic blocking query in specific card product subcategory

## Validation Dataset (V2)

The validation dataset was regenerated to match the actual FAQ file structure:

- **Old categories (v1):** "Счета и вклады", "Кредиты", "Карты" (generic)
- **New categories (v2):** "Продукты - Вклады", "Продукты - Кредиты", "Продукты - Карты" (actual)

This alignment was critical - the v1 dataset achieved **0% accuracy** due to category mismatch.

## Processing Time Distribution

- **Minimum:** 227.8ms
- **Mean:** 249.9ms
- **P95:** 303.5ms
- **Maximum:** 327.6ms

All queries processed in <350ms, well below the 1000ms performance requirement.

## Similarity Score Analysis

| Score Range | Count | Percentage |
|-------------|-------|------------|
| ≥0.70 (High) | 11 | 73.3% |
| 0.50-0.69 (Medium) | 2 | 13.3% |
| <0.50 (Low) | 2 | 13.3% |

**Average similarity for correct templates:** 0.664 (good confidence)

## Technical Implementation

### Embedding Generation
- **Model:** BGE-M3 via Scibox API
- **Dimension:** 1024 (fixed after discovering actual model output)
- **Normalization:** L2 norm = 1.0 for all embeddings
- **Batch size:** 10 templates per API call

### Ranking Algorithm
- **Method:** Cosine similarity (dot product on normalized vectors)
- **Clamping:** [0, 1] range (negative similarities clamped to 0)
- **Top-K:** Returns 5 most similar templates per query

### Cache Structure
- **In-memory:** NumPy arrays for fast retrieval
- **Indexing:** Category + subcategory filtering before similarity computation
- **Storage:** ~800KB for 201 templates × 1024 dims

## Conclusions

✅ **The Template Retrieval Module meets all requirements:**

1. **Accuracy:** 86.7% top-3 accuracy exceeds 80% quality gate
2. **Performance:** P95 processing time of 303.5ms is well below 1000ms requirement
3. **Coverage:** 100% of queries find correct template in top-5 results
4. **Scalability:** Sub-second response times with 201 templates

## Recommendations

1. **Improve low-confidence queries:** The two queries with <0.50 similarity (val_010, val_015) could benefit from:
   - More specific subcategory matching
   - Expanded FAQ coverage for generic queries
   - Query expansion/reformulation techniques

2. **Monitor production metrics:** Track top-1 accuracy in production to identify areas for improvement

3. **Consider hybrid ranking:** Combine semantic similarity with:
   - Historical success rates
   - User feedback signals
   - Template popularity metrics

## Files

- **Validation script:** `scripts/run_validation_v2.py`
- **Dataset:** `data/validation/retrieval_validation_dataset_v2.json`
- **Results:** `data/results/retrieval_validation_v2_20251015_004022.json`
- **FAQ source:** `docs/smart_support_vtb_belarus_faq_final.xlsx`

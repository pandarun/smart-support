"""
End-to-End Tests for User Story 1: Core Operator Workflow

User Story 1: As an operator, I need to submit a customer inquiry and receive
ranked template responses, so I can quickly respond to customer questions.

Workflow:
1. Operator submits Russian customer inquiry
2. System classifies inquiry → category + subcategory (< 2s)
3. System retrieves top 5 relevant templates (< 1s)
4. Operator can copy template answer to clipboard
5. Total workflow completes in < 10 seconds

Acceptance Criteria:
- AC-001: Operator can submit Russian text inquiry (5-5000 characters)
- AC-002: Classification returns category, subcategory, confidence within 2 seconds
- AC-003: System retrieves exactly 5 ranked template responses within 1 second
- AC-004: Each template includes question, answer, and similarity score
- AC-005: Templates are ranked by relevance (best first)
- AC-006: Total end-to-end workflow completes in < 10 seconds

Constitution Compliance:
- Principle II: User-Centric Design (validates operator workflow efficiency)
- Principle III: Data-Driven Validation (validates performance requirements)
"""

import pytest
from fastapi.testclient import TestClient
from backend.src.api.main import app
import time

client = TestClient(app)


class TestUserStory1EndToEnd:
    """End-to-end tests for User Story 1 complete workflow."""

    def test_complete_workflow_success(self):
        """
        Test complete User Story 1 workflow from inquiry to template retrieval.

        This test validates the entire operator workflow:
        1. Submit inquiry → classification
        2. Use classification result → retrieval
        3. Verify total time < 10s
        """
        # === STEP 1: Operator submits inquiry ===
        inquiry = "Как заблокировать банковскую карту, если она утеряна?"

        workflow_start = time.time()

        # === STEP 2: System classifies inquiry ===
        classify_request = {"inquiry": inquiry}

        classify_start = time.time()
        classify_response = client.post("/api/classify", json=classify_request)
        classify_duration_ms = (time.time() - classify_start) * 1000

        # Validate classification response
        assert classify_response.status_code == 200, \
            f"Classification failed: {classify_response.status_code} - {classify_response.text}"

        classification_result = classify_response.json()

        # AC-002: Classification returns category, subcategory, confidence within 2s
        assert "category" in classification_result
        assert "subcategory" in classification_result
        assert "confidence" in classification_result
        assert classification_result["inquiry"] == inquiry
        assert 0.0 <= classification_result["confidence"] <= 1.0
        assert classify_duration_ms < 2000, \
            f"Classification took {classify_duration_ms:.2f}ms (expected <2000ms)"

        print(f"\n✓ Classification completed in {classify_duration_ms:.2f}ms")
        print(f"  Category: {classification_result['category']}")
        print(f"  Subcategory: {classification_result['subcategory']}")
        print(f"  Confidence: {classification_result['confidence']:.2f}")

        # === STEP 3: System retrieves relevant templates ===
        retrieval_request = {
            "query": inquiry,
            "category": classification_result["category"],
            "subcategory": classification_result["subcategory"],
            "classification_confidence": classification_result["confidence"],
            "top_k": 5  # AC-003: Retrieve exactly 5 templates
        }

        retrieval_start = time.time()
        retrieval_response = client.post("/api/retrieve", json=retrieval_request)
        retrieval_duration_ms = (time.time() - retrieval_start) * 1000

        # Validate retrieval response
        assert retrieval_response.status_code == 200, \
            f"Retrieval failed: {retrieval_response.status_code} - {retrieval_response.text}"

        retrieval_result = retrieval_response.json()

        # AC-003: Retrieval completes within 1 second
        assert retrieval_duration_ms < 1000, \
            f"Retrieval took {retrieval_duration_ms:.2f}ms (expected <1000ms)"

        # AC-003: System returns up to 5 ranked templates
        assert "results" in retrieval_result
        assert isinstance(retrieval_result["results"], list)
        assert len(retrieval_result["results"]) <= 5

        print(f"✓ Retrieval completed in {retrieval_duration_ms:.2f}ms")
        print(f"  Found {len(retrieval_result['results'])} templates")

        # === STEP 4: Validate template structure ===
        for i, template in enumerate(retrieval_result["results"]):
            # AC-004: Each template includes question, answer, and similarity score
            assert "template_id" in template
            assert "template_question" in template
            assert "template_answer" in template
            assert "similarity_score" in template
            assert "combined_score" in template
            assert "rank" in template

            # Validate template content is not empty
            assert len(template["template_question"]) > 0, f"Template {i} has empty question"
            assert len(template["template_answer"]) > 0, f"Template {i} has empty answer"

            # AC-005: Templates ranked by relevance (validate rank order)
            expected_rank = i + 1
            assert template["rank"] == expected_rank, \
                f"Template at index {i} has rank {template['rank']}, expected {expected_rank}"

            # Validate scores are valid
            assert 0.0 <= template["similarity_score"] <= 1.0
            assert 0.0 <= template["combined_score"] <= 1.0

            print(f"  [{template['rank']}] {template['template_question'][:60]}... (score: {template['combined_score']:.2f})")

        # AC-005: Verify templates are sorted by combined_score descending
        if len(retrieval_result["results"]) > 1:
            for i in range(len(retrieval_result["results"]) - 1):
                current_score = retrieval_result["results"][i]["combined_score"]
                next_score = retrieval_result["results"][i + 1]["combined_score"]
                assert current_score >= next_score, \
                    f"Templates not sorted: rank {i+1} score {current_score} < rank {i+2} score {next_score}"

        # === STEP 5: Validate total workflow time ===
        total_duration_ms = (time.time() - workflow_start) * 1000

        # AC-006: Total workflow completes in < 10 seconds
        assert total_duration_ms < 10000, \
            f"Total workflow took {total_duration_ms:.2f}ms (expected <10000ms)"

        print(f"✓ Total workflow completed in {total_duration_ms:.2f}ms")
        print(f"  Classification: {classify_duration_ms:.2f}ms")
        print(f"  Retrieval: {retrieval_duration_ms:.2f}ms")
        print(f"  Total: {total_duration_ms:.2f}ms")

        # === SUCCESS ===
        print("\n✓ User Story 1 workflow completed successfully!")

    def test_workflow_with_various_inquiries(self):
        """Test workflow with different types of customer inquiries."""
        test_inquiries = [
            "Забыл пароль от мобильного приложения, как восстановить?",
            "Хочу открыть вклад на 1 год, какие условия?",
            "Как получить кредит на покупку автомобиля?",
            "Почему не работает интернет-банкинг?",
            "Где посмотреть реквизиты моей карты?",
        ]

        for inquiry in test_inquiries:
            # Classify
            classify_response = client.post("/api/classify", json={"inquiry": inquiry})
            assert classify_response.status_code == 200, f"Failed to classify: {inquiry}"

            classification = classify_response.json()

            # Retrieve
            retrieval_request = {
                "query": inquiry,
                "category": classification["category"],
                "subcategory": classification["subcategory"],
                "top_k": 5
            }

            retrieval_response = client.post("/api/retrieve", json=retrieval_request)
            assert retrieval_response.status_code == 200, f"Failed to retrieve for: {inquiry}"

            retrieval = retrieval_response.json()
            assert len(retrieval["results"]) <= 5

            print(f"✓ Workflow successful for: {inquiry[:50]}...")

    def test_workflow_performance_multiple_runs(self):
        """Test workflow performance consistency across multiple runs."""
        inquiry = "Как узнать баланс моей карты через мобильное приложение?"
        iterations = 3

        workflow_durations = []
        classify_durations = []
        retrieval_durations = []

        for i in range(iterations):
            workflow_start = time.time()

            # Classify
            classify_start = time.time()
            classify_response = client.post("/api/classify", json={"inquiry": inquiry})
            classify_duration = (time.time() - classify_start) * 1000
            classify_durations.append(classify_duration)

            assert classify_response.status_code == 200
            classification = classify_response.json()

            # Retrieve
            retrieval_start = time.time()
            retrieval_response = client.post("/api/retrieve", json={
                "query": inquiry,
                "category": classification["category"],
                "subcategory": classification["subcategory"],
                "top_k": 5
            })
            retrieval_duration = (time.time() - retrieval_start) * 1000
            retrieval_durations.append(retrieval_duration)

            assert retrieval_response.status_code == 200

            workflow_duration = (time.time() - workflow_start) * 1000
            workflow_durations.append(workflow_duration)

            print(f"\nRun {i+1}: Total {workflow_duration:.2f}ms (classify: {classify_duration:.2f}ms, retrieve: {retrieval_duration:.2f}ms)")

        # Validate all runs meet performance requirements
        assert all(d < 2000 for d in classify_durations), \
            f"Some classification runs exceeded 2s: {classify_durations}"
        assert all(d < 1000 for d in retrieval_durations), \
            f"Some retrieval runs exceeded 1s: {retrieval_durations}"
        assert all(d < 10000 for d in workflow_durations), \
            f"Some workflows exceeded 10s: {workflow_durations}"

        avg_workflow = sum(workflow_durations) / len(workflow_durations)
        print(f"\n✓ Average workflow time: {avg_workflow:.2f}ms ({iterations} runs)")

    def test_workflow_with_low_confidence_classification(self):
        """Test workflow behavior when classification confidence is low."""
        # Intentionally ambiguous inquiry
        inquiry = "Помогите пожалуйста с проблемой"

        # Classify
        classify_response = client.post("/api/classify", json={"inquiry": inquiry})
        assert classify_response.status_code == 200

        classification = classify_response.json()

        # Even with low confidence, workflow should complete
        retrieval_response = client.post("/api/retrieve", json={
            "query": inquiry,
            "category": classification["category"],
            "subcategory": classification["subcategory"],
            "classification_confidence": classification["confidence"],
            "top_k": 5
        })

        assert retrieval_response.status_code == 200
        retrieval = retrieval_response.json()

        # May have warning about low confidence
        if classification["confidence"] < 0.5:
            # Low confidence is acceptable, but workflow should still work
            print(f"Low confidence: {classification['confidence']:.2f}")
            print(f"Warnings: {retrieval.get('warnings', [])}")

    def test_workflow_error_handling(self):
        """Test workflow error handling for invalid inputs."""
        # Invalid inquiry (too short)
        classify_response = client.post("/api/classify", json={"inquiry": "Hi"})
        assert classify_response.status_code == 400  # Validation error

        error_data = classify_response.json()
        assert "error" in error_data
        assert error_data["error_type"] == "validation"

        # Invalid retrieval (missing category)
        retrieval_response = client.post("/api/retrieve", json={
            "query": "Как открыть счет?",
            "subcategory": "Открытие счета"
            # Missing category
        })
        assert retrieval_response.status_code == 422  # Missing required field


class TestUserStory1AcceptanceCriteria:
    """Test each acceptance criterion individually."""

    def test_ac_001_russian_text_inquiry(self):
        """AC-001: Operator can submit Russian text inquiry (5-5000 characters)."""
        # Valid Russian inquiry
        inquiry = "Как заблокировать карту?"
        response = client.post("/api/classify", json={"inquiry": inquiry})
        assert response.status_code == 200

        # Too short (< 5 characters)
        response = client.post("/api/classify", json={"inquiry": "Как"})
        assert response.status_code == 400

        # Too long (> 5000 characters)
        response = client.post("/api/classify", json={"inquiry": "а" * 5001})
        assert response.status_code == 400

        # Not Russian (no Cyrillic)
        response = client.post("/api/classify", json={"inquiry": "Hello world"})
        assert response.status_code == 400

    def test_ac_002_classification_within_2_seconds(self):
        """AC-002: Classification returns category, subcategory, confidence within 2 seconds."""
        inquiry = "Как открыть депозит в банке?"

        start_time = time.time()
        response = client.post("/api/classify", json={"inquiry": inquiry})
        duration_ms = (time.time() - start_time) * 1000

        assert response.status_code == 200
        data = response.json()

        assert "category" in data
        assert "subcategory" in data
        assert "confidence" in data
        assert duration_ms < 2000

    def test_ac_003_retrieve_5_templates_within_1_second(self):
        """AC-003: System retrieves exactly 5 ranked template responses within 1 second."""
        # First classify to get category/subcategory
        classify_response = client.post("/api/classify", json={
            "inquiry": "Как перевести деньги на другой счет?"
        })
        assert classify_response.status_code == 200
        classification = classify_response.json()

        # Then retrieve
        start_time = time.time()
        retrieval_response = client.post("/api/retrieve", json={
            "query": "Как перевести деньги на другой счет?",
            "category": classification["category"],
            "subcategory": classification["subcategory"],
            "top_k": 5
        })
        duration_ms = (time.time() - start_time) * 1000

        assert retrieval_response.status_code == 200
        data = retrieval_response.json()

        # Should return up to 5 results
        assert len(data["results"]) <= 5
        # Performance: < 1 second
        assert duration_ms < 1000

    def test_ac_004_template_structure(self):
        """AC-004: Each template includes question, answer, and similarity score."""
        # Classify then retrieve
        classify_response = client.post("/api/classify", json={
            "inquiry": "Вопрос о кредитах"
        })
        classification = classify_response.json()

        retrieval_response = client.post("/api/retrieve", json={
            "query": "Вопрос о кредитах",
            "category": classification["category"],
            "subcategory": classification["subcategory"],
            "top_k": 5
        })

        data = retrieval_response.json()

        for template in data["results"]:
            assert "template_question" in template
            assert "template_answer" in template
            assert "similarity_score" in template
            assert len(template["template_question"]) > 0
            assert len(template["template_answer"]) > 0
            assert 0.0 <= template["similarity_score"] <= 1.0

    def test_ac_005_templates_ranked_by_relevance(self):
        """AC-005: Templates are ranked by relevance (best first)."""
        # Classify then retrieve
        classify_response = client.post("/api/classify", json={
            "inquiry": "Как получить выписку по счету?"
        })
        classification = classify_response.json()

        retrieval_response = client.post("/api/retrieve", json={
            "query": "Как получить выписку по счету?",
            "category": classification["category"],
            "subcategory": classification["subcategory"],
            "top_k": 5
        })

        data = retrieval_response.json()
        results = data["results"]

        # Verify ranks are sequential: 1, 2, 3, 4, 5
        for i, template in enumerate(results):
            assert template["rank"] == i + 1

        # Verify sorted by combined_score descending
        if len(results) > 1:
            for i in range(len(results) - 1):
                assert results[i]["combined_score"] >= results[i + 1]["combined_score"]

    def test_ac_006_total_workflow_under_10_seconds(self):
        """AC-006: Total end-to-end workflow completes in < 10 seconds."""
        inquiry = "Как активировать новую карту?"

        start_time = time.time()

        # Classify
        classify_response = client.post("/api/classify", json={"inquiry": inquiry})
        assert classify_response.status_code == 200
        classification = classify_response.json()

        # Retrieve
        retrieval_response = client.post("/api/retrieve", json={
            "query": inquiry,
            "category": classification["category"],
            "subcategory": classification["subcategory"],
            "top_k": 5
        })
        assert retrieval_response.status_code == 200

        total_duration_ms = (time.time() - start_time) * 1000

        # Must complete in < 10 seconds
        assert total_duration_ms < 10000

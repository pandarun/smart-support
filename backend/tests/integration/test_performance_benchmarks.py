"""
Performance Benchmark Tests for Smart Support Operator API

Validates all performance requirements across the system:
- FR-005: Classification must complete in < 2 seconds
- FR-010: Retrieval must complete in < 1 second
- FR-015: Total workflow must complete in < 10 seconds

Tests include:
- Single request performance
- Concurrent request performance
- Statistical analysis (min/max/mean/p95)
- Performance degradation under load

Constitution Compliance:
- Principle III: Data-Driven Validation (quantifiable performance metrics)
- Principle II: User-Centric Design (operator workflow efficiency)
"""

import pytest
from fastapi.testclient import TestClient
from backend.src.api.main import app
import time
import statistics
import concurrent.futures

client = TestClient(app)


def calculate_percentile(data, percentile):
    """Calculate percentile value from list of numbers."""
    sorted_data = sorted(data)
    index = int((percentile / 100.0) * len(sorted_data))
    if index >= len(sorted_data):
        index = len(sorted_data) - 1
    return sorted_data[index]


class TestClassificationPerformance:
    """Performance benchmarks for classification endpoint."""

    def test_classification_performance_single_request(self):
        """Test classification performance for single request (FR-005: <2s)."""
        request_data = {
            "inquiry": "Как заблокировать банковскую карту?"
        }

        durations = []
        iterations = 10

        for _ in range(iterations):
            start_time = time.time()
            response = client.post("/api/classify", json=request_data)
            duration_ms = (time.time() - start_time) * 1000
            durations.append(duration_ms)

            assert response.status_code == 200

        # Calculate statistics
        min_duration = min(durations)
        max_duration = max(durations)
        mean_duration = statistics.mean(durations)
        p95_duration = calculate_percentile(durations, 95)
        p99_duration = calculate_percentile(durations, 99)

        print(f"\nClassification Performance ({iterations} iterations):")
        print(f"  Min:  {min_duration:.2f}ms")
        print(f"  Max:  {max_duration:.2f}ms")
        print(f"  Mean: {mean_duration:.2f}ms")
        print(f"  P95:  {p95_duration:.2f}ms")
        print(f"  P99:  {p99_duration:.2f}ms")

        # FR-005: All requests must complete in < 2 seconds
        assert max_duration < 2000, f"Max duration {max_duration:.2f}ms exceeds 2000ms"
        assert p95_duration < 2000, f"P95 duration {p95_duration:.2f}ms exceeds 2000ms"

    def test_classification_performance_various_lengths(self):
        """Test classification performance with different inquiry lengths."""
        test_cases = [
            ("Short", "Как открыть счет?"),  # ~17 characters
            ("Medium", "Как получить кредит на покупку автомобиля в вашем банке?"),  # ~60 characters
            ("Long", "Я хочу открыть депозитный счет на длительный срок, какие условия предлагает ваш банк для физических лиц, какие процентные ставки действуют на текущий момент?" * 3),  # ~450 characters
        ]

        for label, inquiry in test_cases:
            durations = []
            iterations = 5

            for _ in range(iterations):
                start_time = time.time()
                response = client.post("/api/classify", json={"inquiry": inquiry})
                duration_ms = (time.time() - start_time) * 1000
                durations.append(duration_ms)

                assert response.status_code == 200

            avg_duration = statistics.mean(durations)
            print(f"{label} inquiry ({len(inquiry)} chars): {avg_duration:.2f}ms avg")

            assert max(durations) < 2000, f"{label} inquiry exceeded 2000ms"

    def test_classification_concurrent_requests(self):
        """Test classification performance under concurrent load."""
        inquiries = [
            "Как открыть счет в банке?",
            "Забыл пароль от мобильного приложения",
            "Хочу получить кредит на покупку квартиры",
            "Почему не работает интернет-банкинг?",
            "Как заблокировать карту?",
        ]

        def make_request(inquiry):
            start_time = time.time()
            response = client.post("/api/classify", json={"inquiry": inquiry})
            duration_ms = (time.time() - start_time) * 1000
            return duration_ms, response.status_code

        # Test with 5 concurrent workers
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request, inq) for inq in inquiries]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        durations = [r[0] for r in results]
        statuses = [r[1] for r in results]

        # All should succeed
        assert all(s == 200 for s in statuses), "Some concurrent requests failed"

        # Performance should not degrade significantly
        max_duration = max(durations)
        mean_duration = statistics.mean(durations)

        print(f"\nConcurrent classification (5 parallel):")
        print(f"  Max:  {max_duration:.2f}ms")
        print(f"  Mean: {mean_duration:.2f}ms")

        # Even under concurrent load, should meet <2s requirement
        assert max_duration < 2000, f"Concurrent max {max_duration:.2f}ms exceeds 2000ms"


class TestRetrievalPerformance:
    """Performance benchmarks for retrieval endpoint."""

    def test_retrieval_performance_single_request(self):
        """Test retrieval performance for single request (FR-010: <1s)."""
        # First classify to get category/subcategory
        classify_response = client.post("/api/classify", json={
            "inquiry": "Как узнать баланс карты?"
        })
        assert classify_response.status_code == 200
        classification = classify_response.json()

        request_data = {
            "query": "Как узнать баланс карты?",
            "category": classification["category"],
            "subcategory": classification["subcategory"],
            "top_k": 5
        }

        durations = []
        iterations = 10

        for _ in range(iterations):
            start_time = time.time()
            response = client.post("/api/retrieve", json=request_data)
            duration_ms = (time.time() - start_time) * 1000
            durations.append(duration_ms)

            assert response.status_code == 200

        # Calculate statistics
        min_duration = min(durations)
        max_duration = max(durations)
        mean_duration = statistics.mean(durations)
        p95_duration = calculate_percentile(durations, 95)
        p99_duration = calculate_percentile(durations, 99)

        print(f"\nRetrieval Performance ({iterations} iterations):")
        print(f"  Min:  {min_duration:.2f}ms")
        print(f"  Max:  {max_duration:.2f}ms")
        print(f"  Mean: {mean_duration:.2f}ms")
        print(f"  P95:  {p95_duration:.2f}ms")
        print(f"  P99:  {p99_duration:.2f}ms")

        # FR-010: All requests must complete in < 1 second
        assert max_duration < 1000, f"Max duration {max_duration:.2f}ms exceeds 1000ms"
        assert p95_duration < 1000, f"P95 duration {p95_duration:.2f}ms exceeds 1000ms"

    def test_retrieval_performance_different_top_k(self):
        """Test retrieval performance with different top_k values."""
        # Classify first
        classify_response = client.post("/api/classify", json={
            "inquiry": "Вопрос о кредитах"
        })
        classification = classify_response.json()

        for top_k in [1, 3, 5, 10]:
            request_data = {
                "query": "Вопрос о кредитах",
                "category": classification["category"],
                "subcategory": classification["subcategory"],
                "top_k": top_k
            }

            durations = []
            iterations = 5

            for _ in range(iterations):
                start_time = time.time()
                response = client.post("/api/retrieve", json=request_data)
                duration_ms = (time.time() - start_time) * 1000
                durations.append(duration_ms)

                assert response.status_code == 200

            avg_duration = statistics.mean(durations)
            print(f"top_k={top_k}: {avg_duration:.2f}ms avg")

            assert max(durations) < 1000, f"top_k={top_k} exceeded 1000ms"

    def test_retrieval_concurrent_requests(self):
        """Test retrieval performance under concurrent load."""
        # Classify different inquiries
        inquiries_and_categories = []

        test_inquiries = [
            "Как открыть счет?",
            "Забыл пароль",
            "Нужен кредит",
            "Проблема с картой",
            "Хочу депозит",
        ]

        for inquiry in test_inquiries:
            classify_response = client.post("/api/classify", json={"inquiry": inquiry})
            assert classify_response.status_code == 200
            classification = classify_response.json()
            inquiries_and_categories.append({
                "query": inquiry,
                "category": classification["category"],
                "subcategory": classification["subcategory"],
                "top_k": 5
            })

        def make_request(request_data):
            start_time = time.time()
            response = client.post("/api/retrieve", json=request_data)
            duration_ms = (time.time() - start_time) * 1000
            return duration_ms, response.status_code

        # Test with 5 concurrent workers
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request, req) for req in inquiries_and_categories]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        durations = [r[0] for r in results]
        statuses = [r[1] for r in results]

        # All should succeed
        assert all(s == 200 for s in statuses), "Some concurrent requests failed"

        max_duration = max(durations)
        mean_duration = statistics.mean(durations)

        print(f"\nConcurrent retrieval (5 parallel):")
        print(f"  Max:  {max_duration:.2f}ms")
        print(f"  Mean: {mean_duration:.2f}ms")

        # Even under concurrent load, should meet <1s requirement
        assert max_duration < 1000, f"Concurrent max {max_duration:.2f}ms exceeds 1000ms"


class TestEndToEndWorkflowPerformance:
    """Performance benchmarks for complete User Story 1 workflow."""

    def test_workflow_performance_comprehensive(self):
        """Test complete workflow performance (FR-015: <10s total)."""
        test_inquiries = [
            "Как заблокировать банковскую карту?",
            "Забыл пароль от мобильного приложения",
            "Как получить кредит на покупку автомобиля?",
            "Почему не приходят SMS с кодами?",
            "Как открыть депозит в банке?",
        ]

        all_classify_durations = []
        all_retrieval_durations = []
        all_workflow_durations = []

        for inquiry in test_inquiries:
            workflow_start = time.time()

            # Classify
            classify_start = time.time()
            classify_response = client.post("/api/classify", json={"inquiry": inquiry})
            classify_duration = (time.time() - classify_start) * 1000
            all_classify_durations.append(classify_duration)

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
            all_retrieval_durations.append(retrieval_duration)

            assert retrieval_response.status_code == 200

            workflow_duration = (time.time() - workflow_start) * 1000
            all_workflow_durations.append(workflow_duration)

        # Calculate statistics
        print(f"\nWorkflow Performance ({len(test_inquiries)} workflows):")
        print("\nClassification:")
        print(f"  Min:  {min(all_classify_durations):.2f}ms")
        print(f"  Max:  {max(all_classify_durations):.2f}ms")
        print(f"  Mean: {statistics.mean(all_classify_durations):.2f}ms")

        print("\nRetrieval:")
        print(f"  Min:  {min(all_retrieval_durations):.2f}ms")
        print(f"  Max:  {max(all_retrieval_durations):.2f}ms")
        print(f"  Mean: {statistics.mean(all_retrieval_durations):.2f}ms")

        print("\nTotal Workflow:")
        print(f"  Min:  {min(all_workflow_durations):.2f}ms")
        print(f"  Max:  {max(all_workflow_durations):.2f}ms")
        print(f"  Mean: {statistics.mean(all_workflow_durations):.2f}ms")

        # Validate performance requirements
        assert max(all_classify_durations) < 2000, "Classification exceeded 2s"
        assert max(all_retrieval_durations) < 1000, "Retrieval exceeded 1s"
        assert max(all_workflow_durations) < 10000, "Workflow exceeded 10s"

    def test_workflow_performance_stress(self):
        """Stress test: Run workflow 20 times and validate performance consistency."""
        inquiry = "Как узнать баланс моей карты?"
        iterations = 20

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

        # Calculate comprehensive statistics
        classify_stats = {
            'min': min(classify_durations),
            'max': max(classify_durations),
            'mean': statistics.mean(classify_durations),
            'median': statistics.median(classify_durations),
            'stdev': statistics.stdev(classify_durations) if len(classify_durations) > 1 else 0,
            'p95': calculate_percentile(classify_durations, 95),
        }

        retrieval_stats = {
            'min': min(retrieval_durations),
            'max': max(retrieval_durations),
            'mean': statistics.mean(retrieval_durations),
            'median': statistics.median(retrieval_durations),
            'stdev': statistics.stdev(retrieval_durations) if len(retrieval_durations) > 1 else 0,
            'p95': calculate_percentile(retrieval_durations, 95),
        }

        workflow_stats = {
            'min': min(workflow_durations),
            'max': max(workflow_durations),
            'mean': statistics.mean(workflow_durations),
            'median': statistics.median(workflow_durations),
            'stdev': statistics.stdev(workflow_durations) if len(workflow_durations) > 1 else 0,
            'p95': calculate_percentile(workflow_durations, 95),
        }

        print(f"\nStress Test ({iterations} iterations):")
        print("\nClassification:")
        for key, value in classify_stats.items():
            print(f"  {key.upper():6s}: {value:.2f}ms")

        print("\nRetrieval:")
        for key, value in retrieval_stats.items():
            print(f"  {key.upper():6s}: {value:.2f}ms")

        print("\nTotal Workflow:")
        for key, value in workflow_stats.items():
            print(f"  {key.upper():6s}: {value:.2f}ms")

        # Validate all requirements met
        assert classify_stats['p95'] < 2000, f"Classification P95 {classify_stats['p95']:.2f}ms exceeds 2000ms"
        assert retrieval_stats['p95'] < 1000, f"Retrieval P95 {retrieval_stats['p95']:.2f}ms exceeds 1000ms"
        assert workflow_stats['p95'] < 10000, f"Workflow P95 {workflow_stats['p95']:.2f}ms exceeds 10000ms"

        # Performance should be consistent (stdev < 50% of mean)
        assert classify_stats['stdev'] < classify_stats['mean'] * 0.5, \
            "Classification performance too inconsistent"
        assert retrieval_stats['stdev'] < retrieval_stats['mean'] * 0.5, \
            "Retrieval performance too inconsistent"


class TestPerformanceRequirementsSummary:
    """Summary test validating all performance requirements together."""

    def test_all_performance_requirements(self):
        """Comprehensive test of all performance requirements."""
        inquiry = "Как открыть счет в банке для получения зарплаты?"

        print("\n" + "=" * 70)
        print("PERFORMANCE REQUIREMENTS VALIDATION")
        print("=" * 70)

        # Run workflow multiple times
        iterations = 10
        results = {
            'classify': [],
            'retrieval': [],
            'workflow': []
        }

        for _ in range(iterations):
            workflow_start = time.time()

            # Classify
            classify_start = time.time()
            classify_response = client.post("/api/classify", json={"inquiry": inquiry})
            classify_duration = (time.time() - classify_start) * 1000
            results['classify'].append(classify_duration)

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
            results['retrieval'].append(retrieval_duration)

            assert retrieval_response.status_code == 200

            workflow_duration = (time.time() - workflow_start) * 1000
            results['workflow'].append(workflow_duration)

        # Print summary
        print(f"\nResults ({iterations} iterations):\n")

        for operation, requirement in [
            ('classify', 2000),
            ('retrieval', 1000),
            ('workflow', 10000)
        ]:
            durations = results[operation]
            max_val = max(durations)
            mean_val = statistics.mean(durations)
            p95_val = calculate_percentile(durations, 95)

            status = "✓ PASS" if max_val < requirement else "✗ FAIL"

            print(f"{operation.upper():12s} (requirement: <{requirement}ms)")
            print(f"  Max:  {max_val:7.2f}ms {status}")
            print(f"  Mean: {mean_val:7.2f}ms")
            print(f"  P95:  {p95_val:7.2f}ms")
            print()

            # Assert requirements
            assert max_val < requirement, \
                f"{operation} max {max_val:.2f}ms exceeds requirement {requirement}ms"

        print("=" * 70)
        print("ALL PERFORMANCE REQUIREMENTS MET ✓")
        print("=" * 70)

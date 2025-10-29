#!/usr/bin/env python3
"""
Test Cases for Embedding Update Verification

This script verifies that the embedding update from SentenceTransformer (384 dims)
to Gemini API (768 dims) was successful.

Usage:
    python -m app.test_embedding_update
"""

import os
import sys
from dotenv import load_dotenv
from neo4j import GraphDatabase
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# Load environment variables
load_dotenv()

# Configuration
NEO4J_URI = "neo4j+s://d3db84ff.databases.neo4j.io"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Test results tracking
TESTS_PASSED = 0
TESTS_FAILED = 0
TEST_DETAILS = []


def print_header(text):
    """Print formatted test section header"""
    print("\n" + "=" * 70)
    print(text)
    print("=" * 70)


def print_test_result(test_name, passed, details=""):
    """Print and track test result"""
    global TESTS_PASSED, TESTS_FAILED, TEST_DETAILS

    status = "✓ PASS" if passed else "✗ FAIL"
    print(f"{status}: {test_name}")

    if details:
        print(f"       {details}")

    if passed:
        TESTS_PASSED += 1
    else:
        TESTS_FAILED += 1

    TEST_DETAILS.append({
        "name": test_name,
        "passed": passed,
        "details": details
    })


def test_neo4j_connection():
    """Test 1: Verify Neo4j connection"""
    print_header("TEST 1: Neo4j Connection")

    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        driver.verify_connectivity()
        driver.close()
        print_test_result("Neo4j connection successful", True)
        return True
    except Exception as e:
        print_test_result("Neo4j connection failed", False, str(e))
        return False


def test_embedding_dimensions():
    """Test 2: Verify all embeddings are 768 dimensions"""
    print_header("TEST 2: Embedding Dimensions")

    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

        with driver.session() as session:
            # Check all embeddings
            result = session.run("""
                MATCH (p:Page)
                WHERE p.embedding IS NOT NULL
                WITH p, size(p.embedding) AS dim
                RETURN dim, count(p) AS count
                ORDER BY dim
            """)

            dimension_counts = list(result)

            if not dimension_counts:
                print_test_result("No embeddings found", False, "Database has no pages with embeddings")
                driver.close()
                return False

            # Check if all are 768
            all_768 = all(record["dim"] == 768 for record in dimension_counts)

            if all_768:
                total_pages = sum(record["count"] for record in dimension_counts)
                print_test_result(
                    f"All embeddings are 768 dimensions",
                    True,
                    f"{total_pages} pages verified"
                )
            else:
                details = ", ".join([f"{r['dim']}D: {r['count']} pages" for r in dimension_counts])
                print_test_result(
                    "Embeddings have mixed dimensions",
                    False,
                    details
                )

            driver.close()
            return all_768

    except Exception as e:
        print_test_result("Dimension check failed", False, str(e))
        return False


def test_embedding_model_metadata():
    """Test 3: Verify embedding_model metadata is updated"""
    print_header("TEST 3: Embedding Model Metadata")

    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

        with driver.session() as session:
            result = session.run("""
                MATCH (p:Page)
                WHERE p.embedding IS NOT NULL
                RETURN p.embedding_model AS model, count(p) AS count
            """)

            model_counts = list(result)

            if not model_counts:
                print_test_result("No embedding model metadata found", False)
                driver.close()
                return False

            # Check if any have the new model name
            gemini_count = sum(r["count"] for r in model_counts if r["model"] == "text-embedding-004")
            total_count = sum(r["count"] for r in model_counts)

            if gemini_count == total_count:
                print_test_result(
                    "All pages use Gemini embeddings",
                    True,
                    f"{gemini_count}/{total_count} pages have embedding_model='text-embedding-004'"
                )
                success = True
            elif gemini_count > 0:
                print_test_result(
                    "Partial update detected",
                    False,
                    f"Only {gemini_count}/{total_count} pages updated to Gemini"
                )
                success = False
            else:
                models = ", ".join([f"{r['model']}: {r['count']}" for r in model_counts])
                print_test_result(
                    "No Gemini embeddings found",
                    False,
                    f"Current models: {models}"
                )
                success = False

            driver.close()
            return success

    except Exception as e:
        print_test_result("Metadata check failed", False, str(e))
        return False


def test_vector_index_exists():
    """Test 4: Verify vector index exists with correct dimensions"""
    print_header("TEST 4: Vector Index Configuration")

    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

        with driver.session() as session:
            # Check for vector index
            result = session.run("""
                SHOW INDEXES
                YIELD name, type, labelsOrTypes, properties, options
                WHERE type = 'VECTOR'
                RETURN name, labelsOrTypes, properties, options
            """)

            indexes = list(result)

            if not indexes:
                print_test_result("No vector index found", False, "Vector index needs to be created")
                driver.close()
                return False

            # Find page_embeddings index
            page_index = next((idx for idx in indexes if idx["name"] == "page_embeddings"), None)

            if not page_index:
                print_test_result("page_embeddings index not found", False, "Found: " + str([i["name"] for i in indexes]))
                driver.close()
                return False

            # Check dimensions in options
            options = page_index.get("options", {})
            index_config = options.get("indexConfig", {})
            dimensions = index_config.get("vector.dimensions")

            if dimensions == 768:
                print_test_result(
                    "Vector index configured correctly",
                    True,
                    "page_embeddings index has 768 dimensions"
                )
                success = True
            else:
                print_test_result(
                    "Vector index has wrong dimensions",
                    False,
                    f"Expected 768, got {dimensions}"
                )
                success = False

            driver.close()
            return success

    except Exception as e:
        print_test_result("Vector index check failed", False, str(e))
        return False


def test_vector_search_functionality():
    """Test 5: Verify vector search returns results"""
    print_header("TEST 5: Vector Search Functionality")

    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

        # Initialize embedder
        embedder = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004",
            google_api_key=GEMINI_API_KEY
        )

        # Generate test query embedding
        test_query = "How do I install a lock?"
        query_embedding = embedder.embed_query(test_query)

        if len(query_embedding) != 768:
            print_test_result(
                "Query embedding has wrong dimensions",
                False,
                f"Expected 768, got {len(query_embedding)}"
            )
            driver.close()
            return False

        # Perform vector search
        with driver.session() as session:
            result = session.run("""
                MATCH (p:Page)
                WHERE p.embedding IS NOT NULL
                WITH p,
                     reduce(d=0.0, i IN range(0, size(p.embedding)-1) |
                         d + p.embedding[i] * $emb[i]) AS dot,
                     sqrt(reduce(s=0.0, i IN range(0, size(p.embedding)-1) |
                         s + p.embedding[i]^2)) AS p_norm,
                     sqrt(reduce(s=0.0, i IN range(0, size($emb)-1) |
                         s + $emb[i]^2)) AS q_norm
                WITH p, dot/(p_norm * q_norm) AS similarity
                WHERE similarity > 0.3
                RETURN p.slug AS slug, p.title AS title, similarity
                ORDER BY similarity DESC
                LIMIT 5
            """, emb=query_embedding)

            search_results = list(result)

            if len(search_results) > 0:
                top_result = search_results[0]
                print_test_result(
                    "Vector search returns results",
                    True,
                    f"Found {len(search_results)} matches. Top: '{top_result['title']}' (sim: {top_result['similarity']:.3f})"
                )
                success = True
            else:
                print_test_result(
                    "Vector search returns no results",
                    False,
                    "Expected at least 1 result with similarity > 0.3"
                )
                success = False

            driver.close()
            return success

    except Exception as e:
        print_test_result("Vector search test failed", False, str(e))
        return False


def test_sample_pages_detail():
    """Test 6: Detailed check of sample pages"""
    print_header("TEST 6: Sample Page Verification")

    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

        with driver.session() as session:
            result = session.run("""
                MATCH (p:Page)
                WHERE p.embedding IS NOT NULL
                RETURN p.slug AS slug,
                       p.title AS title,
                       size(p.embedding) AS dim,
                       p.embedding_model AS model,
                       p.embedding_dimension AS stored_dim
                LIMIT 5
            """)

            pages = list(result)

            if not pages:
                print_test_result("No sample pages found", False)
                driver.close()
                return False

            all_valid = True
            print(f"\nSample of {len(pages)} pages:\n")

            for i, page in enumerate(pages, 1):
                is_valid = (
                    page["dim"] == 768 and
                    page["model"] == "text-embedding-004" and
                    page["stored_dim"] == 768
                )

                status = "✓" if is_valid else "✗"
                print(f"  {status} {page['slug']}")
                print(f"       Title: {page['title'][:50]}...")
                print(f"       Embedding: {page['dim']}D, Model: {page['model']}, Stored: {page['stored_dim']}D")

                if not is_valid:
                    all_valid = False

            print()
            print_test_result(
                "All sample pages valid",
                all_valid,
                f"Checked {len(pages)} pages"
            )

            driver.close()
            return all_valid

    except Exception as e:
        print_test_result("Sample page check failed", False, str(e))
        return False


def print_summary():
    """Print test summary"""
    print_header("TEST SUMMARY")

    total_tests = TESTS_PASSED + TESTS_FAILED
    pass_rate = (TESTS_PASSED / total_tests * 100) if total_tests > 0 else 0

    print(f"\nTotal Tests: {total_tests}")
    print(f"Passed: {TESTS_PASSED} ({pass_rate:.1f}%)")
    print(f"Failed: {TESTS_FAILED}")

    if TESTS_FAILED > 0:
        print("\n⚠ FAILURES:")
        for test in TEST_DETAILS:
            if not test["passed"]:
                print(f"  - {test['name']}")
                if test["details"]:
                    print(f"    {test['details']}")

    print("\n" + "=" * 70)

    if TESTS_FAILED == 0:
        print("✓ ALL TESTS PASSED - Embedding update successful!")
    else:
        print(f"✗ {TESTS_FAILED} TEST(S) FAILED - Check details above")

    print("=" * 70 + "\n")

    return TESTS_FAILED == 0


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("Embedding Update Verification Test Suite")
    print("=" * 70)

    # Run all tests
    test_neo4j_connection()
    test_embedding_dimensions()
    test_embedding_model_metadata()
    test_vector_index_exists()
    test_vector_search_functionality()
    test_sample_pages_detail()

    # Print summary
    all_passed = print_summary()

    # Exit with appropriate code
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()

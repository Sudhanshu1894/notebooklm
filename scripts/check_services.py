"""
Service Connectivity Verification Script for GraphRAG Research Notebook.

Checks reachability and authentication for:
1. Gemini API (Google AI Studio Free Tier)
2. Neo4j AuraDB Free Graph Store
3. ChromaDB Local Embedded Vector Store
4. Supabase Free Tier Backend
"""

import sys
import os
import shutil

# Ensure parent directory is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config.settings import get_settings


def check_gemini(settings) -> bool:
    """Verifies Gemini API connectivity with a trivial prompt."""
    print("Checking Gemini API...", end=" ", flush=True)
    if not settings.gemini_api_key:
        print("[SKIP/FAIL] GEMINI_API_KEY not configured in .env")
        return False

    try:
        from google import genai
        client = genai.Client(api_key=settings.gemini_api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Say 'OK' if you can read this."
        )
        if response and response.text:
            print(f"[PASS] Response received: '{response.text.strip()}'")
            return True
        else:
            print("[FAIL] Empty response from Gemini API")
            return False
    except Exception as e:
        print(f"[FAIL] Error: {e}")
        return False


def check_neo4j(settings) -> bool:
    """Verifies Neo4j AuraDB connectivity with a simple RETURN 1 query."""
    print("Checking Neo4j AuraDB...", end=" ", flush=True)
    if not settings.neo4j_uri or not settings.neo4j_password:
        print("[SKIP/FAIL] NEO4J_URI or NEO4J_PASSWORD not configured in .env")
        return False

    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )
        with driver.session() as session:
            result = session.run("RETURN 1 AS test_val")
            record = result.single()
            if record and record["test_val"] == 1:
                print("[PASS] Neo4j AuraDB connection successful ('RETURN 1')")
                driver.close()
                return True
            else:
                print("[FAIL] Neo4j returned unexpected result")
                driver.close()
                return False
    except Exception as e:
        print(f"[FAIL] Error: {e}")
        return False


def check_chromadb(settings) -> bool:
    """Verifies local ChromaDB initialization, collection creation, dummy insert, query, and cleanup."""
    print("Checking Local ChromaDB...", end=" ", flush=True)
    test_dir = "./data/chroma_test_temp"
    try:
        import chromadb
        client = chromadb.PersistentClient(path=test_dir)
        collection = client.get_or_create_collection("test_connectivity")
        
        # Insert test item with dummy vector (384 dims)
        dummy_vector = [0.1] * 384
        collection.add(
            ids=["test_1"],
            embeddings=[dummy_vector],
            documents=["This is a test document for ChromaDB."],
            metadatas=[{"source": "connectivity_test"}]
        )

        # Query test item
        results = collection.query(
            query_embeddings=[dummy_vector],
            n_results=1
        )

        if results and results["ids"] and results["ids"][0][0] == "test_1":
            client.delete_collection("test_connectivity")
            print("[PASS] ChromaDB collection create, insert, query, and cleanup successful")
            # Cleanup temp directory
            if os.path.exists(test_dir):
                shutil.rmtree(test_dir, ignore_errors=True)
            return True
        else:
            print("[FAIL] ChromaDB query failed to retrieve test record")
            return False
    except Exception as e:
        print(f"[FAIL] Error: {e}")
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir, ignore_errors=True)
        return False


def check_supabase(settings) -> bool:
    """Verifies Supabase REST endpoint authentication."""
    print("Checking Supabase...", end=" ", flush=True)
    if not settings.supabase_url or not settings.supabase_key:
        print("[SKIP/FAIL] SUPABASE_URL or SUPABASE_KEY not configured in .env")
        return False

    try:
        import requests
        # Simple ping to Supabase REST health or root endpoint
        endpoint = f"{settings.supabase_url.rstrip('/')}/rest/v1/"
        headers = {
            "apikey": settings.supabase_key,
            "Authorization": f"Bearer {settings.supabase_key}"
        }
        res = requests.get(endpoint, headers=headers, timeout=5)
        if res.status_code in (200, 404):  # REST root returns 200 or swagger OpenAPI
            print(f"[PASS] Supabase client authenticated successfully (HTTP {res.status_code})")
            return True
        else:
            print(f"[FAIL] Supabase returned status code: {res.status_code}")
            return False
    except Exception as e:
        print(f"[FAIL] Error: {e}")
        return False


def main():
    print("=" * 65)
    print("        GRAPHRAG SERVICE CONNECTIVITY VERIFICATION        ")
    print("=" * 65)

    settings = get_settings()
    results = {
        "Gemini API": check_gemini(settings),
        "Neo4j AuraDB": check_neo4j(settings),
        "ChromaDB": check_chromadb(settings),
        "Supabase": check_supabase(settings),
    }

    print("-" * 65)
    print("CONNECTIVITY SUMMARY:")
    passed_count = sum(1 for v in results.values() if v)
    total_count = len(results)

    for service, status in results.items():
        symbol = "[PASS]" if status else "[FAIL/SKIP]"
        print(f"  - {service:<20}: {symbol}")

    print("-" * 65)
    print(f"Passed {passed_count}/{total_count} service connectivity checks.")
    print("=" * 65)

    if passed_count == total_count:
        print("\nAll free-tier external services are fully operational!")
        sys.exit(0)
    else:
        print("\nSome services failed or missing credentials. Please update .env before running pipeline.")
        sys.exit(1)


if __name__ == "__main__":
    main()

import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Load environment variables from .env file
load_dotenv()

# Neo4j Configuration - use the same as in your builder script
NEO4J_URI = "neo4j+s://d3db84ff.databases.neo4j.io" # This is a placeholder, replace with your actual AuraDB URI
NEO4J_USER = "neo4j" # For AuraDB, the default user is typically 'neo4j'
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD") # Loaded from .env

def test_connection():
    driver = None
    try:
        print(f"Attempting to connect to Neo4j at {NEO4J_URI}...")
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        driver.verify_connectivity()
        print("Connection successful!")

        with driver.session() as session:
            # Test 1: Count all nodes
            result = session.run("MATCH (n) RETURN count(n) AS node_count")
            node_count = result.single()["node_count"]
            print(f"Total nodes in the database: {node_count}")

            # Test 2: Count specific label (e.g., Page nodes)
            result = session.run("MATCH (p:Page) RETURN count(p) AS page_count")
            page_count = result.single()["page_count"]
            print(f"Total Page nodes: {page_count}")
            
            # Test 3: Count relationships (e.g., BELONGS_TO_CATEGORY)
            result = session.run("MATCH ()-[r:BELONGS_TO_CATEGORY]->() RETURN count(r) AS rel_count")
            rel_count = result.single()["rel_count"]
            print(f"Total BELONGS_TO_CATEGORY relationships: {rel_count}")

            if node_count > 0 and page_count > 0:
                print("\nSuccess! Data appears to be present in your AuraDB instance.")
            else:
                print("\nWarning: No data or Page nodes found. The import might not have worked as expected.")

    except Exception as e:
        print(f"\nError connecting to Neo4j or running queries: {e}")
        print("Please check your NEO4J_URI, username, password, and ensure your AuraDB instance is running.")
    finally:
        if driver:
            driver.close()
            print("Connection closed.")

if __name__ == "__main__":
    test_connection()












# import os
# import google.generativeai as genai
# from dotenv import load_dotenv
# load_dotenv()

# genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# model = genai.GenerativeModel("models/gemini-2.5-flash")

# response = model.generate_content("Say hello in 3 different ways.")
# print(response.text)





# from neo4j import GraphDatabase

# driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "123456789"))

# with driver.session() as session:
#     result = session.run("RETURN 'Hello Neo4j' AS msg")
#     for record in result:
#         print(record["msg"])

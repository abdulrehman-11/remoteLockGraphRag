import os
import textwrap
from dotenv import load_dotenv

from langchain_neo4j import Neo4jGraph
from langchain.prompts.prompt import PromptTemplate
from langchain.chains import GraphCypherQAChain
from langchain_google_genai import ChatGoogleGenerativeAI

# Load environment variables (for NEO4J & GEMINI/OpenAI keys)
load_dotenv()

# -----------------------------
# 1. Setup Neo4j connection
# -----------------------------
graph = Neo4jGraph(
    uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
    username=os.getenv("NEO4J_USER", "neo4j"),
    password=os.getenv("NEO4J_PASSWORD", "123456789"),
)

# -----------------------------
# 2. System Prompt for Cypher generation
# -----------------------------
SYSTEM_PROMPT = """
You are a Cypher query generator for a Neo4j knowledge graph. 
Your ONLY job is to translate natural language into Cypher queries.

The knowledge graph schema:
- (Category)-[:HAS_PAGE]->(Page)
- (Page)-[:BELONGS_TO]->(Category)
- (Page)-[:RELATED_TO]-(Page) {similarity: Float}
- (Page)-[:HAS_KEYWORD]->(Keyword)

Node properties:
- Category {name}
- Page {title, url, content_text, vector}
- Keyword {name}

Rules:
1. ALWAYS return valid Cypher queries only (no explanations, no markdown).
2. Use CONTAINS for fuzzy string matching on Page.title and Page.content_text.
3. Prefer navigation via relationships (HAS_PAGE, RELATED_TO, HAS_KEYWORD).
4. Always RETURN p.title, p.url, p.content_text for Page results.
5. Limit results to 5 unless the user explicitly asks for more.
6. If a Category is mentioned, use (Category)-[:HAS_PAGE]->(Page).
7. Never hallucinate properties — only use the ones listed above.
"""

cypher_prompt = PromptTemplate(
    input_variables=["schema", "question"],
    template=SYSTEM_PROMPT + "\nSchema:\n{schema}\n\nUser: {question}\nCypher:"
)

# -----------------------------
# 3. Setup GraphCypherQAChain
# -----------------------------
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0
)

cypher_chain = GraphCypherQAChain.from_llm(
    llm=llm,
    graph=graph,
    verbose=True,
    cypher_prompt=cypher_prompt,
    allow_dangerous_requests=True  # required for schema exploration
)

# -----------------------------
# 4. Helper function
# -----------------------------
def generate_cypher_query(question: str) -> str:
    """
    Generates a Cypher query from a natural language question using GraphCypherQAChain.
    """
    response = cypher_chain.run(question)
    return textwrap.fill(response, 60)


# -----------------------------
# 5. Run interactively
# -----------------------------
if __name__ == "__main__":
    print("✅ Connected to Neo4j! You can now ask questions.")
    while True:
        q = input("\n🔎 Ask a question (or type 'exit'): ")
        if q.lower() == "exit":
            break
        try:
            cypher = generate_cypher_query(q)
            print("\n📝 Generated Cypher:\n", cypher)
        except Exception as e:
            print("❌ Error generating query:", e)


from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from neo4j import GraphDatabase
import numpy as np

app = FastAPI()

# ---- Neo4j connection ----
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "your_password"

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

# ---- Embedding Model ----
MODEL_NAME = "all-MiniLM-L6-v2"
model = SentenceTransformer(MODEL_NAME)

# ---- Request Schema ----
class SearchRequest(BaseModel):
    query: str
    top_k: int = 5

# ---- Search Endpoint ----
@app.post("/search")
async def search(req: SearchRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        # Generate query embedding
        query_vec = model.encode(req.query, normalize_embeddings=True).tolist()

        with driver.session() as session:
            result = session.run(
                """
                MATCH (p:Page)
                WHERE p.vector IS NOT NULL
                WITH p,
                gds.similarity.cosine(p.vector, $query_vec) AS score
                ORDER BY score DESC LIMIT $top_k
                RETURN p.title AS title, p.url AS url, p.category AS category,
                       score, substring(p.content_text, 0, 200) + "..." AS snippet
                """,
                {"query_vec": query_vec, "top_k": req.top_k},
            )

            records = [
                {
                    "title": r["title"],
                    "url": r["url"],
                    "category": r["category"],
                    "score": float(r["score"]),
                    "snippet": r["snippet"],
                }
                for r in result
            ]

        return {"results": records}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")



















# #import neo4j

# from fastapi import FastAPI, Query
# from pydantic import BaseModel
# from typing import List
# from neo4j import GraphDatabase
# from sentence_transformers import SentenceTransformer
# import uvicorn

# # -------- Neo4j connection --------
# NEO4J_URI = "bolt://localhost:7687"
# NEO4J_USER = "neo4j"
# NEO4J_PASS = "password"

# driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))

# # -------- Embedding model --------
# MODEL_NAME = "all-MiniLM-L6-v2"  # 384-dim, matches your preprocessing
# model = SentenceTransformer(MODEL_NAME)

# def get_embedding(text: str):
#     """Generate embedding using sentence-transformers"""
#     return model.encode(text, normalize_embeddings=True).tolist()

# # -------- FastAPI app --------
# app = FastAPI(title="Vector Search API", version="1.0")

# class SearchResult(BaseModel):
#     url: str
#     title: str
#     category: str
#     score: float
#     snippet: str

# @app.get("/search", response_model=List[SearchResult])
# async def vector_search(query: str = Query(..., description="Search query text"), top_k: int = 5):
#     query_vec = get_embedding(query)

#     with driver.session() as session:
#         results = session.run(
#             """
#             MATCH (a:Article)
#             WHERE a.vector IS NOT NULL
#             WITH a, gds.similarity.cosine(a.vector, $query_vec) AS score
#             RETURN a.url AS url, a.title AS title, a.category AS category, a.content_text AS content, score
#             ORDER BY score DESC LIMIT $top_k
#             """,
#             query_vec=query_vec,
#             top_k=top_k
#         )

#         output = []
#         for rec in results:
#             snippet = (rec["content"][:200] + "...") if rec["content"] else ""
#             output.append({
#                 "url": rec["url"],
#                 "title": rec["title"],
#                 "category": rec["category"],
#                 "score": float(rec["score"]),
#                 "snippet": snippet,
#             })

#     return output

# if __name__ == "__main__":
#     uvicorn.run("search_api:app", host="0.0.0.0", port=8000, reload=True)

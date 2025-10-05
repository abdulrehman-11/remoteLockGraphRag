# import os
# import json
# from neo4j import GraphDatabase
# import google.generativeai as genai
# from dotenv import load_dotenv

# load_dotenv()

# # Configuration
# NEO4J_URI = "bolt://localhost:7687"
# NEO4J_USER = "neo4j"
# NEO4J_PASSWORD = "123456789"

# driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
# genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# class SimpleKnowledgeRetriever:
#     def __init__(self):
#         self.driver = driver
#         self.model = genai.GenerativeModel("gemini-2.5-flash")
#         self.schema = self.get_schema()
#         self.system_prompt = self.build_prompt()
    
#     def get_schema(self):
#         """Get basic schema information."""
#         try:
#             with self.driver.session() as session:
#                 # Get sample categories
#                 result = session.run("MATCH (c:Category) RETURN c.name LIMIT 10")
#                 categories = [r["c.name"] for r in result]
                
#                 return {
#                     "categories": categories,
#                     "nodes": ["Category", "Page", "Keyword"],
#                     "relationships": ["HAS_PAGE", "BELONGS_TO", "RELATED_TO", "HAS_KEYWORD"]
#                 }
#         except:
#             return {
#                 "categories": ["General", "WiFi Connectivity Troubleshooting", "Legacy Product Troubleshooting"],
#                 "nodes": ["Category", "Page", "Keyword"],
#                 "relationships": ["HAS_PAGE", "BELONGS_TO", "RELATED_TO", "HAS_KEYWORD"]
#             }
    
#     def build_prompt(self):
#         """Build simple system prompt."""
#         categories_list = ", ".join(self.schema["categories"])
        
#         return f"""Task: Generate Cypher statement to query a troubleshooting knowledge graph.

# Schema:
# - Nodes: Category, Page, Keyword
# - Relationships: (Category)-[:HAS_PAGE]->(Page), (Page)-[:BELONGS_TO]->(Category), (Page)-[:RELATED_TO]-(Page), (Page)-[:HAS_KEYWORD]->(Keyword)
# - Available Categories: {categories_list}

# Page Properties:
# - url: string
# - title: string (EMPTY - don't use)
# - content_text: string (main content)
# - source: string
# - extracted_at: number

# Instructions:
# - Use only the provided relationships and properties
# - Page.title is EMPTY - extract title from URL using split(p.url, '/')[-1]
# - Search content using content_text field
# - Use toLower() and CONTAINS for text matching
# - Always return: title (extracted from URL), url, category, preview
# - Limit results to 5
# - No explanations, only Cypher code

# Examples:

# Question: WiFi connectivity issues
# MATCH (c:Category)-[:HAS_PAGE]->(p:Page)
# WHERE toLower(c.name) CONTAINS 'wifi' OR toLower(p.content_text) CONTAINS 'wifi'
# RETURN split(p.url, '/')[-1] as title, p.url, c.name as category, substring(p.content_text, 0, 200) as preview
# LIMIT 5

# Question: Lock not working
# MATCH (c:Category)-[:HAS_PAGE]->(p:Page)
# WHERE toLower(p.content_text) CONTAINS 'lock'
# RETURN split(p.url, '/')[-1] as title, p.url, c.name as category, substring(p.content_text, 0, 200) as preview
# LIMIT 5

# Question: Battery problems
# MATCH (c:Category)-[:HAS_PAGE]->(p:Page)
# WHERE toLower(p.content_text) CONTAINS 'battery'
# RETURN split(p.url, '/')[-1] as title, p.url, c.name as category, substring(p.content_text, 0, 200) as preview
# LIMIT 5

# The question is: {{question}}"""
    
#     def generate_query(self, question):
#         """Generate Cypher query."""
#         try:
#             prompt = self.system_prompt.replace("{{question}}", question)
#             response = self.model.generate_content(prompt)
#             query = response.text.strip()
            
#             # Clean query
#             query = query.replace("```cypher", "").replace("```", "").strip()
#             return query
            
#         except Exception as e:
#             print(f"Query generation failed: {e}")
#             return self.fallback_query(question)
    
#     def fallback_query(self, question):
#         """Simple fallback query."""
#         words = question.lower().split()[:3]
#         conditions = " OR ".join([f"toLower(p.content_text) CONTAINS '{w}'" for w in words if len(w) > 2])
        
#         return f"""
#         MATCH (c:Category)-[:HAS_PAGE]->(p:Page)
#         WHERE {conditions}
#         RETURN split(p.url, '/')[-1] as title, p.url, c.name as category, substring(p.content_text, 0, 200) as preview
#         LIMIT 5
#         """
    
#     def search(self, question):
#         """Search knowledge graph."""
#         print(f"🔍 Searching: {question}")
        
#         try:
#             # Generate query
#             query = self.generate_query(question)
#             print(f"📝 Query: {query[:100]}...")
            
#             # Execute query
#             with self.driver.session() as session:
#                 result = session.run(query)
#                 results = []
#                 for record in result:
#                     results.append({
#                         "title": record.get("title", "").replace("-", " ").title(),
#                         "url": record.get("url", ""),
#                         "category": record.get("category", ""),
#                         "preview": record.get("preview", "")
#                     })
            
#             print(f"✅ Found {len(results)} results")
#             return results
            
#         except Exception as e:
#             print(f"❌ Search failed: {e}")
#             return []

# def main():
#     """Main function."""
#     print("🚀 Simple Knowledge Graph Retriever")
#     print("=" * 40)
    
#     retriever = SimpleKnowledgeRetriever()
    
#     # Show basic info
#     print(f"📊 Categories: {len(retriever.schema['categories'])}")
#     print(f"📁 Available: {', '.join(retriever.schema['categories'][:5])}")
    
#     # Interactive search
#     print("\n💬 Ask questions (type 'exit' to quit):")
    
#     while True:
#         question = input("\n🔎 Question: ").strip()
        
#         if question.lower() in ['exit', 'quit', 'q']:
#             break
        
#         if not question:
#             continue
        
#         results = retriever.search(question)
        
#         if results:
#             print(f"\n📋 Results:")
#             print("-" * 50)
            
#             for i, r in enumerate(results, 1):
#                 print(f"{i}. {r['title']}")
#                 print(f"   Category: {r['category']}")
#                 print(f"   URL: {r['url']}")
#                 print(f"   Preview: {r['preview'][:150]}...")
#                 print()
#         else:
#             print("❌ No results found.")

# if __name__ == "__main__":
#     main()





























# import os
# import json
# from neo4j import GraphDatabase
# import google.generativeai as genai
# from dotenv import load_dotenv
# from typing import List, Dict, Any
# import re

# load_dotenv()

# # Configuration
# NEO4J_URI = "bolt://localhost:7687"
# NEO4J_USER = "neo4j"
# NEO4J_PASSWORD = "123456789"

# driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
# genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# class KnowledgeGraphRetriever:
#     """Knowledge Graph Retriever for your exact schema structure."""
    
#     def __init__(self):
#         self.driver = driver
#         self.model = genai.GenerativeModel("gemini-2.5-flash")
#         self.schema_info = self._analyze_current_schema()
#         self.system_prompt = self._build_expert_system_prompt()
    
#     def _analyze_current_schema(self) -> Dict[str, Any]:
#         """Analyze the current knowledge graph to understand available data."""
#         schema = {
#             "categories": [],
#             "sample_titles": [],
#             "sample_keywords": [],
#             "total_pages": 0,
#             "total_relationships": 0,
#             "has_vectors": False,
#             "content_types": []
#         }
        
#         try:
#             with self.driver.session() as session:
#                 # Get categories
#                 result = session.run("MATCH (c:Category) RETURN c.name as name ORDER BY c.name")
#                 schema["categories"] = [record["name"] for record in result]
                
#                 # Get sample page titles (extracted from URLs since title field is empty)
#                 result = session.run("""
#                     MATCH (p:Page) 
#                     WHERE p.url IS NOT NULL 
#                     RETURN split(p.url, '/')[-1] as url_part 
#                     LIMIT 10
#                 """)
#                 schema["sample_titles"] = [
#                     record["url_part"].replace('-', ' ').title() 
#                     for record in result
#                 ]
                
#                 # Get sample keywords
#                 result = session.run("MATCH (k:Keyword) RETURN k.name LIMIT 20")
#                 schema["sample_keywords"] = [record["k.name"] for record in result]
                
#                 # Count pages
#                 result = session.run("MATCH (p:Page) RETURN count(p) as count")
#                 schema["total_pages"] = result.single()["count"]
                
#                 # Count relationships
#                 result = session.run("MATCH ()-[r:RELATED_TO]->() RETURN count(r) as count")
#                 schema["total_relationships"] = result.single()["count"]
                
#                 # Check if vectors exist
#                 result = session.run("MATCH (p:Page) WHERE p.vector IS NOT NULL RETURN count(p) as count")
#                 schema["has_vectors"] = result.single()["count"] > 0
                
#                 # Check content types available
#                 result = session.run("""
#                     MATCH (p:Page) 
#                     RETURN 
#                         count(CASE WHEN p.content_text IS NOT NULL AND p.content_text <> '' THEN 1 END) as text_count,
#                         count(CASE WHEN p.content_html IS NOT NULL AND p.content_html <> '' THEN 1 END) as html_count,
#                         count(CASE WHEN p.content_markdown IS NOT NULL AND p.content_markdown <> '' THEN 1 END) as markdown_count
#                 """)
#                 record = result.single()
#                 if record["text_count"] > 0:
#                     schema["content_types"].append("content_text")
#                 if record["html_count"] > 0:
#                     schema["content_types"].append("content_html")
#                 if record["markdown_count"] > 0:
#                     schema["content_types"].append("content_markdown")
                
#         except Exception as e:
#             print(f"⚠️ Schema analysis failed: {e}")
        
#         return schema
    
#     def _build_expert_system_prompt(self) -> str:
#         """Build a comprehensive system prompt based on the exact schema."""
        
#         categories = ", ".join(self.schema_info["categories"])
#         sample_keywords = ", ".join(self.schema_info["sample_keywords"][:15])
#         content_fields = ", ".join(self.schema_info["content_types"])
        
#         return f"""You are an expert Cypher query generator for a RemoteLock troubleshooting knowledge graph.
# Your job is to create precise, efficient Cypher queries that retrieve the most relevant information.

# EXACT DATABASE SCHEMA:
# Nodes:
# - Category {{name: string}} - Available categories: {categories}
# - Page {{url: string, title: string (EMPTY), content_text: string, content_html: string, content_markdown: string, source: string, extracted_at: int, vector: array}}
# - Keyword {{name: string}} - Available keywords include: {sample_keywords}

# Relationships:
# - (Category)-[:HAS_PAGE]->(Page) - Category contains pages
# - (Page)-[:BELONGS_TO]->(Category) - Page belongs to category  
# - (Page)-[:RELATED_TO]-(Page) {{similarity: float}} - Semantically similar pages
# - (Page)-[:HAS_KEYWORD]->(Keyword) - Page contains keyword

# IMPORTANT SCHEMA FACTS:
# - Page.title field is EMPTY for all records - DO NOT use it
# - Use URL parsing to extract readable titles: split(p.url, '/')[-1]
# - Primary content is in: {content_fields}
# - Vector embeddings available: {self.schema_info["has_vectors"]}
# - Total pages: {self.schema_info["total_pages"]}
# - Similarity relationships: {self.schema_info["total_relationships"]}
# - Keywords count: {self.schema_info["total_keywords"]} (may be 0 if not created)

# CRITICAL QUERY RULES:
# 1. NEVER use p.title - it's empty. Extract title from URL instead
# 2. Search content using content_text (primary field)
# 3. Use case-insensitive matching with toLower() and CONTAINS  
# 4. Always limit results (default: 5, max: 10)
# 5. Return: extracted title, url, category, content preview
# 6. NEVER use length() function on text fields - causes errors
# 7. Use simple ordering: ORDER BY p.extracted_at DESC or no complex ordering
# 8. If Keywords count is 0, avoid keyword-based searches

# SAFE QUERY PATTERNS (NO length() FUNCTION):

# Basic Content Search (PREFERRED):
# ```cypher
# MATCH (c:Category)-[:HAS_PAGE]->(p:Page)
# WHERE toLower(p.content_text) CONTAINS toLower('search_keyword')
# RETURN 
#     replace(split(p.url, '/')[-1], '-', ' ') as title,
#     p.url,
#     c.name as category,
#     substring(p.content_text, 0, 300) + '...' as preview
# ORDER BY p.extracted_at DESC
# LIMIT 5
# ```

# Multi-Keyword Search:
# ```cypher
# MATCH (c:Category)-[:HAS_PAGE]->(p:Page)
# WHERE toLower(p.content_text) CONTAINS toLower('keyword1')
#   AND toLower(p.content_text) CONTAINS toLower('keyword2')
# RETURN 
#     replace(split(p.url, '/')[-1], '-', ' ') as title,
#     p.url,
#     c.name as category,
#     substring(p.content_text, 0, 300) + '...' as preview
# ORDER BY p.extracted_at DESC
# LIMIT 5
# ```

# Category-Specific Search:
# ```cypher
# MATCH (c:Category)-[:HAS_PAGE]->(p:Page)
# WHERE toLower(c.name) CONTAINS toLower('category_keyword')
#   AND toLower(p.content_text) CONTAINS toLower('search_keyword')
# RETURN 
#     replace(split(p.url, '/')[-1], '-', ' ') as title,
#     p.url,
#     c.name as category,
#     substring(p.content_text, 0, 300) + '...' as preview
# ORDER BY p.extracted_at DESC
# LIMIT 5
# ```

# Similarity-Based Search:
# ```cypher
# MATCH (p1:Page)-[r:RELATED_TO]-(p2:Page)
# WHERE toLower(p1.content_text) CONTAINS toLower('search_keyword')
# MATCH (p1)-[:BELONGS_TO]->(c1:Category)
# RETURN 
#     replace(split(p1.url, '/')[-1], '-', ' ') as title,
#     p1.url,
#     c1.name as category,
#     substring(p1.content_text, 0, 200) + '...' as preview,
#     r.similarity
# ORDER BY r.similarity DESC
# LIMIT 5
# ```

# Simple OR Search:
# ```cypher
# MATCH (c:Category)-[:HAS_PAGE]->(p:Page)
# WHERE toLower(p.content_text) CONTAINS toLower('keyword1')
#    OR toLower(p.content_text) CONTAINS toLower('keyword2')
# RETURN 
#     replace(split(p.url, '/')[-1], '-', ' ') as title,
#     p.url,
#     c.name as category,
#     substring(p.content_text, 0, 300) + '...' as preview
# ORDER BY p.extracted_at DESC
# LIMIT 5
# ```

# CRITICAL INSTRUCTIONS:
# - NEVER use length() function - it causes type errors
# - NEVER reference p.title (it's empty)
# - ALWAYS extract title using: replace(split(p.url, '/')[-1], '-', ' ')
# - Use content_text for all text searching
# - Use simple ordering: ORDER BY p.extracted_at DESC
# - Avoid keyword-based searches if keyword count is 0
# - Use proper text matching with toLower() and CONTAINS
# - Return consistent field names: title, url, category, preview
# - Keep queries simple and avoid complex aggregations

# Generate ONLY the Cypher query. No explanations, no markdown formatting, just pure Cypher code."""

#     def generate_cypher_query(self, user_question: str) -> str:
#         """Generate optimized Cypher query for user question."""
#         try:
#             prompt = f"{self.system_prompt}\n\nUser Question: {user_question}\n\nCypher Query:"
            
#             response = self.model.generate_content(prompt)
#             query = response.text.strip()
            
#             # Clean the response
#             query = re.sub(r'```cypher\s*', '', query, flags=re.IGNORECASE)
#             query = re.sub(r'```\s*', '', query)
#             query = re.sub(r'^cypher\s*', '', query, flags=re.IGNORECASE)
#             query = query.strip()
            
#             return query
            
#         except Exception as e:
#             print(f"❌ Query generation failed: {e}")
#             return self._create_fallback_query(user_question)
    
#     def _create_fallback_query(self, user_question: str) -> str:
#         """Create a reliable fallback query."""
#         words = [word.strip() for word in user_question.lower().split() if len(word.strip()) > 2][:3]
        
#         if not words:
#             return """
#             MATCH (c:Category)-[:HAS_PAGE]->(p:Page)
#             RETURN 
#                 replace(split(p.url, '/')[-1], '-', ' ') as title,
#                 p.url,
#                 c.name as category,
#                 substring(p.content_text, 0, 300) + '...' as preview
#             ORDER BY p.extracted_at DESC
#             LIMIT 5
#             """
        
#         conditions = " OR ".join([f"toLower(p.content_text) CONTAINS '{word}'" for word in words])
        
#         return f"""
#         MATCH (c:Category)-[:HAS_PAGE]->(p:Page)
#         WHERE {conditions}
#         RETURN 
#             replace(split(p.url, '/')[-1], '-', ' ') as title,
#             p.url,
#             c.name as category,
#             substring(p.content_text, 0, 300) + '...' as preview
#         ORDER BY p.extracted_at DESC
#         LIMIT 5
#         """
    
#     def test_basic_query(self) -> bool:
#         """Test basic database connectivity and query functionality."""
#         try:
#             print("🧪 Testing basic database connectivity...")
            
#             with self.driver.session() as session:
#                 # Test basic query
#                 result = session.run("""
#                     MATCH (c:Category)-[:HAS_PAGE]->(p:Page)
#                     RETURN 
#                         replace(split(p.url, '/')[-1], '-', ' ') as title,
#                         p.url,
#                         c.name as category,
#                         substring(p.content_text, 0, 100) + '...' as preview
#                     LIMIT 3
#                 """)
                
#                 results = list(result)
#                 print(f"✅ Basic query successful - found {len(results)} test results")
                
#                 if results:
#                     print("📋 Sample results:")
#                     for i, record in enumerate(results[:2], 1):
#                         print(f"   {i}. {record['title']}")
#                         print(f"      Category: {record['category']}")
                
#                 return True
                
#         except Exception as e:
#             print(f"❌ Basic query test failed: {e}")
#             return False

#     def retrieve_information(self, user_question: str) -> List[Dict[str, Any]]:
#         """Main retrieval function."""
#         try:
#             print(f"🔍 Processing question: {user_question}")
            
#             # Generate Cypher query
#             cypher_query = self.generate_cypher_query(user_question)
#             print(f"📝 Generated query:\n{cypher_query}\n")
            
#             # Execute query
#             with self.driver.session() as session:
#                 result = session.run(cypher_query)
#                 results = []
                
#                 for record in result:
#                     # Convert neo4j record to dict
#                     result_dict = {}
#                     for key in record.keys():
#                         value = record[key]
#                         # Handle any neo4j specific types
#                         if hasattr(value, 'value'):
#                             result_dict[key] = value.value
#                         else:
#                             result_dict[key] = value
#                     results.append(result_dict)
            
#             print(f"✅ Retrieved {len(results)} results")
#             return results
            
#         except Exception as e:
#             print(f"❌ Retrieval failed: {e}")
#             print("🔄 Trying fallback method...")
#             return self._fallback_retrieve(user_question)
    
#     def _fallback_retrieve(self, user_question: str) -> List[Dict[str, Any]]:
#         """Fallback retrieval with simple query."""
#         try:
#             fallback_query = self._create_fallback_query(user_question)
            
#             with self.driver.session() as session:
#                 result = session.run(fallback_query)
#                 results = []
                
#                 for record in result:
#                     result_dict = {}
#                     for key in record.keys():
#                         result_dict[key] = record[key]
#                     results.append(result_dict)
                
#                 return results
                
#         except Exception as e:
#             print(f"❌ Even fallback failed: {e}")
#             return []
    
#     def get_database_summary(self) -> Dict[str, Any]:
#         """Get comprehensive database summary."""
#         summary = {}
        
#         try:
#             with self.driver.session() as session:
#                 # Basic counts
#                 result = session.run("MATCH (c:Category) RETURN count(c) as count")
#                 summary["total_categories"] = result.single()["count"]
                
#                 result = session.run("MATCH (p:Page) RETURN count(p) as count")  
#                 summary["total_pages"] = result.single()["count"]
                
#                 result = session.run("MATCH (k:Keyword) RETURN count(k) as count")
#                 summary["total_keywords"] = result.single()["count"]
                
#                 result = session.run("MATCH ()-[r:RELATED_TO]->() RETURN count(r) as count")
#                 summary["similarity_relationships"] = result.single()["count"]
                
#                 # Categories with page counts
#                 result = session.run("""
#                     MATCH (c:Category)-[:HAS_PAGE]->(p:Page)
#                     RETURN c.name as category, count(p) as page_count
#                     ORDER BY page_count DESC
#                 """)
#                 summary["categories_breakdown"] = {record["category"]: record["page_count"] for record in result}
                
#         except Exception as e:
#             summary["error"] = str(e)
        
#         return summary

# def main():
#     """Interactive main function."""
#     print("🚀 Knowledge Graph Information Retriever")
#     print("=" * 50)
    
#     retriever = KnowledgeGraphRetriever()
    
#     # Test basic functionality first
#     if not retriever.test_basic_query():
#         print("❌ Basic database test failed. Please check your Neo4j connection and data.")
#         return
    
#     # Show database summary
#     summary = retriever.get_database_summary()
#     print("\n📊 Database Summary:")
#     print(f"   Categories: {summary.get('total_categories', 'Unknown')}")
#     print(f"   Pages: {summary.get('total_pages', 'Unknown')}")  
#     print(f"   Keywords: {summary.get('total_keywords', 'Unknown')}")
#     print(f"   Similarity Links: {summary.get('similarity_relationships', 'Unknown')}")
    
#     if summary.get('categories_breakdown'):
#         print("\n📁 Categories:")
#         for cat, count in summary['categories_breakdown'].items():
#             print(f"   {cat}: {count} pages")
    
#     print(f"\n🧠 Schema Analysis:")
#     print(f"   Available categories: {retriever.schema_info['categories']}")
#     print(f"   Content types: {retriever.schema_info['content_types']}")
#     print(f"   Has vector embeddings: {retriever.schema_info['has_vectors']}")
    
#     # Interactive retrieval loop
#     print(f"\n💬 Ask questions about your knowledge base (type 'exit' to quit):")
    
#     while True:
#         user_question = input("\n🔎 Your question: ").strip()
        
#         if user_question.lower() in ['exit', 'quit', 'q']:
#             print("👋 Goodbye!")
#             break
        
#         if not user_question:
#             continue
        
#         # Retrieve information
#         results = retriever.retrieve_information(user_question)
        
#         # Display results
#         if results:
#             print(f"\n📋 Found {len(results)} relevant results:")
#             print("=" * 70)
            
#             for i, result in enumerate(results, 1):
#                 title = result.get('title', 'Unknown Title')
#                 category = result.get('category', 'Unknown Category')
#                 url = result.get('url', 'No URL')
#                 preview = result.get('preview', 'No preview available')
                
#                 print(f"\n{i}. {title}")
#                 print(f"   📁 Category: {category}")
#                 print(f"   🔗 URL: {url}")
#                 print(f"   📄 Preview: {preview}")
                
#                 # Show additional fields if present
#                 if 'similarity' in result:
#                     print(f"   📊 Similarity: {result['similarity']:.3f}")
#                 if 'keyword_matches' in result:
#                     print(f"   🎯 Keyword Matches: {result['keyword_matches']}")
#                 if 'related_title' in result:
#                     print(f"   🔗 Related: {result['related_title']}")
                
#         else:
#             print("❌ No results found.")
#             print("💡 Try simpler keywords like: 'wifi', 'battery', 'lock', 'unlock', 'troubleshoot'")
            
#             # Suggest a simple test
#             print("🧪 Testing with simple query...")
#             try:
#                 with retriever.driver.session() as session:
#                     test_result = session.run("""
#                         MATCH (c:Category)-[:HAS_PAGE]->(p:Page)
#                         WHERE toLower(p.content_text) CONTAINS 'lock'
#                         RETURN 
#                             replace(split(p.url, '/')[-1], '-', ' ') as title,
#                             c.name as category
#                         LIMIT 2
#                     """)
#                     test_results = list(test_result)
#                     if test_results:
#                         print(f"   Found {len(test_results)} pages containing 'lock':")
#                         for r in test_results:
#                             print(f"   - {r['title']} ({r['category']})")
#                     else:
#                         print("   No pages found containing 'lock' - check your data")
#             except Exception as e:
#                 print(f"   Test query failed: {e}")

# if __name__ == "__main__":
#     main()

















# import os
# import json
# from neo4j import GraphDatabase
# import google.generativeai as genai
# from dotenv import load_dotenv
# from typing import List, Dict, Any
# import re

# load_dotenv()

# # Configuration
# NEO4J_URI = "bolt://localhost:7687"
# NEO4J_USER = "neo4j"
# NEO4J_PASSWORD = "123456789"

# driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
# genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# class KnowledgeGraphRetriever:
#     """Knowledge Graph Retriever for your exact schema structure."""
    
#     def __init__(self):
#         self.driver = driver
#         self.model = genai.GenerativeModel("gemini-2.5-flash")
#         self.schema_info = self._analyze_current_schema()
#         self.system_prompt = self._build_expert_system_prompt()
    
#     def _analyze_current_schema(self) -> Dict[str, Any]:
#         """Analyze the current knowledge graph to understand available data."""
#         schema = {
#             "categories": [],
#             "sample_titles": [],
#             "sample_keywords": [],
#             "total_pages": 0,
#             "total_relationships": 0,
#             "has_vectors": False,
#             "content_types": []
#         }
        
#         try:
#             with self.driver.session() as session:
#                 # Get categories
#                 result = session.run("MATCH (c:Category) RETURN c.name as name ORDER BY c.name")
#                 schema["categories"] = [record["name"] for record in result]
                
#                 # Get sample page titles (extracted from URLs since title field is empty)
#                 result = session.run("""
#                     MATCH (p:Page) 
#                     WHERE p.url IS NOT NULL 
#                     RETURN split(p.url, '/')[-1] as url_part 
#                     LIMIT 10
#                 """)
#                 schema["sample_titles"] = [
#                     record["url_part"].replace('-', ' ').title() 
#                     for record in result
#                 ]
                
#                 # Get sample keywords
#                 result = session.run("MATCH (k:Keyword) RETURN k.name LIMIT 20")
#                 schema["sample_keywords"] = [record["k.name"] for record in result]
                
#                 # Count pages
#                 result = session.run("MATCH (p:Page) RETURN count(p) as count")
#                 schema["total_pages"] = result.single()["count"]
                
#                 # Count relationships
#                 result = session.run("MATCH ()-[r:RELATED_TO]->() RETURN count(r) as count")
#                 schema["total_relationships"] = result.single()["count"]
                
#                 # Check if vectors exist
#                 result = session.run("MATCH (p:Page) WHERE p.vector IS NOT NULL RETURN count(p) as count")
#                 schema["has_vectors"] = result.single()["count"] > 0
                
#                 # Check content types available
#                 result = session.run("""
#                     MATCH (p:Page) 
#                     RETURN 
#                         count(CASE WHEN p.content_text IS NOT NULL AND p.content_text <> '' THEN 1 END) as text_count,
#                         count(CASE WHEN p.content_html IS NOT NULL AND p.content_html <> '' THEN 1 END) as html_count,
#                         count(CASE WHEN p.content_markdown IS NOT NULL AND p.content_markdown <> '' THEN 1 END) as markdown_count
#                 """)
#                 record = result.single()
#                 if record["text_count"] > 0:
#                     schema["content_types"].append("content_text")
#                 if record["html_count"] > 0:
#                     schema["content_types"].append("content_html")
#                 if record["markdown_count"] > 0:
#                     schema["content_types"].append("content_markdown")
                
#         except Exception as e:
#             print(f"⚠️ Schema analysis failed: {e}")
        
#         return schema
    
#     def _build_expert_system_prompt(self) -> str:
#         """Build a comprehensive system prompt based on the exact schema."""
        
#         categories = ", ".join(self.schema_info["categories"])
#         sample_keywords = ", ".join(self.schema_info["sample_keywords"][:15])
#         content_fields = ", ".join(self.schema_info["content_types"])
        
#         return f"""You are an expert Cypher query generator for a RemoteLock troubleshooting knowledge graph.
# Your job is to create precise, efficient Cypher queries that retrieve the most relevant information.

# EXACT DATABASE SCHEMA:
# Nodes:
# - Category {{name: string}} - Available categories: {categories}
# - Page {{url: string, title: string (EMPTY), content_text: string, content_html: string, content_markdown: string, source: string, extracted_at: int, vector: array}}
# - Keyword {{name: string}} - Available keywords include: {sample_keywords}

# Relationships:
# - (Category)-[:HAS_PAGE]->(Page) - Category contains pages
# - (Page)-[:BELONGS_TO]->(Category) - Page belongs to category  
# - (Page)-[:RELATED_TO]-(Page) {{similarity: float}} - Semantically similar pages
# - (Page)-[:HAS_KEYWORD]->(Keyword) - Page contains keyword

# IMPORTANT SCHEMA FACTS:
# - Page.title field is EMPTY for all records - DO NOT use it
# - Use URL parsing to extract readable titles: split(p.url, '/')[-1]
# - Primary content is in: {content_fields}
# - Vector embeddings available: {self.schema_info["has_vectors"]}
# - Total pages: {self.schema_info["total_pages"]}
# - Similarity relationships: {self.schema_info["total_relationships"]}

# QUERY GENERATION RULES:
# 1. NEVER use p.title - it's empty. Extract title from URL instead
# 2. Search content using content_text (primary field)
# 3. Use case-insensitive matching with toLower() and CONTAINS  
# 4. Always limit results (default: 5, max: 10)
# 5. Return: extracted title, url, category, content preview
# 6. Order by relevance (content length, similarity score)
# 7. Use semantic similarity when available

# PROVEN QUERY PATTERNS:

# Basic Content Search:
# ```cypher
# MATCH (c:Category)-[:HAS_PAGE]->(p:Page)
# WHERE toLower(p.content_text) CONTAINS toLower('search_keyword')
# RETURN 
#     replace(split(p.url, '/')[-1], '-', ' ') as title,
#     p.url,
#     c.name as category,
#     substring(p.content_text, 0, 300) + '...' as preview
# ORDER BY length(p.content_text) DESC
# LIMIT 5
# ```

# Multi-Keyword Search:
# ```cypher
# MATCH (c:Category)-[:HAS_PAGE]->(p:Page)
# WHERE toLower(p.content_text) CONTAINS toLower('keyword1')
#   AND toLower(p.content_text) CONTAINS toLower('keyword2')
# RETURN 
#     replace(split(p.url, '/')[-1], '-', ' ') as title,
#     p.url,
#     c.name as category,
#     substring(p.content_text, 0, 300) + '...' as preview
# ORDER BY length(p.content_text) DESC
# LIMIT 5
# ```

# Category-Specific Search:
# ```cypher
# MATCH (c:Category)-[:HAS_PAGE]->(p:Page)
# WHERE toLower(c.name) CONTAINS toLower('category_keyword')
#   AND toLower(p.content_text) CONTAINS toLower('search_keyword')
# RETURN 
#     replace(split(p.url, '/')[-1], '-', ' ') as title,
#     p.url,
#     c.name as category,
#     substring(p.content_text, 0, 300) + '...' as preview
# ORDER BY length(p.content_text) DESC
# LIMIT 5
# ```

# Keyword-Based Search:
# ```cypher
# MATCH (p:Page)-[:HAS_KEYWORD]->(k:Keyword)
# WHERE toLower(k.name) CONTAINS toLower('keyword')
# WITH p, count(k) as keyword_matches
# MATCH (p)-[:BELONGS_TO]->(c:Category)
# RETURN 
#     replace(split(p.url, '/')[-1], '-', ' ') as title,
#     p.url,
#     c.name as category,
#     substring(p.content_text, 0, 300) + '...' as preview,
#     keyword_matches
# ORDER BY keyword_matches DESC, length(p.content_text) DESC
# LIMIT 5
# ```

# Similarity-Based Search:
# ```cypher
# MATCH (p1:Page)-[r:RELATED_TO]-(p2:Page)
# WHERE toLower(p1.content_text) CONTAINS toLower('search_keyword')
# MATCH (p1)-[:BELONGS_TO]->(c1:Category)
# MATCH (p2)-[:BELONGS_TO]->(c2:Category)
# RETURN 
#     replace(split(p1.url, '/')[-1], '-', ' ') as title,
#     p1.url,
#     c1.name as category,
#     substring(p1.content_text, 0, 200) + '...' as preview,
#     replace(split(p2.url, '/')[-1], '-', ' ') as related_title,
#     p2.url as related_url,
#     r.similarity
# ORDER BY r.similarity DESC
# LIMIT 5
# ```

# Complex Problem-Solving Search:
# ```cypher
# MATCH (p:Page)-[:HAS_KEYWORD]->(k:Keyword)
# WHERE toLower(k.name) IN ['troubleshoot', 'problem', 'issue', 'fix', 'error']
#   AND toLower(p.content_text) CONTAINS toLower('search_keyword')
# WITH p, count(k) as problem_keywords
# MATCH (p)-[:BELONGS_TO]->(c:Category)
# RETURN 
#     replace(split(p.url, '/')[-1], '-', ' ') as title,
#     p.url,
#     c.name as category,
#     substring(p.content_text, 0, 300) + '...' as preview,
#     problem_keywords
# ORDER BY problem_keywords DESC, length(p.content_text) DESC
# LIMIT 5
# ```

# CRITICAL INSTRUCTIONS:
# - NEVER reference p.title (it's empty)
# - ALWAYS extract title using: replace(split(p.url, '/')[-1], '-', ' ')
# - Use content_text for all text searching
# - Include category information in results
# - Use proper text matching with toLower() and CONTAINS
# - Order results meaningfully
# - Limit results appropriately
# - Return consistent field names: title, url, category, preview

# Generate ONLY the Cypher query. No explanations, no markdown formatting, just pure Cypher code."""

#     def generate_cypher_query(self, user_question: str) -> str:
#         """Generate optimized Cypher query for user question."""
#         try:
#             prompt = f"{self.system_prompt}\n\nUser Question: {user_question}\n\nCypher Query:"
            
#             response = self.model.generate_content(prompt)
#             query = response.text.strip()
            
#             # Clean the response
#             query = re.sub(r'```cypher\s*', '', query, flags=re.IGNORECASE)
#             query = re.sub(r'```\s*', '', query)
#             query = re.sub(r'^cypher\s*', '', query, flags=re.IGNORECASE)
#             query = query.strip()
            
#             return query
            
#         except Exception as e:
#             print(f"❌ Query generation failed: {e}")
#             return self._create_fallback_query(user_question)
    
#     def _create_fallback_query(self, user_question: str) -> str:
#         """Create a reliable fallback query."""
#         words = [word.strip() for word in user_question.lower().split() if len(word.strip()) > 2][:3]
        
#         if not words:
#             return """
#             MATCH (c:Category)-[:HAS_PAGE]->(p:Page)
#             RETURN 
#                 replace(split(p.url, '/')[-1], '-', ' ') as title,
#                 p.url,
#                 c.name as category,
#                 substring(p.content_text, 0, 300) + '...' as preview
#             ORDER BY length(p.content_text) DESC
#             LIMIT 5
#             """
        
#         conditions = " OR ".join([f"toLower(p.content_text) CONTAINS '{word}'" for word in words])
        
#         return f"""
#         MATCH (c:Category)-[:HAS_PAGE]->(p:Page)
#         WHERE {conditions}
#         RETURN 
#             replace(split(p.url, '/')[-1], '-', ' ') as title,
#             p.url,
#             c.name as category,
#             substring(p.content_text, 0, 300) + '...' as preview
#         ORDER BY length(p.content_text) DESC
#         LIMIT 5
#         """
    
#     def retrieve_information(self, user_question: str) -> List[Dict[str, Any]]:
#         """Main retrieval function."""
#         try:
#             print(f"🔍 Processing question: {user_question}")
            
#             # Generate Cypher query
#             cypher_query = self.generate_cypher_query(user_question)
#             print(f"📝 Generated query:\n{cypher_query}\n")
            
#             # Execute query
#             with self.driver.session() as session:
#                 result = session.run(cypher_query)
#                 results = []
                
#                 for record in result:
#                     # Convert neo4j record to dict
#                     result_dict = {}
#                     for key in record.keys():
#                         value = record[key]
#                         # Handle any neo4j specific types
#                         if hasattr(value, 'value'):
#                             result_dict[key] = value.value
#                         else:
#                             result_dict[key] = value
#                     results.append(result_dict)
            
#             print(f"✅ Retrieved {len(results)} results")
#             return results
            
#         except Exception as e:
#             print(f"❌ Retrieval failed: {e}")
#             print("🔄 Trying fallback method...")
#             return self._fallback_retrieve(user_question)
    
#     def _fallback_retrieve(self, user_question: str) -> List[Dict[str, Any]]:
#         """Fallback retrieval with simple query."""
#         try:
#             fallback_query = self._create_fallback_query(user_question)
            
#             with self.driver.session() as session:
#                 result = session.run(fallback_query)
#                 results = []
                
#                 for record in result:
#                     result_dict = {}
#                     for key in record.keys():
#                         result_dict[key] = record[key]
#                     results.append(result_dict)
                
#                 return results
                
#         except Exception as e:
#             print(f"❌ Even fallback failed: {e}")
#             return []
    
#     def get_database_summary(self) -> Dict[str, Any]:
#         """Get comprehensive database summary."""
#         summary = {}
        
#         try:
#             with self.driver.session() as session:
#                 # Basic counts
#                 result = session.run("MATCH (c:Category) RETURN count(c) as count")
#                 summary["total_categories"] = result.single()["count"]
                
#                 result = session.run("MATCH (p:Page) RETURN count(p) as count")  
#                 summary["total_pages"] = result.single()["count"]
                
#                 result = session.run("MATCH (k:Keyword) RETURN count(k) as count")
#                 summary["total_keywords"] = result.single()["count"]
                
#                 result = session.run("MATCH ()-[r:RELATED_TO]->() RETURN count(r) as count")
#                 summary["similarity_relationships"] = result.single()["count"]
                
#                 # Categories with page counts
#                 result = session.run("""
#                     MATCH (c:Category)-[:HAS_PAGE]->(p:Page)
#                     RETURN c.name as category, count(p) as page_count
#                     ORDER BY page_count DESC
#                 """)
#                 summary["categories_breakdown"] = {record["category"]: record["page_count"] for record in result}
                
#         except Exception as e:
#             summary["error"] = str(e)
        
#         return summary

# def main():
#     """Interactive main function."""
#     print("🚀 Knowledge Graph Information Retriever")
#     print("=" * 50)
    
#     retriever = KnowledgeGraphRetriever()
    
#     # Show database summary
#     summary = retriever.get_database_summary()
#     print("📊 Database Summary:")
#     print(f"   Categories: {summary.get('total_categories', 'Unknown')}")
#     print(f"   Pages: {summary.get('total_pages', 'Unknown')}")  
#     print(f"   Keywords: {summary.get('total_keywords', 'Unknown')}")
#     print(f"   Similarity Links: {summary.get('similarity_relationships', 'Unknown')}")
    
#     if summary.get('categories_breakdown'):
#         print("\n📁 Categories:")
#         for cat, count in summary['categories_breakdown'].items():
#             print(f"   {cat}: {count} pages")
    
#     print(f"\n🧠 Schema Analysis:")
#     print(f"   Available categories: {retriever.schema_info['categories']}")
#     print(f"   Content types: {retriever.schema_info['content_types']}")
#     print(f"   Has vector embeddings: {retriever.schema_info['has_vectors']}")
    
#     # Interactive retrieval loop
#     print(f"\n💬 Ask questions about your knowledge base (type 'exit' to quit):")
    
#     while True:
#         user_question = input("\n🔎 Your question: ").strip()
        
#         if user_question.lower() in ['exit', 'quit', 'q']:
#             print("👋 Goodbye!")
#             break
        
#         if not user_question:
#             continue
        
#         # Retrieve information
#         results = retriever.retrieve_information(user_question)
        
#         # Display results
#         if results:
#             print(f"\n📋 Found {len(results)} relevant results:")
#             print("=" * 70)
            
#             for i, result in enumerate(results, 1):
#                 title = result.get('title', 'Unknown Title')
#                 category = result.get('category', 'Unknown Category')
#                 url = result.get('url', 'No URL')
#                 preview = result.get('preview', 'No preview available')
                
#                 print(f"\n{i}. {title}")
#                 print(f"   📁 Category: {category}")
#                 print(f"   🔗 URL: {url}")
#                 print(f"   📄 Preview: {preview}")
                
#                 # Show additional fields if present
#                 if 'similarity' in result:
#                     print(f"   📊 Similarity: {result['similarity']:.3f}")
#                 if 'keyword_matches' in result:
#                     print(f"   🎯 Keyword Matches: {result['keyword_matches']}")
#                 if 'related_title' in result:
#                     print(f"   🔗 Related: {result['related_title']}")
                
#         else:
#             print("❌ No results found.")
#             print("💡 Try using different keywords or check your question.")

# if __name__ == "__main__":
#     main()






























import json
import itertools
import numpy as np
from neo4j import GraphDatabase



# Neo4j credentials
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "123456789"

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

def cosine_similarity(vec1, vec2):
    """Compute cosine similarity between two vectors."""
    if not vec1 or not vec2:
        return 0.0
    v1, v2 = np.array(vec1), np.array(vec2)
    return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))

def create_nodes_and_relationships(tx, record):
    # Create category and page node
    tx.run("""
        MERGE (c:Category {name: $category})
        MERGE (p:Page {url: $url})
        SET p.title = $title,
            p.content_text = $content_text,
            p.content_html = $content_html,
            p.content_markdown = $content_markdown,
            p.source = $source,
            p.extracted_at = $extracted_at,
            p.vector = $vector
        MERGE (c)-[:HAS_PAGE]->(p)
        MERGE (p)-[:BELONGS_TO]->(c)
    """, record)

    # Create keyword nodes
    for kw in record.get("keywords", []):
        tx.run("""
            MERGE (k:Keyword {name: $kw})
            MERGE (p:Page {url: $url})
            MERGE (p)-[:HAS_KEYWORD]->(k)
        """, {"kw": kw, "url": record["url"]})

def create_related_links(records, threshold=0.75):
    """Create RELATED_TO links between similar pages."""
    with driver.session() as session:
        for rec1, rec2 in itertools.combinations(records, 2):
            sim = cosine_similarity(rec1.get("vector"), rec2.get("vector"))
            if sim >= threshold:
                session.run("""
                    MATCH (p1:Page {url: $url1}), (p2:Page {url: $url2})
                    MERGE (p1)-[r:RELATED_TO]-(p2)
                    SET r.similarity = $sim
                """, {"url1": rec1["url"], "url2": rec2["url"], "sim": sim})

def load_data(json_file="troubleshooting_with_embeddings.json"):
    with open(json_file, "r", encoding="utf-8") as f:
        records = json.load(f)

    with driver.session() as session:
        for rec in records:
            session.execute_write(create_nodes_and_relationships, rec)

    # After all nodes created, link related pages
    create_related_links(records, threshold=0.75)

    print("✅ Data successfully loaded with relationships!")

if __name__ == "__main__":
    load_data()




# import json
# from neo4j import GraphDatabase

# # Update with your Neo4j credentials
# NEO4J_URI = "bolt://localhost:7687"
# NEO4J_USER = "neo4j"
# NEO4J_PASSWORD = "123456789"  # use the password you set when creating the DB

# driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

# def create_graph(tx, record):
#     # Create or merge category node
#     tx.run("""
#         MERGE (c:Category {name: $category})
#         MERGE (p:Page {url: $url})
#         SET p.title = $title,
#             p.content_text = $content_text,
#             p.content_html = $content_html,
#             p.content_markdown = $content_markdown,
#             p.source = $source,
#             p.extracted_at = $extracted_at,
#             p.vector = $vector
#         MERGE (p)-[:BELONGS_TO]->(c)
#     """, record)

# def load_data(json_file="troubleshooting_with_embeddings.json"):
#     with open(json_file, "r", encoding="utf-8") as f:
#         records = json.load(f)

#     with driver.session() as session:
#         for rec in records:
#             session.execute_write(create_graph, rec)

#     print("✅ Data successfully loaded into Neo4j!")

# if __name__ == "__main__":
#     load_data()

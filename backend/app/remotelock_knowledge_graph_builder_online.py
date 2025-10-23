# remotelock_knowledge_graph_builder.py
import json
import re
from typing import List, Dict, Set
from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer
import numpy as np
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Neo4j Configuration
# Update with your AuraDB connection details
NEO4J_URI = "neo4j+s://d3db84ff.databases.neo4j.io" # This is a placeholder, replace with your actual AuraDB URI
NEO4J_USER = "neo4j" # For AuraDB, the default user is typically 'neo4j'
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD") # Loaded from .env

INPUT_FILE = "remotelock_nodes_with_embeddings.json"

class KnowledgeGraphBuilder:
    def __init__(self, uri, user, password):
        # For AuraDB, it's recommended to disable encrypted=False if using neo4j+s://
        # as it implies encrypted connection.
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        
    def close(self):
        self.driver.close()
    
    def clear_database(self):
        """Clear existing data (optional - use with caution)"""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            print("Database cleared")
    
    def create_schema(self):
        """Create optimized schema with constraints and indexes"""
        with self.driver.session() as session:
            # Drop existing constraints if any
            try:
                session.run("DROP CONSTRAINT page_url IF EXISTS")
                session.run("DROP CONSTRAINT category_name IF EXISTS")
                session.run("DROP CONSTRAINT subcategory_name IF EXISTS")
            except Exception as e:
                print(f"Error dropping constraints (may not exist): {e}")
                pass
            
            # Create constraints
            session.run("""
                CREATE CONSTRAINT page_url IF NOT EXISTS
                FOR (p:Page) REQUIRE p.url IS UNIQUE
            """)
            
            session.run("""
                CREATE CONSTRAINT category_name IF NOT EXISTS
                FOR (c:Category) REQUIRE c.name IS UNIQUE
            """)
            
            session.run("""
                CREATE CONSTRAINT subcategory_name IF NOT EXISTS
                FOR (s:Subcategory) REQUIRE s.name IS UNIQUE
            """)
            
            # Create indexes for faster lookups
            session.run("CREATE INDEX page_title IF NOT EXISTS FOR (p:Page) ON (p.title)")
            session.run("CREATE INDEX page_slug IF NOT EXISTS FOR (p:Page) ON (p.slug)")
            session.run("CREATE INDEX category_name_idx IF NOT EXISTS FOR (c:Category) ON (c.name)")
            
            # Create vector index for semantic search (Neo4j 5.11+)
            try:
                session.run("""
                    CREATE VECTOR INDEX page_embeddings IF NOT EXISTS
                    FOR (p:Page) ON (p.embedding)
                    OPTIONS {
                        indexConfig: {
                            `vector.dimensions`: 384,
                            `vector.similarity_function`: 'cosine'
                        }
                    }
                """)
                print("Vector index created successfully")
            except Exception as e:
                print(f"Vector index creation skipped: {e}") # This often fails if version is too old or security issue
            
            print("Schema created successfully")
    
    def extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords from text"""
        if not text:
            return []
        
        # Common support keywords to extract
        patterns = [
            r'\b(lock|unlock|wifi|battery|installation|troubleshooting|setup|configure|reset|offline|error|code)\b',
            r'\b(\d{3,4})\s*series\b',  # Series numbers
            r'\b(deadbolt|lever|mortise|keypad|ACS|ResortLock|OpenEdge)\b',
        ]
        
        keywords = set()
        text_lower = text.lower()
        
        for pattern in patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            keywords.update(matches)
        
        return list(keywords)[:20]  # Limit to top 20
    
    def extract_product_models(self, text: str) -> List[str]:
        """Extract product model numbers from text"""
        if not text:
            return []
        
        patterns = [
            r'\b(LS-\w+)\b',  # LS- models
            r'\b(RL-?\d{4})\b',  # RL models
            r'\b(\d{3,4})\s*[Ss]eries\b',  # Series numbers
            r'\b(DB-?\d{3,4}\w*)\b',  # DB models
            r'\b(LP-?\d{4})\b',  # LP models
            r'\b(MR-?\d{2})\b',  # MR models
        ]
        
        models = set()
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            models.update(matches)
        
        return list(models)
    
    def calculate_similarity(self, emb1: List[float], emb2: List[float]) -> float:
        """Calculate cosine similarity between two embeddings"""
        arr1 = np.array(emb1)
        arr2 = np.array(emb2)
        return float(np.dot(arr1, arr2) / (np.linalg.norm(arr1) * np.linalg.norm(arr2)))
    
    def create_page_node(self, node: Dict):
        """Create a Page node with all properties"""
        with self.driver.session() as session:
            session.run("""
                MERGE (p:Page {url: $url})
                SET p.id = $id,
                    p.title = $title,
                    p.content = $content,
                    p.slug = $slug,
                    p.content_length = $content_length,
                    p.word_count = $word_count,
                    p.embedding = $embedding,
                    p.keywords = $keywords,
                    p.product_models = $product_models,
                    p.scraped_at = $scraped_at,
                    p.source = $source
            """, 
                id=node.get("id"),
                url=node.get("url"),
                title=node.get("title", ""),
                content=node.get("content", ""),
                slug=node.get("slug", ""),
                content_length=node.get("content_length", 0),
                word_count=node.get("word_count", 0),
                embedding=node.get("embedding"),
                keywords=self.extract_keywords(node.get("content", "") + " " + node.get("title", "")),
                product_models=self.extract_product_models(node.get("content", "") + " " + node.get("title", "")),
                scraped_at=node.get("scraped_at"),
                source=node.get("source", "")
            )
    
    def create_category_node(self, category_name: str):
        """Create a Category node"""
        with self.driver.session() as session:
            session.run("""
                MERGE (c:Category {name: $name})
            """, name=category_name)
    
    def create_subcategory_node(self, subcategory_name: str):
        """Create a Subcategory node"""
        with self.driver.session() as session:
            session.run("""
                MERGE (s:Subcategory {name: $name})
            """, name=subcategory_name)
    
    def link_page_to_category(self, page_url: str, category_name: str):
        """Link Page to Category"""
        with self.driver.session() as session:
            session.run("""
                MATCH (p:Page {url: $page_url})
                MATCH (c:Category {name: $category_name})
                MERGE (p)-[:BELONGS_TO_CATEGORY]->(c)
            """, page_url=page_url, category_name=category_name)
    
    def link_page_to_subcategory(self, page_url: str, subcategory_name: str):
        """Link Page to Subcategory"""
        with self.driver.session() as session:
            session.run("""
                MATCH (p:Page {url: $page_url})
                MATCH (s:Subcategory {name: $subcategory_name})
                MERGE (p)-[:BELONGS_TO_SUBCATEGORY]->(s)
            """, page_url=page_url, subcategory_name=subcategory_name)
    
    def link_subcategory_to_category(self, subcategory_name: str, category_name: str):
        """Link Subcategory to Category"""
        with self.driver.session() as session:
            session.run("""
                MATCH (s:Subcategory {name: $subcategory_name})
                MATCH (c:Category {name: $category_name})
                MERGE (s)-[:PART_OF_CATEGORY]->(c)
            """, subcategory_name=subcategory_name, category_name=category_name)
    
    def create_semantic_relationships(self, nodes: List[Dict], similarity_threshold: float = 0.75):
        """Create RELATED_TO relationships between semantically similar pages"""
        print(f"\nCreating semantic relationships (threshold: {similarity_threshold})...")
        
        # Filter nodes with embeddings
        nodes_with_emb = [n for n in nodes if n.get("embedding")]
        total = len(nodes_with_emb)
        relationships_created = 0
        
        for i, node1 in enumerate(nodes_with_emb):
            if i % 10 == 0:
                print(f"  Progress: {i}/{total} nodes processed...", end="\r")
            
            for node2 in nodes_with_emb[i+1:]:
                # Calculate similarity
                similarity = self.calculate_similarity(
                    node1["embedding"], 
                    node2["embedding"]
                )
                
                # Create relationship if above threshold
                if similarity >= similarity_threshold:
                    with self.driver.session() as session:
                        session.run("""
                            MATCH (p1:Page {url: $url1})
                            MATCH (p2:Page {url: $url2})
                            MERGE (p1)-[r:RELATED_TO]->(p2)
                            SET r.similarity = $similarity
                        """, 
                            url1=node1["url"], 
                            url2=node2["url"], 
                            similarity=similarity
                        )
                        relationships_created += 1
        
        print(f"\n  Created {relationships_created} semantic relationships")
    
    def create_keyword_relationships(self):
        """Create relationships between pages sharing keywords"""
        print("\nCreating keyword-based relationships...")
        
        with self.driver.session() as session:
            result = session.run("""
                MATCH (p1:Page), (p2:Page)
                WHERE p1 <> p2 
                AND size(p1.keywords) > 0 
                AND size(p2.keywords) > 0
                AND any(k IN p1.keywords WHERE k IN p2.keywords)
                WITH p1, p2, 
                     [k IN p1.keywords WHERE k IN p2.keywords] AS shared_keywords,
                     size([k IN p1.keywords WHERE k IN p2.keywords]) AS shared_count
                WHERE shared_count >= 2
                MERGE (p1)-[r:SHARES_KEYWORDS]->(p2)
                SET r.keywords = shared_keywords,
                    r.count = shared_count
                RETURN count(r) as relationships_created
            """)
            
            record = result.single()
            if record:
                print(f"  Created {record['relationships_created']} keyword relationships")
    
    def create_product_model_relationships(self):
        """Create relationships between pages mentioning same products"""
        print("\nCreating product model relationships...")
        
        with self.driver.session() as session:
            result = session.run("""
                MATCH (p1:Page), (p2:Page)
                WHERE p1 <> p2 
                AND size(p1.product_models) > 0 
                AND size(p2.product_models) > 0
                AND any(m IN p1.product_models WHERE m IN p2.product_models)
                WITH p1, p2, 
                     [m IN p1.product_models WHERE m IN p2.product_models] AS shared_models
                MERGE (p1)-[r:MENTIONS_SAME_PRODUCT]->(p2)
                SET r.products = shared_models
                RETURN count(r) as relationships_created
            """)
            
            record = result.single()
            if record:
                print(f"  Created {record['relationships_created']} product model relationships")
    
    def create_troubleshooting_links(self):
        """Link troubleshooting pages to related installation/info pages"""
        print("\nCreating troubleshooting links...")
        
        with self.driver.session() as session:
            # Link troubleshooting to same series/product pages
            result = session.run("""
                MATCH (trouble:Page)-[:BELONGS_TO_CATEGORY]->(c:Category)
                WHERE c.name = 'Troubleshooting'
                MATCH (info:Page)
                WHERE info.url <> trouble.url
                AND (
                    any(m IN trouble.product_models WHERE m IN info.product_models)
                    OR any(k IN trouble.keywords WHERE k IN info.keywords)
                )
                AND NOT (trouble)-[:TROUBLESHOOTS]->(info)
                MERGE (trouble)-[r:TROUBLESHOOTS]->(info)
                RETURN count(r) as links_created
            """)
            
            record = result.single()
            if record:
                print(f"  Created {record['links_created']} troubleshooting links")
    
    def get_statistics(self):
        """Get knowledge graph statistics"""
        with self.driver.session() as session:
            stats = {}
            
            # Node counts
            result = session.run("MATCH (p:Page) RETURN count(p) as count")
            stats['pages'] = result.single()['count']
            
            result = session.run("MATCH (c:Category) RETURN count(c) as count")
            stats['categories'] = result.single()['count']
            
            result = session.run("MATCH (s:Subcategory) RETURN count(s) as count")
            stats['subcategories'] = result.single()['count']
            
            # Relationship counts
            result = session.run("MATCH ()-[r:RELATED_TO]->() RETURN count(r) as count")
            stats['semantic_relationships'] = result.single()['count']
            
            result = session.run("MATCH ()-[r:SHARES_KEYWORDS]->() RETURN count(r) as count")
            stats['keyword_relationships'] = result.single()['count']
            
            result = session.run("MATCH ()-[r:MENTIONS_SAME_PRODUCT]->() RETURN count(r) as count")
            stats['product_relationships'] = result.single()['count']
            
            result = session.run("MATCH ()-[r:TROUBLESHOOTS]->() RETURN count(r) as count")
            stats['troubleshooting_links'] = result.single()['count']
            
            result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
            stats['total_relationships'] = result.single()['count']
            
            return stats

def main():
    print("="*70)
    print("RemoteLock Knowledge Graph Builder")
    print("="*70)
    
    # Load nodes
    print(f"\nLoading nodes from {INPUT_FILE}...")
    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            nodes = json.load(f)
        print(f"Loaded {len(nodes)} nodes")
    except FileNotFoundError:
        print(f"Error: {INPUT_FILE} not found!")
        print("Please run the embedding generator first.")
        return
    
    # Initialize graph builder
    print("\nConnecting to Neo4j...")
    graph = KnowledgeGraphBuilder(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    
    # Optional: Clear existing data
    # Uncomment the next line if you want to start fresh on your AuraDB instance.
    # Be careful, this will delete all data in your AuraDB database!
    # graph.clear_database()
    
    # Create schema
    print("\nCreating schema...")
    graph.create_schema()
    
    # Build the graph
    print("\nBuilding knowledge graph...")
    
    # Track categories and subcategories
    categories = set()
    subcategories = {}
    
    # First pass: Create all nodes
    print("\nCreating nodes...")
    for i, node in enumerate(nodes):
        if i % 10 == 0:
            print(f"  Progress: {i}/{len(nodes)} nodes...", end="\r")
        
        # Create page node
        graph.create_page_node(node)
        
        # Track category
        if node.get("category"):
            categories.add(node["category"])
        
        # Track subcategory
        if node.get("subcategory"):
            subcategories[node["subcategory"]] = node["category"]
    
    print(f"\n  Created {len(nodes)} page nodes")
    
    # Create category and subcategory nodes
    print("\nCreating category nodes...")
    for category in categories:
        graph.create_category_node(category)
    print(f"  Created {len(categories)} category nodes")
    
    print("\nCreating subcategory nodes...")
    for subcategory in subcategories:
        graph.create_subcategory_node(subcategory)
    print(f"  Created {len(subcategories)} subcategory nodes")
    
    # Second pass: Create hierarchical relationships
    print("\nCreating hierarchical relationships...")
    for i, node in enumerate(nodes):
        if i % 10 == 0:
            print(f"  Progress: {i}/{len(nodes)} relationships...", end="\r")
        
        # Link page to category
        if node.get("category"):
            graph.link_page_to_category(node["url"], node["category"])
        
        # Link page to subcategory
        if node.get("subcategory"):
            graph.link_page_to_subcategory(node["url"], node["subcategory"])
    
    print(f"\n  Created hierarchical relationships")
    
    # Link subcategories to categories
    print("\nLinking subcategories to categories...")
    for subcategory, category in subcategories.items():
        graph.link_subcategory_to_category(subcategory, category)
    print(f"  Linked {len(subcategories)} subcategories")
    
    # Create semantic relationships
    graph.create_semantic_relationships(nodes, similarity_threshold=0.75)
    
    # Create keyword relationships
    graph.create_keyword_relationships()
    
    # Create product model relationships
    graph.create_product_model_relationships()
    
    # Create troubleshooting links
    graph.create_troubleshooting_links()
    
    # Get and print statistics
    print("\n" + "="*70)
    print("KNOWLEDGE GRAPH STATISTICS")
    print("="*70)
    stats = graph.get_statistics()
    print(f"Pages:                        {stats['pages']}")
    print(f"Categories:                   {stats['categories']}")
    print(f"Subcategories:                {stats['subcategories']}")
    print(f"\nRelationships:")
    print(f"  Semantic (RELATED_TO):      {stats['semantic_relationships']}")
    print(f"  Keywords (SHARES_KEYWORDS): {stats['keyword_relationships']}")
    print(f"  Products:                   {stats['product_relationships']}")
    print(f"  Troubleshooting:            {stats['troubleshooting_links']}")
    print(f"  Total:                      {stats['total_relationships']}")
    print("="*70)
    
    # Close connection
    graph.close()
    print("\nKnowledge graph created successfully!")
    print("\nYou can now query the graph using Neo4j Browser at your AuraDB instance URL.")

if __name__ == "__main__":
    main()
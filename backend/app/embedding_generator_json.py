# remotelock_embedding_generator.py
import json
import time
from sentence_transformers import SentenceTransformer
from typing import List, Dict

MODEL_NAME = "all-MiniLM-L6-v2"
INPUT_FILE = "remotelock_nodes.json"
OUTPUT_FILE = "remotelock_nodes_with_embeddings.json"

class EmbeddingGenerator:
    def __init__(self, model_name: str = MODEL_NAME):
        """Initialize the embedding model"""
        print(f"🔧 Loading model: {model_name}...")
        self.model = SentenceTransformer(model_name)
        print(f"✅ Model loaded successfully")
        print(f"   Embedding dimension: {self.model.get_sentence_embedding_dimension()}")
    
    def create_embedding_text(self, node: Dict) -> str:
        """Create a combined text for embedding generation"""
        parts = []
        
        # Add title with weight
        if node.get("title"):
            parts.append(f"Title: {node['title']}")
        
        # Add category context
        if node.get("category"):
            parts.append(f"Category: {node['category']}")
        
        # Add subcategory context
        if node.get("subcategory"):
            parts.append(f"Subcategory: {node['subcategory']}")
        
        # Add main content
        if node.get("content"):
            parts.append(node["content"])
        
        return "\n\n".join(parts)
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        if not text or not text.strip():
            return None
        
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    def needs_embedding(self, node: Dict) -> bool:
        """Check if a node needs an embedding"""
        # Node needs embedding if:
        # 1. It has no embedding property, OR
        # 2. Embedding is None, OR
        # 3. Embedding is an empty list
        if "embedding" not in node:
            return True
        if node["embedding"] is None:
            return True
        if isinstance(node["embedding"], list) and len(node["embedding"]) == 0:
            return True
        return False
    
    def process_nodes(self, nodes: List[Dict], batch_size: int = 32) -> tuple:
        """Process all nodes and generate embeddings where needed"""
        total_nodes = len(nodes)
        nodes_needing_embedding = [n for n in nodes if self.needs_embedding(n)]
        nodes_to_process = len(nodes_needing_embedding)
        
        print(f"\n📊 Embedding Status:")
        print(f"   Total nodes:                {total_nodes}")
        print(f"   Nodes needing embeddings:   {nodes_to_process}")
        print(f"   Already embedded:           {total_nodes - nodes_to_process}")
        
        if nodes_to_process == 0:
            print("\n✅ All nodes already have embeddings!")
            return nodes, 0
        
        print(f"\n🚀 Starting embedding generation...")
        print(f"   Batch size: {batch_size}")
        print(f"   Model: {MODEL_NAME}\n")
        
        processed_count = 0
        failed_count = 0
        start_time = time.time()
        
        # Process in batches for efficiency
        for i in range(0, len(nodes), batch_size):
            batch = nodes[i:i + batch_size]
            batch_texts = []
            batch_indices = []
            
            # Collect nodes that need embedding in this batch
            for idx, node in enumerate(batch):
                if self.needs_embedding(node):
                    embedding_text = self.create_embedding_text(node)
                    if embedding_text.strip():
                        batch_texts.append(embedding_text)
                        batch_indices.append(i + idx)
            
            # Generate embeddings for the batch
            if batch_texts:
                try:
                    embeddings = self.model.encode(
                        batch_texts, 
                        convert_to_numpy=True,
                        show_progress_bar=False
                    )
                    
                    # Assign embeddings to nodes
                    for node_idx, embedding in zip(batch_indices, embeddings):
                        nodes[node_idx]["embedding"] = embedding.tolist()
                        nodes[node_idx]["embedding_model"] = MODEL_NAME
                        nodes[node_idx]["embedding_dimension"] = len(embedding)
                        nodes[node_idx]["embedded_at"] = int(time.time())
                        processed_count += 1
                    
                    # Progress update
                    progress = (processed_count / nodes_to_process) * 100
                    print(f"   ✅ Progress: {processed_count}/{nodes_to_process} ({progress:.1f}%)", end="\r")
                
                except Exception as e:
                    print(f"\n   ❌ Error processing batch: {e}")
                    failed_count += len(batch_texts)
        
        elapsed_time = time.time() - start_time
        
        print(f"\n\n✅ Embedding generation complete!")
        print(f"   Successfully processed:  {processed_count}")
        print(f"   Failed:                  {failed_count}")
        print(f"   Time elapsed:            {elapsed_time:.2f}s")
        print(f"   Average time per node:   {elapsed_time/processed_count:.3f}s" if processed_count > 0 else "")
        
        return nodes, processed_count

def load_nodes(filepath: str) -> List[Dict]:
    """Load nodes from JSON file"""
    print(f"📂 Loading nodes from: {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        nodes = json.load(f)
    print(f"✅ Loaded {len(nodes)} nodes")
    return nodes

def save_nodes(nodes: List[Dict], filepath: str):
    """Save nodes to JSON file"""
    print(f"\n💾 Saving nodes to: {filepath}")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(nodes, f, indent=2, ensure_ascii=False)
    print(f"✅ Saved {len(nodes)} nodes")

def print_statistics(nodes: List[Dict]):
    """Print detailed statistics about embeddings"""
    embedded_nodes = [n for n in nodes if n.get("embedding") is not None]
    nodes_with_content = [n for n in nodes if n.get("content") and n["content"].strip()]
    
    print("\n" + "="*70)
    print("📊 EMBEDDING STATISTICS")
    print("="*70)
    print(f"Total nodes:                {len(nodes)}")
    print(f"Nodes with embeddings:      {len(embedded_nodes)}")
    print(f"Nodes with content:         {len(nodes_with_content)}")
    print(f"Embedding coverage:         {(len(embedded_nodes)/len(nodes)*100):.1f}%")
    
    if embedded_nodes:
        print(f"\nEmbedding details:")
        print(f"   Model:                   {embedded_nodes[0].get('embedding_model', 'N/A')}")
        print(f"   Dimension:               {embedded_nodes[0].get('embedding_dimension', 'N/A')}")
    
    # Category breakdown
    category_stats = {}
    for node in nodes:
        cat = node.get("category", "Unknown")
        if cat not in category_stats:
            category_stats[cat] = {"total": 0, "embedded": 0}
        category_stats[cat]["total"] += 1
        if node.get("embedding") is not None:
            category_stats[cat]["embedded"] += 1
    
    print(f"\n📁 Embeddings per category:")
    for cat, stats in sorted(category_stats.items()):
        coverage = (stats["embedded"] / stats["total"] * 100) if stats["total"] > 0 else 0
        print(f"   {cat:40s} {stats['embedded']:3d}/{stats['total']:3d} ({coverage:.0f}%)")
    
    print("="*70)

def main():
    """Main execution function"""
    print("="*70)
    print("🚀 RemoteLock Embedding Generator")
    print("="*70)
    
    # Load nodes
    try:
        nodes = load_nodes(INPUT_FILE)
    except FileNotFoundError:
        print(f"❌ Error: File '{INPUT_FILE}' not found!")
        print("   Please run the scraper first to generate the nodes file.")
        return
    except json.JSONDecodeError:
        print(f"❌ Error: Invalid JSON in '{INPUT_FILE}'")
        return
    
    # Initialize embedding generator
    generator = EmbeddingGenerator(MODEL_NAME)
    
    # Process nodes
    updated_nodes, processed_count = generator.process_nodes(nodes, batch_size=32)
    
    # Save updated nodes
    if processed_count > 0:
        save_nodes(updated_nodes, OUTPUT_FILE)
        print(f"\n💡 Original file kept as: {INPUT_FILE}")
        print(f"   New file with embeddings: {OUTPUT_FILE}")
    else:
        print(f"\n💡 No changes made - all embeddings already exist")
    
    # Print statistics
    print_statistics(updated_nodes)
    
    print("\n✅ Process complete! Ready for Neo4j import.")

if __name__ == "__main__":
    main()
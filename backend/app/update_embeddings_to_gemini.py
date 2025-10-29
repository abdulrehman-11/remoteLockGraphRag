#!/usr/bin/env python3
"""
Update Node Embeddings to Gemini API

This script updates existing Page node embeddings in Neo4j from SentenceTransformer
(384 dimensions) to Gemini API embeddings (768 dimensions) WITHOUT rebuilding the
entire knowledge graph.

Usage:
    python -m app.update_embeddings_to_gemini
"""

import os
import sys
import time
import logging
from dotenv import load_dotenv
from typing import List, Dict, Any
from neo4j import GraphDatabase
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/embedding_update.log')
    ]
)
logger = logging.getLogger(__name__)

# Configuration
NEO4J_URI = "neo4j+s://d3db84ff.databases.neo4j.io"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

BATCH_SIZE = 10  # Process 10 pages at a time for API efficiency

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set")
if not NEO4J_PASSWORD:
    raise ValueError("NEO4J_PASSWORD environment variable not set")


class EmbeddingUpdater:
    """Updates embeddings on existing Neo4j Page nodes"""

    def __init__(self):
        """Initialize Neo4j connection and Gemini embeddings"""
        logger.info("="*70)
        logger.info("EMBEDDING UPDATE TO GEMINI API")
        logger.info("="*70)

        # Connect to Neo4j
        logger.info("Connecting to Neo4j...")
        self.driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD),
            max_connection_pool_size=5
        )
        self.driver.verify_connectivity()
        logger.info("✓ Neo4j connection established")

        # Initialize Gemini embeddings
        logger.info("Initializing Gemini embeddings API...")
        self.embedder = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004",
            google_api_key=GEMINI_API_KEY
        )
        logger.info("✓ Gemini embeddings API initialized")

    def create_embedding_text(self, node: Dict) -> str:
        """
        Create embedding text in the EXACT same format as original embedding_generator_json.py
        to ensure consistency with the original embeddings approach.

        Format from architecturedetails.md lines 297-302:
        Title: {title}
        Category: {category}
        Subcategory: {subcategory}
        {content}
        """
        parts = []

        # Add title
        if node.get('title'):
            parts.append(f"Title: {node['title']}")

        # Add category
        if node.get('category'):
            parts.append(f"Category: {node['category']}")

        # Add subcategory
        if node.get('subcategory'):
            parts.append(f"Subcategory: {node['subcategory']}")

        # Add content
        if node.get('content'):
            parts.append(node['content'])

        return "\n".join(parts)

    def fetch_all_pages(self) -> List[Dict[str, Any]]:
        """Fetch all Page nodes from Neo4j"""
        logger.info("Fetching all Page nodes from Neo4j...")

        query = """
        MATCH (p:Page)
        RETURN p.id AS id,
               p.slug AS slug,
               p.title AS title,
               p.content AS content,
               p.category AS category,
               p.subcategory AS subcategory,
               p.url AS url
        ORDER BY p.id
        """

        with self.driver.session() as session:
            result = session.run(query)
            pages = [dict(record) for record in result]

        logger.info(f"✓ Found {len(pages)} Page nodes to update")
        return pages

    def update_page_embedding(self, session, page_id: str, embedding: List[float]) -> bool:
        """Update a single page's embedding in Neo4j"""
        try:
            query = """
            MATCH (p:Page {id: $id})
            SET p.embedding = $embedding,
                p.embedding_model = 'text-embedding-004',
                p.embedding_dimension = $dimension,
                p.embedding_updated_at = timestamp()
            RETURN p.slug AS slug
            """

            result = session.run(
                query,
                id=page_id,
                embedding=embedding,
                dimension=len(embedding)
            )

            record = result.single()
            return record is not None

        except Exception as e:
            logger.error(f"Failed to update page {page_id}: {e}")
            return False

    def update_embeddings_batch(self, pages: List[Dict]) -> tuple:
        """
        Update embeddings for a batch of pages
        Returns: (success_count, failed_count)
        """
        success_count = 0
        failed_count = 0

        # Prepare embedding texts
        embedding_texts = []
        for page in pages:
            text = self.create_embedding_text(page)
            embedding_texts.append(text)

        try:
            # Generate embeddings via Gemini API (batch)
            logger.info(f"  Generating {len(pages)} embeddings via Gemini API...")
            embeddings = self.embedder.embed_documents(embedding_texts)

            # Update each page in Neo4j
            with self.driver.session() as session:
                for page, embedding in zip(pages, embeddings):
                    success = self.update_page_embedding(session, page['id'], embedding)

                    if success:
                        success_count += 1
                        logger.info(f"  ✓ Updated: {page['slug']} (id: {page['id']}, {len(embedding)} dims)")
                    else:
                        failed_count += 1
                        logger.error(f"  ✗ Failed: {page['slug']} (id: {page['id']})")

        except Exception as e:
            logger.error(f"Batch processing error: {e}")
            failed_count += len(pages)

        return success_count, failed_count

    def rebuild_vector_index(self):
        """Drop old vector index and create new one with 768 dimensions"""
        logger.info("="*70)
        logger.info("REBUILDING VECTOR INDEX")
        logger.info("="*70)

        with self.driver.session() as session:
            # Drop old index
            logger.info("Dropping old vector index (384 dimensions)...")
            try:
                session.run("DROP INDEX page_embeddings IF EXISTS")
                logger.info("✓ Old index dropped")
            except Exception as e:
                logger.warning(f"Could not drop old index (may not exist): {e}")

            # Create new index
            logger.info("Creating new vector index (768 dimensions)...")
            try:
                session.run("""
                    CREATE VECTOR INDEX page_embeddings IF NOT EXISTS
                    FOR (p:Page) ON (p.embedding)
                    OPTIONS {
                        indexConfig: {
                            `vector.dimensions`: 768,
                            `vector.similarity_function`: 'cosine'
                        }
                    }
                """)
                logger.info("✓ New vector index created (768 dimensions)")
                logger.info("  Note: Index may take 1-2 minutes to build")
            except Exception as e:
                logger.error(f"Failed to create vector index: {e}")
                raise

    def run(self):
        """Main execution method"""
        start_time = time.time()

        try:
            # Fetch all pages
            pages = self.fetch_all_pages()

            if not pages:
                logger.warning("No pages found to update!")
                return

            total_pages = len(pages)
            total_success = 0
            total_failed = 0

            logger.info("="*70)
            logger.info(f"PROCESSING {total_pages} PAGES IN BATCHES OF {BATCH_SIZE}")
            logger.info("="*70)

            # Process in batches
            for i in range(0, total_pages, BATCH_SIZE):
                batch = pages[i:i + BATCH_SIZE]
                batch_num = (i // BATCH_SIZE) + 1
                total_batches = (total_pages + BATCH_SIZE - 1) // BATCH_SIZE

                logger.info(f"\nProcessing batch {batch_num}/{total_batches} (pages {i+1}-{i+len(batch)})...")

                success, failed = self.update_embeddings_batch(batch)
                total_success += success
                total_failed += failed

                # Progress update
                progress_pct = ((i + len(batch)) / total_pages) * 100
                logger.info(f"Progress: {i+len(batch)}/{total_pages} ({progress_pct:.1f}%)")
                logger.info(f"Success: {total_success}, Failed: {total_failed}")

                # Rate limiting: small delay between batches
                if i + BATCH_SIZE < total_pages:
                    time.sleep(0.5)

            # Rebuild vector index
            logger.info("\n")
            self.rebuild_vector_index()

            # Summary
            elapsed_time = time.time() - start_time
            logger.info("="*70)
            logger.info("UPDATE COMPLETE")
            logger.info("="*70)
            logger.info(f"Total pages processed: {total_pages}")
            logger.info(f"Successfully updated: {total_success}")
            logger.info(f"Failed: {total_failed}")
            logger.info(f"Time elapsed: {elapsed_time:.1f} seconds ({elapsed_time/60:.1f} minutes)")

            if total_failed == 0:
                logger.info("✓ All embeddings updated successfully from 384→768 dimensions!")
            else:
                logger.warning(f"⚠ {total_failed} pages failed to update - check logs")

        except KeyboardInterrupt:
            logger.warning("\n\n⚠ Update interrupted by user")
            logger.info("You can re-run this script to continue from where it left off")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            sys.exit(1)
        finally:
            self.close()

    def close(self):
        """Close Neo4j connection"""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed")


def main():
    """Entry point"""
    print("\n" + "="*70)
    print("RemoteLock Embedding Update Script")
    print("Updates embeddings from SentenceTransformer (384) to Gemini API (768)")
    print("="*70 + "\n")

    updater = EmbeddingUpdater()
    updater.run()


if __name__ == "__main__":
    main()

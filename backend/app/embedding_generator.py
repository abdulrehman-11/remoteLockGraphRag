# pip install sentence-transformers
# python add_embeddings_open_source.py


# add_embeddings_open_source.py
import json
from sentence_transformers import SentenceTransformer

INPUT_FILE = "troubleshooting.json"
OUTPUT_FILE = "troubleshooting_with_embeddings.json"

# You can switch to another model, e.g. "all-mpnet-base-v2" (higher quality, slower)
MODEL_NAME = "all-MiniLM-L6-v2"

print(f"Loading model: {MODEL_NAME}")
model = SentenceTransformer(MODEL_NAME)

def generate_embedding(text: str):
    """Generate embedding vector for given text"""
    if not text.strip():
        return []
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()

def main():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        records = json.load(f)

    updated = []
    for rec in records:
        if not rec.get("vector"):  # empty or None
            print(f"→ Creating embedding for: {rec.get('title','(no title)')}")
            try:
                rec["vector"] = generate_embedding(rec.get("content_text", ""))
            except Exception as e:
                print(f"❌ Failed on {rec.get('url')}: {e}")
                rec["vector"] = []
        updated.append(rec)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(updated, f, indent=2, ensure_ascii=False)

    print(f"✅ Updated file saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()


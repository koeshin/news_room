import os
import json
import chromadb
from sentence_transformers import SentenceTransformer
from chromadb.utils import embedding_functions

# --- Configuration ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Data is in the project root, one level up from this script
# --- Configuration ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Data is in the project root, one level up from this script
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "scraped_data_history")
# DB is in the same directory as this script -> NO, it should be in parent? ORIGINAL WAS IN SCRIPT_DIR (news_room_v2). Now script is in news_room_v2/core. DB should be in news_room_v2/chroma_db. So ".." is correct.
DB_PATH = os.path.join(SCRIPT_DIR, "..", "chroma_db")
COLLECTION_NAME = "news_articles"
MODEL_NAME = "intfloat/multilingual-e5-small"

def get_scraped_files(root_dir):
    files = []
    for dirpath, _, filenames in os.walk(root_dir):
        for f in filenames:
            if f.endswith(".json"):
                files.append(os.path.join(dirpath, f))
    return files

def main():
    print(f"🔄 Initializing Vector Store in {DB_PATH}...")
    
    # 1. Setup ChromaDB
    client = chromadb.PersistentClient(path=DB_PATH)
    
    # 2. Setup Embedding Model
    print(f"Loading Embedding Model ({MODEL_NAME})...")
    model = SentenceTransformer(MODEL_NAME)
    
    # Custom embedding function for Chroma
    class E5EmbeddingFunction(chromadb.EmbeddingFunction):
        def __call__(self, input: list) -> list:
            # Add 'passage: ' prefix for documents
            processed_input = [f"passage: {text}" for text in input]
            embeddings = model.encode(processed_input, normalize_embeddings=True)
            return embeddings.tolist()

    embedding_fn = E5EmbeddingFunction()

    # Get or Create Collection
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"} # Cosine similarity
    )

    # 3. Process Data
    files = get_scraped_files(DATA_DIR)
    print(f"📂 Found {len(files)} JSON files to process.")
    
    total_articles = 0
    
    for file_path in files:
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                articles = json.load(f)
            except json.JSONDecodeError:
                print(f"❌ Error reading {file_path}")
                continue
            
            ids = []
            documents = []
            metadatas = []
            
            for article in articles:
                url = article.get("url", "")
                if not url: continue
                
                title = article.get("title", "")
                subtitle = article.get("subtitle", "")
                # Clean up summary sentences (remove empty strings)
                summary = " ".join([s for s in article.get("summary_sentences", []) if s])
                
                # Combine for embedding content
                content = f"{title} {subtitle} {summary}".strip()
                if not content: continue
                
                # Metadata
                meta = {
                    "url": url,
                    "title": title,
                    "media_code": article.get("media_code", ""),
                    "media_name": article.get("media_name", ""),
                    "date": article.get("date", ""),
                    "page": article.get("page", "")
                }
                
                ids.append(url) # Use URL as ID
                documents.append(content)
                metadatas.append(meta)
            
            if ids:
                # Upsert (Insert or Update)
                collection.upsert(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas
                )
                total_articles += len(ids)
                print(f"✅ Processed {len(ids)} articles from {os.path.basename(file_path)}")

    print(f"\n🎉 Finished! Total {total_articles} articles stored in Vector DB.")

if __name__ == "__main__":
    main()

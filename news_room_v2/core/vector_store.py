import os
import json
import chromadb
from sentence_transformers import SentenceTransformer
from chromadb.utils import embedding_functions
import argparse

# --- Configuration ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Data is in the project root, one level up from this script
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "scraped_data_history")
# DB is in the parent directory of 'core'
DB_PATH = os.path.join(SCRIPT_DIR, "..", "chroma_db")
COLLECTION_NAME = "news_articles"
MODEL_NAME = "intfloat/multilingual-e5-small"

def get_scraped_files(root_dir, start_date=None, end_date=None):
    files = []
    if not os.path.exists(root_dir):
        return []
        
    start_int = int(start_date) if start_date else None
    end_int = int(end_date) if end_date else None

    for dirpath, _, filenames in os.walk(root_dir):
        for f in filenames:
            if f.endswith(".json"):
                # File format: {OID}_{YYYYMMDD}.json
                try:
                    parts = f.replace('.json', '').split('_')
                    if len(parts) < 2: continue
                    date_str = parts[-1]
                    
                    if len(date_str) != 8 or not date_str.isdigit():
                        continue
                        
                    date_int = int(date_str)
                    
                    if start_int and date_int < start_int:
                        continue
                    if end_int and date_int > end_int:
                        continue
                        
                    files.append(os.path.join(dirpath, f))
                except:
                    continue
    return files

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start_date", type=str, help="Start date (YYYYMMDD)")
    parser.add_argument("--end_date", type=str, help="End date (YYYYMMDD)")
    args = parser.parse_args()

    print(f"Initializing Vector Store in {DB_PATH}...")
    if args.start_date:
        print(f"Filter Start Date: {args.start_date}")
    if args.end_date:
        print(f"Filter End Date: {args.end_date}")
    
    # 1. Setup ChromaDB
    client = chromadb.PersistentClient(path=DB_PATH)
    
    # 2. Setup Embedding Model
    print(f"Loading Embedding Model ({MODEL_NAME})...")
    model = SentenceTransformer(MODEL_NAME)
    
    # Custom embedding function for Chroma
    class E5EmbeddingFunction(chromadb.EmbeddingFunction):
        def __init__(self, model):
            self.model = model
            
        def __call__(self, input: list) -> list:
            # Add 'passage: ' prefix for documents
            processed_input = [f"passage: {text}" for text in input]
            embeddings = self.model.encode(processed_input, normalize_embeddings=True)
            return embeddings.tolist()

    embedding_fn = E5EmbeddingFunction(model)

    # Get or Create Collection
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"} # Cosine similarity
    )

    # 3. Process Data
    files = get_scraped_files(DATA_DIR, args.start_date, args.end_date)
    print(f"Found {len(files)} JSON files to process.")
    
    total_articles = 0
    
    for file_path in files:
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                articles = json.load(f)
            except json.JSONDecodeError:
                print(f"Error reading {file_path}")
                continue
            
            ids = []
            documents = []
            metadatas = []
            
            for article in articles:
                url = article.get("url", "")
                if not url: continue
                
                title = article.get("title", "")
                subtitle = article.get("subtitle", "")
                # Clean up summary sentences
                summary_sentences = article.get("summary_sentences", [])
                if isinstance(summary_sentences, list):
                    summary = " ".join([s for s in summary_sentences if s])
                else:
                    summary = str(summary_sentences)
                
                # Combine for embedding content
                content = f"{title} {subtitle} {summary}".strip()
                if not content: continue
                
                # Extract Keywords (List of Strings)
                # ChromaDB does not support lists in metadata (unless newer versions do, but safe is string)
                # We will join them by comma for storage
                keywords_list = article.get("keywords", [])
                keywords_str = ",".join(keywords_list) if isinstance(keywords_list, list) else str(keywords_list)
                
                # Metadata
                meta = {
                    "url": url,
                    "title": title,
                    "media_code": article.get("media_code", ""),
                    "media_name": article.get("media_name", ""),
                    "date": article.get("date", ""),
                    "page": article.get("page", ""),
                    "keywords": keywords_str # Store as string
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
                print(f"Processed {len(ids)} articles from {os.path.basename(file_path)}")

    print(f"\nFinished! Total {total_articles} articles stored in Vector DB.")

if __name__ == "__main__":
    main()

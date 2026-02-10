import chromadb
import numpy as np
import json
import os
import argparse
import re
from datetime import datetime, timedelta
from sentence_transformers import SentenceTransformer

# --- Configuration ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Data is in the project root, one level up from this script
DB_PATH = os.path.join(SCRIPT_DIR, "..", "chroma_db")
PERSONA_DIR = os.path.join(SCRIPT_DIR, "..", "personas")
COLLECTION_NAME = "news_articles"
MODEL_NAME = "intfloat/multilingual-e5-small"

class E5EmbeddingFunction(chromadb.EmbeddingFunction):
    def __init__(self, model):
        self.model = model
        
    def __call__(self, input: list) -> list:
        processed_input = [f"query: {text}" for text in input]
        embeddings = self.model.encode(processed_input, normalize_embeddings=True)
        return embeddings.tolist()

def init_chromadb():
    client = chromadb.PersistentClient(path=DB_PATH)
    model = SentenceTransformer(MODEL_NAME)
    embedding_fn = E5EmbeddingFunction(model)
    return client, embedding_fn, model

def parse_persona_markdown(persona_name):
    """
    Parses the persona markdown file to extract:
    1. Positive Keywords (Interests)
    2. Negative Keywords (Filtering)
    """
    file_path = os.path.join(PERSONA_DIR, f"persona_{persona_name}.md")
    if not os.path.exists(file_path):
        return None

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    data = {
        "interests": [],
        "positive_keywords": [],
        "negative_keywords": [] # Explicit negative keywords
    }

    # Extract Key Interests
    # ## Characteristics
    # - **Key Interests:** IT, Tech, ...
    match_interests = re.search(r'\*\*Key Interests:\*\*(.*?)\n', content)
    if match_interests:
        interests_str = match_interests.group(1).strip()
        data["interests"] = [x.strip() for x in interests_str.split(',')]

    # Extract Keywords for Filtering (Positive)
    # ## Keywords for Filtering
    # - AI, ...
    # - ...
    # (Matches lines starting with - under the header)
    
    # Simple parsing: Find section and read bullets
    lines = content.split('\n')
    section = None
    
    for line in lines:
        line = line.strip()
        if line.startswith("## Keywords for Filtering"):
            section = "positive"
            continue
        elif line.startswith("## Negative Keywords"): # Future proofing
            section = "negative"
            continue
        elif line.startswith("## "):
            section = None
            
        if section == "positive" and line.startswith("-"):
            # Remove '- ' and split by comma
            keywords = line[2:].strip()
            data["positive_keywords"].extend([k.strip() for k in keywords.split(',')])
            
        if section == "negative" and line.startswith("-"):
            keywords = line[2:].strip()
            data["negative_keywords"].extend([k.strip() for k in keywords.split(',')])

    return data

def recommend_articles(persona_name, json_output=None):
    client, embedding_fn, model = init_chromadb()
    collection = client.get_collection(name=COLLECTION_NAME, embedding_function=embedding_fn)
    
    persona_data = parse_persona_markdown(persona_name)
    if not persona_data:
        print(f"❌ Persona {persona_name} not found.")
        return

    print(f"🔍 Persona '{persona_name}' Loaded.")
    print(f"  - Interests: {persona_data['interests']}")
    print(f"  - Filters: {persona_data['positive_keywords']}")
    print(f"  - Negatives: {persona_data['negative_keywords']}")

    # 1. Query Vector DB using detailed interests
    query_text = " ".join(persona_data["interests"] + persona_data["positive_keywords"])
    
    # Fetch more candidates to filter later
    results = collection.query(
        query_texts=[query_text],
        n_results=100,
        include=['metadatas', 'documents', 'distances'] 
        # Note: Chroma returns distances. Cosine similarity = 1 - distance (if using cosine distance)
        # But we used 'hnsw:space': 'cosine' which returns cosine DISTANCE by default in Chroma.
        # Cosine Similarity = 1 - Cosine Distance.
    )
    
    candidates = []
    ids = results['ids'][0]
    distances = results['distances'][0]
    metadatas = results['metadatas'][0]
    documents = results['documents'][0]
    
    for i in range(len(ids)):
        # Calculate Similarity Score (0 to 1)
        # Cosine distance ranges from 0 (identical) to 2 (opposite).
        # We want similarity.
        similarity = 1 - distances[i] 
        
        url = ids[i]
        meta = metadatas[i]
        doc = documents[i]
        
        # 2. Apply Negative Filtering
        penalty = 0.0
        
        # Check title and doc for negative keywords
        full_text = f"{meta.get('title', '')} {doc}".lower()
        
        for nk in persona_data["negative_keywords"]:
            if nk.lower() in full_text:
                penalty += 0.3 # Strong penalty for explicit negative keywords
                # print(f"  [Penalty] '{nk}' found in {meta['title']}")
        
        final_score = similarity - penalty
        
        candidates.append({
            "id": url,
            "title": meta.get('title', ''),
            "media": meta.get('media_name', ''),
            "date": meta.get('date', ''),
            "summary": doc,
            "score": final_score,
            "original_score": similarity,
            "penalty": penalty
        })
        
    # 3. Sort by Final Score
    candidates.sort(key=lambda x: x['score'], reverse=True)
    
    # Top 10
    top_10 = candidates[:10]
    
    print(f"\n🏆 Top 10 Recommendations for {persona_name}:")
    for rank, item in enumerate(top_10, 1):
        print(f"  {rank}. [{item['media']}] {item['title']}")
        print(f"     Score: {item['score']:.4f} (Sim: {item['original_score']:.4f} - Pen: {item['penalty']:.1f})")
    
    if json_output:
        with open(json_output, "w", encoding="utf-8") as f:
            json.dump(top_10, f, ensure_ascii=False, indent=2)
        print(f"\n✅ Recommendations saved to {json_output}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--persona", type=str, required=True, help="Target persona name (e.g., 20s)")
    parser.add_argument("--output", type=str, help="Output JSON file")
    args = parser.parse_args()
    
    recommend_articles(args.persona, args.output)

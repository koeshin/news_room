import chromadb
import numpy as np
import json
import os
import argparse
from sentence_transformers import SentenceTransformer

# --- Configuration ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "..", "chroma_db")
COLLECTION_NAME = "news_articles"
MODEL_NAME = "intfloat/multilingual-e5-small"

# Define Persona Rules
PERSONA_RULES = {
    "20s": {
        "special_media": ["030", "076"],
        "base_media": ["023", "025", "020"],
        "keywords": ["AI", "인공지능", "스타트업", "채용", "공채", "취업", "코딩", "개발자", "팝업", "핫플레이스", "넷플릭스", "아이돌", "손흥민", "축구", "야구", "IT", "테크", "과학"]
    },
    "30s": {
        "special_media": ["009", "015"],
        "base_media": ["023", "025", "020"],
        "keywords": ["아파트", "분양", "청약", "금리", "주식", "코스피", "삼성전자", "반도체", "투자", "재테크", "전세", "월세", "대출", "금융", "경제", "증권", "부동산"]
    },
    "50s": {
        "special_media": ["021", "081"],
        "base_media": ["023", "025", "020"],
        "keywords": ["사설", "칼럼", "여당", "야당", "국회", "대통령", "정책", "건강", "등산", "골프", "노후", "연금", "지방", "행정", "정치", "사회", "오피니언"]
    }
}

class E5EmbeddingFunction(chromadb.EmbeddingFunction):
    def __init__(self, model):
        self.model = model
        
    def __call__(self, input: list) -> list:
        processed_input = [f"query: {text}" for text in input]
        embeddings = self.model.encode(processed_input, normalize_embeddings=True)
        return embeddings.tolist()

def init_chromadb():
    client = chromadb.PersistentClient(path=DB_PATH)
    print(f" Loading Embedding Model ({MODEL_NAME})...")
    model = SentenceTransformer(MODEL_NAME)
    embedding_fn = E5EmbeddingFunction(model)
    return client, embedding_fn

def fetch_all_metadata(client):
    try:
        # Re-initializing embedding function here might be redundant if we just want metadata
        # But get_collection needs it if we want to query by embedding later.
        # For simple fetch, we can skip it, but let's keep it safe.
        model = SentenceTransformer(MODEL_NAME)
        embedding_fn = E5EmbeddingFunction(model)
        collection = client.get_collection(name=COLLECTION_NAME, embedding_function=embedding_fn)
        
        result = collection.get(include=['metadatas', 'documents', 'embeddings'])
        
        all_articles = []
        for i in range(len(result['ids'])):
            article = {
                'id': result['ids'][i],
                'metadata': result['metadatas'][i],
                'document': result['documents'][i],
                'embedding': np.array(result['embeddings'][i])
            }
            all_articles.append(article)
        return all_articles
    except Exception as e:
        print(f" Error fetching data: {e}")
        return []

def match_persona_rule(media_code, title, content, rules):
    if media_code in rules["special_media"]:
        return True
    if media_code in rules["base_media"]:
        text = str(title) + " " + str(content)
        for kw in rules["keywords"]:
            if kw.lower() in text.lower():
                return True
    return False

def get_persona_history_vectors(rules, train_articles):
    history_vectors = []
    for article in train_articles:
        meta = article['metadata']
        doc = article['document']
        if match_persona_rule(meta['media_code'], meta['title'], doc, rules):
            history_vectors.append(article['embedding'])
    return history_vectors

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json_output", type=str, help="Save recommendations to JSON file")
    args = parser.parse_args()

    print("Initializing Simulation...")
    client, _ = init_chromadb()
    
    print("Fetching all metadata...")
    all_articles = fetch_all_metadata(client)
    print(f" Total Articles: {len(all_articles)}")

    if not all_articles:
        return

    # Split Train/Test
    # Simple logic: 2025 is train, 2026 is test
    train_articles = [a for a in all_articles if a['metadata'].get('date', '').startswith('2025')]
    test_articles_2026 = [a for a in all_articles if a['metadata'].get('date', '').startswith('2026')]
    
    print(f"Train Set (2025): {len(train_articles)}")
    print(f"Test Set (2026): {len(test_articles_2026)}")
    
    # Allow running without train data (use fallback)
    if not train_articles and not test_articles_2026:
        print("No data found. Skipping.")
        return

    all_recommendations = []

    for p_name, rules in PERSONA_RULES.items():
        print(f"\n Simulating Persona: {p_name}")
    
      
        # 1. Profile Building
        history_vectors = get_persona_history_vectors(rules, train_articles)
        print(f"  Read {len(history_vectors)} articles in 2025.")
        
        if not history_vectors:
            print("  No history found. Skipping.")
            continue
            
        persona_vector = np.mean(history_vectors, axis=0)
        
        # 2. Recommendation
        # If no history, use keywords to build a synthetic profile vector
        if not history_vectors:
             print("  No history found. Using Keywords for synthetic profile.")
             keywords_text = " ".join(rules["keywords"])
             model = SentenceTransformer(MODEL_NAME)
             persona_vector = model.encode([f"query: {keywords_text}"], normalize_embeddings=True)[0]
        else:
             persona_vector = np.mean(history_vectors, axis=0)

        # Get all candidates (test set)
        test_vectors = np.array([a['embedding'] for a in test_articles_2026])
        if len(test_vectors) == 0:
            print("  No test articles found for 2026.")
            continue
            
        scores = np.dot(test_vectors, persona_vector)
        
        # --- NEW LOGIC: Recency + Threshold ---
        from datetime import datetime, timedelta
        today = datetime.now()
        seven_days_ago = (today - timedelta(days=7)).strftime("%Y%m%d")
        
        candidates = []
        for idx, article in enumerate(test_articles_2026):
            score = scores[idx]
            date_str = article['metadata'].get('date', '19000101')
            
            # Threshold Check
            if score < 0.6:
                continue
                
            candidates.append({
                "article": article,
                "score": score,
                "date": date_str,
                "is_recent": date_str >= seven_days_ago
            })
            
        # Sort Logic: Recent first, then by Score
        # Group 1: Recent & High Score
        # Group 2: Old & High Score
        # Inside each group, sort by Score DESC
        
        recent_group = sorted([c for c in candidates if c['is_recent']], key=lambda x: x['score'], reverse=True)
        old_group = sorted([c for c in candidates if not c['is_recent']], key=lambda x: x['score'], reverse=True)
        
        final_candidates = recent_group + old_group
        
        top_k = 50 # Generate pool of 50
        top_candidates = final_candidates[:top_k]
        
        print(f" Top {len(top_candidates)} Recommendations (Threshold >= 0.6, Recent First):")
        
        for rank, item in enumerate(top_candidates, 1):
            article = item['article']
            score = item['score']
            is_recent = " if item['is_recent'] else   "
            print(f"    {rank}. {is_recent} [{article['metadata']['media_name']}] {article['metadata']['title']} (Score: {score:.4f}, Date: {item['date']})")
            
            all_recommendations.append({
                "persona": p_name,
                "rank": rank,
                "id": article['id'],
                "title": article['metadata']['title'],
                "media": article['metadata']['media_name'],
                "date": item['date'],
                "summary": article['document'][:200] + "...",
                "full_text": article['document'],
                "score": float(score)
            })

    if args.json_output:
        with open(args.json_output, "w") as f:
            json.dump(all_recommendations, f, ensure_ascii=False, indent=2)
        print(f"\n Recommendations saved to {args.json_output}")

if __name__ == "__main__":
    main()

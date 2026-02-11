import chromadb
import numpy as np
import json
import os
import argparse
import re
import random
from datetime import datetime, timedelta
from sentence_transformers import SentenceTransformer
import google.generativeai as genai

# Add project root to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
import sys
sys.path.append(PROJECT_ROOT)
import storage

# --- Configuration ---
DB_PATH = os.path.join(SCRIPT_DIR, "..", "chroma_db")
PERSONA_DIR = os.path.join(SCRIPT_DIR, "..", "personas")
COLLECTION_NAME = "news_articles"
MODEL_NAME = "intfloat/multilingual-e5-small"
DEFAULT_OUTPUT_FILE = os.path.join(PROJECT_ROOT, "data", "recommands.json")

# Load Env
env_path = os.path.join(PROJECT_ROOT, "..", ".env") # Assumed location based on previous context
if os.path.exists(env_path):
    with open(env_path, "r") as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                key, value = line.strip().split("=", 1)
                os.environ[key] = value

if "GOOGLE_API_KEY" in os.environ:
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

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
    3. Interest Groups (Dict)
    4. Sentence Preferences (List)
    """
    file_path = os.path.join(PERSONA_DIR, f"persona_{persona_name}.md")
    if not os.path.exists(file_path):
        return None

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    data = {
        "interests": [],
        "positive_keywords": [],
        "negative_keywords": [],
        "interest_groups": {},
        "sentence_preferences": [],
        "negative_sentences": []
    }

    lines = content.split('\n')
    section = None
    
    for line in lines:
        line = line.strip()
        if not line: continue
        
        if line.startswith("## Characteristics"):
            section = "chars"
            continue
        elif line.startswith("## Interest Groups"):
            section = "groups"
            continue
        elif line.startswith("## Sentence Preferences"):
            section = "sentences"
            continue
        elif line.startswith("## Keywords for Filtering"):
            section = "positive"
            continue
        elif line.startswith("## Negative Keywords"):
            section = "negative"
            continue
        elif line.startswith("## Negative Sentences"):
            section = "negative_sentences"
            continue
        elif line.startswith("##"):
            section = None
            
        # Parsing Logic
        if section == "chars" and line.startswith("- **Key Interests:**"):
            val = line.split(":", 1)[1].strip()
            data["interests"] = [x.strip() for x in val.split(',')]
            
        elif section == "groups" and line.startswith("- **"):
            # - **Tech:** AI, Startups...
            parts = line.replace("- **", "").split(":**", 1)
            if len(parts) == 2:
                g_name = parts[0].strip()
                g_vals = [x.strip() for x in parts[1].split(',')]
                data["interest_groups"][g_name] = g_vals
                
        elif section == "sentences" and line.startswith("-"):
            data["sentence_preferences"].append(line[1:].strip())
            
        elif section == "positive" and line.startswith("-"):
            keywords = line[2:].strip()
            data["positive_keywords"].extend([k.strip() for k in keywords.split(',')])
            
        elif section == "negative" and line.startswith("-"):
            keywords = line[2:].strip()
            data["negative_keywords"].extend([k.strip() for k in keywords.split(',')])

        elif section == "negative_sentences" and line.startswith("-"):
            data["negative_sentences"].append(line[1:].strip())

    return data

def get_recent_scraps(limit=5):
    """Get recent scraps to use for 'Why This' explainability."""
    scraps_data = storage.load_scraps()
    all_scraps = []
    for date_str, items in scraps_data.items():
        all_scraps.extend(items)
    all_scraps.sort(key=lambda x: x.get('scrapped_at', ''), reverse=True)
    return all_scraps[:limit]

def llm_rerank(candidates, persona_data):
    """
    Reranks the candidates using Gemini based on sentence preferences.
    Returns the top candidates with updated scores and reasoning.
    """
    if not candidates:
        return []
        
    print(f"🤖 LLM Reranking {len(candidates)} candidates...")
    
    model = genai.GenerativeModel('gemini-3-flash-preview')
    
    # Prepare input for LLM
    articles_lite = []
    for i, c in enumerate(candidates):
        articles_lite.append({
            "id": i, # Rank/Index
            "title": c['title'], # Including title as "Link Text" context
            "url": c['id'],      # Article Link
            "keywords": c.get('keywords', [])
        })
    
    persona_desc = "\n".join([f"- {s}" for s in persona_data['sentence_preferences']])
    
    negative_sentences_text = '\n'.join([f'- {s}' for s in persona_data.get('negative_sentences', [])])
    
    prompt = f"""
    You are an expert news curator for a specific user.
    
    User Persona Sentences:
    {persona_desc}

    User Negative Sentences (AVOID these topics):
    {negative_sentences_text}
    
    User Interest Groups:
    {json.dumps(persona_data['interest_groups'], indent=1, ensure_ascii=False)}
    
    Task:
    1. Identify the news article directly through the link (URL) and keywords.
    2. Create the optimal news recommendation ranking for the persona.
    3. Select the TOP 10 articles.
    
    Input Articles (Rank, Link, Keywords):
    {json.dumps(articles_lite, indent=1, ensure_ascii=False)}
    
    Output JSON Format:
    [
        {{"id": 0, "rank": 1, "reason": "Reason string"}},
        {{"id": 5, "rank": 2, "reason": "Reason string"}},
        ...
    ]
    Return ONLY valid JSON.
    """
    
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```json"): text = text[7:]
        if text.endswith("```"): text = text[:-3]
        text = text.strip()
        
        ranking = json.loads(text)
        
        # Map back to candidates
        final_list = []
        for rank_item in ranking:
            idx = rank_item.get('id')
            if idx is not None and 0 <= idx < len(candidates):
                cand = candidates[idx]
                cand['rank'] = rank_item.get('rank')
                cand['reason'] = rank_item.get('reason')
                cand['llm_selected'] = True
                final_list.append(cand)
                
        # Fill rest with non-selected if needed (but usually top 10 is enough)
        final_list.sort(key=lambda x: x['rank'])
        return final_list
        
    except Exception as e:
        print(f"❌ LLM Reranking failed: {e}")
        # Fallback: return original top 10
        return candidates[:10]

def recommend_articles(persona_name, json_output=DEFAULT_OUTPUT_FILE):
    client, embedding_fn, model = init_chromadb()
    collection = client.get_collection(name=COLLECTION_NAME, embedding_function=embedding_fn)
    
    persona_data = parse_persona_markdown(persona_name)
    if not persona_data:
        print(f"❌ Persona {persona_name} not found.")
        return

    print(f"🔍 Persona '{persona_name}' Loaded.")
    print(f"  - Groups: {list(persona_data['interest_groups'].keys())}")
    
    # --- 1. Date Priority Fetching ---
    target_count = 50
    candidates = []
    seen_ids = set()
    
    today = datetime.now()
    dates_to_check = [(today - timedelta(days=i)).strftime("%Y%m%d") for i in range(3)]
    
    # Encode vectors for EACH interest group
    group_vectors = {}
    for g_name, keywords in persona_data['interest_groups'].items():
        query = f"query: {' '.join(keywords)}"
        vec = model.encode([query], normalize_embeddings=True)[0]
        group_vectors[g_name] = vec
    
    # Also create a composite General vector
    general_query = " ".join(persona_data["interests"] + persona_data["positive_keywords"])
    
    # Fetch Loop
    for date_str in dates_to_check:
        if len(candidates) >= target_count:
            break
            
        print(f"  Fetching from {date_str}...")
        results = collection.query(
            query_texts=[general_query],
            n_results=target_count, 
            where={"date": date_str}, 
            include=['metadatas', 'documents', 'embeddings'] # Need embeddings for group scoring
        )
        
        ids = results['ids'][0]
        metadatas = results['metadatas'][0]
        documents = results['documents'][0]
        embeddings = results['embeddings'][0]
        
        for i in range(len(ids)):
            if ids[i] in seen_ids: continue
            
            # --- Advanced Group Scoring ---
            # Calculate max similarity across all groups
            art_vec = np.array(embeddings[i])
            # Normalize just in case (Chroma returns normalized usually if set?)
            # But let's assume it's normalized or we compute cosine similarity correctly
            # Cosine Sim = dot product of normalized vectors
            
            max_group_score = -1.0
            best_group = "General"
            
            for g_name, g_vec in group_vectors.items():
                score = np.dot(art_vec, g_vec)
                if score > max_group_score:
                    max_group_score = score
                    best_group = g_name
            
            # Apply Filter Penalty
            penalty = 0.0
            full_text = f"{metadatas[i].get('title', '')} {documents[i]}".lower()
            for nk in persona_data["negative_keywords"]:
                if nk.lower() in full_text:
                    penalty += 0.3
            
            final_score = max_group_score - penalty
            
            cand = {
                "id": ids[i],
                "title": metadatas[i].get('title', ''),
                "media": metadatas[i].get('media_name', ''),
                "date": metadatas[i].get('date', ''),
                "summary": documents[i],
                "keywords": metadatas[i].get('keywords', []), # Assuming scraping saved this
                "score": float(final_score),
                "matched_group": best_group,
                "penalty": penalty
            }
            
            if final_score > 0.3: # Threshold
                candidates.append(cand)
                seen_ids.add(ids[i])

    # Sort by initial vector score
    candidates.sort(key=lambda x: x['score'], reverse=True)
    candidates = candidates[:50] # Take top 50 for Reranking
    
    print(f"  Prepared {len(candidates)} candidates for Reranking.")
    
    print("\n📊 [Comparison] Top 5 Vector-Only Recommendations:")
    for i, c in enumerate(candidates[:5]):
        print(f"  {i+1}. {c['title']} (Score: {c['score']:.4f})")

    # --- 2. Serendipity Injection (Must Read) ---
    # We still want this even with LLM reranking? Yes.
    # LLM can rank them, but we need to inject them into the candidate pool or force them.
    # Let's force 2 serendipity items.
    
    serendipity_candidates = []
    try:
        serendipity_query = "사회" 
        s_results = collection.query(
            query_texts=[serendipity_query],
            n_results=10,
            include=['metadatas', 'documents']
        )
        s_ids = s_results['ids'][0]
        s_metas = s_results['metadatas'][0]
        s_docs = s_results['documents'][0]
        
        for i in range(len(s_ids)):
            if s_ids[i] not in seen_ids:
                item = {
                     "id": s_ids[i],
                     "title": s_metas[i].get('title', ''),
                     "media": s_metas[i].get('media_name', ''),
                     "date": s_metas[i].get('date', ''),
                     "summary": s_docs[i],
                     "score": 0.0,
                     "reason": "Must Read (Breaking/Society)",
                     "is_must_read": True
                }
                serendipity_candidates.append(item)
    except:
        pass
        
    must_reads = random.sample(serendipity_candidates, min(2, len(serendipity_candidates))) if serendipity_candidates else []

    # --- 3. LLM Reranking ---
    # Only rerank the organic candidates
    top_candidates = llm_rerank(candidates, persona_data)
    
    # Combine
    final_recommendations = must_reads + top_candidates
    
    # Assign Final Ranks
    for i, item in enumerate(final_recommendations):
        item['persona'] = persona_name 
        item['rank'] = i + 1

    print(f"\n🏆 Final Recommendations for {persona_name}:")
    
    # Create Comparison Table
    print(f"\n{'Final':<6} | {'Vector':<6} | {'Title':<50} | {'Reason'}")
    print("-" * 100)
    
    for item in final_recommendations:
        label = "[Must Read]" if item.get('is_must_read') else f"[{item['matched_group']}]"
        
        # Find original vector rank (if it exists in generic candidates)
        original_rank = "-"
        for idx, cand in enumerate(candidates):
            if cand['id'] == item['id']:
                original_rank = str(idx + 1)
                break
                
        title_short = (item['title'][:45] + '..') if len(item['title']) > 45 else item['title']
        reason_short = (item.get('reason', '')[:50] + '..') if item.get('reason') else ''
        
        print(f"{item['rank']:<6} | {original_rank:<6} | {title_short:<50} | {reason_short}")

        # Detailed print for debugging
        # print(f"  {item['rank']}. {label} {item['title']} ({item.get('reason', '')})")
    
    if json_output:
        with open(json_output, "w", encoding="utf-8") as f:
            json.dump(final_recommendations, f, ensure_ascii=False, indent=2)
        print(f"\nRecommendations saved to {json_output}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--persona", type=str, default="20s", help="Target persona name (default: 20s)")
    parser.add_argument("--output", type=str, help="Output JSON file")
    args = parser.parse_args()
    
    output_file = args.output if args.output else DEFAULT_OUTPUT_FILE
    
    recommend_articles(args.persona, output_file)

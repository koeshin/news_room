import os
import json
import argparse
from tqdm import tqdm
from gliner import GLiNER
from sentence_transformers import SentenceTransformer
from keybert import KeyBERT
from kiwipiepy import Kiwi
from sklearn.feature_extraction.text import CountVectorizer

# --- Configuration ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "scraped_data_full")
COMPARISON_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "tag_comparison_results")

# --- Models ---
class ComparisonExtractor:
    def __init__(self):
        print("⏳ Loading Models...")
        
        # 1. GLiNER
        print("  - Loading GLiNER...")
        self.gliner_model = GLiNER.from_pretrained("urchade/gliner_medium-v2.1")
        self.gliner_labels = [
            "company", "politician", "business person", "country", "organization", "key technology"
        ]
        
        # 2. KeyBERT + Kiwi
        print("  - Loading KeyBERT & Kiwi...")
        self.kiwi = Kiwi()
        self.sbert_model = SentenceTransformer('jhgan/ko-sroberta-multitask')
        self.kw_model = KeyBERT(model=self.sbert_model)
        
        print("✅ All Models Loaded.")

    def run_gliner(self, text, max_tags=5):
        if not text: return []
        entities = self.gliner_model.predict_entities(text, self.gliner_labels, threshold=0.4)
        
        unique_tags = {}
        for e in entities:
            tag = e['text'].strip()
            score = e['score']
            if len(tag) < 2: continue
            if tag in unique_tags:
                if score > unique_tags[tag]: unique_tags[tag] = score
            else:
                unique_tags[tag] = score
        
        sorted_tags = sorted(unique_tags.items(), key=lambda x: x[1], reverse=True)
        return [tag for tag, score in sorted_tags[:max_tags]]

    def run_keybert(self, text, max_tags=5):
        if not text: return []
        
        # Noun extraction
        tokens = self.kiwi.tokenize(text)
        nouns = [t.form for t in tokens if t.tag.startswith('NN')]
        noun_text = " ".join(nouns)
        
        if not noun_text.strip(): return []

        keywords = self.kw_model.extract_keywords(
            noun_text,
            keyphrase_ngram_range=(1, 2),
            stop_words=None, # Already filtered to nouns
            use_mmr=True,
            diversity=0.7,
            top_n=max_tags
        )
        return [kw[0] for kw in keywords]

def process_file(file_path, extractor, output_dir):
    with open(file_path, 'r', encoding='utf-8') as f:
        articles = json.load(f)

    results = []
    
    # Process only top 10 articles for comparison to save time/tokens if large
    # User said "let's try it", implying a test. But I'll do all of them if reasonable number.
    
    for article in tqdm(articles, desc=f"Processing {os.path.basename(file_path)}"):
        title = article.get("title", "")
        full_text = article.get("full_text", "")
        
        # Use full text + title
        text_to_analyze = f"{title}\n{full_text}".strip()
        
        if not text_to_analyze:
            continue
            
        tags_gliner = extractor.run_gliner(text_to_analyze)
        tags_keybert = extractor.run_keybert(text_to_analyze)
        
        results.append({
            "title": title,
            "url": article.get("url", ""),
            "full_text_snippet": full_text[:200],
            "tags_gliner": tags_gliner,
            "tags_keybert": tags_keybert
        })

    # Save comparison result
    os.makedirs(output_dir, exist_ok=True)
    out_name = "comparison_" + os.path.basename(file_path)
    out_path = os.path.join(output_dir, out_name)
    
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  Saved comparison to {out_path}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=str, required=True, help="Date YYYYMMDD")
    args = parser.parse_args()
    
    date = args.date
    ym = date[:6]
    
    input_dir = os.path.join(DATA_DIR, ym)
    if not os.path.exists(input_dir):
        print(f"No data found for {date} in {input_dir}")
        return

    extractor = ComparisonExtractor()
    
    files = [f for f in os.listdir(input_dir) if f.endswith(f"_{date}.json")]
    if not files:
        print(f"No JSON files found for {date}")
        return
        
    for f in files:
        process_file(os.path.join(input_dir, f), extractor, COMPARISON_OUTPUT_DIR)

if __name__ == "__main__":
    main()

import os
import json
import argparse
from tqdm import tqdm
from keybert import KeyBERT
from sentence_transformers import SentenceTransformer
from kiwipiepy import Kiwi
from sklearn.feature_extraction.text import CountVectorizer

# --- Configuration ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "scraped_data_history")

class NewsKeywordExtractor:
    def __init__(self):
        print("⏳ Loading Embedding Model (jhgan/ko-sroberta-multitask)...")
        self.embedding_model = SentenceTransformer('jhgan/ko-sroberta-multitask')
        print("⏳ Loading KeyBERT...")
        self.kw_model = KeyBERT(model=self.embedding_model)
        print("⏳ Loading Kiwi...")
        self.kiwi = Kiwi()
        print("✅ All models loaded.")

    def extract(self, text):
        # 2. 명사만 추출하는 함수 (조사 제거용)
        def noun_tokenizer(text):
            return [token.form for token in self.kiwi.tokenize(text) if token.tag.startswith('NN')]

        if not text or len(text) < 10:
            return []

        try:
            keywords = self.kw_model.extract_keywords(
                text,
                keyphrase_ngram_range=(1, 2),  # 1~2단어 조합
                stop_words=None,               # 불용어 처리는 형태소 분석기가 대신함
                use_mmr=True,                  # ★중요★: 유사한 단어 제거 (다양성 확보)
                diversity=0.7,                 # 0.7 정도가 뉴스에 적당함
                top_n=5,                       # 뽑을 개수
                vectorizer=CountVectorizer(tokenizer=noun_tokenizer) # 명사만 타겟팅
            )
            return [kw[0] for kw in keywords]
        except Exception as e:
            # print(f"KeyBERT Error: {e}")
            return []

def process_file(file_path, extractor):
    with open(file_path, 'r', encoding='utf-8') as f:
        try:
            articles = json.load(f)
        except json.JSONDecodeError:
            print(f"Skipping Invalid JSON: {file_path}")
            return

    modified = False
    for article in tqdm(articles, desc=f"Processing {os.path.basename(file_path)}"):
        # Force update even if keywords exist, as we changed the logic
        # if "keywords" in article and article["keywords"]:
        #     continue
            
        # Construct text for extraction
        title = article.get("title", "")
        subtitle = article.get("subtitle", "")
        summary_sentences = article.get("summary_sentences", [])
        
        if isinstance(summary_sentences, list):
            summary_text = " ".join(summary_sentences)
        else:
            summary_text = str(summary_sentences)
            
        full_text = f"{title} {subtitle} {summary_text}".strip()
        
        if full_text:
            keywords = extractor.extract(full_text)
            article["keywords"] = keywords
            modified = True
            
    if modified:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)
        print(f"  Saved updates to {os.path.basename(file_path)}")
    else:
        print(f"  No changes for {os.path.basename(file_path)}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=str, help="Specific date to process (YYYYMMDD)")
    args = parser.parse_args()

    extractor = NewsKeywordExtractor()

    if args.date:
        # Process specific date across all OIDs (folders are by Month)
        target_ym = args.date[:6]
        month_dir = os.path.join(DATA_DIR, target_ym)
        if not os.path.exists(month_dir):
            print(f"Directory not found: {month_dir}")
            return
            
        files = [f for f in os.listdir(month_dir) if f.endswith(f"_{args.date}.json")]
        if not files:
            print(f"No files found for date {args.date}")
            return
            
        for f in files:
            process_file(os.path.join(month_dir, f), extractor)
            
    else:
        # Process ALL files
        for root, dirs, files in os.walk(DATA_DIR):
            for f in files:
                if f.endswith(".json"):
                    process_file(os.path.join(root, f), extractor)

if __name__ == "__main__":
    main()

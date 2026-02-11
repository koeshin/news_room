import os
import json
import argparse
from tqdm import tqdm
from gliner import GLiNER

# --- Configuration ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "scraped_data_history")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "scraped_data_gliner")

class GlinerExtractor:
    def __init__(self):
        print("⏳ Loading GLiNER Model (urchade/gliner_medium-v2.1)...")
        self.model = GLiNER.from_pretrained("urchade/gliner_medium-v2.1")
        print("✅ GLiNER model loaded.")
        
        self.labels = [
            "company",          # 기업 (삼성전자, 구글)
            "politician",       # 정치인 (대통령, 의원)
            "business person",  # 기업인 (CEO, 회장)
            "country",          # 국가 (미국, 한국)
            "organization",     # 기관 (검찰, 국회)
            "key technology"    # 핵심 기술 (AI, 반도체)
        ]

    def get_clean_tags(self, text, max_tags=5):
        if not text:
            return []
            
        # 2. 예측 실행 (Threshold 0.4 이상만)
        entities = self.model.predict_entities(text, self.labels, threshold=0.4)
        
        # 3. 중복 제거 및 정제
        unique_tags = {}
        for e in entities:
            tag = e['text'].strip()
            score = e['score']
            
            # (옵션) 1글자짜리 태그 삭제 (예: '미', '쪽' 등 노이즈 제거)
            if len(tag) < 2: 
                continue
                
            # 이미 있는 태그면 더 높은 점수로 갱신
            if tag in unique_tags:
                if score > unique_tags[tag]:
                    unique_tags[tag] = score
            else:
                unique_tags[tag] = score
        
        # 4. 점수순 정렬 후 상위 N개만 자르기 (Top-N Strategy)
        sorted_tags = sorted(unique_tags.items(), key=lambda x: x[1], reverse=True)
        
        # 태그 이름만 리스트로 반환
        final_tags = [tag for tag, score in sorted_tags[:max_tags]]
        
        return final_tags

def process_file(file_path, extractor):
    rel_path = os.path.relpath(file_path, DATA_DIR)
    output_path = os.path.join(OUTPUT_DIR, rel_path)
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(file_path, 'r', encoding='utf-8') as f:
        try:
            articles = json.load(f)
        except json.JSONDecodeError:
            print(f"Skipping Invalid JSON: {file_path}")
            return

    modified = False
    for article in tqdm(articles, desc=f"Processing {os.path.basename(file_path)}"):
        # Construct text for extraction
        title = article.get("title", "")
        # subtitle = article.get("subtitle", "") # Optionally include subtitle
        summary_sentences = article.get("summary_sentences", [])
        
        if isinstance(summary_sentences, list):
            summary_text = " ".join(summary_sentences)
        else:
            summary_text = str(summary_sentences)
            
        full_text = f"{title} {summary_text}".strip()
        
        if full_text:
            keywords = extractor.get_clean_tags(full_text)
            article["keywords"] = keywords # Overwrite or add keywords
            
            # Add extra metadata to know it's GLiNER
            article["tagging_method"] = "gliner_medium_v2.1"
            modified = True
            
    if modified:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)
        print(f"  Saved GLiNER tags to {output_path}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=str, help="Specific date to process (YYYYMMDD)")
    args = parser.parse_args()

    extractor = GlinerExtractor()

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

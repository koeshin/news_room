import json
import os
import argparse
import google.generativeai as genai
from typing import List, Dict

# --- Configuration ---
# NOTE: YOU MUST SET YOUR GEMINI API KEY IN ENV VAR 'GEMINI_API_KEY'
# export GEMINI_API_KEY="your_api_key_here"

def load_persona(persona_name: str) -> str:
    """Loads persona definition from markdown file."""
    try:
        with open(f"news_room_v2/personas/persona_{persona_name}.md", "r") as f:
            return f.read()
    except FileNotFoundError:
        return ""

def evaluate_articles(persona_def: str, articles: List[Dict]) -> List[Dict]:
    """Uses Gemini to evaluate articles based on persona."""
    
    if not os.environ.get("GEMINI_API_KEY"):
        print("⚠️ GEMINI_API_KEY not found. Returning mock scores.")
        # Mock behavior for testing without API key
        for article in articles:
            article["agent_score"] = 3
            article["agent_comment"] = "API Key missing. Mock score."
        return articles

    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')

    prompt = f"""
    You are acting as the following persona:
    {persona_def}

    Evaluate the following news articles. 
    For each article, provide a 'score' (1-5, where 5 is highly relevant/interesting to you) and a short 'comment' explaining why.
    
    Input Articles:
    {json.dumps(articles, ensure_ascii=False, indent=2)}

    Output JSON Format:
    [
        {{"id": "article_id", "score": 1-5, "comment": "reason"}}
    ]
    Return ONLY valid JSON.
    """

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        # Remove markdown code blocks if present
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        evaluations = json.loads(text)
        
        # Merge eval into articles
        eval_map = {e["id"]: e for e in evaluations}
        for article in articles:
            if article["id"] in eval_map:
                article["agent_score"] = eval_map[article["id"]]["score"]
                article["agent_comment"] = eval_map[article["id"]]["comment"]
            else:
                article["agent_score"] = 0 
                article["agent_comment"] = "Failed to evaluate"
                
    except Exception as e:
        print(f"Error during LLM evaluation: {e}")

    return articles

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--persona", type=str, required=True, help="20s, 30s, or 50s")
    parser.add_argument("--input", type=str, required=True, help="Input JSON file with recommendations")
    parser.add_argument("--output", type=str, required=True, help="Output JSON file with feedback")
    args = parser.parse_args()

    # 1. Load Persona
    persona_def = load_persona(args.persona)
    if not persona_def:
        print(f"❌ Persona {args.persona} not found.")
        exit(1)

    # 2. Load Recommendations
    with open(args.input, "r") as f:
        recs = json.load(f)

    # Filter for target persona
    target_recs = [r for r in recs if r.get("persona") == args.persona]
    
    # 3. Evaluate
    print(f"🤖 Agent ({args.persona}) is reading {len(target_recs)} articles...")
    evaluated_recs = evaluate_articles(persona_def, target_recs)

    # 4. Save Feedback
    with open(args.output, "w") as f:
        json.dump(evaluated_recs, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Feedback saved to {args.output}")

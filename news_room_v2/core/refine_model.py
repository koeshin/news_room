import json
import os
import argparse
import sys
from agent_persona import update_persona_definition

# We reuse the persona update logic from agent_persona.py

# Removed adjust_vector function as we are updating the persona definition directly

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--feedback", type=str, required=True, help="Input feedback JSON")
    parser.add_argument("--persona", type=str, required=True, help="Target persona to update")
    args = parser.parse_args()
    
    print(f" Adjusting persona '{args.persona}' based on feedback...")
    
    with open(args.feedback, "r", encoding="utf-8") as f:
        feedback_data = json.load(f)
        
    # Analyze alignment
    # If we have feedback, let's update the persona definition directly
    # This aligns with Roadmap 1-2 & 1-3 (Persona Elevation)
    
    if not feedback_data:
        print("⚠️ No feedback data found.")
        exit(0)
        
    print(f"  - Loaded {len(feedback_data)} feedback items.")
    
    # Call the update function
    update_persona_definition(args.persona, feedback_data)

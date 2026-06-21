import os
import json

def load_questions_bank(path):
    """Loads the question bank JSON and returns a list of vignettes."""
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("vignettes", [])
    except Exception as e:
        print(f"Error loading question bank: {e}")
        return []

def save_questions_bank(path, vignettes):
    """Saves a list of vignettes to the question bank JSON path."""
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"vignettes": vignettes}, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving question bank: {e}")
        return False

def merge_vignettes(existing_vignettes, new_vignettes):
    """Merges new vignettes into existing ones, filtering out duplicate topics."""
    existing_topics = {v["topic"].strip().lower() for v in existing_vignettes}
    merged = list(existing_vignettes)
    added_count = 0
    
    for v in new_vignettes:
        topic_key = v["topic"].strip().lower()
        if topic_key not in existing_topics:
            merged.append(v)
            existing_topics.add(topic_key)
            added_count += 1
            
    return merged, added_count

def load_progress(path):
    """Loads the user's progress from progress_path, initializing if missing."""
    default_progress = {
        "attempted_questions": {},  # key: "vignette_topic::question_idx", value: {"user_answer": "...", "is_correct": bool, "feedback": {...}}
        "completed_vignettes": [],  # list of vignette topics completed
        "score": 0,
        "total_attempted": 0,
        "statistics": {
            "None": 0,
            "Calculation Error": 0,
            "Conceptual Gap": 0,
            "Formula Misuse": 0,
            "Reading Misinterpretation": 0
        },
        "flashcards": []  # list of dicts: {"id", "subject", "front", "back", "box", "next_review"}
    }
    
    if not os.path.exists(path):
        return default_progress
        
    try:
        with open(path, "r", encoding="utf-8") as f:
            progress = json.load(f)
            # Ensure keys exist
            for k, v in default_progress.items():
                if k not in progress:
                    progress[k] = v
            return progress
    except Exception as e:
        print(f"Error loading progress, resetting to default: {e}")
        return default_progress

def save_progress(path, progress):
    """Saves the user's progress to the progress_path."""
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(progress, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving progress: {e}")
        return False

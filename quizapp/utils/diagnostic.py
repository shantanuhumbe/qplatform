import json

def prepare_incorrect_questions_summary(progress_data, vignettes):
    """
    Correlates the attempted incorrect questions in the progress dictionary
    with the official vignette data to build a detailed summary for the LLM.
    """
    attempted = progress_data.get("attempted_questions", {})
    incorrect_list = []
    
    # Group vignettes by topic for O(1) lookup
    vignettes_by_topic = {v["topic"]: v for v in vignettes}
    
    for key, attempt_info in attempted.items():
        if attempt_info.get("is_correct", True):
            continue
            
        # Parse key: "Topic Name::q_idx"
        if "::q_" not in key:
            continue
            
        try:
            topic_name, q_idx_str = key.rsplit("::q_", 1)
            q_idx = int(q_idx_str)
        except Exception:
            continue
            
        vignette = vignettes_by_topic.get(topic_name)
        if not vignette:
            continue
            
        questions = vignette.get("questions", [])
        if q_idx < 0 or q_idx >= len(questions):
            continue
            
        q = questions[q_idx]
        feedback = attempt_info.get("feedback", {})
        
        incorrect_entry = {
            "module": vignette.get("module", "CFA Topic"),
            "vignette_topic": topic_name,
            "question_text": q.get("question_text", ""),
            "options": q.get("options", []),
            "user_answer": attempt_info.get("user_answer", ""),
            "correct_answer": q.get("correct_answer", ""),
            "official_explanation": q.get("official_explanation", ""),
            "user_explanation": attempt_info.get("user_explanation", ""),
            "grader_error_category": feedback.get("error_category", "Unclassified"),
            "grader_feedback": feedback.get("feedback_text", "")
        }
        incorrect_list.append(incorrect_entry)
        
    return incorrect_list

def calculate_subject_metrics(progress_data, vignettes):
    """
    Computes performance metrics (total attempted, correct, incorrect, accuracy)
    grouped by Learning Module (subject) to show which subjects are performing well/poorly.
    """
    attempted = progress_data.get("attempted_questions", {})
    
    # Group vignettes by topic for O(1) lookup
    vignettes_by_topic = {v["topic"]: v for v in vignettes}
    
    subject_stats = {}
    
    for key, attempt_info in attempted.items():
        if "::q_" not in key:
            continue
            
        try:
            topic_name, q_idx_str = key.rsplit("::q_", 1)
        except Exception:
            continue
            
        vignette = vignettes_by_topic.get(topic_name)
        if not vignette:
            continue
            
        module = vignette.get("module", "Other CFA Topic")
        is_correct = attempt_info.get("is_correct", False)
        
        if module not in subject_stats:
            subject_stats[module] = {
                "attempted": 0,
                "correct": 0,
                "incorrect": 0,
                "error_categories": {}
            }
            
        stats = subject_stats[module]
        stats["attempted"] += 1
        if is_correct:
            stats["correct"] += 1
        else:
            stats["incorrect"] += 1
            feedback = attempt_info.get("feedback", {})
            err_cat = feedback.get("error_category", "Unclassified")
            stats["error_categories"][err_cat] = stats["error_categories"].get(err_cat, 0) + 1
            
    # Calculate accuracy percentages
    for module, stats in subject_stats.items():
        stats["accuracy"] = (stats["correct"] / stats["attempted"] * 100) if stats["attempted"] > 0 else 0.0
        
    return subject_stats


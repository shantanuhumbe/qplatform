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

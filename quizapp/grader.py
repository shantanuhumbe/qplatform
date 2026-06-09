import json
import urllib.request
import urllib.error
import ssl

# Bypasses local SSL certificate issues common on macOS
try:
    ssl._create_default_https_context = ssl._create_unverified_context
except AttributeError:
    pass
from quizapp.config import GRADER_SYSTEM_INSTRUCTION
from quizapp.models import GraderFeedback

def grade_user_answer(api_key, model, question_text, options, selected_option, correct_option, official_explanation, user_explanation=""):
    """Evaluates the student's answer and explanation of reasoning against the correct answer and official rationale."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    
    prompt = (
        f"Evaluate the following multiple-choice response and reasoning:\n\n"
        f"Question: {question_text}\n"
        f"Choices:\n" + "\n".join(f"  - {opt}" for opt in options) + "\n"
        f"Student Selected: {selected_option}\n"
        f"Correct Answer: {correct_option}\n"
        f"Official Explanation: {official_explanation}\n"
        f"Student Reasoning/Explanation: {user_explanation if user_explanation.strip() else 'No reasoning provided.'}\n"
    )
    
    # Structured response schema
    schema = {
        "type": "OBJECT",
        "properties": {
            "is_correct": {"type": "BOOLEAN"},
            "conceptual_score": {"type": "INTEGER"},
            "feedback_text": {"type": "STRING"},
            "error_category": {"type": "STRING"},
            "calculation_error_identified": {"type": "BOOLEAN"}
        },
        "required": ["is_correct", "conceptual_score", "feedback_text", "error_category", "calculation_error_identified"]
    }
    
    request_data = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "systemInstruction": {
            "parts": [
                {"text": GRADER_SYSTEM_INSTRUCTION}
            ]
        },
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": schema
        }
    }
    
    headers = {"Content-Type": "application/json"}
    req_body = json.dumps(request_data).encode("utf-8")
    
    req = urllib.request.Request(url, data=req_body, headers=headers, method="POST")
    
    ctx = ssl._create_unverified_context()
    try:
        with urllib.request.urlopen(req, context=ctx) as response:
            res_data = response.read().decode("utf-8")
            res_json = json.loads(res_data)
            
            candidates = res_json.get("candidates", [])
            if not candidates:
                raise ValueError("No candidates returned from Gemini Grader API.")
                
            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                raise ValueError("No content parts returned from Gemini Grader API.")
                
            raw_text = parts[0].get("text", "")
            feedback_json = json.loads(raw_text)
            
            # Pydantic validation
            validated = GraderFeedback(**feedback_json)
            return validated.model_dump()
            
    except urllib.error.HTTPError as e:
        error_msg = e.read().decode("utf-8")
        print(f"Grader HTTP Error {e.code}: {e.reason}\nDetails: {error_msg}")
        # Return fallback result in case of network/API error
        is_match = selected_option.strip().upper() == correct_option.strip().upper()
        return {
            "is_correct": is_match,
            "conceptual_score": 10 if is_match else 1,
            "feedback_text": f"Fallback grading: Your answer is {'correct' if is_match else 'incorrect'}. (API call encountered an error: {e.reason})",
            "error_category": "None" if is_match else "Unclassified",
            "calculation_error_identified": False
        }
    except Exception as e:
        print(f"Grader call failure: {e}")
        is_match = selected_option.strip().upper() == correct_option.strip().upper()
        return {
            "is_correct": is_match,
            "conceptual_score": 10 if is_match else 1,
            "feedback_text": f"Fallback grading: Your answer is {'correct' if is_match else 'incorrect'}. (API call error: {e})",
            "error_category": "None" if is_match else "Unclassified",
            "calculation_error_identified": False
        }

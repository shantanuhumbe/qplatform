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

def explain_question_llm(api_key, model, vignette_text, question_text, options, selected_option, correct_option, official_explanation, user_query):
    """Sends a point-in-time tutor question to Gemini API and returns the AI's explanation."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    
    prompt = (
        f"You are a professional CFA Level II tutor helping a student understand a practice question.\n\n"
        f"--- VIGNETTE CONTEXT ---\n"
        f"{vignette_text}\n\n"
        f"--- QUESTION ---\n"
        f"{question_text}\n\n"
        f"--- OPTIONS ---\n" + "\n".join(f"  - {opt}" for opt in options) + "\n\n"
        f"--- CORRECT ANSWER ---\n"
        f"Option {correct_option}\n\n"
        f"--- STUDENT SELECTED ---\n"
        f"Option {selected_option}\n\n"
        f"--- OFFICIAL EXPLANATION ---\n"
        f"{official_explanation}\n\n"
        f"--- STUDENT'S QUESTION/CONFUSION ---\n"
        f"{user_query}\n\n"
        f"Provide a clear, helpful, and concise response to the student's question, explaining the concept or calculation step-by-step.\n\n"
        f"FORMATTING INSTRUCTIONS:\n"
        f"- Format all math calculations and formulas using standard LaTeX: use double dollar signs ($$ ... $$) on their own lines for block equations, and single dollar signs ($ ... $) for inline variables/expressions (e.g. $FCFF$).\n"
        f"- Ensure there are proper spaces around all operators (e.g. +, -, *, =, x) to avoid character squashing.\n"
        f"- Do NOT wrap LaTeX math blocks (with $ or $$) inside markdown bold (**) or italics (*).\n"
        f"- Keep lists and paragraphs cleanly separated with double line breaks for maximum readability."
    )
    
    request_data = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
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
                return "Gemini returned no candidates in response."
                
            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                return "Gemini returned empty content parts."
                
            return parts[0].get("text", "")
            
    except urllib.error.HTTPError as e:
        try:
            error_msg = e.read().decode("utf-8")
        except:
            error_msg = ""
        return f"HTTP Error {e.code}: {e.reason}\nDetails: {error_msg}"
    except Exception as e:
        return f"Error: {e}"

def validate_api_key(api_key, model="gemini-2.5-flash"):
    """Sends a lightweight prompt to validate the API key."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    request_data = {
        "contents": [
            {
                "parts": [
                    {"text": "Hello"}
                ]
            }
        ]
    }
    headers = {"Content-Type": "application/json"}
    req_body = json.dumps(request_data).encode("utf-8")
    req = urllib.request.Request(url, data=req_body, headers=headers, method="POST")
    ctx = ssl._create_unverified_context()
    try:
        with urllib.request.urlopen(req, context=ctx) as response:
            return True, "Key is valid."
    except urllib.error.HTTPError as e:
        try:
            err_data = json.loads(e.read().decode("utf-8"))
            err_msg = err_data.get("error", {}).get("message", e.reason)
        except:
            err_msg = e.reason
        return False, f"API Error: {err_msg}"
    except Exception as e:
        return False, f"Connection Error: {e}"

def generate_diagnostic_report(api_key, model, incorrect_questions_summary, subject_metrics=None):
    """Calls the Gemini API to compile an in-depth study diagnostic based on incorrect questions and subject metrics."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    
    prompt = (
        "You are an elite Chartered Financial Analyst (CFA) tutor and study advisor.\n"
        "Your task is to analyze the student's practice history and build a granular performance diagnostic report.\n\n"
    )
    
    if subject_metrics:
        prompt += "Here is the student's cumulative performance metrics by CFA learning module / subject area:\n"
        for subject, stats in subject_metrics.items():
            err_cats_str = ", ".join(f"{k} ({v} times)" for k, v in stats['error_categories'].items()) if stats['error_categories'] else "None"
            prompt += f"- **{subject}**: {stats['correct']}/{stats['attempted']} correct ({stats['accuracy']:.1f}% accuracy). Common error categories: {err_cats_str}\n"
        prompt += "\n"
        
    prompt += (
        "Here is a list of practice questions the student answered incorrectly, along with their selected answers, correct answers, "
        "their typed explanations (if any), official rationales, and the diagnostic error category assigned by the automated grader:\n\n"
    )
    
    for idx, item in enumerate(incorrect_questions_summary):
        prompt += (
            f"--- Entry {idx+1} ---\n"
            f"Learning Module: {item['module']}\n"
            f"Vignette Topic: {item['vignette_topic']}\n"
            f"Question: {item['question_text']}\n"
            f"Choices:\n" + "\n".join(f"  - {opt}" for opt in item['options']) + "\n"
            f"Student Selected: {item['user_answer']}\n"
            f"Correct Answer: {item['correct_answer']}\n"
            f"Official Explanation: {item['official_explanation']}\n"
            f"Student Reasoning: {item['user_explanation'] if item['user_explanation'].strip() else 'No explanation written.'}\n"
            f"Grader Error Category: {item['grader_error_category']}\n"
            f"Grader Feedback: {item['grader_feedback']}\n\n"
        )
        
    prompt += (
        "Based on this data, generate a highly detailed and actionable diagnostic report in Markdown format. The report MUST include the following sections:\n\n"
        "### 📈 Executive Summary & Subject Overview\n"
        "Provide a high-level overview of the student's performance. Clearly state which subjects/modules the student is performing well in (high accuracy) versus which subjects/modules they are performing poorly in (low accuracy, frequent errors).\n\n"
        "### 🎯 Ranked Focus Areas (Descending Order of Urgency)\n"
        "Provide a ranked list of specific weakness topics to focus on, ordered from most critical (highest count of incorrect questions / conceptual misunderstandings) to least critical.\n\n"
        "### 🔍 Detailed Weakness Diagnosis (Granular Level)\n"
        "Analyze the conceptual patterns behind the incorrect answers. Group by specific CFA curriculum modules/topics, and explain:\n"
        "- What specific theoretical bits, formulas, or concepts the student is struggling with (e.g. calculation of FCFF starting from Net Income vs EBIT, or spot rate replication in arbitrage-free valuation).\n"
        "- The nature of their errors (e.g. pattern of 'Formula Misuse' vs 'Conceptual Gaps' or 'Calculation Errors').\n\n"
        "### 📚 Critical Focus Areas (Review Guide)\n"
        "Provide a clear, brief review explanation of the core concepts the student got wrong, helping them re-learn the material immediately. Use LaTeX formatting for all formulas (e.g., $$ ... $$ for block formulas, $ ... $ for inline variables).\n\n"
        "### 🎓 CFA Level II Exam Readiness Verdict\n"
        "Provide a concrete verdict on the student's readiness for the CFA Level II Exam (e.g. READY, BORDERLINE, or NOT READY YET). Back up your verdict with insights from their accuracy rates, types of errors made, and suggest specific mock exam targets or performance benchmarks they need to hit next.\n\n"
        "### 📋 Actionable Study Plan\n"
        "Provide a concrete, step-by-step study schedule or set of actions the student should take to address these gaps (e.g., specific practice focus, reading modules, note-taking strategies).\n\n"
        "FORMATTING INSTRUCTIONS:\n"
        "- Use standard Markdown syntax with clear headings, subheadings, lists, and tables where helpful.\n"
        "- Format all equations using LaTeX double dollar signs ($$ ... $$) on their own lines for block formulas, and single dollar signs ($ ... $) for inline expressions. Ensure spaces are placed around all math operators (e.g., +, -, *, =, x).\n"
        "- Do NOT wrap LaTeX math blocks inside markdown bold (**) or italics (*).\n"
        "- Keep paragraphs cleanly separated with line breaks."
    )
    
    request_data = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
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
                return "Gemini returned no candidates in response."
                
            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                return "Gemini returned empty content parts."
                
            return parts[0].get("text", "")
            
    except urllib.error.HTTPError as e:
        try:
            error_msg = e.read().decode("utf-8")
        except:
            error_msg = ""
        return f"HTTP Error {e.code}: {e.reason}\nDetails: {error_msg}"
    except Exception as e:
        return f"Error: {e}"

def discuss_diagnostic_llm(api_key, model, subject_metrics, incorrect_questions_summary, diagnostic_report, chat_history, user_query):
    """Sends the diagnostic report and user study query to Gemini to act as a study coach."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    
    # Compile subject metrics string
    metrics_str = ""
    if subject_metrics:
        for subject, stats in subject_metrics.items():
            metrics_str += f"- {subject}: {stats['correct']}/{stats['attempted']} ({stats['accuracy']:.1f}% accuracy)\n"
            
    # Compile chat history format
    history_str = ""
    for msg in chat_history:
        role = "Student" if msg["role"] == "user" else "Advisor"
        history_str += f"{role}: {msg['content']}\n"
        
    prompt = (
        f"You are an elite CFA Level II study advisor and executive coach.\n"
        f"You are helping a student review their performance diagnostic and draft a strategy to pass the exam.\n\n"
        f"--- STUDENT PERFORMANCE METRICS ---\n"
        f"{metrics_str}\n\n"
        f"--- GENERATED DIAGNOSTIC REPORT ---\n"
        f"{diagnostic_report}\n\n"
        f"--- CONVERSATION HISTORY ---\n"
        f"{history_str}\n"
        f"Student: {user_query}\n\n"
        f"Provide an encouraging, direct, and actionable answer to the student's question. Offer concrete recommendations, study advice, "
        f"or explain specific concepts if asked. Maintain LaTeX formatting ($ ... $ for inline variables, $$ ... $$ for block formulas) if citing mathematical equations."
    )
    
    request_data = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
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
                return "Gemini returned no candidates in response."
                
            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                return "Gemini returned empty content parts."
                
            return parts[0].get("text", "")
            
    except urllib.error.HTTPError as e:
        try:
            error_msg = e.read().decode("utf-8")
        except:
            error_msg = ""
        return f"HTTP Error {e.code}: {e.reason}\nDetails: {error_msg}"
    except Exception as e:
        return f"Error: {e}"


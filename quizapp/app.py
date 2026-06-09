import os
import sys

# Ensure parent directory is in python search path for streamlit absolute imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import streamlit as st
from quizapp.config import DEFAULT_OUTPUT_PATH, DEFAULT_PROGRESS_PATH, DEFAULT_GRADE_MODEL
from quizapp.utils.data_manager import load_questions_bank, load_progress, save_progress
from quizapp.ui.styles import apply_custom_styles
from quizapp.ui.components import render_sidebar, render_navigation_dots
from quizapp.grader import grade_user_answer

# Force wide mode layout for visual split screen columns
st.set_page_config(layout="wide", page_title="CFA Case Study Quiz App", page_icon="🎯")

def main():
    apply_custom_styles()
    
    # 1. Initialize API key and state variables
    if "api_key" not in st.session_state:
        env_key = os.environ.get("GEMINI_API_KEY", "").strip()
        is_env_valid = (
            len(env_key) >= 10 and 
            not any(c.isspace() for c in env_key) and
            all(32 <= ord(c) <= 126 for c in env_key)
        )
        st.session_state.api_key = env_key if is_env_valid else ""
        
    if "active_vignette_topic" not in st.session_state:
        st.session_state.active_vignette_topic = ""
        
    if "question_index" not in st.session_state:
        st.session_state.question_index = 0
        
    if "reset_progress" in st.session_state and st.session_state.reset_progress:
        if os.path.exists(DEFAULT_PROGRESS_PATH):
            try:
                os.remove(DEFAULT_PROGRESS_PATH)
            except:
                pass
        if "active_vignette_topic" in st.session_state:
            del st.session_state.active_vignette_topic
        st.session_state.question_index = 0
        st.session_state.reset_progress = False
        st.success("Session progress reset successfully!")
        
    # Load question bank and progress databases
    vignettes = load_questions_bank(DEFAULT_OUTPUT_PATH)
    progress = load_progress(DEFAULT_PROGRESS_PATH)
    
    # Sidebar rendering
    render_sidebar(progress, vignettes)
    
    if not vignettes:
        st.title("🎯 CFA Case Study Quiz Platform")
        st.warning("⚠️ Question Bank is currently empty.")
        st.markdown(
            "Please parse some pages from your CFA PDF to populate the database.\n"
            "You can run the parsing script via terminal:\n"
            "```bash\n"
            "python3 run.py parse --module 1\n"
            "```\n"
            "*Make sure you have set the `GEMINI_API_KEY` in your environment first.*"
        )
        return
        
    # 2. Filter vignettes based on study mode settings
    filtered_vignettes = list(vignettes)
    if st.session_state.get("filtering_mode", "Random") == "Topic" and st.session_state.get("selected_topic"):
        filtered_vignettes = [v for v in vignettes if v["module"] == st.session_state.selected_topic]
        
    # Filter out completed vignettes, unless all have been completed
    completed_topics = set(progress.get("completed_vignettes", []))
    uncompleted = [v for v in filtered_vignettes if v["topic"] not in completed_topics]
    
    if uncompleted:
        active_list = uncompleted
    else:
        active_list = filtered_vignettes
        st.sidebar.info("🎉 All vignettes in this category completed! Showing repeated items.")
        
    # 3. Active Vignette Selection
    active_vignette = None
    
    # If selected topic or filter changed, ensure current vignette is still in the active list
    curr_topic = st.session_state.get("active_vignette_topic", "")
    if curr_topic:
        active_vignette = next((v for v in active_list if v["topic"] == curr_topic), None)
        
    # If not set or no longer valid, pick a new one
    if not active_vignette and active_list:
        if st.session_state.get("filtering_mode", "Random") == "Random":
            import random
            active_vignette = random.choice(active_list)
        else:
            active_vignette = active_list[0]
        st.session_state.active_vignette_topic = active_vignette["topic"]
        st.session_state.question_index = 0
    elif not active_list:
        st.error("No vignettes available under the current learning module.")
        return
    questions = active_vignette.get("questions", [])
    active_q_idx = st.session_state.question_index
    
    # Track completion status of questions in this active vignette
    attempted_status = {}
    for idx in range(len(questions)):
        key = f"{active_vignette['topic']}::q_{idx}"
        if key in progress["attempted_questions"]:
            attempted_status[idx] = {
                "answered": True,
                "is_correct": progress["attempted_questions"][key]["is_correct"],
                "data": progress["attempted_questions"][key]
            }
        else:
            attempted_status[idx] = {"answered": False}
            
    # 3. UI Layout Splitting
    col1, col2 = st.columns(2)
    
    # Left column: Fixed Scrollable Case Study Vignette
    with col1:
        st.markdown(
            f'<div class="badge badge-module">{active_vignette.get("module", "CFA Module")}</div>', 
            unsafe_allow_html=True
        )
        st.markdown(
            f'<h2 style="margin-top: 0px; font-family: \'Outfit\', sans-serif;">{active_vignette.get("topic", "Topic")}</h2>', 
            unsafe_allow_html=True
        )
        
        # Render case study text in a customized scrollable container
        st.markdown(
            f'<div class="left-panel glass-card" style="height: 75vh; overflow-y: auto; padding: 20px;">'
            f'{active_vignette.get("case_study_text", "")}'
            f'</div>', 
            unsafe_allow_html=True
        )
        
    # Right column: Active Question, Answers, Navigation and grading
    with col2:
        st.markdown("<h3 style='margin-bottom: 0px; font-family: \"Outfit\", sans-serif;'>📋 Question Panel</h3>", unsafe_allow_html=True)
        render_navigation_dots(questions, attempted_status, active_q_idx)
        
        if not questions:
            st.warning("No questions found for this vignette.")
            return
            
        q = questions[active_q_idx]
        q_key = f"{active_vignette['topic']}::q_{active_q_idx}"
        
        st.markdown(
            f'<div class="glass-card" style="padding: 20px; border-radius: 12px; margin-top: 10px;">'
            f'<strong>Question {active_q_idx + 1}:</strong><br/>{q.get("question_text", "")}'
            f'</div>',
            unsafe_allow_html=True
        )
        
        is_answered = attempted_status[active_q_idx]["answered"]
        options = q.get("options", [])
        
        if is_answered:
            # Question is already answered: display locked values and AI Grader feedback
            answer_data = attempted_status[active_q_idx]["data"]
            user_ans = answer_data.get("user_answer", "")
            user_expl = answer_data.get("user_explanation", "")
            feedback = answer_data.get("feedback", {})
            
            # Show selected answer
            st.markdown(f"**Your selected option:** `{user_ans}`")
            if user_expl:
                st.markdown(f"**Your reasoning:**\n> *{user_expl}*")
            
            # Format feedback callout box style based on correctness
            feedback_class = "feedback-correct" if answer_data.get("is_correct") else "feedback-incorrect"
            status_text = "✅ CORRECT" if answer_data.get("is_correct") else "❌ INCORRECT"
            
            st.markdown(
                f'<div class="feedback-box {feedback_class}">'
                f'<h4>{status_text} (Score: {feedback.get("conceptual_score", 10)}/10)</h4>'
                f'<p><strong>Error Classification:</strong> {feedback.get("error_category", "None")}</p>'
                f'<p style="margin-top: 10px;">{feedback.get("feedback_text", "")}</p>'
                f'</div>',
                unsafe_allow_html=True
            )
            
            # If the attempt used offline fallback, allow retrying the grading
            if feedback.get("feedback_text", "").startswith("Fallback grading:"):
                st.info("ℹ️ Offline fallback grading was used for this attempt due to a transient API issue.")
                if st.button("🔄 Retry AI Grading", key=f"retry_{q_key}"):
                    if not st.session_state.api_key:
                        st.error("⚠️ API Key is missing. Please set your Gemini API Key in the sidebar.")
                    else:
                        with st.spinner("Retrying grading with Gemini API..."):
                            grading_feedback = grade_user_answer(
                                api_key=st.session_state.api_key,
                                model=DEFAULT_GRADE_MODEL,
                                question_text=q.get("question_text", ""),
                                options=options,
                                selected_option=user_ans,
                                correct_option=q.get("correct_answer", ""),
                                official_explanation=q.get("official_explanation", ""),
                                user_explanation=user_expl
                            )
                            
                            # Save updated feedback
                            is_correct = grading_feedback.get("is_correct", False)
                            progress["attempted_questions"][q_key] = {
                                "user_answer": user_ans,
                                "user_explanation": user_expl,
                                "is_correct": is_correct,
                                "feedback": grading_feedback
                            }
                            
                            # Update statistics
                            old_err = feedback.get("error_category", "None")
                            if old_err in progress["statistics"] and progress["statistics"][old_err] > 0:
                                progress["statistics"][old_err] -= 1
                                
                            err_cat = grading_feedback.get("error_category", "None")
                            if err_cat not in progress["statistics"]:
                                progress["statistics"][err_cat] = 0
                            progress["statistics"][err_cat] += 1
                            
                            save_progress(DEFAULT_PROGRESS_PATH, progress)
                            st.rerun()
            
            # Display official rationale
            st.markdown("---")
            with st.expander("📖 View Official Rationale / Explanation"):
                st.markdown(f"**Correct Option Letter:** `{q.get('correct_answer', '')}`")
                st.markdown(q.get("official_explanation", ""))
                
        else:
            # Question is unanswered: Render options radio and submit controls
            selected = st.radio(
                "Choose your option:",
                options,
                index=0,
                key=f"radio_{q_key}"
            )
            
            # Reasoning textbox
            reasoning = st.text_area(
                "Explain your logical reasoning or work (optional, helps AI diagnosis):",
                placeholder="Write down your formulas or assumptions...",
                key=f"text_{q_key}"
            )
            
            # Extract Option Letter (e.g. "A" from "A. Valuation...")
            option_letter = selected.split(")")[0].split(".")[0].strip() if selected else ""
            if len(option_letter) > 1:
                option_letter = option_letter[0]
                
            if st.button("Submit Answer", type="primary"):
                # Submits answer to LLM grader
                if not st.session_state.api_key:
                    st.error("⚠️ API Key is missing. Please set your Gemini API Key in the sidebar to grade your answer.")
                else:
                    with st.spinner("Grading answer with Gemini API..."):
                        grading_feedback = grade_user_answer(
                            api_key=st.session_state.api_key,
                            model=DEFAULT_GRADE_MODEL,
                            question_text=q.get("question_text", ""),
                            options=options,
                            selected_option=option_letter,
                            correct_option=q.get("correct_answer", ""),
                            official_explanation=q.get("official_explanation", ""),
                            user_explanation=reasoning
                        )
                        
                        # Save result
                        is_correct = grading_feedback.get("is_correct", False)
                        progress["attempted_questions"][q_key] = {
                            "user_answer": option_letter,
                            "user_explanation": reasoning,
                            "is_correct": is_correct,
                            "feedback": grading_feedback
                        }
                        
                        # Update scores
                        progress["total_attempted"] += 1
                        if is_correct:
                            progress["score"] += 1
                            
                        # Update error category statistics
                        err_cat = grading_feedback.get("error_category", "None")
                        if err_cat not in progress["statistics"]:
                            progress["statistics"][err_cat] = 0
                        progress["statistics"][err_cat] += 1
                        
                        save_progress(DEFAULT_PROGRESS_PATH, progress)
                        st.rerun()
                        
        # 4. Question Navigation controls
        st.markdown("---")
        nav_col1, nav_col2 = st.columns(2)
        with nav_col1:
            if st.button("⬅️ Previous Question", disabled=(active_q_idx == 0)):
                st.session_state.question_index -= 1
                st.rerun()
        with nav_col2:
            if st.button("Next Question ➡️", disabled=(active_q_idx == len(questions) - 1)):
                st.session_state.question_index += 1
                st.rerun()
                
        # 5. Handle complete vignette navigation
        all_answered = all(attempted_status[idx]["answered"] for idx in range(len(questions)))
        if all_answered:
            st.success("🎉 You have completed all questions in this case study!")
            if st.button("Move to Next Case Study ➡️", type="primary"):
                # Track completed vignette topic to avoid repeating
                if active_vignette["topic"] not in progress["completed_vignettes"]:
                    progress["completed_vignettes"].append(active_vignette["topic"])
                    save_progress(DEFAULT_PROGRESS_PATH, progress)
                    
                # Pick next vignette by clearing topic so selection runs on rerun
                if "active_vignette_topic" in st.session_state:
                    del st.session_state.active_vignette_topic
                st.session_state.question_index = 0
                st.rerun()

if __name__ == "__main__":
    main()

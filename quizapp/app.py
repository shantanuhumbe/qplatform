import os
import sys

# Ensure parent directory is in python search path — MUST be first
# Streamlit runs app.py as __main__ so we set the path before any quizapp imports
_parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from quizapp.utils.table_renderer import render_case_study
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
        
        # Convert case study text to HTML with smart table rendering
        raw_case_text = active_vignette.get("case_study_text", "")
        case_study_html = render_case_study(raw_case_text)
        
        # Render case study text in a customized scrollable container
        st.markdown(
            f'<div class="left-panel glass-card" style="height: 75vh; overflow-y: auto; padding: 20px;">'
            f'{case_study_html}'
            f'</div>', 
            unsafe_allow_html=True
        )
        
    # Right column: Active Question, Answers, Navigation and grading
    with col2:
        # Determine if all questions in this vignette are answered
        all_answered = all(attempted_status[idx]["answered"] for idx in range(len(questions)))
        
        # Conditionally split layout into tabs if vignette is complete
        if all_answered:
            tab_review, tab_summary = st.tabs(["📋 Question Review", "📊 Vignette Performance Summary"])
            q_container = tab_review
        else:
            q_container = st.container()
            
        with q_container:
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
                
                # Normalize and cap the score dynamically (LLM might return value out of 100 instead of 10)
                raw_score = feedback.get("conceptual_score", 10)
                try:
                    raw_score = int(raw_score)
                    if raw_score > 10:
                        raw_score = int(round(raw_score / 10.0))
                    score_display = max(0, min(10, raw_score))
                except:
                    score_display = 10 if answer_data.get("is_correct") else 1
                
                st.markdown(
                    f'<div class="feedback-box {feedback_class}">'
                    f'<h4>{status_text} (Score: {score_display}/10)</h4>'
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
                                    model=st.session_state.get("grade_model", DEFAULT_GRADE_MODEL),
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
                                model=st.session_state.get("grade_model", DEFAULT_GRADE_MODEL),
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
                    
        # 5. Handle complete vignette summary and navigation
        if all_answered:
            with tab_summary:
                st.markdown("<h3 style='margin-bottom: 10px; font-family: \"Outfit\", sans-serif;'>📊 Vignette Study Summary</h3>", unsafe_allow_html=True)
                
                # Calculate score for this vignette
                local_score = 0
                local_attempted = len(questions)
                local_errors = []
                
                for idx in range(len(questions)):
                    key = f"{active_vignette['topic']}::q_{idx}"
                    if key in progress["attempted_questions"]:
                        q_data = progress["attempted_questions"][key]
                        feedback = q_data.get("feedback", {})
                        if q_data.get("is_correct", False):
                            local_score += 1
                        else:
                            local_errors.append({
                                "q_idx": idx,
                                "category": feedback.get("error_category", "Unclassified"),
                                "feedback": feedback.get("feedback_text", "No feedback details.")
                            })
                
                local_pct = (local_score / local_attempted * 100) if local_attempted > 0 else 0.0
                
                # Display Score card
                st.markdown(
                    f'<div class="glass-card" style="padding: 20px; border-radius: 12px; margin-top: 10px; border-left: 5px solid #3B82F6;">'
                    f'<h4 style="margin: 0; font-family: \'Outfit\', sans-serif;">Case Study Score: '
                    f'<span style="color: #93C5FD;">{local_score}/{local_attempted} ({local_pct:.1f}%)</span></h4>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                
                # Weakness analysis
                if local_errors:
                    st.markdown("#### 🔍 Weaknesses Identified in this Case Study")
                    for err in local_errors:
                        st.markdown(
                            f'<div class="feedback-box feedback-incorrect" style="margin-top: 10px;">'
                            f'<strong>Question {err["q_idx"] + 1}:</strong> Graded as <span style="color: #EF4444; font-weight: 600;">{err["category"]}</span><br/>'
                            f'<p style="margin-top: 5px; font-size: 0.9em; line-height: 1.4;">{err["feedback"]}</p>'
                            f'</div>',
                            unsafe_allow_html=True
                        )
                    
                    st.markdown("---")
                    st.markdown("#### 💡 Targeted Recommendations")
                    
                    err_categories_in_session = set(err["category"] for err in local_errors)
                    for cat in err_categories_in_session:
                        if cat == "Calculation Error":
                            st.markdown(
                                "👉 **Calculation Error**: Double-check arithmetic, write down intermediate calculation steps, "
                                "and verify decimal places/inputs on your calculator."
                            )
                        elif cat == "Conceptual Gap":
                            st.markdown(
                                "👉 **Conceptual Gap**: Review the underlying CFA curriculum readings for this specific section. "
                                "Make notes of assumptions, parameters, and structural dynamics."
                            )
                        elif cat == "Formula Misuse":
                            st.markdown(
                                "👉 **Formula Misuse**: Maintain a dedicated formula sheet. Write down the formulas daily and "
                                "verify compounding periods (e.g. daily, monthly, semi-annual vs. annual compounding)."
                            )
                        elif cat == "Reading Misinterpretation":
                            st.markdown(
                                "👉 **Reading Misinterpretation**: Slow down when reading vignette descriptions. Highlight "
                                "qualifiers like *except*, *most likely*, *least likely*, and trace the correct date references."
                            )
                        else:
                            st.markdown(
                                f"👉 **{cat}**: Carefully read the official rationale to understand the gap between your logic and the correct answer."
                            )
                else:
                    st.balloons()
                    st.markdown(
                        '<div class="feedback-box feedback-correct" style="margin-top: 15px;">'
                        '<h4>🌟 Perfect Score!</h4>'
                        '<p>Superb performance! You got all questions in this vignette correct. You have demonstrated '
                        'excellent conceptual mastery and detail-oriented focus for this topic!</p>'
                        '</div>',
                        unsafe_allow_html=True
                    )
                
                # Cumulative progress overview
                st.markdown("---")
                st.markdown("#### 📈 Cumulative Performance Analysis")
                stats = progress.get("statistics", {})
                error_stats = {k: v for k, v in stats.items() if k != "None" and v > 0}
                
                if error_stats:
                    sorted_weaknesses = sorted(error_stats.items(), key=lambda x: x[1], reverse=True)
                    top_weakness, count = sorted_weaknesses[0]
                    
                    st.warning(f"⚠️ Your most frequent cumulative weakness across all study sessions is **{top_weakness}** (triggered **{count}** times).")
                    
                    if top_weakness == "Calculation Error":
                        st.info("💡 **Practice Action**: Focus on step-by-step arithmetic verification. Don't skip writing down intermediate steps.")
                    elif top_weakness == "Conceptual Gap":
                        st.info("💡 **Practice Action**: Focus on studying core curriculum concepts. Create flashcards for vocabulary and assumptions.")
                    elif top_weakness == "Formula Misuse":
                        st.info("💡 **Practice Action**: Dedicate study time to active formula recall. Write down formulas from memory and outline their parameters.")
                    elif top_weakness == "Reading Misinterpretation":
                        st.info("💡 **Practice Action**: Practice scanning vignettes for negations/extremes ('except', 'not', 'only', 'must'). Slow down on reading.")
                else:
                    st.info("No errors recorded yet. Practice more questions to get personalized cumulative insights!")
            
            st.markdown("---")
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

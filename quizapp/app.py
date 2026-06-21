import os
import sys

# Ensure parent directory is in python search path — MUST be first
# Streamlit runs app.py as __main__ so we set the path before any quizapp imports
_parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from quizapp.utils.table_renderer import render_case_study
import streamlit as st
from quizapp.config import DEFAULT_OUTPUT_PATH, DEFAULT_PROGRESS_PATH, DEFAULT_GRADE_MODEL, MERGED_OUTPUT_PATH, MERGED_PROGRESS_PATH
from quizapp.utils.data_manager import load_questions_bank, load_progress, save_progress
from quizapp.ui.styles import apply_custom_styles
from quizapp.ui.components import render_sidebar, render_navigation_dots, render_header
from quizapp.grader import grade_user_answer
from quizapp.calculator import render_calculator_drawer

# Force wide mode layout for visual split screen columns
st.set_page_config(layout="wide", page_title="CFA Case Study Quiz App", page_icon="🎯")

def main():
    apply_custom_styles()
    
    # 0. Handle URL Query Parameters (initialize state if present in URL)
    if "active_db" not in st.session_state:
        url_q_bank = st.query_params.get("q_bank")
        if url_q_bank in ["default", "merged"]:
            st.session_state.active_db = url_q_bank
        else:
            st.session_state.active_db = "default"

    if "grade_model" not in st.session_state:
        url_model = st.query_params.get("model")
        valid_models = ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash", "gemini-2.5-pro"]
        if url_model in valid_models:
            st.session_state.grade_model = url_model
        else:
            st.session_state.grade_model = "gemini-2.5-flash"
            
    if "active_vignette_topic" not in st.session_state:
        url_topic = st.query_params.get("topic")
        st.session_state.active_vignette_topic = url_topic if url_topic else ""
        
    if "question_index" not in st.session_state:
        url_q_idx = st.query_params.get("q_idx")
        try:
            st.session_state.question_index = int(url_q_idx) if url_q_idx is not None else 0
        except ValueError:
            st.session_state.question_index = 0
            
    # 1. Initialize API key and state variables
    if "api_key" not in st.session_state:
        env_key = os.environ.get("GEMINI_API_KEY", "").strip()
        is_env_valid = (
            len(env_key) >= 10 and 
            not any(c.isspace() for c in env_key) and
            all(32 <= ord(c) <= 126 for c in env_key)
        )
        st.session_state.api_key = env_key if is_env_valid else ""

    active_db = st.session_state.get("active_db", "default")
    if active_db == "merged":
        vignette_path = MERGED_OUTPUT_PATH
        progress_path = MERGED_PROGRESS_PATH
    else:
        vignette_path = DEFAULT_OUTPUT_PATH
        progress_path = DEFAULT_PROGRESS_PATH

    if "reset_progress" in st.session_state and st.session_state.reset_progress:
        if os.path.exists(progress_path):
            try:
                os.remove(progress_path)
            except:
                pass
        if "active_vignette_topic" in st.session_state:
            del st.session_state.active_vignette_topic
        st.session_state.question_index = 0
        st.query_params.pop("topic", None)
        st.query_params.pop("q_idx", None)
        st.session_state.reset_progress = False
        st.success("Session progress reset successfully!")
        
    # Load question bank and progress databases
    vignettes = load_questions_bank(vignette_path)
    progress = load_progress(progress_path)
    
    # Header rendering
    render_header(progress, vignettes)
    
    # Sidebar rendering
    render_sidebar(progress, vignettes)
    
    # Page Routing
    if st.session_state.get("active_page", "Practice Quiz") == "AI Performance Diagnostic":
        render_diagnostic_page(progress, vignettes)
        return
        
    if st.session_state.get("active_page", "Practice Quiz") == "Incorrect Questions Review":
        render_incorrect_review_page(progress, vignettes)
        return

    if st.session_state.get("active_page", "Practice Quiz") == "AI Flashcards & Active Recall":
        render_flashcards_page(progress, vignettes, progress_path)
        return
    
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
    if len(questions) > 0:
        if st.session_state.question_index < 0 or st.session_state.question_index >= len(questions):
            st.session_state.question_index = 0
    active_q_idx = st.session_state.question_index
    
    # Sync current values to URL parameters so they appear in browser URL
    st.query_params["q_bank"] = st.session_state.active_db
    st.query_params["model"] = st.session_state.grade_model
    st.query_params["topic"] = st.session_state.active_vignette_topic
    st.query_params["q_idx"] = str(st.session_state.question_index)
    
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
            
    # Calculator drawer (collapsible above quiz)
    render_calculator_drawer()
    
    # 3. UI Layout Splitting
    col1, col2 = st.columns(2)
    
    # Left column: Fixed Scrollable Case Study Vignette
    with col1:
        header_col1, header_col2 = st.columns([3, 1])
        with header_col1:
            st.markdown(
                f'<div class="badge badge-module">{active_vignette.get("module", "CFA Module")}</div>', 
                unsafe_allow_html=True
            )
            st.markdown(
                f'<h2 style="margin-top: 0px; font-family: \'Outfit\', sans-serif; font-size: 1.6em; line-height: 1.2;">{active_vignette.get("topic", "Topic")}</h2>', 
                unsafe_allow_html=True
            )
        with header_col2:
            st.markdown('<div style="height: 18px;"></div>', unsafe_allow_html=True)
            if st.button("🔄 Next Case", use_container_width=True, help="Load the next case study / vignette"):
                if st.session_state.get("filtering_mode", "Random") == "Random":
                    # Random: pick another random vignette from the active list that isn't the current one
                    candidates = [v for v in active_list if v["topic"] != active_vignette["topic"]]
                    if candidates:
                        import random
                        next_v = random.choice(candidates)
                    else:
                        next_v = active_vignette
                else:
                    # Topic: pick the next sequential vignette from the active list
                    current_idx = -1
                    for idx, v in enumerate(active_list):
                        if v["topic"] == active_vignette["topic"]:
                            current_idx = idx
                            break
                    if current_idx != -1 and current_idx + 1 < len(active_list):
                        next_v = active_list[current_idx + 1]
                    else:
                        next_v = active_list[0]
                
                st.session_state.active_vignette_topic = next_v["topic"]
                st.session_state.question_index = 0
                st.query_params["topic"] = next_v["topic"]
                st.query_params["q_idx"] = "0"
                st.rerun()
        
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
                
                # Show all options with selection highlighting
                st.markdown("#### 📋 Question Options:")
                for opt in options:
                    opt_letter = opt.strip()[0].upper() if (opt.strip() and opt.strip()[0].upper() in ['A', 'B', 'C']) else ""
                    is_correct = opt_letter == q.get('correct_answer', '').upper()
                    is_user = opt_letter == user_ans.upper()
                    
                    if is_correct and is_user:
                        st.markdown(f"<div style='padding: 8px 12px; border-radius: 6px; background-color: rgba(16, 185, 129, 0.15); border-left: 5px solid #10B981; margin-bottom: 6px; font-family: sans-serif;'>🟢 <strong>{opt}</strong> <em>(Selected & Correct)</em></div>", unsafe_allow_html=True)
                    elif is_correct:
                        st.markdown(f"<div style='padding: 8px 12px; border-radius: 6px; background-color: rgba(59, 130, 246, 0.15); border-left: 5px solid #3B82F6; margin-bottom: 6px; font-family: sans-serif;'>🔵 <strong>{opt}</strong> <em>(Correct Answer)</em></div>", unsafe_allow_html=True)
                    elif is_user:
                        st.markdown(f"<div style='padding: 8px 12px; border-radius: 6px; background-color: rgba(239, 68, 68, 0.15); border-left: 5px solid #EF4444; margin-bottom: 6px; font-family: sans-serif;'>🔴 <del>{opt}</del> <em>(Selected & Incorrect)</em></div>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div style='padding: 8px 12px; border-radius: 6px; background-color: rgba(255, 255, 255, 0.05); margin-bottom: 6px; font-family: sans-serif; opacity: 0.7;'>⚪ {opt}</div>", unsafe_allow_html=True)
                st.markdown("")
                
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
                                
                                save_progress(progress_path, progress)
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
                    if not st.session_state.api_key:
                        is_match = option_letter.strip().upper() == q.get("correct_answer", "").strip().upper()
                        grading_feedback = {
                            "is_correct": is_match,
                            "conceptual_score": 10 if is_match else 0,
                            "feedback_text": f"Offline local grading: Your answer is {'correct' if is_match else 'incorrect'} (set Gemini API Key in the sidebar to get full AI feedback and diagnostic analysis).",
                            "error_category": "None" if is_match else "Unclassified",
                            "calculation_error_identified": False
                        }
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
                    
                    save_progress(progress_path, progress)
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
                    save_progress(progress_path, progress)
                    
                # Pick next vignette by clearing topic so selection runs on rerun
                if "active_vignette_topic" in st.session_state:
                    del st.session_state.active_vignette_topic
                st.session_state.question_index = 0
                st.rerun()

    # 6. Full-Width AI Tutor Chat at the bottom of the page (underneath columns)
    if questions and active_q_idx < len(questions):
        q_key = f"{active_vignette['topic']}::q_{active_q_idx}"
        if q_key in progress["attempted_questions"]:
            answer_data = progress["attempted_questions"][q_key]
            user_ans = answer_data.get("user_answer", "")
            q = questions[active_q_idx]
            options = q.get("options", [])
            raw_case_text = active_vignette.get("case_study_text", "")
            
            st.markdown("---")
            
            # Initialize chat history for this question key in session state
            if "tutor_chats" not in st.session_state:
                st.session_state.tutor_chats = {}
            if q_key not in st.session_state.tutor_chats:
                st.session_state.tutor_chats[q_key] = []
            
            chat_header_col1, chat_header_col2 = st.columns([6, 1])
            with chat_header_col1:
                st.markdown("<h4 style='font-family: \"Outfit\", sans-serif; margin: 0;'>💬 Discuss with Gemini Tutor</h4>", unsafe_allow_html=True)
            with chat_header_col2:
                if st.session_state.tutor_chats[q_key]:
                    st.markdown('<div class="clear-chat-container">', unsafe_allow_html=True)
                    if st.button("🗑️ Clear", key=f"clear_chat_{q_key}", use_container_width=True):
                        st.session_state.tutor_chats[q_key] = []
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
            
            # Render existing messages
            if st.session_state.tutor_chats[q_key]:
                for msg in st.session_state.tutor_chats[q_key]:
                    with st.chat_message(msg["role"]):
                        st.markdown(msg["content"])
            else:
                # Beautiful empty state suggestion card
                st.markdown(
                    '<div class="feedback-box" style="border-left: 4px solid #8B5CF6; background-color: rgba(139, 92, 246, 0.03); padding: 16px; border-radius: 0 8px 8px 0; margin-bottom: 15px;">'
                    '<h5 style="margin-top: 0; color: #A78BFA; font-family: \'Outfit\', sans-serif;">💡 Ask the AI Tutor Anything</h5>'
                    '<p style="font-size: 0.88em; opacity: 0.85; margin-bottom: 10px;">Get point-in-time clarification on this question, options, or curriculum logic. Try asking:</p>'
                    '<ul style="font-size: 0.85em; opacity: 0.8; margin-left: 20px; line-height: 1.5; padding-left: 0;">'
                    '<li><em>"Can you explain the step-by-step calculations?"</em></li>'
                    '<li><em>"Why is my selected option incorrect in this context?"</em></li>'
                    '<li><em>"What is the key difference between Option A and Option B?"</em></li>'
                    '</ul>'
                    '</div>',
                    unsafe_allow_html=True
                )
            
            # Form for user input with side-by-side layout
            with st.form(key=f"chat_form_{q_key}", clear_on_submit=True):
                input_col, btn_col = st.columns([10, 1])
                with input_col:
                    chat_query = st.text_input(
                        label="Ask the AI Tutor:",
                        label_visibility="collapsed",
                        placeholder="Ask a question about this vignette, options, or grading...",
                        key=f"tutor_input_val_{q_key}"
                    )
                with btn_col:
                    st.markdown('<div class="chat-send-container">', unsafe_allow_html=True)
                    submit_button = st.form_submit_button(label="🚀 Send")
                    st.markdown('</div>', unsafe_allow_html=True)
            
            if submit_button and chat_query.strip():
                if not st.session_state.get("api_key"):
                    st.warning("⚠️ Please provide a Gemini API Key in the sidebar settings to use the AI Tutor.")
                else:
                    # Add user message to history
                    st.session_state.tutor_chats[q_key].append({"role": "user", "content": chat_query.strip()})
                    
                    from quizapp.grader import explain_question_llm
                    with st.spinner("Gemini is formulating an explanation..."):
                        response = explain_question_llm(
                            api_key=st.session_state.api_key,
                            model=st.session_state.get("grade_model", DEFAULT_GRADE_MODEL),
                            vignette_text=raw_case_text,
                            question_text=q.get("question_text", ""),
                            options=options,
                            selected_option=user_ans,
                            correct_option=q.get("correct_answer", ""),
                            official_explanation=q.get("official_explanation", ""),
                            user_query=chat_query.strip()
                        )
                    # Add assistant response to history
                    st.session_state.tutor_chats[q_key].append({"role": "assistant", "content": response})
                    st.rerun()

def render_diagnostic_page(progress, vignettes):
    import json
    st.title("📊 AI Performance Diagnostic & Study Advisor")
    st.write("Extract granular insights about your strengths and weaknesses from your curriculum practice history using Google's Gemini API.")
    
    st.markdown("---")
    
    # Selection of diagnostic target
    diag_mode = st.radio(
        "Select Performance Data Source",
        ["Analyze Current Active Session", "Upload Saved Progress JSON File"],
        horizontal=True
    )
    
    selected_progress = None
    
    if diag_mode == "Analyze Current Active Session":
        selected_progress = progress
        st.info("Analyzing your current local session scores and history.")
    else:
        uploaded_file = st.file_uploader(
            "Upload cfa_study_progress.json",
            type=["json"],
            help="Upload your saved progress JSON file to analyze."
        )
        if uploaded_file is not None:
            try:
                uploaded_data = json.load(uploaded_file)
                required_keys = ["attempted_questions", "completed_vignettes", "score", "total_attempted", "statistics"]
                if all(k in uploaded_data for k in required_keys):
                    selected_progress = uploaded_data
                    st.success("✅ Progress file loaded successfully!")
                else:
                    st.error("❌ Invalid file format: missing required progress keys.")
            except Exception as e:
                st.error(f"❌ Error parsing progress file: {e}")
        else:
            st.info("Please upload a saved progress JSON file to begin analysis.")
            return

    if not selected_progress:
        return
        
    attempted_questions = selected_progress.get("attempted_questions", {})
    total_attempted = len(attempted_questions)
    
    if total_attempted == 0:
        st.warning("⚠️ No practice history found in this session. Go attempt some quiz questions first!")
        return
        
    correct_count = sum(1 for q in attempted_questions.values() if q.get("is_correct", False))
    incorrect_count = total_attempted - correct_count
    accuracy = (correct_count / total_attempted * 100) if total_attempted > 0 else 0.0
    
    # Render stats grid
    st.markdown("### 📈 Session Summary Metrics")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Questions Attempted", total_attempted)
    with col2:
        st.metric("Accuracy Rate", f"{accuracy:.1f}%")
    with col3:
        st.metric("Correct Answers", correct_count)
    with col4:
        st.metric("Incorrect Answers", incorrect_count)
        
    # CFA Level II Exam Predictor & Passing Gauge
    st.markdown("---")
    st.markdown("### 🎯 CFA Level II Exam Simulator & Score Predictor")
    
    pred_col_left, pred_col_right = st.columns([1, 1])
    
    # Calculate predicted score range using standard error of a proportion
    import math
    p = accuracy / 100.0
    n = total_attempted
    # Capped margin of error between 2% and 25% based on sample size
    stderr = math.sqrt(max(0.01, p * (1 - p)) / n)
    margin_fallback = max(2.0, min(25.0, 1.96 * stderr * 100.0))
    
    # Check if we have active AI-generated prediction
    has_ai_prediction = "predicted_score" in st.session_state
    gauge_value = st.session_state.get("predicted_score", accuracy)
    gauge_margin = st.session_state.get("confidence_margin", margin_fallback)
    
    predicted_min = max(0.0, gauge_value - gauge_margin)
    predicted_max = min(100.0, gauge_value + gauge_margin)
    
    # Determine Status Verdict
    mps = 65.0
    if predicted_min >= mps:
        verdict_status = "🎉 PASS PREDICTED"
        verdict_desc = "AI High Confidence Pass" if has_ai_prediction else "Baseline High Confidence Pass"
        verdict_color = "#10B981" # Green
        verdict_bg = "rgba(16, 185, 129, 0.08)"
        verdict_border = "1px solid #10B981"
        verdict_tip = "Your performance is safely above the historical Minimum Passing Score (MPS). The AI evaluates your logic as highly solid and structured for the CFA L2 syllabus." if has_ai_prediction else "Your cumulative accuracy is safely above the historical Minimum Passing Score (MPS). Keep practicing to narrow down the margin of error."
    elif gauge_value >= mps:
        verdict_status = "⚠️ BORDERLINE PASS"
        verdict_desc = "AI Moderate Confidence" if has_ai_prediction else "Baseline Moderate Confidence"
        verdict_color = "#F59E0B" # Amber
        verdict_bg = "rgba(245, 158, 11, 0.08)"
        verdict_border = "1px solid #F59E0B"
        verdict_tip = "Your predicted average is passing, but your score confidence interval dips below the MPS. AI warns that errors in high-weight topics could jeopardize your outcome." if has_ai_prediction else "Your average is passing, but your score confidence interval dips below the MPS due to sample size or performance fluctuations."
    elif predicted_max >= mps:
        verdict_status = "⚠️ BORDERLINE FAIL"
        verdict_desc = "AI Low Confidence" if has_ai_prediction else "Baseline Low Confidence"
        verdict_color = "#F59E0B" # Amber
        verdict_bg = "rgba(245, 158, 11, 0.08)"
        verdict_border = "1px solid #F59E0B"
        verdict_tip = "You are close to the passing threshold. The AI notes specific conceptual gaps in key formula sections that are holding you back." if has_ai_prediction else "You are close to the passing threshold, but currently tracking below the MPS. Standardizing your formulas and reviewing Conceptual Gaps will quickly push you into passing range."
    else:
        verdict_status = "🚨 FAIL PREDICTED"
        verdict_desc = "AI Requires Immediate Review" if has_ai_prediction else "Baseline Low Score"
        verdict_color = "#EF4444" # Red
        verdict_bg = "rgba(239, 68, 68, 0.08)"
        verdict_border = "1px solid #EF4444"
        verdict_tip = "Your performance is currently below the historical passing threshold. The AI advises dedicated syllabus review on your Critical Focus subjects before attempting mock exams." if has_ai_prediction else "Your performance is currently below the historical passing threshold. We recommend focusing heavily on your top Critical Focus subject areas and generating an AI study advisor report."
        
    with pred_col_left:
        import plotly.graph_objects as go
        
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number+delta",
            value = gauge_value,
            domain = {'x': [0, 1], 'y': [0, 1]},
            delta = {'reference': mps, 'position': "top", 'valueformat': '.1f', 'increasing': {'color': "#10B981"}, 'decreasing': {'color': "#EF4444"}},
            gauge = {
                'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "#94A3B8"},
                'bar': {'color': "#3B82F6"},
                'bgcolor': "rgba(255, 255, 255, 0.02)",
                'borderwidth': 1,
                'bordercolor': "rgba(255, 255, 255, 0.1)",
                'steps': [
                    {'range': [0, 60], 'color': 'rgba(239, 68, 68, 0.08)'},
                    {'range': [60, 65], 'color': 'rgba(245, 158, 11, 0.08)'},
                    {'range': [65, 100], 'color': 'rgba(16, 185, 129, 0.06)'}
                ],
                'threshold': {
                    'line': {'color': "#F59E0B", 'width': 3},
                    'thickness': 0.75,
                    'value': mps
                }
            }
        ))
        
        fig_gauge.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font={'color': "#F1F5F9", 'family': "Inter"},
            height=200,
            margin=dict(l=30, r=30, t=10, b=10)
        )
        st.plotly_chart(fig_gauge, use_container_width=True, config={'displayModeBar': False})
        
    with pred_col_right:
        st.markdown(
            f'<div class="glass-card" style="border-left: 5px solid {verdict_color}; background-color: {verdict_bg}; '
            f'border-top: {verdict_border}; border-right: {verdict_border}; border-bottom: {verdict_border}; '
            f'padding: 16px 20px; border-radius: 12px; margin-top: 10px; height: 100%;">'
            f'<h4 style="margin: 0; color: {verdict_color}; font-size: 1.1em; letter-spacing: 0.05em;">{verdict_status} ({verdict_desc})</h4>'
            f'<p style="margin: 8px 0 4px 0; font-size: 0.95em; font-weight: 600; color: #E2E8F0;">'
            f'Predicted Score Range: <strong>{predicted_min:.1f}% to {predicted_max:.1f}%</strong>'
            f'</p>'
            f'<p style="margin: 0 0 8px 0; font-size: 0.8em; color: #94A3B8;">'
            f'Confidence Interval (95% CI): ±{gauge_margin:.1f}% based on {n} attempts'
            f'</p>'
            f'<p style="margin: 0; font-size: 0.85em; line-height: 1.5; color: #CBD5E1;">'
            f'{verdict_tip}'
            f'</p>'
            f'</div>',
            unsafe_allow_html=True
        )
        
    # Calculate subject level metrics
    from quizapp.utils.diagnostic import calculate_subject_metrics
    subject_stats = calculate_subject_metrics(selected_progress, vignettes)
    
    st.markdown("---")
    st.markdown("### 🔍 Subject Performance & Focus Priorities")
    
    col_chart, col_rank = st.columns([5, 4])
    
    with col_chart:
        st.markdown("#### 📊 Competency Diagnostics")
        if subject_stats:
            import pandas as pd
            import plotly.express as px
            import plotly.graph_objects as go
            
            tab_bar, tab_radar = st.tabs(["📊 Subject Error Volume", "🕸️ Competency Radar Profile"])
            
            with tab_bar:
                # Build data list
                chart_data = []
                for sub, stats in subject_stats.items():
                    chart_data.append({
                        "Subject Area": sub,
                        "Accuracy (%)": round(stats["accuracy"], 1),
                        "Errors": stats["incorrect"],
                        "Attempted": stats["attempted"]
                    })
                
                df_subject = pd.DataFrame(chart_data)
                # Sort by Errors ascending so when plotted horizontally, largest errors is at the top
                df_subject = df_subject.sort_values(by="Errors", ascending=True)
                
                fig = px.bar(
                    df_subject,
                    x="Errors",
                    y="Subject Area",
                    orientation='h',
                    text="Accuracy (%)",
                    color="Accuracy (%)",
                    color_continuous_scale="RdYlGn",
                    hover_data=["Attempted", "Errors"],
                    template="plotly_dark"
                )
                
                num_items = len(chart_data)
                chart_item_height = 50
                chart_padding = 80
                fig_height = max(180, chart_item_height * num_items + chart_padding)
                
                fig.update_layout(
                    margin=dict(l=10, r=10, t=10, b=10),
                    height=fig_height,
                    xaxis_title="Number of Incorrect Attempts (Error Count)",
                    yaxis_title=None,
                    coloraxis_colorbar=dict(title="Accuracy %")
                )
                fig.update_traces(
                    texttemplate='%{text}% Acc',
                    textposition='inside',
                    insidetextanchor='end'
                )
                
                # Keep 10 items visible, make remaining scrollable
                if num_items > 10:
                    container_height = chart_item_height * 10 + chart_padding
                    with st.container(height=container_height, border=False):
                        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                else:
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            
            with tab_radar:
                categories = list(subject_stats.keys())
                if categories:
                    # Close the path for radar chart
                    categories_closed = categories + [categories[0]]
                    accuracy_values = [round(subject_stats[cat]["accuracy"], 1) for cat in categories]
                    accuracy_values_closed = accuracy_values + [accuracy_values[0]]
                    
                    mps_values = [65.0] * len(categories_closed)
                    mastery_values = [80.0] * len(categories_closed)
                    
                    fig_radar = go.Figure()
                    
                    # Student path
                    fig_radar.add_trace(go.Scatterpolar(
                        r=accuracy_values_closed,
                        theta=categories_closed,
                        fill='toself',
                        name='Your Accuracy',
                        fillcolor='rgba(139, 92, 246, 0.15)',
                        line=dict(color='#8B5CF6', width=2)
                    ))
                    
                    # MPS boundary
                    fig_radar.add_trace(go.Scatterpolar(
                        r=mps_values,
                        theta=categories_closed,
                        name='65% Pass Mark (MPS)',
                        line=dict(color='#F59E0B', width=1.5, dash='dash')
                    ))
                    
                    # Mastery boundary
                    fig_radar.add_trace(go.Scatterpolar(
                        r=mastery_values,
                        theta=categories_closed,
                        name='80% Mastery Target',
                        line=dict(color='#10B981', width=1.5, dash='dot')
                    ))
                    
                    fig_radar.update_layout(
                        polar=dict(
                            radialaxis=dict(
                                visible=True,
                                range=[0, 100],
                                color="#94A3B8"
                            ),
                            bgcolor='rgba(255, 255, 255, 0.01)'
                        ),
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(color="#F1F5F9", family="Inter"),
                        margin=dict(l=40, r=40, t=40, b=40),
                        height=420,
                        showlegend=True
                    )
                    st.plotly_chart(fig_radar, use_container_width=True, config={'displayModeBar': False})
                else:
                    st.info("No categories to plot yet.")
        else:
            st.info("No subject metrics available. Please practice some questions first.")
            
    with col_rank:
        st.markdown("#### 🎯 Priority Ranking (Weakest Subjects first)")
        if subject_stats:
            # Sort by:
            # 1. Has errors (incorrect > 0) comes first.
            # 2. Accuracy rate ascending (lower accuracy is weaker).
            # 3. Incorrect count descending (more errors is weaker).
            sorted_subjects = sorted(
                subject_stats.items(),
                key=lambda x: (
                    x[1]["incorrect"] == 0,
                    x[1]["accuracy"],
                    -x[1]["incorrect"]
                )
            )
            # Filter to only subjects with attempted questions
            sorted_subjects = [s for s in sorted_subjects if s[1]["attempted"] > 0]
            
            cards_html = []
            for rank_idx, (subject, stats) in enumerate(sorted_subjects):
                errors = stats["incorrect"]
                accuracy = stats["accuracy"]
                attempted = stats["attempted"]
                
                # Determine tag styling and text based on accuracy and attempt volume
                if errors > 0:
                    if accuracy < 50.0:
                        tag_color = "#EF4444" # Red
                        tag_bg = "rgba(239, 68, 68, 0.15)"
                        tag_border = "1px solid #EF4444"
                        priority_tag = "🔴 CRITICAL FOCUS"
                    elif accuracy < 75.0:
                        tag_color = "#F59E0B" # Amber
                        tag_bg = "rgba(245, 158, 11, 0.15)"
                        tag_border = "1px solid #F59E0B"
                        priority_tag = "🟡 HIGH PRIORITY"
                    else:
                        tag_color = "#3B82F6" # Blue
                        tag_bg = "rgba(59, 130, 246, 0.15)"
                        tag_border = "1px solid #3B82F6"
                        priority_tag = "🔵 REVIEW FOCUS"
                else:
                    if attempted >= 5:
                        tag_color = "#10B981" # Green
                        tag_bg = "rgba(16, 185, 129, 0.15)"
                        tag_border = "1px solid #10B981"
                        priority_tag = "🟢 MASTERY STABLE"
                    else:
                        tag_color = "#6EE7B7" # Light green
                        tag_bg = "rgba(110, 231, 183, 0.1)"
                        tag_border = "1px solid rgba(110, 231, 183, 0.3)"
                        priority_tag = "🟢 PASSING (Low Data)"
                        
                cards_html.append(
                    f'<div style="background-color: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); '
                    f'padding: 12px 16px; border-radius: 10px; margin-bottom: 8px; display: flex; '
                    f'justify-content: space-between; align-items: center;">'
                    f'<div>'
                    f'<h5 style="margin: 0; font-size: 0.95em; color: #E2E8F0;">Rank {rank_idx+1}: {subject}</h5>'
                    f'<p style="margin: 4px 0 0 0; font-size: 0.8em; color: #94A3B8;">'
                    f'Score: {stats["correct"]}/{attempted} | Accuracy: {accuracy:.1f}%'
                    f'</p>'
                    f'</div>'
                    f'<span style="color: {tag_color}; background-color: {tag_bg}; border: {tag_border}; '
                    f'padding: 4px 8px; border-radius: 6px; font-size: 0.75em; font-weight: 600; '
                    f'letter-spacing: 0.05em; display: inline-block;">'
                    f'{priority_tag}'
                    f'</span>'
                    f'</div>'
                )
            
            # Render scrollable container with customized scrollbar
            # Keep 10 items visible (card height is ~58px, so max-height is set to 580px) and make remaining scrollable
            scrollable_wrapper = (
                f'<div style="max-height: 580px; overflow-y: auto; padding-right: 8px; '
                f'display: flex; flex-direction: column; gap: 2px;">'
                f'{"".join(cards_html)}'
                f'</div>'
            )
            st.markdown(scrollable_wrapper, unsafe_allow_html=True)
        else:
            st.info("Rankings will populate once you attempt questions.")
            
    st.markdown("---")
    
    # Render error category counts
    categories = {}
    for q in attempted_questions.values():
        if not q.get("is_correct", True):
            cat = q.get("feedback", {}).get("error_category", "Unclassified")
            categories[cat] = categories.get(cat, 0) + 1
            
    col_err_left, col_err_right = st.columns([1, 1])
    with col_err_left:
        st.markdown("#### 🔍 Error Category Frequencies")
        if categories:
            for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
                st.write(f"- **{cat}**: {count} errors")
        else:
            st.success("🎉 Excellent! Zero incorrect questions found in this session.")
            
    with col_err_right:
        st.markdown("#### ⚙️ Generate AI Diagnostic Report")
        st.write("Generates an advanced study review document including subject overview analysis, focus priority lists, and a **CFA Level II Readiness Verdict**.")
        
        api_key_set = bool(st.session_state.get("api_key"))
        if not api_key_set:
            st.warning("⚠️ Please provide and verify a Gemini API Key in the sidebar settings to generate the diagnostic report.")
            
        btn_diag = st.button(
            "Generate AI Diagnostic Report", 
            use_container_width=True, 
            disabled=(incorrect_count == 0 or not api_key_set),
            type="primary"
        )
        
        if btn_diag:
            from quizapp.utils.diagnostic import prepare_incorrect_questions_summary
            from quizapp.grader import generate_diagnostic_report
            
            incorrect_summary = prepare_incorrect_questions_summary(selected_progress, vignettes)
            
            if not incorrect_summary:
                st.error("Could not find matching question bank data for your incorrect attempts.")
            else:
                with st.spinner("Analyzing syllabus weak points, compiling accuracy rankings, and drafting exam readiness verdict..."):
                    res = generate_diagnostic_report(
                        api_key=st.session_state.api_key,
                        model=st.session_state.get("grade_model", DEFAULT_GRADE_MODEL),
                        incorrect_questions_summary=incorrect_summary,
                        subject_metrics=subject_stats
                    )
                    st.session_state.diagnostic_report = res.get("report_markdown", "")
                    st.session_state.predicted_score = res.get("predicted_score", accuracy)
                    st.session_state.confidence_margin = res.get("confidence_margin", margin_fallback)
                    st.success("✅ Diagnostic report generated successfully!")
                    st.rerun()

    # Display generated report
    if st.session_state.get("diagnostic_report"):
        st.markdown("---")
        st.markdown("### 📋 AI Diagnostic Report & Study Plan")
        
        st.markdown(
            f'<div class="glass-card" style="padding: 30px; border-radius: 12px; margin-bottom: 20px;">',
            unsafe_allow_html=True
        )
        st.markdown(st.session_state.diagnostic_report)
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.download_button(
            label="📥 Download Diagnostic Report (.md)",
            data=st.session_state.diagnostic_report,
            file_name="cfa_performance_diagnostic_report.md",
            mime="text/markdown",
            use_container_width=True
        )
        
        st.markdown("---")
        
        # Initialize chat history for diagnostic advisor
        if "diagnostic_chats" not in st.session_state:
            st.session_state.diagnostic_chats = []
            
        chat_header_col1, chat_header_col2 = st.columns([6, 1])
        with chat_header_col1:
            st.markdown("<h4 style='font-family: \"Outfit\", sans-serif; margin: 0;'>💬 Discuss Coach Diagnostic & Strategy</h4>", unsafe_allow_html=True)
        with chat_header_col2:
            if st.session_state.diagnostic_chats:
                st.markdown('<div class="clear-chat-container">', unsafe_allow_html=True)
                if st.button("🗑️ Clear", key="clear_diagnostic_chat", use_container_width=True):
                    st.session_state.diagnostic_chats = []
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
                
        # Render advisor messages
        if st.session_state.diagnostic_chats:
            for msg in st.session_state.diagnostic_chats:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
        else:
            st.markdown(
                '<div class="feedback-box" style="border-left: 4px solid #8B5CF6; background-color: rgba(139, 92, 246, 0.03); padding: 16px; border-radius: 0 8px 8px 0; margin-bottom: 15px;">'
                '<h5 style="margin-top: 0; color: #A78BFA; font-family: \'Outfit\', sans-serif;">💡 Discuss Study Strategy with the AI Coach</h5>'
                '<p style="font-size: 0.88em; opacity: 0.85; margin-bottom: 10px;">Ask for clarification on next steps, ask how to improve on specific subjects, or discuss readiness. Try asking:</p>'
                '<ul style="font-size: 0.85em; opacity: 0.8; margin-left: 20px; line-height: 1.5; padding-left: 0;">'
                '<li><em>"What are the top three actions I should focus on this week?"</em></li>'
                '<li><em>"How can I resolve my weakness in Using Multifactor Models?"</em></li>'
                '<li><em>"What concrete steps can I take to move from BORDERLINE to READY?"</em></li>'
                '</ul>'
                '</div>',
                unsafe_allow_html=True
            )
            
        # Form for coach chat input
        with st.form(key="diagnostic_chat_form", clear_on_submit=True):
            input_col, btn_col = st.columns([10, 1])
            with input_col:
                coach_query = st.text_input(
                    label="Ask the Coach:",
                    label_visibility="collapsed",
                    placeholder="Discuss study plans, mock targets, or specific weaknesses...",
                    key="diagnostic_coach_query"
                )
            with btn_col:
                st.markdown('<div class="chat-send-container">', unsafe_allow_html=True)
                submit_coach = st.form_submit_button(label="🚀 Send")
                st.markdown('</div>', unsafe_allow_html=True)
                
        if submit_coach and coach_query.strip():
            if not st.session_state.get("api_key"):
                st.warning("⚠️ API key required for AI Study Coach.")
            else:
                st.session_state.diagnostic_chats.append({"role": "user", "content": coach_query.strip()})
                
                from quizapp.grader import discuss_diagnostic_llm
                from quizapp.utils.diagnostic import prepare_incorrect_questions_summary
                
                # Fetch incorrect summary
                incorrect_summary = prepare_incorrect_questions_summary(selected_progress, vignettes)
                
                with st.spinner("AI Study Coach is formulating a strategy..."):
                    coach_response = discuss_diagnostic_llm(
                        api_key=st.session_state.api_key,
                        model=st.session_state.get("grade_model", DEFAULT_GRADE_MODEL),
                        subject_metrics=subject_stats,
                        incorrect_questions_summary=incorrect_summary,
                        diagnostic_report=st.session_state.diagnostic_report,
                        chat_history=st.session_state.diagnostic_chats[:-1],
                        user_query=coach_query.strip()
                    )
                st.session_state.diagnostic_chats.append({"role": "assistant", "content": coach_response})
                st.rerun()

def render_incorrect_review_page(progress, vignettes):
    import re
    from quizapp.utils.diagnostic import prepare_incorrect_questions_summary
    
    st.title("📋 Incorrect Questions Review Locker")
    st.write("Review all questions you answered incorrectly in this practice session, inspect your logic against official curriculum answers, and study diagnostic feedback.")
    
    st.markdown("---")
    
    # 1. Fetch incorrect questions
    incorrect_summary = prepare_incorrect_questions_summary(progress, vignettes)
    
    if not incorrect_summary:
        st.success("🎉 Outstanding! You have zero incorrect questions in this session.")
        st.info("💡 Keep practicing vignettes and mock exams to maintain this momentum!")
        return
        
    # Group vignettes by topic for context retrieval
    vignettes_by_topic = {v["topic"]: v for v in vignettes}
    
    # Calculate some helper counts for metrics
    total_incorrect = len(incorrect_summary)
    
    # Get error category counts
    error_counts = {}
    for item in incorrect_summary:
        cat = item.get("grader_error_category", "Unclassified")
        error_counts[cat] = error_counts.get(cat, 0) + 1
        
    dominant_error = "None"
    if error_counts:
        dominant_error = max(error_counts.items(), key=lambda x: x[1])[0]
        
    # Get modules with errors
    module_counts = {}
    for item in incorrect_summary:
        mod = item.get("module", "Other")
        module_counts[mod] = module_counts.get(mod, 0) + 1
        
    worst_module = "None"
    if module_counts:
        worst_module = max(module_counts.items(), key=lambda x: x[1])[0]
        
    # Render premium diagnostic metrics
    st.markdown("### 📊 Error Diagnostics")
    m_col1, m_col2, m_col3 = st.columns(3)
    with m_col1:
        st.metric("Total Incorrect Questions", total_incorrect)
    with m_col2:
        st.metric("Dominant Error Type", dominant_error)
    with m_col3:
        st.metric("Weakest Subject Area", worst_module)
        
    st.markdown("---")
    
    # 2. Filters Row
    st.markdown("### 🔍 Search & Filters")
    f_col1, f_col2, f_col3 = st.columns([1.5, 1.5, 2])
    
    # Extract unique modules and categories in correct summary for filter dropdowns
    available_modules = ["All Subject Areas"] + sorted(list({item["module"] for item in incorrect_summary}))
    available_categories = ["All Error Types"] + sorted(list({item["grader_error_category"] for item in incorrect_summary}))
    
    with f_col1:
        selected_mod_filter = st.selectbox("Filter by Subject", options=available_modules, key="incorrect_review_mod_filter")
    with f_col2:
        selected_cat_filter = st.selectbox("Filter by Error Type", options=available_categories, key="incorrect_review_cat_filter")
    with f_col3:
        search_query = st.text_input("Search Questions / Explanations", placeholder="Search keywords...", key="incorrect_review_search")
        
    # Apply filtering
    filtered_list = []
    for item in incorrect_summary:
        # Subject Filter
        if selected_mod_filter != "All Subject Areas" and item["module"] != selected_mod_filter:
            continue
        # Category Filter
        if selected_cat_filter != "All Error Types" and item["grader_error_category"] != selected_cat_filter:
            continue
        # Search keyword
        if search_query:
            query = search_query.lower()
            text_match = (
                query in item["question_text"].lower() or 
                query in item["official_explanation"].lower() or
                query in item["vignette_topic"].lower()
            )
            if not text_match:
                continue
        filtered_list.append(item)
        
    st.markdown(f"**Showing {len(filtered_list)} of {total_incorrect} incorrect attempts**")
    
    # 3. Export to Markdown option
    if filtered_list:
        # Build beautiful markdown review document
        export_lines = [
            f"# CFA Practice Review: Incorrect Questions Study Sheet",
            f"Generated on {st.query_params.get('q_bank', 'default').title()} Question Bank database.",
            f"Total Incorrect Questions in Review: {len(filtered_list)}\n",
            "---"
        ]
        
        for index, item in enumerate(filtered_list):
            export_lines.extend([
                f"## [{item['module']}] {item['vignette_topic']} - Question {index + 1}",
                f"**Question:** {item['question_text']}",
                f"**Your Answer:** Option {item['user_answer']}",
                f"**Correct Answer:** Option {item['correct_answer']}\n",
                f"**Error Category Diagnosis:** {item['grader_error_category']}",
                f"**AI Tutor Feedback:** {item['grader_feedback']}\n",
                f"**User original Reasoning:** *{item['user_explanation'] or 'No reasoning provided.'}*\n",
                f"**Official Curriculum Explanation:** {item['official_explanation']}",
                "\n---"
            ])
            
        export_md = "\n".join(export_lines)
        st.download_button(
            label="📥 Export Filtered Incorrect Questions (.md)",
            data=export_md,
            file_name="cfa_incorrect_questions_study_sheet.md",
            mime="text/markdown",
            use_container_width=True
        )
        
    st.markdown("")
    
    # 4. Render Expandable Question List
    for index, item in enumerate(filtered_list):
        vig = vignettes_by_topic.get(item["vignette_topic"])
        case_study_html = ""
        if vig:
            raw_case_text = vig.get("case_study_text", "")
            case_study_html = render_case_study(raw_case_text)
            
        expander_title = f"[{item['module']}] {item['vignette_topic']} (Error: {item['grader_error_category']})"
        
        with st.expander(expander_title):
            # Display collapsible Case Study context if available
            if case_study_html:
                with st.expander("📖 View Case Study Scenario / Exhibits"):
                    st.markdown(
                        f'<div class="left-panel glass-card" style="max-height: 50vh; overflow-y: auto; padding: 20px;">'
                        f'{case_study_html}'
                        f'</div>', 
                        unsafe_allow_html=True
                    )
            
            # Display Question text
            st.markdown(
                f'<div class="glass-card" style="padding: 15px; border-radius: 8px; margin-top: 10px; border-left: 4px solid #3B82F6;">'
                f'<strong>Question:</strong> {item["question_text"]}'
                f'</div>',
                unsafe_allow_html=True
            )
            
            # Display Options
            st.markdown("#### 📋 Choices & Selections:")
            for opt in item["options"]:
                opt_letter = opt.strip()[0].upper() if (opt.strip() and opt.strip()[0].upper() in ['A', 'B', 'C']) else ""
                is_correct = opt_letter == item["correct_answer"].upper()
                is_user = opt_letter == item["user_answer"].upper()
                
                if is_correct and is_user:
                    st.markdown(f"<div style='padding: 6px 12px; border-radius: 4px; background-color: rgba(16, 185, 129, 0.15); border-left: 4px solid #10B981; margin-bottom: 4px;'>🟢 <strong>{opt}</strong> <em>(Selected & Correct)</em></div>", unsafe_allow_html=True)
                elif is_correct:
                    st.markdown(f"<div style='padding: 6px 12px; border-radius: 4px; background-color: rgba(59, 130, 246, 0.15); border-left: 4px solid #3B82F6; margin-bottom: 4px;'>🔵 <strong>{opt}</strong> <em>(Correct Answer)</em></div>", unsafe_allow_html=True)
                elif is_user:
                    st.markdown(f"<div style='padding: 6px 12px; border-radius: 4px; background-color: rgba(239, 68, 68, 0.15); border-left: 4px solid #EF4444; margin-bottom: 4px;'>🔴 <del>{opt}</del> <em>(Your Selected Answer)</em></div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div style='padding: 6px 12px; border-radius: 4px; background-color: rgba(255, 255, 255, 0.03); margin-bottom: 4px; opacity: 0.7;'>⚪ {opt}</div>", unsafe_allow_html=True)
            
            # User original reasoning
            st.markdown("---")
            user_reasoning_display = item["user_explanation"] if item["user_explanation"] else "*No reasoning was provided.*"
            st.markdown(f"**Your original reasoning:**\n> *{user_reasoning_display}*")
            
            # AI Grader diagnostic feedback
            feedback_class = "feedback-incorrect"
            st.markdown(
                f'<div class="feedback-box {feedback_class}" style="margin-top: 15px;">'
                f'<h4>🔍 Grader Diagnostic Diagnosis: {item["grader_error_category"]}</h4>'
                f'<p>{item["grader_feedback"]}</p>'
                f'</div>',
                unsafe_allow_html=True
            )
            
            # Official Explanation
            with st.expander("📖 View Official Curriculum Explanation"):
                st.markdown(item["official_explanation"])

def render_flashcards_page(progress, vignettes, progress_path):
    import uuid
    import hashlib
    from quizapp.utils.diagnostic import prepare_incorrect_questions_summary
    from quizapp.grader import generate_flashcards_llm
    
    st.title("🎴 AI Spaced Repetition Flashcards")
    st.write("Retain formulas, calculator procedures, and core definitions using active recall and Leitner system spaced repetition.")
    
    st.markdown("---")
    
    flashcards = progress.get("flashcards", [])
    
    # Calculate stats for the spaced repetition grid
    box_1_cnt = sum(1 for c in flashcards if c.get("box", 1) == 1)
    box_2_cnt = sum(1 for c in flashcards if c.get("box", 1) == 2)
    box_3_cnt = sum(1 for c in flashcards if c.get("box", 1) == 3)
    box_4_cnt = sum(1 for c in flashcards if c.get("box", 1) == 4)
    
    st.markdown(
        f"""
        <div class="spaced-rep-grid">
            <div class="spaced-rep-item" style="border-left: 4px solid #EF4444;">
                <div class="count" style="color: #FCA5A5;">{box_1_cnt}</div>
                <div class="label">Box 1: Hard</div>
            </div>
            <div class="spaced-rep-item" style="border-left: 4px solid #F59E0B;">
                <div class="count" style="color: #FDE047;">{box_2_cnt}</div>
                <div class="label">Box 2: Medium</div>
            </div>
            <div class="spaced-rep-item" style="border-left: 4px solid #3B82F6;">
                <div class="count" style="color: #93C5FD;">{box_3_cnt}</div>
                <div class="label">Box 3: Easy</div>
            </div>
            <div class="spaced-rep-item" style="border-left: 4px solid #10B981;">
                <div class="count" style="color: #86EFAC;">{box_4_cnt}</div>
                <div class="label">🏆 Mastered</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Check key and diagnostics
    api_key_set = bool(st.session_state.get("api_key"))
    incorrect_summary = prepare_incorrect_questions_summary(progress, vignettes)
    
    # Sidebar generator / controls block
    with st.expander("🛠️ Card Generator & Management", expanded=not flashcards):
        g_col1, g_col2 = st.columns([2, 1])
        with g_col1:
            st.markdown("#### ⚡ Generate AI Flashcards")
            if incorrect_summary:
                st.write(f"You currently have **{len(incorrect_summary)}** incorrect questions recorded. We can generate high-yield study cards mapping to these specific mistakes.")
            else:
                st.write("You don't have any incorrect attempts recorded yet. We will generate standard foundational study cards from the curriculum.")
                
            card_limit = st.slider("Number of cards to generate", min_value=3, max_value=15, value=8)
            
            if not api_key_set:
                st.warning("⚠️ Enter and verify your Gemini API Key in the sidebar to generate flashcards.")
                
            btn_gen = st.button("Generate Cards", type="primary", disabled=not api_key_set, use_container_width=True)
            if btn_gen:
                with st.spinner("Gemini is analyzing curriculum concepts and generating flashcards..."):
                    generated_cards = generate_flashcards_llm(
                        api_key=st.session_state.api_key,
                        model=st.session_state.get("grade_model", "gemini-2.5-flash"),
                        incorrect_questions_summary=incorrect_summary,
                        fallback_vignettes=vignettes,
                        limit=card_limit
                    )
                    
                    if not generated_cards:
                        st.error("Failed to generate flashcards. Please check connection or API key.")
                    else:
                        import time
                        added_count = 0
                        # Prevent duplicate flashcards by checking fronts
                        existing_fronts = {c["front"].strip().lower() for c in flashcards}
                        
                        for c in generated_cards:
                            front_txt = c.get("front", "").strip()
                            if front_txt and front_txt.lower() not in existing_fronts:
                                # Create unique ID
                                cid = hashlib.md5(f"{front_txt}_{time.time()}".encode("utf-8")).hexdigest()[:12]
                                flashcards.append({
                                    "id": cid,
                                    "subject": c.get("subject", "General"),
                                    "front": front_txt,
                                    "back": c.get("back", "").strip(),
                                    "box": 1,
                                    "next_review": ""
                                })
                                existing_fronts.add(front_txt.lower())
                                added_count += 1
                                
                        if added_count > 0:
                            progress["flashcards"] = flashcards
                            save_progress(progress_path, progress)
                            st.success(f"Successfully generated and added {added_count} active study cards!")
                            st.rerun()
                        else:
                            st.warning("All generated cards were duplicates of existing cards. Try resetting the deck first or practicing more questions.")
                            
        with g_col2:
            st.markdown("#### 🗑️ Card Management")
            st.write("Reset card positions to Box 1, or wipe the current deck to start clean.")
            if st.button("Reset Cards to Box 1", use_container_width=True):
                for c in flashcards:
                    c["box"] = 1
                progress["flashcards"] = flashcards
                save_progress(progress_path, progress)
                st.success("All cards reset to Box 1!")
                st.rerun()
                
            if st.button("Clear Deck (Delete All)", use_container_width=True, type="secondary"):
                progress["flashcards"] = []
                save_progress(progress_path, progress)
                st.success("Wiped card database!")
                st.rerun()
                
    if not flashcards:
        st.info("💡 Your card deck is empty. Open the management drawer above and click 'Generate Cards' to begin.")
        return
        
    # Spaced repetition filter: review Box 1, Box 2, Box 3. Box 4 is mastered.
    active_cards = [c for c in flashcards if c.get("box", 1) < 4]
    
    if not active_cards:
        st.balloons()
        st.markdown(
            """
            <div class="feedback-box feedback-correct" style="padding: 30px; text-align: center;">
                <h3>🎉 Card Deck Mastered!</h3>
                <p>Outstanding! You have successfully reviewed and categorized all flashcards into your Mastered Box.</p>
                <p>Open the management drawer above to reset card positions and run another recall cycle.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        return
        
    # Navigation tracking for active cards
    if "current_card_idx" not in st.session_state:
        st.session_state.current_card_idx = 0
        
    if st.session_state.current_card_idx >= len(active_cards):
        st.session_state.current_card_idx = max(0, len(active_cards) - 1)
        
    card_idx = st.session_state.current_card_idx
    card = active_cards[card_idx]
    
    # Initialize card flip state
    if "card_flipped" not in st.session_state:
        st.session_state.card_flipped = False
        
    flipped = st.session_state.card_flipped
    box_num = card.get("box", 1)
    
    box_labels = {
        1: "Box 1: Hard",
        2: "Box 2: Medium",
        3: "Box 3: Easy",
        4: "🏆 Mastered"
    }
    
    # Outer Glass Card Layout
    card_html = f"""
    <div class="flashcard-outer">
        <span class="flashcard-subject-badge">{card.get("subject", "General")}</span>
        <span class="flashcard-status-badge flashcard-box-{box_num}">{box_labels[box_num]}</span>
        <div style="height: 25px;"></div>
    """
    st.markdown(card_html, unsafe_allow_html=True)
    
    if not flipped:
        st.markdown(f"<div class='flashcard-front'>{card.get('front')}</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='flashcard-back'>", unsafe_allow_html=True)
        st.markdown("#### Answer / Explanation:")
        st.markdown(card.get("back"))
        st.markdown("</div>", unsafe_allow_html=True)
        
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Card controls (Flip / Review ratings)
    ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([1, 2, 1])
    with ctrl_col2:
        if not flipped:
            if st.button("🔄 Reveal Answer", type="primary", use_container_width=True):
                st.session_state.card_flipped = True
                st.rerun()
        else:
            # Leitner buttons
            b_col1, b_col2, b_col3, b_col4 = st.columns(4)
            with b_col1:
                if st.button("🔴 Hard", help="Keep in Box 1", use_container_width=True):
                    update_card_box(progress, card["id"], 1, progress_path)
            with b_col2:
                if st.button("🟡 Good", help="Move to Box 2", use_container_width=True):
                    update_card_box(progress, card["id"], 2, progress_path)
            with b_col3:
                if st.button("🔵 Easy", help="Move to Box 3", use_container_width=True):
                    update_card_box(progress, card["id"], 3, progress_path)
            with b_col4:
                if st.button("🏆 Master", help="Archive to Mastered", use_container_width=True):
                    update_card_box(progress, card["id"], 4, progress_path)
                    
            if st.button("🔄 Show Question", use_container_width=True):
                st.session_state.card_flipped = False
                st.rerun()
                
    # Footer navigation controls
    st.markdown("---")
    nav_col1, nav_col2, nav_col3 = st.columns([1, 2, 1])
    with nav_col1:
        if st.button("⬅️ Previous Card", disabled=card_idx == 0, use_container_width=True):
            st.session_state.current_card_idx -= 1
            st.session_state.card_flipped = False
            st.rerun()
    with nav_col2:
        st.markdown(f"<p style='text-align: center; font-size: 0.9em; margin-top: 8px;'>Card {card_idx + 1} of {len(active_cards)} active cards</p>", unsafe_allow_html=True)
    with nav_col3:
        if st.button("Next Card ➡️", disabled=card_idx == len(active_cards) - 1, use_container_width=True):
            st.session_state.current_card_idx += 1
            st.session_state.card_flipped = False
            st.rerun()

def update_card_box(progress, card_id, target_box, progress_path):
    """Updates a card's box level in the progress file and resets states."""
    for c in progress["flashcards"]:
        if c["id"] == card_id:
            c["box"] = target_box
            break
    save_progress(progress_path, progress)
    st.session_state.card_flipped = False
    st.rerun()

if __name__ == "__main__":
    main()

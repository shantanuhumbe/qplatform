import streamlit as st
import pandas as pd
import plotly.express as px
import os
import json

def render_sidebar(progress, vignettes):
    """Renders the quiz study dashboard sidebar, statistics, and configuration inputs."""
    with st.sidebar:
        st.markdown("<h2 style='text-align: center; color: #3B82F6;'>🎯 Study Dashboard</h2>", unsafe_allow_html=True)
        st.markdown("---")
        
        # Page Navigation
        st.subheader("📂 Navigation")
        if "active_page" not in st.session_state:
            st.session_state.active_page = "Practice Quiz"
            
        active_page = st.selectbox(
            "Select Page View",
            options=["Practice Quiz", "AI Performance Diagnostic"],
            index=0 if st.session_state.active_page == "Practice Quiz" else 1,
            key="page_navigation_selectbox",
            help="Switch between the practice questions workspace and the AI performance analyzer."
        )
        if active_page != st.session_state.active_page:
            st.session_state.active_page = active_page
            st.rerun()
            
        st.markdown("---")
        
        # 0. Question Bank Selector
        st.subheader("📚 Question Bank")
        active_db = st.session_state.get("active_db", "default")
        db_options = {
            "default": "CFA Combined QB (Default)",
            "merged": "Merged Q-Bank (qbank_merged)"
        }
        selected_db = st.selectbox(
            "Select Question Bank",
            options=["default", "merged"],
            format_func=lambda x: db_options[x],
            index=0 if active_db == "default" else 1,
            help="Select which question bank database to load questions from."
        )
        if selected_db != active_db:
            st.session_state.active_db = selected_db
            st.session_state.active_vignette_topic = ""
            st.session_state.question_index = 0
            st.rerun()
            
        st.markdown("---")
        
        # 1. API Configuration
        st.subheader("🔑 API Settings")
        
        env_key = os.environ.get("GEMINI_API_KEY", "").strip()
        is_env_valid = (
            len(env_key) >= 10 and 
            not any(c.isspace() for c in env_key) and
            all(32 <= ord(c) <= 126 for c in env_key)
        )
        
        if "api_key" not in st.session_state:
            st.session_state.api_key = env_key if is_env_valid else ""
            
        if "api_key_validation" not in st.session_state:
            st.session_state.api_key_validation = None
            
        curr_key = st.session_state.api_key
        
        with st.form("api_key_form", clear_on_submit=False):
            api_key_input = st.text_input(
                "Gemini API Key", 
                type="password", 
                value=curr_key,
                help="Optional. Used for dynamic AI grading and parsing new PDFs. Offline fallback grading is used if not provided."
            )
            btn_clicked = st.form_submit_button("Apply & Verify Key", use_container_width=True)
            
        if btn_clicked:
            api_key_clean = api_key_input.strip()
            if not api_key_clean:
                st.session_state.api_key = ""
                st.session_state.api_key_validation = None
                st.rerun()
            else:
                is_input_valid = (
                    len(api_key_clean) >= 10 and 
                    not any(c.isspace() for c in api_key_clean) and
                    all(32 <= ord(c) <= 126 for c in api_key_clean)
                )
                if is_input_valid:
                    from quizapp.grader import validate_api_key
                    model = st.session_state.get("grade_model", "gemini-2.5-flash")
                    with st.spinner("Validating API Key with a sample request..."):
                        is_valid, msg = validate_api_key(api_key_clean, model)
                        if is_valid:
                            st.session_state.api_key = api_key_clean
                            st.session_state.api_key_validation = ("success", "✅ API Key validated successfully! (Connection active)")
                        else:
                            st.session_state.api_key_validation = ("error", f"❌ Validation failed: {msg}")
                    st.rerun()
                else:
                    st.session_state.api_key_validation = ("error", "❌ Invalid key format (must be at least 10 chars, no spaces).")
                    st.rerun()
                    
        # Display validation feedback
        if st.session_state.api_key_validation:
            status, msg = st.session_state.api_key_validation
            if status == "success":
                st.success(msg)
            else:
                st.error(msg)
        elif not st.session_state.api_key:
            if is_env_valid:
                st.info("Using Gemini API Key from environment.")
            else:
                st.info("Optional: Set API Key for AI grading. Otherwise, offline fallback will be used.")
            
        # Model Selection
        model_options = {
            "gemini-2.5-flash": "Gemini 2.5 Flash (Default - Fast & Smart)",
            "gemini-2.5-flash-lite": "Gemini 2.5 Flash-Lite (Rate-Limit Friendly)",
            "gemini-2.0-flash": "Gemini 2.0 Flash (Fast & Balanced)",
            "gemini-2.5-pro": "Gemini 2.5 Pro (Detailed - Slow)"
        }
        
        curr_model = st.session_state.get("grade_model", "gemini-2.5-flash")
        if curr_model not in model_options:
            curr_model = "gemini-2.5-flash"
            
        selected_model_key = st.selectbox(
            "AI Grading Model",
            options=list(model_options.keys()),
            format_func=lambda x: model_options[x],
            index=list(model_options.keys()).index(curr_model),
            help="Select the Gemini model for evaluation. If you hit 'Too Many Requests (429)' errors, try switching to Gemini 1.5 Flash."
        )
        st.session_state.grade_model = selected_model_key
        
        st.markdown("---")
        
        # 2. Filtering Options
        st.subheader("📚 Study Mode")
        mode = st.radio("Selection Mode", ["Random Vignettes", "Topic-Based"],
                        index=0 if st.session_state.get("filtering_mode", "Random") == "Random" else 1)
        st.session_state.filtering_mode = "Random" if mode == "Random Vignettes" else "Topic"
        
        if st.session_state.filtering_mode == "Topic":
            # Extract unique topics/modules from vignettes list
            topics = sorted(list({v["module"] for v in vignettes})) if vignettes else []
            if topics:
                selected_topic = st.selectbox("Select Learning Module", topics,
                                              index=topics.index(st.session_state.get("selected_topic")) if st.session_state.get("selected_topic") in topics else 0)
                st.session_state.selected_topic = selected_topic
            else:
                st.warning("No modules found in question bank. Parse some pages first!")
        
        st.markdown("---")
        
        # 3. Session Statistics
        st.subheader("📈 Performance Analysis")
        score = progress.get("score", 0)
        attempted = progress.get("total_attempted", 0)
        pct = (score / attempted * 100) if attempted > 0 else 0.0
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Score", f"{score}/{attempted}")
        with col2:
            st.metric("Accuracy", f"{pct:.1f}%")
            
        # 4. Error Category Chart
        stats = progress.get("statistics", {})
        # Filter out 'None' for error categories
        error_stats = {k: v for k, v in stats.items() if k != "None" and v > 0}
        
        if error_stats:
            st.markdown("#### 🔍 Error Analysis (Weaknesses)")
            df = pd.DataFrame(list(error_stats.items()), columns=["Error Category", "Count"])
            fig = px.bar(df, x="Count", y="Error Category", orientation='h',
                         color="Error Category",
                         color_discrete_sequence=px.colors.sequential.Sunsetdark,
                         template="plotly_dark")
            fig.update_layout(
                margin=dict(l=10, r=10, t=10, b=10),
                height=150,
                showlegend=False,
                xaxis_title=None,
                yaxis_title=None
            )
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        else:
            st.info("No error categories tracked yet. Attempt questions to diagnose weak areas.")
            
        # 5. Backup & Restore
        st.markdown("---")
        st.subheader("💾 Backup & Restore")
        
        try:
            progress_json_str = json.dumps(progress, indent=2, ensure_ascii=False)
            st.download_button(
                label="📥 Download Progress JSON",
                data=progress_json_str,
                file_name="cfa_study_progress.json",
                mime="application/json",
                use_container_width=True,
                help="Download your session scores and stats to save locally."
            )
        except Exception as e:
            st.error(f"Error preparing download: {e}")
            
        uploaded_file = st.file_uploader(
            "Restore Progress",
            type=["json"],
            help="Upload a previously saved cfa_study_progress.json to restore your progress."
        )
        if uploaded_file is not None:
            try:
                uploaded_data = json.load(uploaded_file)
                required_keys = ["attempted_questions", "completed_vignettes", "score", "total_attempted", "statistics"]
                if all(k in uploaded_data for k in required_keys):
                    if uploaded_data != progress:
                        from quizapp.utils.data_manager import save_progress
                        from quizapp.config import DEFAULT_PROGRESS_PATH, MERGED_PROGRESS_PATH
                        active_db = st.session_state.get("active_db", "default")
                        prog_path = MERGED_PROGRESS_PATH if active_db == "merged" else DEFAULT_PROGRESS_PATH
                        save_progress(prog_path, uploaded_data)
                        st.success("✅ Progress uploaded and restored!")
                        st.rerun()
                else:
                    st.error("❌ Invalid format: missing required progress keys.")
            except Exception as e:
                st.error(f"❌ Error parsing progress file: {e}")

        st.markdown("---")
        
        # 6. Reset progress button
        if st.button("Reset Session Progress"):
            st.session_state.reset_progress = True
            st.rerun()

def render_navigation_dots(questions, attempted_status, active_idx):
    """Draws visual interactive progress dot indicators for vignette questions."""
    html_dots = []
    for idx in range(len(questions)):
        key = f"q_{idx}"
        status = attempted_status.get(idx, {})
        
        # Determine dot styling class
        if idx == active_idx:
            dot_class = "dot-current"
        elif status.get("answered", False):
            dot_class = "dot-correct" if status.get("is_correct", False) else "dot-incorrect"
        else:
            dot_class = "dot-unanswered"
            
        html_dots.append(f'<span class="nav-dot {dot_class}" title="Question {idx+1}"></span>')
        
    dot_row = "".join(html_dots)
    st.markdown(f'<div class="dot-container"><span>Questions:</span> {dot_row}</div>', unsafe_allow_html=True)

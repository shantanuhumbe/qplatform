import streamlit as st
import pandas as pd
import plotly.express as px
import os

def render_sidebar(progress, vignettes):
    """Renders the quiz study dashboard sidebar, statistics, and configuration inputs."""
    with st.sidebar:
        st.markdown("<h2 style='text-align: center; color: #3B82F6;'>🎯 Study Dashboard</h2>", unsafe_allow_html=True)
        st.markdown("---")
        
        # 1. API Configuration
        st.subheader("🔑 API Settings")
        
        env_key = os.environ.get("GEMINI_API_KEY", "").strip()
        is_env_valid = (
            len(env_key) >= 10 and 
            not any(c.isspace() for c in env_key) and
            all(32 <= ord(c) <= 126 for c in env_key)
        )
        
        curr_key = st.session_state.get("api_key", "")
        curr_key_valid = (
            len(curr_key) >= 10 and 
            not any(c.isspace() for c in curr_key) and
            all(32 <= ord(c) <= 126 for c in curr_key)
        )
        if not curr_key_valid and is_env_valid:
            curr_key = env_key
            st.session_state.api_key = env_key
            
        api_key = st.text_input("Gemini API Key", type="password", 
                               value=curr_key,
                               help="Required for dynamic AI grading and parsing new PDFs.")
        
        if api_key:
            api_key_clean = api_key.strip()
            is_input_valid = (
                len(api_key_clean) >= 10 and 
                not any(c.isspace() for c in api_key_clean) and
                all(32 <= ord(c) <= 126 for c in api_key_clean)
            )
            if is_input_valid:
                st.session_state.api_key = api_key_clean
            else:
                st.warning("⚠️ Invalid key format detected (spaces or special characters). Browser autofill might have inserted web text. Using env key or fallback.")
                if is_env_valid:
                    st.session_state.api_key = env_key
                else:
                    st.session_state.api_key = ""
        else:
            if is_env_valid:
                st.session_state.api_key = env_key
            else:
                st.info("API Key required. Enter key or set GEMINI_API_KEY environment variable.")
            
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
            
        # 5. Reset progress button
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

import streamlit as st

CUSTOM_CSS = """
<style>
/* Import modern typography from Google Fonts */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;600;700&display=swap');

/* Apply general fonts and layout styling */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    color: #F1F5F9;
}

h1, h2, h3, h4, h5, h6 {
    font-family: 'Outfit', sans-serif;
}

/* Background gradient for premium look */
.main {
    background: radial-gradient(circle at top right, #111827, #030712);
}

/* Glassmorphism containers */
.glass-card {
    background: rgba(17, 24, 39, 0.7);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    padding: 24px;
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
    margin-bottom: 20px;
}

.left-panel {
    border-right: 1px solid rgba(255, 255, 255, 0.08);
    padding-right: 20px;
    height: 85vh;
    overflow-y: auto;
}

.right-panel {
    padding-left: 20px;
    height: 85vh;
    overflow-y: auto;
}

/* Custom badges */
.badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 12px;
}

.badge-topic {
    background: linear-gradient(135deg, #3B82F6, #1D4ED8);
    color: #FFFFFF;
}

.badge-module {
    background: linear-gradient(135deg, #10B981, #047857);
    color: #FFFFFF;
}

/* Custom scrollbars */
::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}

::-webkit-scrollbar-track {
    background: rgba(255, 255, 255, 0.02);
    border-radius: 9999px;
}

::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.15);
    border-radius: 9999px;
}

::-webkit-scrollbar-thumb:hover {
    background: rgba(255, 255, 255, 0.3);
}

/* Math equations and markdown tables rendering */
.left-panel table,
.glass-card table,
table, .stMarkdown table, .stTable table {
    width: 100%;
    border-collapse: collapse;
    margin: 16px 0;
    font-size: 0.85rem;
    table-layout: auto;
    overflow-wrap: break-word;
}

/* Wrapper for horizontal scroll on wide tables */
.left-panel {
    overflow-x: auto;
}

.left-panel table,
.glass-card table,
.stMarkdown th, .stMarkdown td, th, td {
    border: 1px solid rgba(255, 255, 255, 0.12);
    padding: 8px 12px;
    text-align: left;
    white-space: nowrap;
}

/* Allow cell content to wrap when needed */
.left-panel td,
.glass-card td {
    white-space: normal;
    word-break: break-word;
    min-width: 60px;
}

.left-panel th,
.glass-card th,
th {
    background: linear-gradient(135deg, rgba(59, 130, 246, 0.15), rgba(59, 130, 246, 0.05));
    font-weight: 600;
    color: #93C5FD;
    white-space: normal;
    word-break: break-word;
}

.left-panel tr:nth-child(even),
.glass-card tr:nth-child(even),
tr:nth-child(even) {
    background-color: rgba(255, 255, 255, 0.03);
}

.left-panel tr:hover,
.glass-card tr:hover,
tr:hover {
    background-color: rgba(59, 130, 246, 0.08);
    transition: background-color 0.2s ease;
}

/* Dot Navigation Indicators */
.dot-container {
    display: flex;
    gap: 8px;
    margin: 15px 0;
    align-items: center;
}

.nav-dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    display: inline-block;
}

.dot-correct {
    background-color: #10B981;
    box-shadow: 0 0 8px #10B981;
}

.dot-incorrect {
    background-color: #EF4444;
    box-shadow: 0 0 8px #EF4444;
}

.dot-unanswered {
    background-color: #4B5563;
    border: 1px solid rgba(255, 255, 255, 0.2);
}

.dot-current {
    background-color: #3B82F6;
    box-shadow: 0 0 8px #3B82F6;
    border: 2px solid #FFFFFF;
}

/* Interactive elements */
div.stButton > button {
    background: linear-gradient(135deg, #3B82F6, #1D4ED8);
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 24px;
    font-weight: 600;
    transition: all 0.3s ease;
    box-shadow: 0 4px 14px rgba(59, 130, 246, 0.4);
}

div.stButton > button:hover {
    background: linear-gradient(135deg, #2563EB, #1E40AF);
    box-shadow: 0 6px 20px rgba(59, 130, 246, 0.6);
    transform: translateY(-1px);
}

div.stButton > button:active {
    transform: translateY(1px);
}

/* Feedback blocks */
.feedback-box {
    border-left: 4px solid #3B82F6;
    background-color: rgba(59, 130, 246, 0.05);
    padding: 16px;
    border-radius: 0 8px 8px 0;
    margin-top: 15px;
}

.feedback-correct {
    border-left: 4px solid #10B981;
    background-color: rgba(16, 185, 129, 0.05);
}

.feedback-incorrect {
    border-left: 4px solid #EF4444;
    background-color: rgba(239, 68, 68, 0.05);
}
</style>
"""

def apply_custom_styles():
    """Injects the custom premium stylesheet into the Streamlit app context."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

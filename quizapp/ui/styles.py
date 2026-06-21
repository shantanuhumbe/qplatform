import streamlit as st

CUSTOM_CSS = """
<style>
/* Import modern typography from Google Fonts */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;600;700&display=swap');

/* Apply general fonts and layout styling */
html, body {
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

/* Premium overrides for Streamlit's native chat messages */
[data-testid="stChatMessage"] {
    background-color: rgba(255, 255, 255, 0.02) !important;
    border: 1px solid rgba(255, 255, 255, 0.05) !important;
    border-radius: 12px !important;
    padding: 12px 16px !important;
    margin-bottom: 12px !important;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2) !important;
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    transition: all 0.3s ease;
}

[data-testid="stChatMessage"]:hover {
    border-color: rgba(255, 255, 255, 0.1) !important;
    background-color: rgba(255, 255, 255, 0.04) !important;
}

/* User message specific style */
[data-testid="stChatMessageUser"] {
    background: linear-gradient(135deg, rgba(37, 99, 235, 0.08), rgba(124, 58, 237, 0.08)) !important;
    border: 1px solid rgba(124, 58, 237, 0.25) !important;
    box-shadow: 0 4px 15px rgba(124, 58, 237, 0.05) !important;
}

[data-testid="stChatMessageUser"]:hover {
    background: linear-gradient(135deg, rgba(37, 99, 235, 0.12), rgba(124, 58, 237, 0.12)) !important;
    border-color: rgba(124, 58, 237, 0.35) !important;
}

/* Assistant message specific style */
[data-testid="stChatMessageAssistant"] {
    background: rgba(255, 255, 255, 0.02) !important;
    border: 1px solid rgba(255, 255, 255, 0.05) !important;
}

/* Hide Streamlit default avatar borders or improve them */
[data-testid="stChatMessage"] [data-testid="stChatMessageAvatar"] {
    background-color: rgba(255, 255, 255, 0.04) !important;
    border-radius: 50% !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
}

/* Style chat forms to be borderless and clean */
[data-testid="stForm"] {
    border: none !important;
    padding: 0 !important;
    background-color: transparent !important;
    margin-top: 15px !important;
}

/* Target buttons inside clear-chat-container */
.clear-chat-container div.stButton > button {
    background: rgba(239, 68, 68, 0.05) !important;
    color: #EF4444 !important;
    border: 1px solid rgba(239, 68, 68, 0.2) !important;
    box-shadow: none !important;
    border-radius: 8px !important;
    padding: 4px 10px !important;
    font-size: 0.8rem !important;
    font-weight: 500 !important;
    transition: all 0.2s ease !important;
    height: 32px !important;
}

.clear-chat-container div.stButton > button:hover {
    background: rgba(239, 68, 68, 0.12) !important;
    border-color: #EF4444 !important;
    color: #F87171 !important;
}

/* Style chat send button to look integrated and premium */
.chat-send-container button {
    background: linear-gradient(135deg, #10B981, #059669) !important;
    box-shadow: 0 4px 12px rgba(16, 185, 129, 0.2) !important;
    border-radius: 8px !important;
    width: 100% !important;
    padding: 8px 16px !important;
    font-size: 0.95rem !important;
    border: none !important;
    color: white !important;
    transition: all 0.2s ease !important;
}

.chat-send-container button:hover {
    background: linear-gradient(135deg, #059669, #047857) !important;
    box-shadow: 0 6px 16px rgba(16, 185, 129, 0.4) !important;
    transform: translateY(-1px);
}

/* Premium style for Apply & Verify Key button */
div.stFormSubmitButton > button {
    background: linear-gradient(135deg, #8B5CF6, #6D28D9) !important;
    box-shadow: 0 4px 12px rgba(139, 92, 246, 0.25) !important;
    border: none !important;
    border-radius: 8px !important;
    color: white !important;
    transition: all 0.2s ease !important;
    width: 100% !important;
}

div.stFormSubmitButton > button:hover {
    background: linear-gradient(135deg, #7C3AED, #5B21B6) !important;
    box-shadow: 0 6px 16px rgba(139, 92, 246, 0.45) !important;
    transform: translateY(-1px);
}

/* Remove default border, background, and padding from sidebar form container */
[data-testid="stSidebar"] [data-testid="stForm"] {
    border: none !important;
    background: transparent !important;
    padding: 0 !important;
}

/* Flashcards Custom Styles */
.flashcard-outer {
    background: rgba(30, 41, 59, 0.4);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid rgba(139, 92, 246, 0.25);
    border-radius: 20px;
    padding: 35px 30px;
    min-height: 280px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    box-shadow: 0 12px 40px 0 rgba(0, 0, 0, 0.4);
    margin: 20px 0;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    overflow: hidden;
}

.flashcard-outer:hover {
    border-color: rgba(139, 92, 246, 0.5);
    box-shadow: 0 16px 48px 0 rgba(139, 92, 246, 0.15);
    transform: translateY(-2px);
}

.flashcard-front {
    color: #E2E8F0;
    font-size: 1.35em;
    font-weight: 500;
    text-align: center;
    font-family: 'Outfit', sans-serif;
    line-height: 1.4;
}

.flashcard-back {
    color: #CBD5E1;
    font-size: 1.05em;
    font-weight: 400;
    text-align: left;
    line-height: 1.5;
    width: 100%;
}

.flashcard-back h4 {
    color: #A78BFA;
    margin-top: 0;
    font-family: 'Outfit', sans-serif;
}

.flashcard-subject-badge {
    position: absolute;
    top: 15px;
    left: 20px;
    font-size: 0.72rem;
    font-weight: 600;
    background: rgba(139, 92, 246, 0.15);
    border: 1px solid rgba(139, 92, 246, 0.3);
    color: #C084FC;
    padding: 3px 10px;
    border-radius: 9999px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.flashcard-status-badge {
    position: absolute;
    top: 15px;
    right: 20px;
    font-size: 0.72rem;
    font-weight: 600;
    padding: 3px 10px;
    border-radius: 9999px;
    letter-spacing: 0.05em;
}

.flashcard-box-1 {
    background: rgba(239, 68, 68, 0.15);
    border: 1px solid rgba(239, 68, 68, 0.3);
    color: #FCA5A5;
}

.flashcard-box-2 {
    background: rgba(245, 158, 11, 0.15);
    border: 1px solid rgba(245, 158, 11, 0.3);
    color: #FDE047;
}

.flashcard-box-3 {
    background: rgba(59, 130, 246, 0.15);
    border: 1px solid rgba(59, 130, 246, 0.3);
    color: #93C5FD;
}

.flashcard-box-4 {
    background: rgba(16, 185, 129, 0.15);
    border: 1px solid rgba(16, 185, 129, 0.3);
    color: #86EFAC;
}

.spaced-rep-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-bottom: 25px;
}

.spaced-rep-item {
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 12px;
    padding: 12px;
    text-align: center;
}

.spaced-rep-item .count {
    font-size: 1.5em;
    font-weight: 700;
    margin-bottom: 2px;
    font-family: 'Outfit', sans-serif;
}

.spaced-rep-item .label {
    font-size: 0.75em;
    color: #94A3B8;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
</style>

"""

def apply_custom_styles():
    """Injects the custom premium stylesheet into the Streamlit app context."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

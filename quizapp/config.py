import os

# API Configuration
DEFAULT_PARSE_MODEL = "gemini-2.5-flash"
DEFAULT_GRADE_MODEL = "gemini-2.5-flash"

# Parsing parameters
DEFAULT_CHUNK_SIZE = 15
DEFAULT_OVERLAP = 3

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_PDF_PATH = os.path.join(BASE_DIR, "CFA Combined QB (1).pdf")
DEFAULT_OUTPUT_PATH = os.path.join(BASE_DIR, "questions_bank.json")
DEFAULT_PROGRESS_PATH = os.path.join(BASE_DIR, "user_progress.json")

# Default prompt templates
PARSER_SYSTEM_INSTRUCTION = (
    "You are an expert curriculum content parser. Extract all vignettes (case studies/scenarios) "
    "and their associated multiple-choice questions from the provided text.\n"
    "Identify where a case study or vignette starts and capture all background information. "
    "Link all subsequent multiple-choice questions to that case study.\n"
    "Ensure each question contains the question text, options (typically A, B, C), the correct letter answer (only 'A', 'B', or 'C'), "
    "and the official explanation or answer rationale.\n"
    "CRITICAL REQUIREMENT: Do NOT extract or return any vignette or question that is cut off or incomplete "
    "at the beginning or end of the page range. Only extract complete, fully self-contained vignettes and "
    "their corresponding questions. If a vignette is cut off, discard it entirely.\n"
    "FORMATTING REQUIREMENT: Format the `case_study_text` using rich, readable markdown. "
    "Organize long text walls with clear sub-headings (e.g. `### Background`, `### Company Information`), "
    "bold key names/terms/statements, use bulleted lists for company characteristics or key conditions, "
    "and construct markdown tables for any numeric/tabular datasets. This is essential for students to easily scan "
    "and locate statements.\n"
    "Generate a structured JSON response matching the provided schema."
)

GRADER_SYSTEM_INSTRUCTION = (
    "You are an expert tutor grading a student's answer for a vignette-based multiple-choice question.\n"
    "Compare the student's selected answer and their explanation of reasoning against the correct answer and "
    "the official explanation.\n"
    "Perform a conceptual diagnosis. Identify if they made a calculation error, a conceptual gap, a formula misuse, "
    "or a reading misinterpretation. Grade their response and provide constructive, detailed feedback explaining why.\n"
    "Generate a structured JSON response matching the provided schema."
)

# CFA Module to Page mappings (1-indexed)
CFA_MODULES = {
    1: ("Equity Valuation: Applications and Processes", 1, 16),
    2: ("Discounted Dividend Valuation", 17, 63),
    3: ("Free Cash Flow Valuation", 64, 101),
    4: ("Market-Based Valuation: Price and Enterprise Value", 102, 135),
    5: ("Residual Income Valuation", 136, 167),
    6: ("Private Company Valuation", 168, 196),
    7: ("Code of Ethics and Standards of Professional Conduct", 197, 208),
    8: ("Guidance for Standards I–VII", 209, 274),
    9: ("Application of the Code and Standards: Level II", 275, 282),
    10: ("The Term Structure and Interest Rate Dynamics", 283, 318),
    11: ("The Arbitrage-Free Valuation Framework", 319, 353),
    12: ("Valuation and Analysis of Bonds with Embedded Options", 354, 400),
    13: ("Credit Analysis Models", 401, 452),
    14: ("Credit Default Swaps", 453, 474),
    15: ("Economics and Investment Markets", 475, 502),
    16: ("Analysis of Active Portfolio Management", 503, 538),
    17: ("Exchange-Traded Funds: Mechanics and Applications", 539, 556),
    18: ("Using Multifactor Models", 557, 585),
    19: ("Measuring and Managing Market Risk", 586, 620),
    20: ("Backtesting and Simulation", 621, 637),
    21: ("Introduction to Commodities and Commodity Derivatives", 638, 665),
    22: ("Overview of Types of Real Estate Investment", 666, 677),
    23: ("Investments in Real Estate through Publicly Traded", 678, 696),
    24: ("Hedge Fund Strategies", 697, 727),
    25: ("Analysis of Dividends and Share Repurchases", 728, 754),
    26: ("Environmental, Social, and Governance (ESG)", 755, 768),
    27: ("Cost of Capital: Advanced Topics", 769, 780),
    28: ("Corporate Restructuring", 781, 894),
    29: ("Currency Exchange Rates: Understanding Equilibrium Value", 895, 943),
    30: ("Economic Growth", 944, 980),
}

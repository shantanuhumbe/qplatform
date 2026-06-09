# Goal: CFA Quiz Platform (QPlatform) Implementation Plan

Create a fully offline-parsed, LLM-graded CFA practice platform in the `qplatform` directory. The application will process the 980-page `CFA Combined QB (1).pdf`, extract Vignettes and associated multiple-choice questions into a structured JSON database, and serve them via a premium, dark-themed, split-screen Streamlit application with real-time LLM-assisted grading.

---

## User Review Required

> [!IMPORTANT]
> - **Gemini API Key**: The parsing pipeline and runtime grader require a `GEMINI_API_KEY`. You will need to provide this key by setting it as an environment variable or entering it in the Streamlit UI sidebar.
> - **Incremental Sliced Parsing**: Because a single LLM call cannot output the structured JSON for all 980 pages without exceeding the output token limits, the script will parse the PDF in increments/slices matching the 30 Learning Modules.

---

## Open Questions

> [!NOTE]
> - **Model Choice**: Should we use `gemini-2.5-flash` for the parser to optimize speed and cost, or `gemini-2.5-pro` to ensure the highest accuracy for the mathematical formulas and vignette context extraction?
> - **Grading Interaction**: For the LLM grader, do we want to show a detailed feedback report (e.g., showing exact logical gaps in the user's reasoning compared to the official explanation) or just a quick "Correct/Incorrect" explanation?
> - **Session & Score Persistence**: Streamlit resets all state on page refresh. Should we save user progress (e.g., attempted questions, scores, and historical responses) to a lightweight local `user_progress.json` file so study sessions can be resumed across refreshes/restarts?
> - **Topical Filtering**: Since the question bank covers 30 diverse learning modules, should we add a dropdown in the Streamlit sidebar to filter quiz sets by specific topics (e.g. "Ethics", "Fixed Income", "Derivatives") rather than always drawing at random?
> - **Error Category Diagnostics**: Should the LLM grader categorize user errors (e.g., "Calculation Error" vs "Conceptual Gap" vs "Wrong Formula") so we can render a visual breakdown chart of their weak areas in the sidebar?
> - **Boundary Vignette Handling**: When parsing pages in chunks (e.g., 15 pages), a vignette might start at the end of page 15 and continue onto page 16. To prevent cut-off vignettes, should we implement an overlapping chunk strategy (e.g., overlapping chunks by 3-5 pages) and filter duplicates during database merging?

---

## Proposed Changes

We will organize the code into a modular package structure under the `qplatform` directory:

```
qplatform/
├── requirements.txt
├── implementation_plan.md
├── run.py                 # Main entry point to run Streamlit or parser commands
├── questions_bank.json    # Consolidated parsed question database
├── user_progress.json     # Saved progress, scores, and historical responses
└── app/
    ├── __init__.py
    ├── config.py          # App constants, module configurations, and page mapping
    ├── models.py          # Pydantic schemas (Vignette, Question, GraderFeedback)
    ├── parser.py          # PDF reading and Gemini API parsing logic
    ├── grader.py          # Dynamic LLM Grading engine
    ├── ui/
    │   ├── __init__.py
    │   ├── components.py  # Render sidebar, split layouts, questions list
    │   └── styles.py      # Premium dark-mode/glassmorphism CSS injections
    └── utils/
        ├── __init__.py
        └── data_manager.py# Handles load/save/merge logic for questions and progress
```

---

### File Specifications

#### [MODIFY] [requirements.txt](file:///Users/shantanuhumbe/gemini/qplatform/requirements.txt)
Includes necessary dependencies:
```
streamlit
pypdf
google-genai
pydantic
pandas
plotly
```

#### [NEW] [run.py](file:///Users/shantanuhumbe/gemini/qplatform/run.py)
A command-line dispatcher that routes execution:
- To parse using the generic parser: 
  - `python3 run.py parse --pdf path/to/book.pdf --chunk-size 15` (scans pages in batches of 15)
  - `python3 run.py parse --pdf path/to/book.pdf --pages 1-20` (scans specific pages)
  - `python3 run.py parse --module 1` (scans pre-mapped CFA Module 1)
- To run UI: `python3 run.py web` (starts the Streamlit application)

#### [NEW] [app/config.py](file:///Users/shantanuhumbe/gemini/qplatform/app/config.py)
Holds configurable settings for the parsing pipeline and runtime grader. It allows users to run the quiz app on other document structures without rewriting code:
```python
import os

# API Configuration
DEFAULT_PARSE_MODEL = "gemini-2.5-flash"
DEFAULT_GRADE_MODEL = "gemini-2.5-flash"

# Parsing Parameters
DEFAULT_CHUNK_SIZE = 15  # Parse N pages at a time to stay within output token limits

# Default Prompt Templates
PARSER_SYSTEM_INSTRUCTION = (
    "You are an expert curriculum content parser. Extract all vignettes (case studies/scenarios) "
    "and their associated multiple-choice questions from the provided text.\n"
    "Identify where a case study or vignette starts and capture all background information. "
    "Link all subsequent multiple-choice questions to that case study.\n"
    "Ensure each question contains the question text, options (typically A, B, C), the correct letter answer, "
    "and the official explanation or answer rationale.\n"
    "CRITICAL REQUIREMENT: Do NOT extract or return any vignette or question that is cut off or incomplete "
    "at the beginning or end of the page range. Only extract complete, fully self-contained vignettes and "
    "their corresponding questions. If a vignette is cut off, discard it entirely.\n"
    "Generate a structured JSON response matching the provided schema."
)
```

#### [NEW] [app/models.py](file:///Users/shantanuhumbe/gemini/qplatform/app/models.py)
Defines the generic Pydantic models for data validation and schema enforcement:
```python
from pydantic import BaseModel
from typing import Optional

class Question(BaseModel):
    question_text: str
    options: list[str]
    correct_answer: str
    official_explanation: str

class Vignette(BaseModel):
    module: str
    topic: str
    case_study_text: str
    questions: list[Question]

class GraderFeedback(BaseModel):
    is_correct: bool
    conceptual_score: int  # scale 1-10
    feedback_text: str
    error_category: str  # e.g., "None", "Calculation Error", "Conceptual Gap", "Formula Misuse", "Reading Misinterpretation"
    calculation_error_identified: bool
```

#### [NEW] [app/parser.py](file:///Users/shantanuhumbe/gemini/qplatform/app/parser.py)
A generic PDF reader and parser that:
1. Dynamically slices any PDF into chunks of a given page size (e.g., 15 pages) with a configurable overlap (default 3 pages) to prevent missing vignettes at boundaries.
2. Extracts page text using `pypdf`.
3. Calls the Gemini API with structured output mapping to extract complete case studies and questions, automatically discarding half-cut items as instructed.
4. Returns validated Pydantic objects.

#### [NEW] [app/grader.py](file:///Users/shantanuhumbe/gemini/qplatform/app/grader.py)
Handles dynamic LLM call to grade a student's answer, parsing the response against `GraderFeedback` schema.

#### [NEW] [app/ui/styles.py](file:///Users/shantanuhumbe/gemini/qplatform/app/ui/styles.py)
Contains Tailwind/custom Vanilla CSS code string templates injected into Streamlit pages using `st.markdown(css, unsafe_allow_html=True)` to create a dark-mode theme, glassmorphic cards, custom borders, and animated buttons.

#### [NEW] [app/ui/components.py](file:///Users/shantanuhumbe/gemini/qplatform/app/ui/components.py)
Renders frontend layouts:
- `render_sidebar()`: statistics, progress tracker, API key inputs.
- `render_split_screen(vignette, answered_state)`: 
  - **Left Column (Context Panel)**: Displays the scrollable case study/vignette text (with markdown tables and LaTeX math formulas rendered). This remains static and visible at all times as the student reviews the scenario.
  - **Right Column (Question Panel)**: 
    - Renders **one active question at a time** from the vignette list, preventing visual clutter.
    - Shows options as radio buttons, an optional reasoning text box for dynamic grading, and a Submit button.
    - Displays a question navigation bar: `[Previous Question]` and `[Next Question]` buttons, along with a visual progress bar (e.g. circles representing question states: Green = Correct, Red = Incorrect, Gray = Unanswered).
    - Renders a "Move to Next Vignette" button once all questions in the current vignette are completed.

#### [NEW] [app/utils/data_manager.py](file:///Users/shantanuhumbe/gemini/qplatform/app/utils/data_manager.py)
Core manager for `questions_bank.json` file operations: load, merge new items without duplicates, and dump back.

---

## Data Extraction & Rendering Strategy (Tables, Math, Graphs)

To handle complex layout elements common in financial exam materials:

1. **Tables & Financial Exhibits**:
   - Raw PDF text converters extract tables as unstructured text lines, losing alignment. The Gemini parser is instructed to locate these text blocks and reconstruct them into clean **Markdown tables** (e.g. `| Col 1 | Col 2 |`) within the `case_study_text` field.
   - Streamlit renders these tables natively and beautifully using `st.markdown()`.

2. **Mathematical Equations**:
   - The parser instructs the LLM to convert formulas (e.g. discount rates, option equations) into standard **LaTeX expressions** (wrapped in `$` for inline math, and `$$` for block math).
   - Streamlit natively processes LaTeX inside markdown, rendering sharp mathematical symbols.

3. **Graphs & Chart Exhibits**:
   - Most "Exhibits" in CFA materials are actually tabular data. 
   - For visual charts (e.g., a plotted yield curve), the system instructions prompt the LLM to represent the data as a Markdown table of values or write a detailed text description (e.g., "The chart exhibits a normal upward-sloping yield curve starting at 2.5% for 1-year and flattening at 5.0% for 10-year...") so that the student has full context to answer the questions.

---

## Verification Plan

### Automated Verification
- Write a quick unit/integration test to verify that parsing successfully validates output against the Pydantic schemas.
- Run a linting check on Python files.

### Manual Verification
1. Run a test parse on page 1-16 (Module 1: Equity Valuation):
   ```bash
   python3 run.py parse --module 1
   ```
2. Start the Streamlit application:
   ```bash
   python3 run.py web
   ```
3. Open `http://localhost:8501` in the browser, verify layout, select an option, input an explanation, and click "Submit" to confirm the LLM grader provides feedback.

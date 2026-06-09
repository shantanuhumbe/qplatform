from pydantic import BaseModel
from typing import List

class Question(BaseModel):
    question_text: str
    options: List[str]
    correct_answer: str  # Must be 'A', 'B', or 'C'
    official_explanation: str

class Vignette(BaseModel):
    module: str
    topic: str
    case_study_text: str
    questions: List[Question]

class VignetteList(BaseModel):
    vignettes: List[Vignette]

class GraderFeedback(BaseModel):
    is_correct: bool
    conceptual_score: int  # 1 to 10
    feedback_text: str
    error_category: str  # "None", "Calculation Error", "Conceptual Gap", "Formula Misuse", "Reading Misinterpretation", etc.
    calculation_error_identified: bool

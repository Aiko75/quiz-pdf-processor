from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class LineData:
    text: str
    is_bold: bool
    color_int: int
    page_number: int
    x0: float
    y0: float


@dataclass
class OptionData:
    label: str
    text: str
    emphasized: bool = False
    is_bold: bool = False
    color_int: int = 0
    page_number: int = -1
    x0: float = 0.0
    y0: float = 0.0


@dataclass
class QuestionData:
    question: str = ""
    options: List[OptionData] = field(default_factory=list)
    answer_label: Optional[str] = None
    page_number: int = -1
    x0: float = 0.0
    y0: float = 0.0


@dataclass
class ValidationResult:
    pdf_name: str
    original_questions: int
    recognized_answers: int
    answer_doc_questions: int
    practice_doc_questions: int
    mismatch_count: int
    no_highlight_count: int
    multi_highlight_count: int
    practice_highlight_count: int


@dataclass
class QuizOptionState:
    label: str
    text: str
    highlighted: bool = False
    is_bold: bool = False
    color_rgb: Optional[Tuple[int, int, int]] = None
    bg_highlight: Optional[Any] = None


@dataclass
class QuizQuestionState:
    question: str
    options: Dict[str, QuizOptionState] = field(default_factory=dict)
    highlighted_labels: List[str] = field(default_factory=list)


@dataclass
class GradingResult:
    answer_file: str
    submission_file: str
    compared_questions: int
    correct_count: int
    wrong_count: int
    unanswered_count: int
    answered_count: int
    skipped_count: int
    wrong_output_file: str
    correct_items: List[Dict[str, object]] = field(default_factory=list)
    correct_questions: List[int] = field(default_factory=list)
    wrong_questions: List[int] = field(default_factory=list)
    unanswered_questions: List[int] = field(default_factory=list)
    skipped_questions: List[int] = field(default_factory=list)
    auto_swapped_files: bool = False
    wrong_items: List[Dict[str, object]] = field(default_factory=list)
    unanswered_items: List[Dict[str, object]] = field(default_factory=list)


@dataclass
class QuizGenerateResult:
    source_file: str
    requested_count: int
    generated_count: int
    quiz_output_file: str

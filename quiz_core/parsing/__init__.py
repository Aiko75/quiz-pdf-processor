from pathlib import Path
from typing import List, Dict, Any
from .pdf_parser import (
    extract_styled_lines, process_pdf_file, process_folder, 
    parse_pdf_questions_for_grading
)
from .docx_parser import (
    write_output_files, parse_docx_questions, parse_docx_questions_for_grading
)
from .core import parse_questions, finalize_answer
from .utils import (
    normalize_question_text, normalize_question_key, pick_single_label,
    _normalize_text, clean_text_noise, repair_fragmented_text, is_lms_noise_line,
    order_options
)
from ..models import QuizQuestionState

def parse_questions_for_grading(source_file: Path) -> List[QuizQuestionState]:
    suffix = source_file.suffix.lower()
    if suffix == ".pdf":
        return parse_pdf_questions_for_grading(source_file)
    elif suffix == ".docx":
        return parse_docx_questions_for_grading(source_file)
    else:
        return []

__all__ = [
    "extract_styled_lines",
    "process_pdf_file",
    "process_folder",
    "write_output_files",
    "parse_docx_questions",
    "parse_questions",
    "finalize_answer",
    "normalize_question_text",
    "normalize_question_key",
    "pick_single_label",
    "parse_questions_for_grading",
    "parse_pdf_questions_for_grading",
    "parse_docx_questions_for_grading",
    "_normalize_text",
    "clean_text_noise",
    "repair_fragmented_text",
    "is_lms_noise_line",
    "order_options"
]

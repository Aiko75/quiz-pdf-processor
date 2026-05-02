import re
from typing import List, Tuple, Optional, Dict
from ..parsing import normalize_question_key

QUESTION_NUMBER_PATTERN = re.compile(
    r"^\s*(?:Câu|Question)\s*(\d+)\s*[\.:\)]?",
    re.IGNORECASE,
)
PLAIN_NUMBER_PATTERN = re.compile(r"^\s*(\d+)\s*[\.)]")

def _extract_question_number(question_text: str) -> Optional[int]:
    question_text = question_text.strip()
    match = QUESTION_NUMBER_PATTERN.match(question_text)
    if match:
        return int(match.group(1))

    match = PLAIN_NUMBER_PATTERN.match(question_text)
    if match:
        return int(match.group(1))

    return None

def _build_pairs_by_question_text(
    submission_questions,
    answer_questions,
) -> List[Tuple[int, int]]:
    compared_pairs: List[Tuple[int, int]] = []
    answer_indices_by_key: Dict[str, List[int]] = {}

    for answer_index, question in enumerate(answer_questions):
        key = normalize_question_key(question.question)
        answer_indices_by_key.setdefault(key, []).append(answer_index)

    for submission_index, question in enumerate(submission_questions):
        key = normalize_question_key(question.question)
        candidates = answer_indices_by_key.get(key)
        if not candidates:
            continue
        answer_index = candidates.pop(0)
        compared_pairs.append((submission_index, answer_index))

    return compared_pairs

def _build_pairs_by_question_number(
    submission_questions,
    answer_questions,
) -> List[Tuple[int, int]]:
    compared_pairs: List[Tuple[int, int]] = []
    answer_indices_by_number: Dict[int, List[int]] = {}

    for answer_index, question in enumerate(answer_questions):
        number = _extract_question_number(question.question)
        if number is None:
            continue
        answer_indices_by_number.setdefault(number, []).append(answer_index)

    for submission_index, question in enumerate(submission_questions):
        number = _extract_question_number(question.question)
        if number is None:
            continue
        candidates = answer_indices_by_number.get(number)
        if not candidates:
            continue
        answer_index = candidates.pop(0)
        compared_pairs.append((submission_index, answer_index))

    return compared_pairs

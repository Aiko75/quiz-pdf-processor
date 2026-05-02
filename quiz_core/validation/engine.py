from typing import List, Dict, Tuple, Optional
import difflib
from ..models import ValidationIssue, ValidationResult
from ..parsing import normalize_question_key, normalize_question_text

def _highlighted_labels(question_data: Dict[str, object]) -> List[str]:
    options = question_data.get('options', {})
    if isinstance(options, dict):
        return [label for label, data in options.items() if isinstance(data, dict) and data.get('highlighted')]
    return []

def _find_best_match(original_key: str, docx_keys: List[str]) -> Tuple[Optional[str], float]:
    if not docx_keys:
        return None, 0.0
    matches = difflib.get_close_matches(original_key, docx_keys, n=1, cutoff=0.6)
    if matches:
        match = matches[0]
        score = difflib.SequenceMatcher(None, original_key, match).ratio()
        return match, score
    return None, 0.0

def validate_output_for_pdf(original_questions, docx_questions) -> List[ValidationIssue]:
    issues = []
    docx_by_key = {normalize_question_key(q['question']): q for q in docx_questions}
    docx_keys = list(docx_by_key.keys())

    for idx, orig_q in enumerate(original_questions, start=1):
        orig_text = orig_q.question
        orig_key = normalize_question_key(orig_text)
        
        match_key, score = _find_best_match(orig_key, docx_keys)
        
        if not match_key or score < 0.8:
            issues.append(ValidationIssue(
                question_number=idx,
                issue_type="missing",
                description=f"Không tìm thấy câu hỏi trong DOCX. (Độ khớp tối đa: {score:.2f})",
                original_text=orig_text
            ))
            continue

        matched_q = docx_by_key[match_key]
        docx_keys.remove(match_key)
        
        highlighted = _highlighted_labels(matched_q)
        if not highlighted:
            issues.append(ValidationIssue(
                question_number=idx,
                issue_type="no_highlight",
                description="Câu hỏi không có đáp án nào được highlight.",
                original_text=orig_text
            ))
        elif len(highlighted) > 1:
            issues.append(ValidationIssue(
                question_number=idx,
                issue_type="multi_highlight",
                description=f"Câu hỏi có nhiều đáp án được highlight: {', '.join(highlighted)}",
                original_text=orig_text
            ))

    for remaining_key in docx_keys:
        issues.append(ValidationIssue(
            question_number=0,
            issue_type="extra",
            description="Câu hỏi dư thừa trong DOCX không có trong PDF gốc.",
            original_text=docx_by_key[remaining_key]['question']
        ))

    return issues

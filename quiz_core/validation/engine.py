import re
import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any
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

def double_check_quiz_structure(questions) -> List[Dict[str, Any]]:
    errors = []
    
    # Matches uppercase A-E, followed by a dot, closing parenthesis, dash/hyphen, or slash, and then whitespace.
    stuck_pattern = re.compile(r'\b([A-E])[\.\):\-\/]\s+')
    
    for idx, q in enumerate(questions, start=1):
        q_errors = []
        
        # 1. Check options count: 3 to 5
        opt_count = len(q.options)
        if opt_count < 3 or opt_count > 5:
            q_errors.append({
                "type": "option_count",
                "message": f"Số lượng đáp án không hợp lệ: {opt_count} (Yêu cầu từ 3 đến 5 đáp án)"
            })
            
        # 1.1 Check for empty options
        if hasattr(q.options, 'items'):
            for label, opt in q.options.items():
                if not opt.text.strip():
                    q_errors.append({
                        "type": "empty_option",
                        "message": f"Đáp án {label} trống (không có nội dung)"
                    })
        elif isinstance(q.options, list):
            for opt in q.options:
                if not opt.text.strip():
                    q_errors.append({
                        "type": "empty_option",
                        "message": f"Đáp án {opt.label} trống (không có nội dung)"
                    })
            
        # 2. Check stuck options in question body
        q_text = q.question
        
        # Clean question number prefix to avoid matching the question number itself if it has A/B/C/D
        # e.g. "Câu 1: ..."
        clean_q = normalize_question_text(q_text)
        
        # Find all option-like markers in the question text
        matches = stuck_pattern.findall(clean_q)
        unique_matches = sorted(list(set(matches)))
        
        # Filter matches based on our logic:
        # A match label is considered a stuck option if:
        # - It is NOT in the parsed options (q.options)
        # OR
        # - There are at least 2 distinct option labels found in the question body
        stuck_labels = []
        
        for label in unique_matches:
            # Check if not in q.options
            not_parsed = True
            if hasattr(q.options, 'keys'):
                if label in q.options:
                    not_parsed = False
            elif isinstance(q.options, list):
                if any(opt.label == label for opt in q.options):
                    not_parsed = False
            
            if not_parsed or len(unique_matches) >= 2:
                stuck_labels.append(label)
                
        if stuck_labels:
            labels_str = ", ".join(f"'{l}'" for l in sorted(stuck_labels))
            q_errors.append({
                "type": "stuck_options",
                "message": f"Phát hiện đáp án bị dính trong câu hỏi: nhãn {labels_str}"
            })
            
        if q_errors:
            # Gather parsed options
            options_dict = {}
            if hasattr(q.options, 'items'):
                options_dict = {label: opt.text for label, opt in q.options.items()}
            elif isinstance(q.options, list):
                options_dict = {opt.label: opt.text for opt in q.options}
                
            errors.append({
                "question_index": idx,
                "logical_index": q.logical_index,
                "question_text": q_text,
                "options": options_dict,
                "errors": q_errors
            })
            
    return errors

def _is_duplicate_feedback(existing_list: List[Dict[str, Any]], new_fb: Dict[str, Any]) -> bool:
    for fb in existing_list:
        if (fb.get("question_index") == new_fb.get("question_index") and
            fb.get("message") == new_fb.get("message")):
            return True
    return False

def save_auto_feedback_to_loop(workspace: str, errors: List[Dict[str, Any]], file_path: str) -> None:
    if not workspace:
        return
    workspace_path = Path(workspace).resolve()
    feedback_file = workspace_path / "feedback_loop.json"
    
    file_name = Path(file_path).name
    
    data = {}
    if feedback_file.exists():
        try:
            with open(feedback_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            pass
            
    # Filter out existing auto feedbacks for this file, keeping manual feedbacks
    file_feedbacks = data.get(file_name, [])
    manual_feedbacks = [f for f in file_feedbacks if f.get("source") == "manual"]
    
    # Convert new errors to auto feedbacks
    new_auto_feedbacks = []
    for err in errors:
        for q_err in err["errors"]:
            fb = {
                "question_index": err["question_index"],
                "type": q_err["type"],
                "message": q_err["message"],
                "source": "auto"
            }
            # Avoid duplicate with manual feedbacks or already added auto feedbacks
            if not _is_duplicate_feedback(manual_feedbacks, fb) and not _is_duplicate_feedback(new_auto_feedbacks, fb):
                new_auto_feedbacks.append(fb)
                
    # Combine and save
    data[file_name] = manual_feedbacks + new_auto_feedbacks
    
    workspace_path.mkdir(parents=True, exist_ok=True)
    with open(feedback_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def add_manual_feedback(workspace: str, file_path: str, question_index: int, message: str) -> None:
    if not workspace:
        return
    workspace_path = Path(workspace).resolve()
    feedback_file = workspace_path / "feedback_loop.json"
    
    file_name = Path(file_path).name
    
    data = {}
    if feedback_file.exists():
        try:
            with open(feedback_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            pass
            
    file_feedbacks = data.get(file_name, [])
    
    new_fb = {
        "question_index": question_index,
        "type": "manual",
        "message": message,
        "source": "manual"
    }
    
    # Check duplicate before appending
    if not _is_duplicate_feedback(file_feedbacks, new_fb):
        file_feedbacks.append(new_fb)
    
    data[file_name] = file_feedbacks
    
    workspace_path.mkdir(parents=True, exist_ok=True)
    with open(feedback_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)



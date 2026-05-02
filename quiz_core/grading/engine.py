from pathlib import Path
from typing import List, Dict, Any, Tuple
from ..parsing import (
    parse_questions_for_grading,
    normalize_question_text,
    pick_single_label
)
from ..models import GradingResult
from .matching import (
    _build_pairs_by_question_text,
    _build_pairs_by_question_number,
    _extract_question_number
)
from .exporter import build_wrong_questions_docx

def _display_question_number(question, fallback_index: int) -> int:
    extracted = _extract_question_number(question.question)
    if extracted is not None:
        return extracted
    return fallback_index + 1

def grade_quiz_files(
    submission_file: Path,
    answer_file: Path,
    output_dir: Path,
) -> GradingResult:
    if not submission_file.exists():
        raise FileNotFoundError(f"Không tìm thấy file bài làm: {submission_file}")
    if not answer_file.exists():
        raise FileNotFoundError(f"Không tìm thấy file đáp án: {answer_file}")

    student_questions = parse_questions_for_grading(submission_file)
    answer_questions = parse_questions_for_grading(answer_file)

    if not student_questions:
        raise ValueError(f"Không nhận diện được câu hỏi nào trong file bài làm: {submission_file}")
    if not answer_questions:
        raise ValueError(f"Không nhận diện được câu hỏi nào trong file đáp án: {answer_file}")

    text_pairs = _build_pairs_by_question_text(student_questions, answer_questions)
    number_pairs = _build_pairs_by_question_number(student_questions, answer_questions)

    pairing_strategy = "question_text"
    compared_pairs = text_pairs

    if len(number_pairs) > len(text_pairs):
        pairing_strategy = "question_number"
        compared_pairs = number_pairs
    
    if not compared_pairs:
        pairing_strategy = "index"
        min_len = min(len(student_questions), len(answer_questions))
        compared_pairs = [(i, i) for i in range(min_len)]

    correct_count = 0
    wrong_count = 0
    unanswered_count = 0
    skipped_count = 0
    compared_questions = 0

    correct_questions = []
    wrong_questions = []
    unanswered_questions = []
    skipped_questions = []
    skipped_details = []

    correct_items = []
    wrong_items = []
    unanswered_items = []

    seen_answer_indices = set()

    for submission_index, answer_index in compared_pairs:
        student_question = student_questions[submission_index]
        answer_key = answer_questions[answer_index]
        seen_answer_indices.add(answer_index)
        compared_questions += 1

        question_number = _display_question_number(student_question, submission_index)
        correct_label = pick_single_label(answer_key.highlighted_labels)
        
        selected_labels = student_question.highlighted_labels
        selected_label = selected_labels[0] if selected_labels else None

        if not selected_label:
            unanswered_count += 1
            unanswered_questions.append(question_number)
        elif correct_label and selected_label == correct_label:
            correct_count += 1
            correct_questions.append(question_number)
        else:
            wrong_count += 1
            wrong_questions.append(question_number)

        merged_options = []
        for label in ["A", "B", "C", "D"]:
            opt = student_question.options.get(label)
            if not opt: continue
            merged_options.append({
                "label": label,
                "text": opt.text,
                "is_correct": label == correct_label,
                "is_selected": label == selected_label
            })

        item_data = {
            "index": question_number,
            "question_text": normalize_question_text(student_question.question),
            "selected_labels": selected_labels,
            "correct_label": correct_label,
            "option_states": merged_options,
        }

        if not selected_label:
            unanswered_items.append(item_data)
        elif correct_label and selected_label == correct_label:
            correct_items.append(item_data)
        else:
            wrong_items.append(item_data)

    output_dir.mkdir(parents=True, exist_ok=True)
    wrong_output_file = output_dir / f"{submission_file.stem}_cac_cau_loi.docx"
    build_wrong_questions_docx(correct_items, unanswered_items, wrong_items, wrong_output_file)

    return GradingResult(
        answer_file=answer_file.name,
        submission_file=submission_file.name,
        compared_questions=compared_questions,
        correct_count=correct_count,
        wrong_count=wrong_count,
        unanswered_count=unanswered_count,
        answered_count=correct_count + wrong_count,
        skipped_count=skipped_count,
        wrong_output_file=str(wrong_output_file),
        correct_items=correct_items,
        correct_questions=correct_questions,
        wrong_questions=wrong_questions,
        unanswered_questions=unanswered_questions,
        skipped_questions=skipped_questions,
        auto_swapped_files=False,
        wrong_items=wrong_items,
        unanswered_items=unanswered_items,
        skipped_details=skipped_details,
        pairing_strategy=pairing_strategy,
        matched_by_text_count=len(text_pairs),
        matched_by_number_count=len(number_pairs),
    )

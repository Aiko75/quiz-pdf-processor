import importlib
import random
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .models import GradingResult, QuizGenerateResult, QuizOptionState
from .parsing import (
    normalize_question_key,
    normalize_question_text,
    parse_questions_for_grading,
    pick_single_label,
)


def _count_single_highlighted(questions) -> int:
    return sum(1 for question in questions if pick_single_label(question.highlighted_labels) is not None)


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


def _display_question_number(question, fallback_index: int) -> int:
    extracted = _extract_question_number(question.question)
    if extracted is not None:
        return extracted
    return fallback_index + 1


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


def _write_error_section(
    document,
    section_title: str,
    items: List[Dict[str, object]],
) -> None:
    RGBColor = importlib.import_module("docx.shared").RGBColor
    option_labels = ["A", "B", "C", "D"]

    document.add_paragraph(section_title)

    if not items:
        document.add_paragraph("Không có câu nào.")
        document.add_paragraph("")
        return

    for item in items:
        index = item["index"]
        question_text = item["question_text"]
        selected_labels = item["selected_labels"]
        correct_label = item["correct_label"]
        option_states = item["option_states"]

        document.add_paragraph(f"Câu {index}: {question_text}")

        for label in option_labels:
            if label not in option_states:
                continue
            state: QuizOptionState = option_states[label]
            paragraph = document.add_paragraph()
            run = paragraph.add_run(f"{label}. {state.text}")

            if label in selected_labels and state.is_bold:
                run.bold = True
            if label in selected_labels and state.color_rgb is not None:
                red, green, blue = state.color_rgb
                run.font.color.rgb = RGBColor(red, green, blue)
            if label in selected_labels and state.bg_highlight is not None:
                run.font.highlight_color = state.bg_highlight

            if label == correct_label:
                run.bold = True
                run.font.color.rgb = RGBColor(255, 0, 0)

        document.add_paragraph("")


def build_wrong_questions_docx(
    correct_items: List[Dict[str, object]],
    unanswered_items: List[Dict[str, object]],
    wrong_items: List[Dict[str, object]],
    output_file: Path,
) -> None:
    docx_module = importlib.import_module("docx")
    docx_shared_module = importlib.import_module("docx.shared")
    Document = docx_module.Document
    Pt = docx_shared_module.Pt

    document = Document()
    style = document.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(12)

    document.add_paragraph("BÁO CÁO KẾT QUẢ CHẤM")
    document.add_paragraph(f"Số câu đúng: {len(correct_items)}")
    document.add_paragraph(f"Số câu sai: {len(wrong_items)}")
    document.add_paragraph(f"Số câu chưa làm: {len(unanswered_items)}")
    document.add_paragraph("")

    _write_error_section(document, "PHẦN 1 - CÁC CÂU LÀM ĐÚNG", correct_items)
    _write_error_section(document, "PHẦN 2 - CÁC CÂU LÀM SAI", wrong_items)
    _write_error_section(document, "PHẦN 3 - CÁC CÂU CHƯA LÀM", unanswered_items)

    document.save(output_file)


def grade_quiz_files(
    submission_file: Path,
    answer_file: Path,
    output_dir: Path,
) -> GradingResult:
    if not submission_file.exists():
        raise FileNotFoundError(f"Không tìm thấy file bài làm: {submission_file}")
    if not answer_file.exists():
        raise FileNotFoundError(f"Không tìm thấy file đáp án: {answer_file}")

    submission_questions = parse_questions_for_grading(submission_file)
    answer_questions = parse_questions_for_grading(answer_file)

    compared_questions = min(len(submission_questions), len(answer_questions))
    auto_swapped_files = False

    if compared_questions > 0:
        answer_single_count = _count_single_highlighted(answer_questions)
        submission_single_count = _count_single_highlighted(submission_questions)
        if answer_single_count == 0 and submission_single_count >= max(3, int(compared_questions * 0.6)):
            answer_questions, submission_questions = submission_questions, answer_questions
            answer_file, submission_file = submission_file, answer_file
            auto_swapped_files = True

    text_pairs = _build_pairs_by_question_text(submission_questions, answer_questions)
    number_pairs = _build_pairs_by_question_number(submission_questions, answer_questions)

    pairing_strategy = "question_text"
    compared_pairs = text_pairs
    if len(number_pairs) > len(compared_pairs):
        compared_pairs = number_pairs
        pairing_strategy = "question_number"

    max_comparable = min(len(submission_questions), len(answer_questions))
    minimum_matches = max(1, int(max_comparable * 0.5)) if max_comparable > 0 else 0
    if len(compared_pairs) < minimum_matches:
        compared_pairs = [(index, index) for index in range(max_comparable)]
        pairing_strategy = "index"

    compared_questions = len(compared_pairs)

    correct_count = 0
    wrong_count = 0
    unanswered_count = 0
    skipped_count = 0
    correct_questions: List[int] = []
    wrong_questions: List[int] = []
    unanswered_questions: List[int] = []
    skipped_questions: List[int] = []
    skipped_details: List[str] = []
    correct_items: List[Dict[str, object]] = []
    unanswered_items: List[Dict[str, object]] = []
    wrong_items: List[Dict[str, object]] = []

    for submission_index, answer_index in compared_pairs:
        student_question = submission_questions[submission_index]
        answer_question = answer_questions[answer_index]
        question_number = _display_question_number(student_question, submission_index)

        correct_label = pick_single_label(answer_question.highlighted_labels)
        selected_labels = list(student_question.highlighted_labels)
        selected_label = pick_single_label(selected_labels)

        if correct_label is None:
            skipped_count += 1
            skipped_questions.append(question_number)
            highlighted_labels = sorted(
                {
                    label.upper()
                    for label in answer_question.highlighted_labels
                    if isinstance(label, str) and label.strip()
                }
            )
            if len(highlighted_labels) == 0:
                skip_reason = (
                    "Không nhận diện được đáp án đúng trong file đáp án "
                    "(0 lựa chọn được nhấn mạnh)."
                )
            else:
                skip_reason = (
                    "File đáp án có nhiều lựa chọn được nhấn mạnh: "
                    f"{', '.join(highlighted_labels)}."
                )
            skipped_details.append(f"Câu {question_number}: {skip_reason}")
            continue

        merged_options: Dict[str, QuizOptionState] = {}
        for label in ["A", "B", "C", "D"]:
            student_option = student_question.options.get(label)
            answer_option = answer_question.options.get(label)
            if student_option:
                merged_options[label] = student_option
            elif answer_option:
                merged_options[label] = QuizOptionState(
                    label=answer_option.label,
                    text=answer_option.text,
                    highlighted=False,
                    is_bold=False,
                    color_rgb=None,
                )

        if len(selected_labels) == 0:
            unanswered_count += 1
            unanswered_questions.append(question_number)
            unanswered_items.append(
                {
                    "index": question_number,
                    "question_text": normalize_question_text(student_question.question),
                    "selected_labels": [],
                    "correct_label": correct_label,
                    "option_states": merged_options,
                }
            )
            continue

        if selected_label == correct_label:
            correct_count += 1
            correct_questions.append(question_number)
            correct_items.append(
                {
                    "index": question_number,
                    "question_text": normalize_question_text(student_question.question),
                    "selected_labels": selected_labels,
                    "correct_label": correct_label,
                    "option_states": merged_options,
                }
            )
            continue

        wrong_count += 1
        wrong_questions.append(question_number)
        wrong_items.append(
            {
                "index": question_number,
                "question_text": normalize_question_text(student_question.question),
                "selected_labels": selected_labels,
                "correct_label": correct_label,
                "option_states": merged_options,
            }
        )

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
        auto_swapped_files=auto_swapped_files,
        wrong_items=wrong_items,
        unanswered_items=unanswered_items,
        skipped_details=skipped_details,
        pairing_strategy=pairing_strategy,
        matched_by_text_count=len(text_pairs),
        matched_by_number_count=len(number_pairs),
    )


def generate_quiz_from_file(
    source_file: Path,
    output_dir: Path,
    question_count: int,
) -> QuizGenerateResult:
    if not source_file.exists() or not source_file.is_file():
        raise FileNotFoundError(f"Không tìm thấy file nguồn để tạo đề: {source_file}")

    if question_count <= 0:
        raise ValueError("Số lượng câu phải lớn hơn 0")

    questions = parse_questions_for_grading(source_file)
    if not questions:
        raise ValueError("Không đọc được câu hỏi từ file nguồn")

    selected_count = min(question_count, len(questions))
    selected_questions = random.sample(questions, selected_count)

    docx_module = importlib.import_module("docx")
    docx_shared_module = importlib.import_module("docx.shared")
    Document = docx_module.Document
    Pt = docx_shared_module.Pt

    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{source_file.stem}_de_trac_nghiem_{selected_count}_cau.docx"

    document = Document()
    style = document.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(12)

    for index, question in enumerate(selected_questions, start=1):
        document.add_paragraph(f"Câu {index}: {normalize_question_text(question.question)}")
        for label in ["A", "B", "C", "D"]:
            option = question.options.get(label)
            if option is None:
                continue
            document.add_paragraph(f"{label}. {option.text}")
        document.add_paragraph("")

    document.save(output_file)

    return QuizGenerateResult(
        source_file=source_file.name,
        requested_count=question_count,
        generated_count=selected_count,
        quiz_output_file=str(output_file),
    )

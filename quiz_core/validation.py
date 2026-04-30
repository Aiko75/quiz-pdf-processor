import importlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .models import ValidationIssue, ValidationResult
from .parsing import (
    extract_styled_lines,
    normalize_question_key,
    normalize_question_text,
    parse_docx_questions,
    parse_questions,
)


def _highlighted_labels(question_data: Dict[str, object]) -> List[str]:
    labels: List[str] = []
    options = question_data.get("options", {})
    if not isinstance(options, dict):
        return labels

    for label, option in options.items():
        if not isinstance(option, dict):
            continue
        if option.get("highlighted"):
            labels.append(str(label).upper())

    return labels


def _question_text_is_mismatched(source_text: str, output_text: str) -> bool:
    return normalize_question_key(source_text) != normalize_question_key(output_text)


def _collect_validation_details(pdf_file: Path, output_dir: Path) -> Tuple[ValidationResult, List[ValidationIssue]]:
    base_name = pdf_file.stem
    answer_doc = output_dir / f"{base_name}_co_dap_an.docx"
    practice_doc = output_dir / f"{base_name}_de_lam.docx"

    if not answer_doc.exists() or not practice_doc.exists():
        raise FileNotFoundError(
            f"Thiếu file output cho {pdf_file.name}: {answer_doc.name} / {practice_doc.name}"
        )

    original_questions = parse_questions(extract_styled_lines(pdf_file))
    answer_doc_questions = parse_docx_questions(answer_doc)
    practice_doc_questions = parse_docx_questions(practice_doc)

    mismatch_count = 0
    no_highlight_count = 0
    multi_highlight_count = 0
    practice_highlight_count = 0
    correct_count = 0
    wrong_count = 0
    missed_count = 0
    title_issue_count = 0
    source_no_answer_count = 0

    for question_data in practice_doc_questions:
        highlighted_options = [
            label
            for label, option in question_data["options"].items()
            if option["highlighted"]
        ]
        if highlighted_options:
            practice_highlight_count += 1

    issues: List[ValidationIssue] = []

    for index in range(min(len(original_questions), len(answer_doc_questions))):
        source = original_questions[index]
        answer = answer_doc_questions[index]

        source_question_text = normalize_question_text(source.question)
        output_question_text = normalize_question_text(str(answer.get("question", "")))
        source_answer = source.answer_label or ""
        detected_answers = _highlighted_labels(answer)
        title_mismatch = _question_text_is_mismatched(source.question, str(answer.get("question", "")))

        if len(answer["options"]) != 4:
            mismatch_count += 1
            if source_answer:
                wrong_count += 1
            issues.append(
                ValidationIssue(
                    index=index + 1,
                    status="malformed_output",
                    reason="File đáp án không có đủ 4 lựa chọn.",
                    source_question=source_question_text,
                    output_question=output_question_text,
                    source_answer=source_answer,
                    detected_answers=detected_answers,
                )
            )
            continue

        if not source_answer:
            source_no_answer_count += 1
            if detected_answers:
                mismatch_count += 1
            issues.append(
                ValidationIssue(
                    index=index + 1,
                    status="source_no_answer",
                    reason="Nguồn không nhận diện được đáp án đúng để đối chiếu.",
                    source_question=source_question_text,
                    output_question=output_question_text,
                    source_answer="",
                    detected_answers=detected_answers,
                )
            )
            continue

        if len(detected_answers) == 0:
            mismatch_count += 1
            no_highlight_count += 1
            missed_count += 1
            if title_mismatch:
                title_issue_count += 1
            issues.append(
                ValidationIssue(
                    index=index + 1,
                    status="missed",
                    reason="Không có đáp án nào được nhấn mạnh trong file output.",
                    source_question=source_question_text,
                    output_question=output_question_text,
                    source_answer=source_answer,
                    detected_answers=[],
                )
            )
            continue

        if len(detected_answers) > 1:
            mismatch_count += 1
            multi_highlight_count += 1
            wrong_count += 1
            if title_mismatch:
                title_issue_count += 1
            issues.append(
                ValidationIssue(
                    index=index + 1,
                    status="multi",
                    reason="Có nhiều hơn một đáp án được nhấn mạnh trong file output.",
                    source_question=source_question_text,
                    output_question=output_question_text,
                    source_answer=source_answer,
                    detected_answers=detected_answers,
                )
            )
            continue

        detected_answer = detected_answers[0]
        if detected_answer != source_answer:
            mismatch_count += 1
            wrong_count += 1
            if title_mismatch:
                title_issue_count += 1
            issues.append(
                ValidationIssue(
                    index=index + 1,
                    status="wrong",
                    reason=f"Đáp án output là {detected_answer}, nhưng nguồn là {source_answer}.",
                    source_question=source_question_text,
                    output_question=output_question_text,
                    source_answer=source_answer,
                    detected_answers=detected_answers,
                )
            )
            continue

        if title_mismatch:
            mismatch_count += 1
            title_issue_count += 1
            wrong_count += 1
            issues.append(
                ValidationIssue(
                    index=index + 1,
                    status="title_issue",
                    reason="Tiêu đề câu hỏi ở output không khớp với câu hỏi nguồn.",
                    source_question=source_question_text,
                    output_question=output_question_text,
                    source_answer=source_answer,
                    detected_answers=detected_answers,
                )
            )
            continue

        correct_count += 1

    result = ValidationResult(
        pdf_name=pdf_file.name,
        original_questions=len(original_questions),
        recognized_answers=sum(1 for question in original_questions if question.answer_label),
        answer_doc_questions=len(answer_doc_questions),
        practice_doc_questions=len(practice_doc_questions),
        mismatch_count=mismatch_count,
        no_highlight_count=no_highlight_count,
        multi_highlight_count=multi_highlight_count,
        practice_highlight_count=practice_highlight_count,
        correct_count=correct_count,
        wrong_count=wrong_count,
        missed_count=missed_count,
        title_issue_count=title_issue_count,
        source_no_answer_count=source_no_answer_count,
    )
    return result, issues


def _issue_status_label(status: str) -> str:
    labels = {
        "wrong": "Sai đáp án",
        "missed": "Miss đáp án",
        "multi": "Nhiều đáp án được nhấn mạnh",
        "title_issue": "Sai tiêu đề câu hỏi",
        "source_no_answer": "Nguồn không có đáp án",
        "malformed_output": "Output thiếu lựa chọn",
    }
    return labels.get(status, status)


def build_validation_report_docx(
    validation_result: ValidationResult,
    issues: List[ValidationIssue],
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

    document.add_paragraph("BÁO CÁO KIỂM TRA SAU XỬ LÝ PDF")
    document.add_paragraph(f"File nguồn: {validation_result.pdf_name}")
    document.add_paragraph(f"Tổng số câu trong PDF: {validation_result.original_questions}")
    document.add_paragraph(f"Số câu có đáp án nhận diện được: {validation_result.recognized_answers}")
    document.add_paragraph(f"Số câu đúng: {validation_result.correct_count}")
    document.add_paragraph(f"Số câu sai đáp án: {validation_result.wrong_count}")
    document.add_paragraph(f"Số câu miss đáp án: {validation_result.missed_count}")
    document.add_paragraph(f"Số câu lỗi tiêu đề: {validation_result.title_issue_count}")
    document.add_paragraph(f"Số câu nguồn không có đáp án: {validation_result.source_no_answer_count}")
    document.add_paragraph(f"Số câu file đáp án có nhiều nhấn mạnh: {validation_result.multi_highlight_count}")
    document.add_paragraph(f"Số câu file làm thử còn nhấn mạnh: {validation_result.practice_highlight_count}")
    document.add_paragraph("")

    if not issues:
        document.add_paragraph("Không phát hiện lỗi trong file output.")
        document.save(output_file)
        return

    document.add_paragraph("CÁC CÂU CẦN XEM LẠI")

    for issue in issues:
        document.add_paragraph(
            f"Câu {issue.index} - {_issue_status_label(issue.status)}"
        )
        document.add_paragraph(f"Lý do: {issue.reason}")
        document.add_paragraph(f"Đáp án nguồn: {issue.source_answer or 'Không có'}")
        document.add_paragraph(
            f"Đáp án output: {', '.join(issue.detected_answers) if issue.detected_answers else 'Không có'}"
        )
        document.add_paragraph(f"Tiêu đề nguồn: {issue.source_question}")
        document.add_paragraph(f"Tiêu đề output: {issue.output_question}")
        document.add_paragraph("")

    document.save(output_file)


def validate_output_for_pdf(pdf_file: Path, output_dir: Path) -> ValidationResult:
    result, _ = _collect_validation_details(pdf_file, output_dir)
    return result


def generate_validation_report_for_pdf(pdf_file: Path, output_dir: Path) -> ValidationResult:
    result, issues = _collect_validation_details(pdf_file, output_dir)
    report_file = output_dir / f"{pdf_file.stem}_bao_cao_kiem_tra.docx"
    build_validation_report_docx(result, issues, report_file)
    result.report_file = str(report_file)
    return result


def validate_folder(input_dir: Path, output_dir: Path) -> List[ValidationResult]:
    pdf_files = sorted(input_dir.glob("*.pdf"))
    if not pdf_files:
        raise FileNotFoundError(f"Không tìm thấy file PDF trong: {input_dir}")

    results: List[ValidationResult] = []
    for pdf_file in pdf_files:
        results.append(generate_validation_report_for_pdf(pdf_file, output_dir))

    return results
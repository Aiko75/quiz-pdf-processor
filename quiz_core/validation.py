from pathlib import Path
from typing import List

from .models import ValidationResult
from .parsing import extract_styled_lines, parse_docx_questions, parse_questions


def validate_output_for_pdf(pdf_file: Path, output_dir: Path) -> ValidationResult:
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

    for question_data in practice_doc_questions:
        highlighted_options = [
            label
            for label, option in question_data["options"].items()
            if option["highlighted"]
        ]
        if highlighted_options:
            practice_highlight_count += 1

    for index in range(min(len(original_questions), len(answer_doc_questions))):
        source = original_questions[index]
        answer = answer_doc_questions[index]

        if len(answer["options"]) != 4:
            mismatch_count += 1
            continue

        highlighted_options = [
            label
            for label, option in answer["options"].items()
            if option["highlighted"]
        ]

        if source.answer_label:
            if len(highlighted_options) == 0:
                no_highlight_count += 1
            elif len(highlighted_options) > 1:
                multi_highlight_count += 1
            elif highlighted_options[0] != source.answer_label:
                mismatch_count += 1
        elif highlighted_options:
            mismatch_count += 1

    return ValidationResult(
        pdf_name=pdf_file.name,
        original_questions=len(original_questions),
        recognized_answers=sum(1 for question in original_questions if question.answer_label),
        answer_doc_questions=len(answer_doc_questions),
        practice_doc_questions=len(practice_doc_questions),
        mismatch_count=mismatch_count,
        no_highlight_count=no_highlight_count,
        multi_highlight_count=multi_highlight_count,
        practice_highlight_count=practice_highlight_count,
    )


def validate_folder(input_dir: Path, output_dir: Path) -> List[ValidationResult]:
    pdf_files = sorted(input_dir.glob("*.pdf"))
    if not pdf_files:
        raise FileNotFoundError(f"Không tìm thấy file PDF trong: {input_dir}")

    results: List[ValidationResult] = []
    for pdf_file in pdf_files:
        results.append(validate_output_for_pdf(pdf_file, output_dir))

    return results

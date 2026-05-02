import importlib
from pathlib import Path
from typing import List
from ..models import ValidationResult
from ..parsing import (
    extract_styled_lines,
    parse_questions,
    parse_docx_questions,
)
from .engine import validate_output_for_pdf

def generate_validation_report_for_pdf(pdf_file: Path, output_dir: Path) -> ValidationResult:
    docx_file = output_dir / f"{pdf_file.stem}_co_dap_an.docx"
    if not docx_file.exists():
        return ValidationResult(
            pdf_name=pdf_file.name,
            original_questions=0,
            recognized_answers=0,
            mismatch_count=0,
            no_highlight_count=0,
            multi_highlight_count=0,
            issues=[],
            report_file=""
        )

    lines = extract_styled_lines(pdf_file)
    original_questions = parse_questions(lines)
    docx_questions = parse_docx_questions(docx_file)

    issues = validate_output_for_pdf(original_questions, docx_questions)
    
    mismatch = sum(1 for i in issues if i.issue_type == "missing")
    no_high = sum(1 for i in issues if i.issue_type == "no_highlight")
    multi_high = sum(1 for i in issues if i.issue_type == "multi_highlight")

    report_file = output_dir / f"{pdf_file.stem}_bao_cao_kiem_tra.docx"
    
    docx_module = importlib.import_module("docx")
    docx_shared_module = importlib.import_module("docx.shared")
    Document = docx_module.Document
    Pt = docx_shared_module.Pt

    doc = Document()
    doc.add_heading(f"BÁO CÁO KIỂM TRA: {pdf_file.name}", 0)
    
    summary = doc.add_paragraph()
    summary.add_run(f"Tổng số câu trong PDF gốc: {len(original_questions)}\n").bold = True
    summary.add_run(f"Số câu nhận diện được trong DOCX: {len(docx_questions)}\n").bold = True
    summary.add_run(f"Số câu khớp hoàn toàn: {len(original_questions) - mismatch}\n")
    summary.add_run(f"Số câu thiếu: {mismatch}\n")
    summary.add_run(f"Số câu không có highlight: {no_high}\n")
    summary.add_run(f"Số câu có nhiều highlight: {multi_high}\n")

    if issues:
        doc.add_heading("DANH SÁCH CÁC VẤN ĐỀ", level=1)
        for issue in issues:
            p = doc.add_paragraph(style='List Bullet')
            p.add_run(f"[{issue.issue_type.upper()}] ").bold = True
            if issue.question_number > 0:
                p.add_run(f"Câu {issue.question_number}: ")
            p.add_run(issue.description)
            if issue.original_text:
                doc.add_paragraph(f"Nội dung: {issue.original_text[:200]}...", style='Caption')

    doc.save(report_file)

    return ValidationResult(
        pdf_name=pdf_file.name,
        original_questions=len(original_questions),
        recognized_answers=len(docx_questions),
        mismatch_count=mismatch,
        no_highlight_count=no_high,
        multi_highlight_count=multi_high,
        issues=issues,
        report_file=str(report_file),
        correct_count=len(original_questions) - mismatch - no_high - multi_high,
        wrong_count=mismatch + no_high + multi_high,
        missed_count=mismatch
    )

def validate_folder(input_dir: Path, output_dir: Path) -> List[ValidationResult]:
    pdf_files = sorted(input_dir.glob("*.pdf"))
    if not pdf_files:
        raise FileNotFoundError(f"Không tìm thấy file PDF trong: {input_dir}")

    results: List[ValidationResult] = []
    for pdf_file in pdf_files:
        results.append(generate_validation_report_for_pdf(pdf_file, output_dir))

    return results

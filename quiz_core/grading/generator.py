import random
import importlib
import shutil
import json
from pathlib import Path
from typing import List, Optional
from ..parsing import (
    normalize_question_text, 
    parse_questions_for_grading
)
from ..models import QuizGenerateResult
from .exporter import _export_to_interactive_json, _write_option_line

def _write_quiz_docx(questions, output_file: Path, with_answers: bool = False):
    docx_module = importlib.import_module("docx")
    docx_shared_module = importlib.import_module("docx.shared")
    Document = docx_module.Document
    Pt = docx_shared_module.Pt

    document = Document()
    style = document.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(12)

    for index, question in enumerate(questions, start=1):
        document.add_paragraph(f"Câu {index}: {normalize_question_text(question.question)}")
        
        # Determine correct label if we need to show answers
        correct_label = None
        if with_answers:
            if hasattr(question, 'highlighted_labels'):
                from ..parsing import pick_single_label
                correct_label = pick_single_label(question.highlighted_labels)
            elif hasattr(question, 'answer_label'):
                correct_label = question.answer_label

        for label in ["A", "B", "C", "D", "E"]:
            option = None
            if hasattr(question.options, 'get'):
                option = question.options.get(label)
            else:
                # Fallback if options is a list or other structure
                pass

            if option is None:
                continue
                
            p = document.add_paragraph()
            r = p.add_run(f"{label}. {option.text}")
            if with_answers and label == correct_label:
                r.bold = True
                r.font.highlight_color = docx_module.enum.text.WD_COLOR_INDEX.YELLOW
                
        document.add_paragraph("")

    document.save(output_file)

def generate_quiz_from_file(
    source_file: Path,
    output_dir: Path,
    question_count: int,
    interactive: bool = False,
    gen_answer: bool = False,
    time_limit: int = 0,
    workspace: str = None,
    sub_folder: str = ""
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

    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{source_file.stem}_random_{selected_count}_cau.docx"
    _write_quiz_docx(selected_questions, output_file, with_answers=False)

    if gen_answer:
        ans_file = output_dir / f"{source_file.stem}_random_{selected_count}_cau_co_dap_an.docx"
        _write_quiz_docx(selected_questions, ans_file, with_answers=True)

    interactive_file = None
    if interactive:
        interactive_file = _export_to_interactive_json(
            selected_questions, 
            source_file.stem, 
            time_limit, 
            workspace=workspace,
            details=f"random_{selected_count}_cau",
            sub_folder=sub_folder
        )

    return QuizGenerateResult(
        source_file=source_file.name,
        requested_count=question_count,
        generated_count=selected_count,
        quiz_output_file=str(interactive_file if interactive else output_file),
    )

def generate_quiz_with_range(
    source_file: Path,
    output_dir: Path,
    from_question: int,
    to_question: Optional[int],
    interactive: bool = False,
    gen_answer: bool = False,
    time_limit: int = 0,
    workspace: str = None,
    sub_folder: str = ""
) -> QuizGenerateResult:
    questions = parse_questions_for_grading(source_file)
    if not questions:
        raise ValueError("Không đọc được câu hỏi từ file nguồn")

    start_idx = max(0, from_question - 1)
    end_idx = min(len(questions), to_question if to_question else len(questions))
    selected_questions = questions[start_idx:end_idx]
    selected_count = len(selected_questions)

    output_dir.mkdir(parents=True, exist_ok=True)
    details = f"cau_{from_question}_den_{to_question if to_question else 'het'}"
    output_file = output_dir / f"{source_file.stem}_{details}.docx"
    _write_quiz_docx(selected_questions, output_file, with_answers=False)

    if gen_answer:
        ans_file = output_dir / f"{source_file.stem}_{details}_co_dap_an.docx"
        _write_quiz_docx(selected_questions, ans_file, with_answers=True)

    interactive_file = None
    if interactive:
        interactive_file = _export_to_interactive_json(
            selected_questions, 
            source_file.stem, 
            time_limit, 
            workspace=workspace,
            details=details,
            sub_folder=sub_folder
        )

    return QuizGenerateResult(
        source_file=source_file.name,
        requested_count=selected_count,
        generated_count=selected_count,
        quiz_output_file=str(interactive_file if interactive else output_file),
    )

def import_quiz_file(source_file: Path, title: str = None, time_limit: int = 0, workspace: str = None, sub_folder: str = "") -> Path:
    suffix = source_file.suffix.lower()
    workspace_path = Path(workspace).resolve() if workspace else Path.cwd() / "quiz_workspace"
    exams_dir = workspace_path / "exams"
    if sub_folder:
        exams_dir = exams_dir / sub_folder
    exams_dir.mkdir(parents=True, exist_ok=True)
    
    if suffix == ".json":
        target_path = exams_dir / source_file.name
        shutil.copy2(source_file, target_path)
        if title or time_limit > 0:
            try:
                with open(target_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if title: data['title'] = title
                if time_limit > 0: data['time_limit'] = time_limit
                with open(target_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception: pass
        return target_path

    questions = parse_questions_for_grading(source_file)
    if not questions:
        raise ValueError("Không đọc được câu hỏi từ file nguồn")
    
    custom_title = title or f"Bài thi: {source_file.stem}"
    return _export_to_interactive_json(
        questions,
        source_file.stem,
        time_limit,
        custom_title=custom_title,
        workspace=workspace,
        details="imported",
        sub_folder=sub_folder
    )

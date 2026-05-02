import importlib
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
from ..parsing import pick_single_label, normalize_question_text

def _write_option_line(document, label: str, text: str, is_correct: bool, is_selected: bool) -> None:
    docx_shared_module = importlib.import_module("docx.shared")
    RGBColor = docx_shared_module.RGBColor
    
    p = document.add_paragraph()
    p.paragraph_format.left_indent = docx_shared_module.Pt(20)
    
    run = p.add_run(f"{label}. {text}")
    
    if is_correct:
        run.bold = True
        run.font.color.rgb = RGBColor(0, 128, 0)  # Green
    
    if is_selected and not is_correct:
        run.font.strike = True
        run.font.color.rgb = RGBColor(255, 0, 0)  # Red

def _write_error_section(document, section_title: str, items: List[Dict[str, Any]]) -> None:
    if not items:
        return

    document.add_heading(section_title, level=1)
    for item in items:
        p = document.add_paragraph()
        p.add_run(f"Câu {item['index']}: ").bold = True
        p.add_run(item['question_text'])

        for opt in item['option_states']:
            _write_option_line(
                document,
                opt['label'],
                opt['text'],
                opt['is_correct'],
                opt['is_selected'],
            )
        document.add_paragraph("")

def build_wrong_questions_docx(
    correct_items: List[Dict[str, Any]],
    unanswered_items: List[Dict[str, Any]],
    wrong_items: List[Dict[str, Any]],
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

def _export_to_interactive_json(questions, source_name: str, time_limit: int, custom_title: str = None, workspace: str = None, details: str = "", sub_folder: str = "") -> Path:
    ws_base = Path(workspace).resolve() if workspace else Path("quiz_workspace").resolve()
    exams_dir = ws_base / "exams"
    if sub_folder:
        exams_dir = exams_dir / sub_folder
    exams_dir.mkdir(parents=True, exist_ok=True)
    
    quiz_id = str(uuid.uuid4())
    created_at = datetime.now().isoformat()
    
    formatted_questions = []
    for i, q in enumerate(questions):
        correct_label = pick_single_label(q.highlighted_labels)
        options = {}
        for label in ["A", "B", "C", "D", "E"]:
            opt = q.options.get(label)
            if opt:
                options[label] = opt.text
        formatted_questions.append({
            "id": i,
            "question": normalize_question_text(q.question),
            "options": options,
            "correct_answer": correct_label
        })
        
    title = custom_title if custom_title else f"Bài thi: {source_name}"
    if details:
        title = f"{title} ({details})"

    data = {
        "id": quiz_id,
        "title": title,
        "created_at": created_at,
        "time_limit": time_limit,
        "questions": formatted_questions
    }
    
    file_name = f"{source_name}_{details}.json" if details else f"quiz_{quiz_id}.json"
    output_path = exams_dir / file_name
    
    if output_path.exists():
        output_path = exams_dir / f"{source_name}_{details}_{quiz_id[:8]}.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    return output_path

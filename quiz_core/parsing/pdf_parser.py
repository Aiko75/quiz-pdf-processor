from pathlib import Path
from typing import List, Dict, Any
import fitz
from .core import parse_questions
from .docx_parser import write_output_files
from .utils import (
    _normalize_text
)
from ..models import LineData, QuizQuestionState, QuizOptionState

def extract_styled_lines(pdf_path: Path) -> List[LineData]:
    document = fitz.open(pdf_path)
    lines: List[LineData] = []
    try:
        for page_index, page in enumerate(document, start=1):
            page_dict = page.get_text("dict")
            for block in page_dict.get("blocks", []):
                if block.get("type") != 0: continue
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "")
                        if not text.strip() and text != '\uf00c': continue
                        bold = "bold" in span.get("font", "").lower()
                        color = span.get("color", 0)
                        bbox = span.get("bbox", (0, 0, 0, 0))
                        lines.append(
                            LineData(
                                text=text,
                                is_bold=bold,
                                color_int=color,
                                page_number=page_index,
                                x0=float(bbox[0]),
                                y0=float(bbox[1]),
                            )
                        )
    finally:
        document.close()
    return lines

def process_pdf_file(pdf_file: Path, output_dir: Path) -> Dict[str, Any]:
    lines = extract_styled_lines(pdf_file)
    questions = parse_questions(lines)
    if not questions:
        return {"status": "skipped", "pdf": pdf_file.name, "question_count": 0}
    write_output_files(questions, pdf_file, output_dir)
    return {"status": "ok", "pdf": pdf_file.name, "question_count": len(questions)}

def process_folder(input_dir: Path, output_dir: Path) -> List[Dict[str, Any]]:
    pdf_files = sorted(input_dir.glob("*.pdf"))
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for f in pdf_files:
        results.append(process_pdf_file(f, output_dir))
    return results

def parse_pdf_questions_for_grading(pdf_file: Path) -> List[QuizQuestionState]:
    lines = extract_styled_lines(pdf_file)
    q_data = parse_questions(lines)
    result = []
    for q in q_data:
        options_map = {}
        highlighted = []
        for opt in q.options:
            is_highlighted = opt.emphasized
            red = (opt.color_int >> 16) & 255
            green = (opt.color_int >> 8) & 255
            blue = opt.color_int & 255
            options_map[opt.label] = QuizOptionState(
                label=opt.label,
                text=opt.text,
                highlighted=is_highlighted,
                is_bold=opt.is_bold,
                color_rgb=(red, green, blue) if opt.color_int != 0 else None
            )
            if is_highlighted:
                highlighted.append(opt.label)
        result.append(QuizQuestionState(
            question=q.question,
            options=options_map,
            highlighted_labels=highlighted
        ))
    return result

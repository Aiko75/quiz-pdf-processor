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
            # Gather highlight rectangles from page drawings and annotations
            highlights = []
            
            # 1. From drawings (e.g. Word highlighted rectangles exported to PDF)
            drawings = page.get_drawings()
            for d in drawings:
                if d.get("type") in ("f", "fs") and d.get("fill") is not None:
                    fill = d["fill"]
                    if len(fill) == 3:
                        r, g, b = fill
                        # Light highlight colors have high sum of RGB values
                        if r + g + b > 1.2:
                            highlights.append(d["rect"])
            
            # 2. From standard PDF annotations (if any)
            annots = page.annots()
            if annots:
                for annot in annots:
                    # 8 = Highlight, 9 = Underline, 10 = Squiggly, 11 = StrikeOut
                    if annot.type[0] in (8, 9, 10, 11):
                        highlights.append(annot.rect)
            
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
                        
                        # Check intersection with highlight areas
                        is_highlighted = False
                        span_rect = fitz.Rect(bbox)
                        for rect in highlights:
                            if span_rect.intersects(rect):
                                intersect_rect = span_rect & rect
                                # Area of intersection should be at least 20% of span's area
                                if intersect_rect.get_area() > 0.2 * span_rect.get_area():
                                    is_highlighted = True
                                    break
                                    
                        lines.append(
                            LineData(
                                text=text,
                                is_bold=bold,
                                color_int=color,
                                page_number=page_index,
                                x0=float(bbox[0]),
                                y0=float(bbox[1]),
                                is_highlighted=is_highlighted,
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
            logical_index=q.logical_index,
            options=options_map,
            highlighted_labels=highlighted
        ))
    return result

import argparse
from collections import Counter
import importlib
import random
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import json

import fitz


QUESTION_PATTERN = re.compile(
    r"^(?:Câu\s*\d+[\.:\)]?|Question\s*\d+[\.:\)]?|\d+[\.)])\s+",
    re.IGNORECASE,
)
UPPER_OPTION_PATTERN = re.compile(r"^([A-D])(?:[\.:\)\-]\s*|\s+)(.+)$")
LOWER_OPTION_PATTERN = re.compile(r"^([a-d])[\.:\)\-]\s*(.+)$")
HEADER_NOISE_PATTERN = re.compile(r"^(Chương\s*\d+\s*:|LTTN\s*\d+\s*:?)$", re.IGNORECASE)
INLINE_NOISE_PATTERN = re.compile(
    r"(Downloaded\s+by|binhprodotcom@gmail\.com|l[O0]M[oO]ARcPSD\|?\d*).*$",
    re.IGNORECASE,
)
FULL_NOISE_PATTERN = re.compile(
    r"^(Downloaded\s+by.*|\s*\d+\s*/\s*\d+\s*|\s*Trang\s*\d+\s*)$",
    re.IGNORECASE,
)


@dataclass
class LineData:
    text: str
    is_bold: bool
    color_int: int
    page_number: int
    x0: float
    y0: float


@dataclass
class OptionData:
    label: str
    text: str
    emphasized: bool = False
    is_bold: bool = False
    color_int: int = 0
    page_number: int = -1
    x0: float = 0.0
    y0: float = 0.0


@dataclass
class QuestionData:
    question: str = ""
    options: List[OptionData] = field(default_factory=list)
    answer_label: Optional[str] = None
    page_number: int = -1
    x0: float = 0.0
    y0: float = 0.0


@dataclass
class ValidationResult:
    pdf_name: str
    original_questions: int
    recognized_answers: int
    answer_doc_questions: int
    practice_doc_questions: int
    mismatch_count: int
    no_highlight_count: int
    multi_highlight_count: int
    practice_highlight_count: int


@dataclass
class QuizOptionState:
    label: str
    text: str
    highlighted: bool = False
    is_bold: bool = False
    color_rgb: Optional[Tuple[int, int, int]] = None
    bg_highlight: Optional[Any] = None


@dataclass
class QuizQuestionState:
    question: str
    options: Dict[str, QuizOptionState] = field(default_factory=dict)
    highlighted_labels: List[str] = field(default_factory=list)


@dataclass
class GradingResult:
    answer_file: str
    submission_file: str
    compared_questions: int
    correct_count: int
    wrong_count: int
    unanswered_count: int
    answered_count: int
    skipped_count: int
    wrong_output_file: str
    correct_questions: List[int] = field(default_factory=list)
    wrong_questions: List[int] = field(default_factory=list)
    unanswered_questions: List[int] = field(default_factory=list)
    skipped_questions: List[int] = field(default_factory=list)
    auto_swapped_files: bool = False
    wrong_items: List[Dict[str, object]] = field(default_factory=list)
    unanswered_items: List[Dict[str, object]] = field(default_factory=list)
    knowledge_report_file: str = ""


@dataclass
class QuizGenerateResult:
    source_file: str
    requested_count: int
    generated_count: int
    quiz_output_file: str


def clean_text_noise(text: str) -> str:
    cleaned = INLINE_NOISE_PATTERN.sub("", text).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def repair_fragmented_text(text: str) -> str:
    tokens = text.split()
    if len(tokens) < 3:
        return text

    rebuilt: List[str] = []
    buffer: List[str] = []

    def flush_buffer() -> None:
        nonlocal buffer
        if not buffer:
            return
        has_single_char = any(len(token) == 1 for token in buffer)
        all_alpha = all(re.fullmatch(r"[A-Za-zÀ-ỹ]+", token) for token in buffer)
        avg_len = sum(len(token) for token in buffer) / len(buffer)
        if all_alpha and has_single_char and avg_len <= 2.0:
            rebuilt.append("".join(buffer))
        else:
            rebuilt.extend(buffer)
        buffer = []

    for token in tokens:
        if re.fullmatch(r"[A-Za-zÀ-ỹ]+", token):
            if len(token) <= 2:
                buffer.append(token)
            else:
                flush_buffer()
                rebuilt.append(token)
        else:
            flush_buffer()
            rebuilt.append(token)

    flush_buffer()
    return " ".join(rebuilt)


def should_append_to_last_option(last_option: OptionData, line: LineData) -> bool:
    if line.page_number != last_option.page_number:
        return False
    if line.y0 - last_option.y0 > 26:
        return False
    if line.x0 - last_option.x0 > 48:
        return False
    if line.color_int != 0 and last_option.color_int != 0 and line.color_int != last_option.color_int:
        return False
    if match_option_line(line.text) or QUESTION_PATTERN.match(line.text):
        return False
    return True


def should_append_to_question(question: QuestionData, line: LineData) -> bool:
    if question.page_number == -1:
        return True
    if line.page_number != question.page_number:
        return False
    if line.y0 - question.y0 > 28:
        return False
    if line.x0 - question.x0 > 64:
        return False
    if match_option_line(line.text) or HEADER_NOISE_PATTERN.match(line.text):
        return False
    return True


def order_options(options: List[OptionData]) -> List[OptionData]:
    expected = ["A", "B", "C", "D"]
    mapping = {option.label: option for option in options}
    if all(label in mapping for label in expected):
        return [mapping[label] for label in expected]
    return options


def match_option_line(text: str) -> Optional[re.Match[str]]:
    upper = UPPER_OPTION_PATTERN.match(text)
    if upper:
        return upper
    lower = LOWER_OPTION_PATTERN.match(text)
    if lower:
        return lower
    return None


def extract_styled_lines(pdf_path: Path) -> List[LineData]:
    document = fitz.open(pdf_path)
    lines: List[LineData] = []
    try:
        for page_index, page in enumerate(document, start=1):
            page_dict = page.get_text("dict")
            for block in page_dict.get("blocks", []):
                if block.get("type") != 0:
                    continue
                for line in block.get("lines", []):
                    spans = line.get("spans", [])
                    text_parts = []
                    bold = False
                    detected_color = 0
                    for span in spans:
                        text = span.get("text", "")
                        if not text:
                            continue
                        text_parts.append(text)

                        font_name = str(span.get("font", "")).lower()
                        flags = int(span.get("flags", 0))
                        if "bold" in font_name or (flags & 16) != 0:
                            bold = True

                        color = int(span.get("color", 0))
                        if color != 0 and detected_color == 0:
                            detected_color = color

                    text = " ".join(part.strip() for part in text_parts if part.strip())
                    text = re.sub(r"\s+", " ", text).strip()
                    if text:
                        line_bbox = line.get("bbox", (0.0, 0.0, 0.0, 0.0))
                        lines.append(
                            LineData(
                                text=text,
                                is_bold=bold,
                                color_int=detected_color,
                                page_number=page_index,
                                x0=float(line_bbox[0]),
                                y0=float(line_bbox[1]),
                            )
                        )
    finally:
        document.close()
    return lines


def parse_questions(lines: List[LineData]) -> List[QuestionData]:
    questions: List[QuestionData] = []
    current: Optional[QuestionData] = None

    for line in lines:
        text = clean_text_noise(line.text)
        if not text or FULL_NOISE_PATTERN.match(text):
            continue

        if HEADER_NOISE_PATTERN.match(text):
            continue

        if QUESTION_PATTERN.match(text):
            if current and len(current.options) == 4:
                current.options = order_options(current.options)
                finalize_answer(current)
                questions.append(current)
            current = QuestionData(
                question=text,
                page_number=line.page_number,
                x0=line.x0,
                y0=line.y0,
            )
            continue

        option_match = match_option_line(text)
        if option_match:
            label = option_match.group(1).upper()
            option_text = option_match.group(2).strip()
            if label not in {"A", "B", "C", "D"}:
                continue

            if current is None:
                current = QuestionData(
                    question="",
                    page_number=line.page_number,
                    x0=line.x0,
                    y0=line.y0,
                )

            current.options.append(
                OptionData(
                    label=label,
                    text=repair_fragmented_text(option_text),
                    emphasized=False,
                    is_bold=line.is_bold,
                    color_int=line.color_int,
                    page_number=line.page_number,
                    x0=line.x0,
                    y0=line.y0,
                )
            )

            if len(current.options) == 4:
                current.question = current.question.strip()
                if current.question:
                    current.options = order_options(current.options)
                    finalize_answer(current)
                    questions.append(current)
                current = None
            continue

        if current is None:
            current = QuestionData(
                question=text,
                page_number=line.page_number,
                x0=line.x0,
                y0=line.y0,
            )
            continue

        if current.options:
            if should_append_to_last_option(current.options[-1], line):
                merged_text = f"{current.options[-1].text} {text}".strip()
                current.options[-1].text = repair_fragmented_text(merged_text)
                current.options[-1].x0 = line.x0
                current.options[-1].y0 = line.y0
        else:
            if should_append_to_question(current, line):
                current.question = f"{current.question} {text}".strip()
                current.x0 = line.x0
                current.y0 = line.y0

    if current and len(current.options) == 4:
        current.options = order_options(current.options)
        finalize_answer(current)
        questions.append(current)

    return deduplicate_questions(questions)


def finalize_answer(question: QuestionData) -> None:
    bold_labels = [opt.label for opt in question.options if opt.is_bold]
    if len(bold_labels) == 1:
        question.answer_label = bold_labels[0]
        for opt in question.options:
            opt.emphasized = opt.label == question.answer_label
        return

    color_values = [opt.color_int for opt in question.options]
    dominant_color = Counter(color_values).most_common(1)[0][0] if color_values else 0
    non_dominant_labels = [opt.label for opt in question.options if opt.color_int != dominant_color]
    if len(non_dominant_labels) == 1:
        question.answer_label = non_dominant_labels[0]
        for opt in question.options:
            opt.emphasized = opt.label == question.answer_label
        return

    question.answer_label = None
    for opt in question.options:
        opt.emphasized = False


def deduplicate_questions(questions: List[QuestionData]) -> List[QuestionData]:
    seen = set()
    deduped: List[QuestionData] = []
    for question in questions:
        question_key = re.sub(r"\s+", " ", question.question).strip().lower()
        options_key = tuple(
            (option.label, re.sub(r"\s+", " ", option.text).strip().lower())
            for option in question.options
        )
        key = (question_key, options_key)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(question)
    return deduped


def write_output_files(
    questions: List[QuestionData],
    input_file: Path,
    output_dir: Path,
) -> None:
    docx_module = importlib.import_module("docx")
    docx_shared_module = importlib.import_module("docx.shared")
    Document = docx_module.Document
    Pt = docx_shared_module.Pt
    RGBColor = docx_shared_module.RGBColor

    base_name = input_file.stem
    with_answers = output_dir / f"{base_name}_co_dap_an.docx"
    practice = output_dir / f"{base_name}_de_lam.docx"

    ans_doc = Document()
    practice_doc = Document()

    for document in (ans_doc, practice_doc):
        style = document.styles["Normal"]
        style.font.name = "Times New Roman"
        style.font.size = Pt(12)

    for idx, question in enumerate(questions, start=1):
        normalized_question = re.sub(
            r"^(?:Câu\s*\d+[\.:\)]?|Question\s*\d+[\.:\)]?|\d+[\.)])\s*",
            "",
            question.question,
            flags=re.IGNORECASE,
        ).strip()
        dominant_color = (
            Counter([opt.color_int for opt in question.options]).most_common(1)[0][0]
            if question.options
            else 0
        )

        ans_doc.add_paragraph(f"Câu {idx}: {normalized_question}")
        practice_doc.add_paragraph(f"Câu {idx}: {normalized_question}")

        for option in question.options:
            option_line = f"{option.label}. {option.text}"

            ans_paragraph = ans_doc.add_paragraph()
            ans_run = ans_paragraph.add_run(option_line)
            if question.answer_label == option.label:
                if option.is_bold:
                    ans_run.bold = True
                if option.color_int != 0 and option.color_int != dominant_color:
                    red = (option.color_int >> 16) & 255
                    green = (option.color_int >> 8) & 255
                    blue = option.color_int & 255
                    ans_run.font.color.rgb = RGBColor(red, green, blue)

            practice_doc.add_paragraph(option_line)

        ans_doc.add_paragraph("")
        practice_doc.add_paragraph("")

    ans_doc.save(with_answers)
    practice_doc.save(practice)


def process_pdf_file(pdf_file: Path, output_dir: Path) -> Dict[str, object]:
    lines = extract_styled_lines(pdf_file)
    questions = parse_questions(lines)
    if not questions:
        return {"status": "skipped", "pdf": pdf_file.name, "question_count": 0}
    write_output_files(questions, pdf_file, output_dir)
    return {
        "status": "ok",
        "pdf": pdf_file.name,
        "question_count": len(questions),
    }


def process_folder(input_dir: Path, output_dir: Path) -> List[Dict[str, object]]:
    pdf_files = sorted(input_dir.glob("*.pdf"))
    if not pdf_files:
        raise FileNotFoundError(f"Không tìm thấy file PDF trong: {input_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)
    results: List[Dict[str, object]] = []

    for pdf_file in pdf_files:
        result = process_pdf_file(pdf_file, output_dir)
        results.append(result)
        if result["status"] != "ok":
            print(f"[BỎ QUA] Không nhận diện được câu hỏi trong: {pdf_file.name}")
            continue
        print(f"[OK] Đã xử lý: {pdf_file.name} -> {result['question_count']} câu")

    return results


def parse_docx_questions(docx_path: Path) -> List[Dict[str, object]]:
    docx_module = importlib.import_module("docx")
    document = docx_module.Document(docx_path)

    option_pattern = re.compile(r"^([A-D])\.\s+(.+)$")
    question_pattern = re.compile(r"^Câu\s+\d+:")

    rows: List[Dict[str, object]] = []
    current: Optional[Dict[str, object]] = None

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue

        if question_pattern.match(text):
            if current:
                rows.append(current)
            current = {"question": text, "options": {}}
            continue

        option_match = option_pattern.match(text)
        if option_match and current is not None:
            label = option_match.group(1)
            option_text = option_match.group(2).strip()
            highlighted = False
            for run in paragraph.runs:
                if run.bold:
                    highlighted = True
                color = run.font.color
                if color is not None and color.rgb is not None:
                    highlighted = True

            current["options"][label] = {
                "text": option_text,
                "highlighted": highlighted,
            }

    if current:
        rows.append(current)

    return rows


def parse_docx_questions_for_grading(docx_path: Path) -> List[QuizQuestionState]:
    docx_module = importlib.import_module("docx")
    document = docx_module.Document(docx_path)

    option_pattern = re.compile(r"^\s*([A-Da-d])[\.:\)\-]\s+(.+)$")
    question_pattern = re.compile(r"^\s*(?:Câu|Question)\s+\d+\s*:", re.IGNORECASE)

    rows: List[QuizQuestionState] = []
    current: Optional[QuizQuestionState] = None

    def run_is_bold(run) -> bool:
        if bool(getattr(run, "bold", False)):
            return True
        if bool(getattr(run.font, "bold", False)):
            return True
        run_xml = str(run._element.xml).lower()
        return "<w:b" in run_xml

    def is_meaningful_rgb(rgb: Any) -> bool:
        if rgb is None:
            return False
        try:
            red, green, blue = int(rgb[0]), int(rgb[1]), int(rgb[2])
        except Exception:
            return False
        return (red, green, blue) != (0, 0, 0)

    def run_has_any_color(run) -> bool:
        color = run.font.color
        if color is None:
            return False
        if color.rgb is not None and is_meaningful_rgb(color.rgb):
            return True
        theme_color = getattr(color, "theme_color", None)
        if theme_color is not None:
            theme_name = str(theme_color).upper()
            if "ACCENT" in theme_name or "HYPERLINK" in theme_name:
                return True
        return False

    def run_has_emphasis_xml(run) -> bool:
        run_xml = str(run._element.xml).lower()
        if "<w:highlight" in run_xml:
            return True
        if "<w:shd" in run_xml:
            return True
        return False

    def paragraph_has_meaningful_shading(paragraph) -> bool:
        paragraph_xml = str(paragraph._element.xml).lower()
        if "<w:shd" not in paragraph_xml:
            return False
        if "w:val=\"clear\"" in paragraph_xml and "w:fill=\"auto\"" in paragraph_xml:
            return False
        if "w:fill=\"ffffff\"" in paragraph_xml:
            return False
        return True

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue

        if question_pattern.match(text):
            if current:
                current.highlighted_labels = [
                    label
                    for label, option in current.options.items()
                    if option.highlighted
                ]
                rows.append(current)
            current = QuizQuestionState(question=text, options={})
            continue

        option_match = option_pattern.match(text)
        if option_match and current is not None:
            label = option_match.group(1).upper()
            option_text = option_match.group(2).strip()

            has_bold = any(run_is_bold(run) for run in paragraph.runs)
            paragraph_has_shading = paragraph_has_meaningful_shading(paragraph)
            color_rgb: Optional[Tuple[int, int, int]] = None
            bg_highlight: Optional[Any] = None
            for run in paragraph.runs:
                color = run.font.color
                if color is not None and color.rgb is not None and is_meaningful_rgb(color.rgb):
                    rgb = color.rgb
                    color_rgb = (rgb[0], rgb[1], rgb[2])
                if run.font.highlight_color is not None and bg_highlight is None:
                    bg_highlight = run.font.highlight_color

            current.options[label] = QuizOptionState(
                label=label,
                text=option_text,
                highlighted=(
                    has_bold
                    or color_rgb is not None
                    or bg_highlight is not None
                    or paragraph_has_shading
                    or any(run_has_emphasis_xml(run) for run in paragraph.runs)
                    or any(run_has_any_color(run) for run in paragraph.runs)
                ),
                is_bold=has_bold,
                color_rgb=color_rgb,
                bg_highlight=bg_highlight,
            )

    if current:
        current.highlighted_labels = [
            label for label, option in current.options.items() if option.highlighted
        ]
        rows.append(current)

    return rows


def parse_pdf_questions_for_grading(pdf_path: Path) -> List[QuizQuestionState]:
    parsed_questions = parse_questions(extract_styled_lines(pdf_path))
    rows: List[QuizQuestionState] = []

    for question in parsed_questions:
        color_values = [option.color_int for option in question.options]
        dominant_color = Counter(color_values).most_common(1)[0][0] if color_values else 0

        options_map: Dict[str, QuizOptionState] = {}
        highlighted_labels: List[str] = []

        for option in question.options:
            has_color_emphasis = option.color_int != 0 and option.color_int != dominant_color
            highlighted = option.is_bold or has_color_emphasis
            color_rgb: Optional[Tuple[int, int, int]] = None
            if option.color_int != 0:
                red = (option.color_int >> 16) & 255
                green = (option.color_int >> 8) & 255
                blue = option.color_int & 255
                color_rgb = (red, green, blue)

            options_map[option.label] = QuizOptionState(
                label=option.label,
                text=option.text,
                highlighted=highlighted,
                is_bold=option.is_bold,
                color_rgb=color_rgb,
                bg_highlight=None,
            )
            if highlighted:
                highlighted_labels.append(option.label)

        rows.append(
            QuizQuestionState(
                question=question.question,
                options=options_map,
                highlighted_labels=highlighted_labels,
            )
        )

    return rows


def parse_questions_for_grading(file_path: Path) -> List[QuizQuestionState]:
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        return parse_pdf_questions_for_grading(file_path)
    if suffix == ".docx":
        return parse_docx_questions_for_grading(file_path)
    raise ValueError(f"Định dạng file chưa hỗ trợ: {file_path.name}")


def normalize_question_text(question: str) -> str:
    return re.sub(
        r"^(?:Câu\s*\d+[\.:\)]?|Question\s*\d+[\.:\)]?|\d+[\.)])\s*",
        "",
        question,
        flags=re.IGNORECASE,
    ).strip()


def normalize_question_key(question: str) -> str:
    normalized = normalize_question_text(question)
    normalized = re.sub(r"\s+", " ", normalized).strip().lower()
    return normalized


def pick_single_label(labels: List[str]) -> Optional[str]:
    if len(labels) == 1:
        return labels[0]
    return None


def _count_single_highlighted(questions: List[QuizQuestionState]) -> int:
    return sum(1 for question in questions if pick_single_label(question.highlighted_labels) is not None)


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

    document.add_paragraph("BÁO CÁO CÂU LỖI")
    document.add_paragraph("")

    _write_error_section(document, "PHẦN 1 - CÁC CÂU LÀM SAI", wrong_items)
    _write_error_section(document, "PHẦN 2 - CÁC CÂU CHƯA LÀM", unanswered_items)

    document.save(output_file)


def _extract_text_from_docx(file_path: Path) -> str:
    docx_module = importlib.import_module("docx")
    document = docx_module.Document(file_path)
    lines = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]
    return "\n".join(lines)


def _extract_text_from_pptx(file_path: Path) -> str:
    pptx_module = importlib.import_module("pptx")
    presentation = pptx_module.Presentation(str(file_path))
    chunks: List[str] = []
    for slide in presentation.slides:
        for shape in slide.shapes:
            text = getattr(shape, "text", "")
            if text and text.strip():
                chunks.append(text.strip())
    return "\n".join(chunks)


def _extract_text_from_pdf(file_path: Path) -> str:
    document = fitz.open(file_path)
    page_texts: List[str] = []
    try:
        for page in document:
            text = page.get_text("text")
            if text and text.strip():
                page_texts.append(text.strip())
    finally:
        document.close()
    return "\n\n".join(page_texts)


def extract_text_from_knowledge_file(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        return _extract_text_from_pdf(file_path)
    if suffix == ".docx":
        return _extract_text_from_docx(file_path)
    if suffix == ".pptx":
        return _extract_text_from_pptx(file_path)
    if suffix in {".txt", ".md"}:
        return file_path.read_text(encoding="utf-8", errors="ignore")
    raise ValueError(f"Định dạng file kiến thức chưa hỗ trợ: {file_path.name}")


def _trim_text(text: str, max_chars: int) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[:max_chars] + " ..."


def _build_knowledge_prompt(
    grading_result: GradingResult,
    knowledge_context: str,
) -> str:
    mistakes_payload = {
        "wrong_questions": [
            {
                "index": item.get("index"),
                "question": item.get("question_text"),
                "selected": item.get("selected_labels"),
                "correct": item.get("correct_label"),
            }
            for item in grading_result.wrong_items
        ],
        "unanswered_questions": [
            {
                "index": item.get("index"),
                "question": item.get("question_text"),
                "correct": item.get("correct_label"),
            }
            for item in grading_result.unanswered_items
        ],
        "score_summary": {
            "compared_questions": grading_result.compared_questions,
            "correct_count": grading_result.correct_count,
            "wrong_count": grading_result.wrong_count,
            "unanswered_count": grading_result.unanswered_count,
        },
    }

    mistakes_json = json.dumps(mistakes_payload, ensure_ascii=False, indent=2)

    return (
        "Bạn là trợ lý học tập tiếng Việt. Dựa trên dữ liệu câu sai/chưa làm và tài liệu kiến thức, "
        "hãy phân tích lý do sai và chỉ ra lỗ hổng kiến thức.\n"
        "Yêu cầu đầu ra: ngắn gọn, rõ ràng, có tiêu đề và gạch đầu dòng.\n"
        "BẮT BUỘC có đủ các phần sau:\n"
        "1) Đánh giá tổng quan kết quả.\n"
        "2) Phân tích từng câu sai/chưa làm (nêu vì sao sai, kiến thức nào bị hổng).\n"
        "3) Điểm mạnh (chủ đề làm tốt).\n"
        "4) Điểm yếu/lỗ hổng kiến thức (gom theo chủ đề).\n"
        "5) Kế hoạch học thêm đề xuất (ưu tiên theo mức độ quan trọng).\n\n"
        "Dữ liệu chấm bài:\n"
        f"{mistakes_json}\n\n"
        "Tài liệu kiến thức tham chiếu:\n"
        f"{knowledge_context}\n"
    )


def _call_ollama_generate(prompt: str, model: str, ollama_url: str) -> str:
    requests_module = importlib.import_module("requests")
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2,
        },
    }
    response = requests_module.post(ollama_url, json=payload, timeout=120)
    response.raise_for_status()
    data = response.json()
    text = str(data.get("response", "")).strip()
    if not text:
        raise RuntimeError("Ollama không trả về nội dung phân tích.")
    return text


def build_knowledge_gap_report(
    grading_result: GradingResult,
    knowledge_files: List[Path],
    output_dir: Path,
    model: str = "llama3.1:8b",
    ollama_url: str = "http://127.0.0.1:11434/api/generate",
) -> Path:
    if not knowledge_files:
        raise ValueError("Chưa có file kiến thức để phân tích.")

    context_parts: List[str] = []
    for file_path in knowledge_files:
        if not file_path.exists() or not file_path.is_file():
            continue
        extracted = extract_text_from_knowledge_file(file_path)
        if not extracted.strip():
            continue
        context_parts.append(f"[Nguồn: {file_path.name}]\n{_trim_text(extracted, 12000)}")

    if not context_parts:
        raise ValueError("Không trích xuất được nội dung từ các file kiến thức.")

    joined_context = "\n\n".join(context_parts)
    prompt = _build_knowledge_prompt(grading_result, _trim_text(joined_context, 35000))
    analysis = _call_ollama_generate(prompt=prompt, model=model, ollama_url=ollama_url)

    output_dir.mkdir(parents=True, exist_ok=True)
    report_file = output_dir / f"{Path(grading_result.submission_file).stem}_phan_tich_kien_thuc.md"

    report_content = (
        "# PHÂN TÍCH LỖ HỔNG KIẾN THỨC\n\n"
        f"- Model Ollama: `{model}`\n"
        f"- Số câu so sánh: {grading_result.compared_questions}\n"
        f"- Đúng: {grading_result.correct_count}\n"
        f"- Sai: {grading_result.wrong_count}\n"
        f"- Chưa làm: {grading_result.unanswered_count}\n\n"
        "## Nội dung phân tích\n\n"
        f"{analysis.strip()}\n"
    )

    report_file.write_text(report_content, encoding="utf-8")
    return report_file


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

    minimum_text_matches = max(1, int(len(submission_questions) * 0.5))
    if len(compared_pairs) < minimum_text_matches:
        compared_pairs = [
            (index, index)
            for index in range(min(len(submission_questions), len(answer_questions)))
        ]

    compared_questions = len(compared_pairs)

    correct_count = 0
    wrong_count = 0
    unanswered_count = 0
    skipped_count = 0
    correct_questions: List[int] = []
    wrong_questions: List[int] = []
    unanswered_questions: List[int] = []
    skipped_questions: List[int] = []
    unanswered_items: List[Dict[str, object]] = []
    wrong_items: List[Dict[str, object]] = []

    for submission_index, answer_index in compared_pairs:
        student_question = submission_questions[submission_index]
        answer_question = answer_questions[answer_index]

        correct_label = pick_single_label(answer_question.highlighted_labels)
        selected_labels = list(student_question.highlighted_labels)
        selected_label = pick_single_label(selected_labels)

        if correct_label is None:
            skipped_count += 1
            skipped_questions.append(submission_index + 1)
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
            unanswered_questions.append(submission_index + 1)
            unanswered_items.append(
                {
                    "index": submission_index + 1,
                    "question_text": normalize_question_text(student_question.question),
                    "selected_labels": [],
                    "correct_label": correct_label,
                    "option_states": merged_options,
                }
            )
            continue

        if selected_label == correct_label:
            correct_count += 1
            correct_questions.append(submission_index + 1)
            continue

        wrong_count += 1
        wrong_questions.append(submission_index + 1)
        wrong_items.append(
            {
                "index": submission_index + 1,
                "question_text": normalize_question_text(student_question.question),
                "selected_labels": selected_labels,
                "correct_label": correct_label,
                "option_states": merged_options,
            }
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    wrong_output_file = output_dir / f"{submission_file.stem}_cac_cau_loi.docx"
    build_wrong_questions_docx(unanswered_items, wrong_items, wrong_output_file)

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
        correct_questions=correct_questions,
        wrong_questions=wrong_questions,
        unanswered_questions=unanswered_questions,
        skipped_questions=skipped_questions,
        auto_swapped_files=auto_swapped_files,
        wrong_items=wrong_items,
        unanswered_items=unanswered_items,
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


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Lọc đề trắc nghiệm từ PDF, giữ lại câu hỏi + 4 đáp án, "
            "xuất 2 file: có đáp án và file để làm; hoặc chấm bài từ file bài làm."
        )
    )
    parser.add_argument(
        "--input",
        default="files",
        help="Thư mục chứa file PDF đầu vào (mặc định: files)",
    )
    parser.add_argument(
        "--output",
        default="processed_quiz",
        help="Thư mục output (mặc định: processed_quiz)",
    )
    parser.add_argument(
        "--grade-submission",
        help="Đường dẫn file bài làm đã tô đáp án (PDF/DOCX)",
    )
    parser.add_argument(
        "--grade-answer",
        help="Đường dẫn file đáp án (PDF/DOCX)",
    )
    args = parser.parse_args()

    output_dir = Path(args.output).resolve()

    if args.grade_submission or args.grade_answer:
        if not args.grade_submission or not args.grade_answer:
            raise ValueError(
                "Khi dùng chế độ chấm bài, cần truyền đủ --grade-submission và --grade-answer"
            )

        submission_file = Path(args.grade_submission).resolve()
        answer_file = Path(args.grade_answer).resolve()

        result = grade_quiz_files(
            submission_file=submission_file,
            answer_file=answer_file,
            output_dir=output_dir,
        )

        print("=== KẾT QUẢ CHẤM BÀI ===")
        print(f"Bài làm: {result.submission_file}")
        print(f"Đáp án: {result.answer_file}")
        print(f"Số câu so sánh: {result.compared_questions}")
        print(f"Số câu đúng: {result.correct_count}")
        print(f"Danh sách câu đúng: {result.correct_questions}")
        print(f"Số câu sai: {result.wrong_count}")
        print(f"Danh sách câu sai: {result.wrong_questions}")
        print(f"Số câu chưa làm: {result.unanswered_count}")
        print(f"Danh sách câu chưa làm: {result.unanswered_questions}")
        print(f"Số câu bỏ qua: {result.skipped_count}")
        print(f"Danh sách câu bỏ qua: {result.skipped_questions}")
        print(f"Số câu đã làm (đúng + sai): {result.answered_count}")
        if result.auto_swapped_files:
            print("[LƯU Ý] Đã tự động đổi vai trò 2 file vì phát hiện bạn chọn nhầm file đáp án/bài làm.")
        print(f"File các câu lỗi (chưa làm + sai): {result.wrong_output_file}")
        return

    input_dir = Path(args.input).resolve()
    process_folder(input_dir, output_dir)


if __name__ == "__main__":
    main()
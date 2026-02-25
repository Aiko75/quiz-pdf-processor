import argparse
from collections import Counter
import importlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

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
            "xuất 2 file: có đáp án và file để làm."
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
    args = parser.parse_args()

    input_dir = Path(args.input).resolve()
    output_dir = Path(args.output).resolve()
    process_folder(input_dir, output_dir)


if __name__ == "__main__":
    main()
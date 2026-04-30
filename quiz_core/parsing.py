from collections import Counter
import importlib
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import fitz

from .models import LineData, OptionData, QuestionData, QuizOptionState, QuizQuestionState


# Standard quiz PDF pattern (original)
QUESTION_PATTERN = re.compile(
    r"^(?:Câu\s*\d+[\.:)]?|Question\s*\d+[\.:)]?|\d+[\.:)])\ +",
    re.IGNORECASE,
)
# LMS PDF pattern: "Câu h ỏ i 1" (with spaces between characters due to PDF extraction)
LMS_QUESTION_PATTERN = re.compile(
    r"^Câu\s+h\s+ỏ\s+i\s+\d+",
    re.IGNORECASE,
)

UPPER_OPTION_PATTERN = re.compile(r"^([A-D])(?:[\.:\)\-]\s*|\s+)(.+)$")
LOWER_OPTION_PATTERN = re.compile(r"^([a-d])[\.:\)\-]\s*(.+)$")
# LMS options: "a." alone or with text  
LMS_OPTION_ALONE_PATTERN = re.compile(r"^([a-dA-D])\.\s*$")
LMS_OPTION_WITH_TEXT_PATTERN = re.compile(r"^([a-dA-D])\.\s+(.+)$")
HEADER_NOISE_PATTERN = re.compile(r"^(Chương\s*\d+\s*:|LTTN\s*\d+\s*:?)$", re.IGNORECASE)
INLINE_NOISE_PATTERN = re.compile(
    r"(Downloaded\s+by|binhprodotcom@gmail\.com|l[O0]M[oO]ARcPSD\|?\d*).*$",
    re.IGNORECASE,
)
FULL_NOISE_PATTERN = re.compile(
    r"^(Downloaded\s+by.*|\s*\d+\s*/\s*\d+\s*|\s*Trang\s*\d+\s*)$",
    re.IGNORECASE,
)


def is_lms_noise_line(text: str) -> bool:
    """
    Check if a line is LMS metadata/noise that should be filtered.
    These are typically header info, status lines, timestamps, URLs, etc.
    """
    # IMPORTANT: Don't filter checkmarks (✓) - they're used for answer detection
    if text.strip() == '\uf00c':
        return False
    
    text = _normalize_text(text)
    text_lower = text.lower().strip()
    
    # Empty or too short
    if not text_lower or len(text_lower) < 2:
        return True
    
    # URLs
    if text_lower.startswith("http://") or text_lower.startswith("https://"):
        return True
    
    # Exact matches for common LMS noise
    exact_noise = [
        _normalize_text("đúng"),
        _normalize_text("sai"),
        _normalize_text("trạng thái"),
        _normalize_text("thời gian thực"),
        _normalize_text("thời gian"),
    ]
    if text_lower in exact_noise:
        return True
    
    # Duration pattern: "27 phút 57 giây" or similar
    if re.match(r"^\d+\s+(phút|giây|tiếng|ngày|tuần).*", text_lower):
        return True
    
    # Page numbers: "1/14", "2/14", etc.
    if re.match(r"^\d+/\d+\s*$", text_lower):
        return True
    
    # Pattern-based noise
    # Timestamps: "11/25/25, 2:24 PM"
    if re.match(r"^\d+/\d+/\d+,?\s*\d+:\d+\s*[AP]M", text):
        return True
    
    # Header lines (contain "bảng điều khiển", "chapter", "week" regardless of length)
    # These are always LMS header lines
    lms_headers = [
        _normalize_text("bảng điều khiển"),
        "chapter",
        "week",
        _normalize_text("bắt đầu vào"),
        _normalize_text("kết thúc lúc"),
    ]
    for header in lms_headers:
        if header in text_lower:
            return True
    
    # Standalone score/time patterns (only these keywords, nothing else substantial)
    if len(text_lower) < 100:  
        simple_noise = [
            _normalize_text("điểm"),
            _normalize_text("đạt điểm"),
            _normalize_text("xem lại"),
            _normalize_text("thời gian"),
        ]
        for noise in simple_noise:
            if noise in text_lower:
                # Make sure text is mostly just this, not incidental
                # e.g., "Điểm" by itself but not "Điểm này là..."
                if text_lower == noise or text_lower.startswith(noise + " "):
                    return True
    
    # Time-like: "Wednesday, 13 August 2025, 11:01 AM"
    if re.match(r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+\d+", text, re.IGNORECASE):
        return True
    
    # Status/score patterns
    if _normalize_text("đã xong") in text_lower or "hiện" == text_lower:
        return True
    
    # Numbers like "49,00/50,00" or "9,80 trên 10,00"
    if re.match(r"^\d+[,\.]\d+(\s*(trên|/|out of))?\s*\d+[,\.]?\d*", text):
        return True
    
    return False


def is_lms_format(lines: List[LineData]) -> bool:
    for line in lines:
        text = clean_text_noise(line.text).strip()
        if text and LMS_QUESTION_PATTERN.match(text):
            return True
    return False




def _normalize_text(text: str) -> str:
    """Normalize unicode text (NFC form) for consistent matching."""
    return unicodedata.normalize('NFC', text)


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
    # LMS format: try to match "a. text" or just "a."
    lms_with_text = LMS_OPTION_WITH_TEXT_PATTERN.match(text)
    if lms_with_text:
        return lms_with_text
    return None


def is_option_label_only(text: str) -> bool:
    """Check if text is only an option label like 'a.' without content."""
    return LMS_OPTION_ALONE_PATTERN.match(text) is not None


def parse_lms_questions(lines: List[LineData]) -> List[QuestionData]:
    """
    Parse LMS PDF format with improved answer detection using geometric positioning.
    
    Strategy:
    1. Sequential line processing (keep current approach).
    2. When encountering checkmark, find the option closest to it geometrically (by y0).
    3. This handles cases where checkmark is not directly after the option text.
    """
    questions: List[QuestionData] = []
    current_question_text: Optional[str] = None
    current_question_meta: Optional[LineData] = None
    current_options: List[OptionData] = []
    current_correct_label: Optional[str] = None
    last_option_index: int = -1
    seen_first_option: bool = False
    last_option_y0: Optional[float] = None

    i = 0
    while i < len(lines):
        line = lines[i]
        text = clean_text_noise(line.text).strip()
        lines_consumed = 1
        
        # Skip empty or noise lines
        if not text or FULL_NOISE_PATTERN.match(text) or is_lms_noise_line(text):
            i += lines_consumed
            continue
        
        # Skip LMS headers
        if LMS_QUESTION_PATTERN.match(text):
            i += lines_consumed
            continue
        
        # Check if this is a checkmark (correct answer indicator)
        if line.text.strip() == '\uf00c':
            # Find option closest to checkmark by geometric position (y0)
            if current_options:
                closest_option = None
                closest_distance = float('inf')
                
                for option in current_options:
                    distance = abs(line.y0 - option.y0)
                    if distance < closest_distance:
                        closest_distance = distance
                        closest_option = option
                
                # Mark the closest option as correct
                if closest_option:
                    closest_option.emphasized = True
                    current_correct_label = closest_option.label
            
            i += lines_consumed
            continue
        
        # Check for option line (a., b., c., d. or with text)
        option_match = match_option_line(text)
        standalone_option = is_option_label_only(text)
        
        if option_match or standalone_option:
            label = (option_match.group(1) if option_match else text[0]).upper()
            option_text = option_match.group(2).strip() if option_match else ""
            
            if label not in {"A", "B", "C", "D"}:
                i += lines_consumed
                continue
            
            seen_first_option = True
            
            # If no option text on same line, try to grab from next line
            if not option_text and i + 1 < len(lines):
                next_line = lines[i + 1]
                next_text = clean_text_noise(next_line.text).strip()
                if (next_text and 
                    not match_option_line(next_text) and 
                    not is_option_label_only(next_text) and 
                    not LMS_QUESTION_PATTERN.match(next_text) and 
                    not is_lms_noise_line(next_text) and
                    next_text != '\uf00c'):
                    option_text = next_text
                    lines_consumed = 2
            
            current_options.append(
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
            last_option_index = len(current_options) - 1
            last_option_y0 = line.y0
            
            # When we have 4 options, save the question
            if len(current_options) == 4:
                # Before saving, look ahead for checkmarks in the next few lines
                if not current_correct_label:  # Only if not already detected
                    for lookahead_idx in range(i + 1, min(i + 10, len(lines))):
                        lookahead_line = lines[lookahead_idx]
                        if lookahead_line.text.strip() == '\uf00c':
                            # Found a checkmark, match it to closest option
                            closest_option = None
                            closest_distance = float('inf')
                            
                            for option in current_options:
                                distance = abs(lookahead_line.y0 - option.y0)
                                if distance < closest_distance:
                                    closest_distance = distance
                                    closest_option = option
                            
                            if closest_option:
                                closest_option.emphasized = True
                                current_correct_label = closest_option.label
                            break
                        
                        # Stop if we hit a new question header
                        lookahead_text = clean_text_noise(lookahead_line.text).strip()
                        if LMS_QUESTION_PATTERN.match(lookahead_text):
                            break
                
                if current_question_text:
                    question = QuestionData(
                        question=current_question_text,
                        page_number=current_question_meta.page_number if current_question_meta else line.page_number,
                        x0=current_question_meta.x0 if current_question_meta else line.x0,
                        y0=current_question_meta.y0 if current_question_meta else line.y0,
                        options=order_options(current_options),
                        answer_label=current_correct_label,
                    )
                    finalize_answer(question)
                    questions.append(question)
                
                # Reset for next question
                current_question_text = None
                current_question_meta = None
                current_options = []
                current_correct_label = None
                last_option_index = -1
                last_option_y0 = None
                seen_first_option = False
            
            i += lines_consumed
            continue
        
        # If we haven't seen the first option yet, accumulate question text
        if not seen_first_option:
            current_question_text = text
            if current_question_meta is None:
                current_question_meta = line
        
        i += lines_consumed
    
    return deduplicate_questions(questions)


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


def preprocess_lms_lines(lines: List[LineData]) -> List[LineData]:
    """
    Preprocess LMS PDF lines:
    1. Remove noise lines (status, scores, timestamps, header info)
    2. Remove 'Câu h ỏ i N' headers
    3. Merge 'a.' alone with next line (which is the option content)
    4. Mark first option 'a.' so we know question text is before it
    """
    result: List[LineData] = []
    i = 0
    
    # Step 1: Filter out noise and headers first
    filtered: List[LineData] = []
    for line in lines:
        text = clean_text_noise(line.text).strip()
        
        # Skip empty lines
        if not text:
            continue
        
        # Skip noise lines
        if FULL_NOISE_PATTERN.match(text) or is_lms_noise_line(text):
            continue
        
        # Skip LMS question headers like 'Câu h ỏ i 1'
        if LMS_QUESTION_PATTERN.match(text):
            continue
        
        filtered.append(line)
    
    # Step 2: Merge "a." + content and detect question text
    i = 0
    option_label_order = []  # Track which labels we've seen in current question set
    
    while i < len(filtered):
        line = filtered[i]
        text = clean_text_noise(line.text).strip()
        
        # If this is an option label alone ('a.', 'b.', etc.)
        if LMS_OPTION_ALONE_PATTERN.match(text):
            label = text.rstrip(".").upper()
            
            # If this is 'a.', it's the start of a new question's options
            # Mark the previous line as question text ONLY if completing previous option set
            should_mark_previous = False
            if label == "A":
                # Mark previous line only if:
                # 1. This is first "a." (len == 0)
                # 2. OR just completed 4 options (len == 4)
                if len(option_label_order) == 0 or len(option_label_order) == 4:
                    should_mark_previous = True
            
            if should_mark_previous and i > 0 and result:
                prev_line = result[-1]
                prev_text = clean_text_noise(prev_line.text).strip()
                # Only mark if not already marked and not an option
                if (not prev_text.startswith("**Q**") and 
                    not is_option_label_only(prev_text)):
                    result[-1].text = f"**Q** {result[-1].text}"
            
            # Append label BEFORE resetting
            option_label_order.append(label)
            
            # Reset when completing a set (at end of "d.")
            if label == "D" and len(option_label_order) == 4:
                option_label_order = []
            
            # Check if next line exists and is content
            if i + 1 < len(filtered):
                next_line = filtered[i + 1]
                next_text = clean_text_noise(next_line.text).strip()
                
                # Only merge if next is NOT another label or question
                if (next_text and 
                    not is_option_label_only(next_text) and
                    not QUESTION_PATTERN.match(next_text)):
                    
                    # Merge: 'a. content'
                    merged_text = f"{text} {next_text}"
                    merged_line = LineData(
                        text=merged_text,
                        is_bold=line.is_bold,
                        color_int=line.color_int,
                        page_number=line.page_number,
                        x0=line.x0,
                        y0=line.y0,
                    )
                    result.append(merged_line)
                    i += 2  # Skip both lines (this label and its content)
                    continue
        
        # Regular line or label that couldn't be merged
        result.append(line)
        i += 1
    
    return result


def parse_questions(lines: List[LineData]) -> List[QuestionData]:
    if is_lms_format(lines):
        return parse_lms_questions(lines)

    # Preprocess LMS PDF format (merge "a." with content, skip "Câu h ỏ i N")
    lines = preprocess_lms_lines(lines)
    
    questions: List[QuestionData] = []
    current: Optional[QuestionData] = None

    for line in lines:
        text = clean_text_noise(line.text)
        if not text or FULL_NOISE_PATTERN.match(text):
            continue

        if HEADER_NOISE_PATTERN.match(text):
            continue

        # Check for marked question text (LMS format)
        is_marked_question = text.startswith("**Q**")
        if is_marked_question:
            text = text[4:].strip()  # Remove "**Q**" prefix

        if QUESTION_PATTERN.match(text) or is_marked_question:
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


        # Only create new question from text if it's a valid question (has pattern/marker)
        # Don't create from arbitrary text lines
        if current is None:
            # Silently skip non-question lines when no current question
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
    # First check if any option is already marked as emphasized (from checkmark)
    emphasized_labels = [opt.label for opt in question.options if opt.emphasized]
    if len(emphasized_labels) == 1:
        question.answer_label = emphasized_labels[0]
        return
    
    # Clear emphasized if multiple or none found
    if len(emphasized_labels) != 1:
        for opt in question.options:
            opt.emphasized = False
    
    # Fallback: check bold styling
    bold_labels = [opt.label for opt in question.options if opt.is_bold]
    if len(bold_labels) == 1:
        question.answer_label = bold_labels[0]
        for opt in question.options:
            opt.emphasized = opt.label == question.answer_label
        return

    # Fallback: check color
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
            
            # Format correct answer with bold
            if question.answer_label == option.label:
                ans_run.bold = True
                # Also apply color if original had different color
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

    from .validation import generate_validation_report_for_pdf

    validation_result = generate_validation_report_for_pdf(pdf_file, output_dir)
    return {
        "status": "ok",
        "pdf": pdf_file.name,
        "question_count": len(questions),
        "validation_report_file": validation_result.report_file,
        "validation_correct_count": validation_result.correct_count,
        "validation_wrong_count": validation_result.wrong_count,
        "validation_missed_count": validation_result.missed_count,
        "validation_title_issue_count": validation_result.title_issue_count,
        "validation_mismatch_count": validation_result.mismatch_count,
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

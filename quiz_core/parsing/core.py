import re
from typing import List, Optional
from .patterns import (
    UPPER_OPTION_PATTERN, LOWER_OPTION_PATTERN, 
    LMS_OPTION_ALONE_PATTERN, LMS_OPTION_WITH_TEXT_PATTERN,
    LMS_QUESTION_PATTERN, QUESTION_PATTERN, QUESTION_PREFIX_ONLY_PATTERN
)
from .utils import (
    _normalize_text, clean_text_noise, repair_fragmented_text, 
    is_lms_noise_line, order_options, normalize_question_text
)
from ..models import LineData, OptionData, QuestionData

def is_option_label_only(text: str) -> bool:
    return bool(LMS_OPTION_ALONE_PATTERN.match(text))

def match_option_line(text: str) -> Optional[re.Match[str]]:
    upper = UPPER_OPTION_PATTERN.match(text)
    if upper: return upper
    lower = LOWER_OPTION_PATTERN.match(text)
    if lower: return lower
    lms_with_text = LMS_OPTION_WITH_TEXT_PATTERN.match(text)
    if lms_with_text: return lms_with_text
    return None

def finalize_answer(question: QuestionData) -> None:
    if question.answer_label: return
    
    # Priority 1: Specifically emphasized (checkmarks, standalone labels)
    for opt in question.options:
        if opt.emphasized:
            question.answer_label = opt.label
            return
            
    # Priority 2: Bold options (fallback for many PDF exports)
    bold_options = [opt for opt in question.options if opt.is_bold]
    if len(bold_options) == 1:
        question.answer_label = bold_options[0].label
        bold_options[0].emphasized = True
        return
        
    # Priority 3: First option with different color (if any)
    colors = [opt.color_int for opt in question.options]
    if colors:
        from collections import Counter
        counts = Counter(colors)
        if len(counts) > 1:
            # If one color is rare (appears once), it's likely the answer
            rare_colors = [c for c, count in counts.items() if count == 1]
            if len(rare_colors) == 1:
                for opt in question.options:
                    if opt.color_int == rare_colors[0]:
                        question.answer_label = opt.label
                        opt.emphasized = True
                        return

    # Priority 4: Specific keywords in text
    for opt in question.options:
        t = opt.text.lower()
        if "(đúng)" in t or "(correct)" in t or "[đúng]" in t or "[correct]" in t:
            question.answer_label = opt.label
            opt.emphasized = True
            # Clean the keyword from the text
            opt.text = re.sub(r"\s*[\(\[]\s*(đúng|correct)\s*[\)\]]\s*", "", opt.text, flags=re.IGNORECASE).strip()
            return

    # Priority 5: Look for "Đáp án: A" or similar in the question text itself
    for opt in question.options:
        pattern = re.compile(r"(?:Đáp án|Answer|Key)\s*[:\-]?\s*" + opt.label + r"\b", re.IGNORECASE)
        if pattern.search(question.question):
            question.answer_label = opt.label
            opt.emphasized = True
            return

def deduplicate_questions(questions: List[QuestionData]) -> List[QuestionData]:
    seen = set()
    deduped = []
    for q in questions:
        key = _normalize_text(q.question).lower().strip()
        if key in seen: continue
        seen.add(key)
        deduped.append(q)
    return deduped

def parse_questions(lines: List[LineData]) -> List[QuestionData]:
    questions: List[QuestionData] = []
    current_question_text = None
    current_question_meta = None
    current_question_x0 = 0.0
    current_options: List[OptionData] = []
    current_correct_label = None
    
    seen_first_option = False
    last_option_index = -1
    
    i = 0
    while i < len(lines):
        line = lines[i]
        text = clean_text_noise(line.text)
        if not text or is_lms_noise_line(text):
            i += 1
            continue
            
        lines_consumed = 1
        
        # Detect standard or LMS question prefix
        is_q = (QUESTION_PATTERN.match(text) or 
                QUESTION_PREFIX_ONLY_PATTERN.match(text) or 
                LMS_QUESTION_PATTERN.match(text))
        
        # Heuristic: If we haven't seen options yet, be very conservative about starting a NEW question
        # unless it's a "strong" prefix. This avoids cutting off multi-line questions.
        should_start_new = False
        if is_q:
            # Check if it's "weak" (e.g. starts with a number like "1. ")
            # but note that QUESTION_PATTERN already includes strong prefixes like "Câu 1"
            is_weak = re.match(r"^\d+[\.:)]\s+", text)
            if not is_weak:
                should_start_new = True
            elif not current_question_text or seen_first_option:
                should_start_new = True

        if should_start_new:
            # End previous question
            if current_question_text:
                # Validation: Only add if it looks like a real question
                is_header = any(x in current_question_text.lower() for x in ["nội dung câu hỏi", "lựa chọn", "đáp án đúng"])
                has_prefix = (QUESTION_PATTERN.match(current_question_text) or 
                             QUESTION_PREFIX_ONLY_PATTERN.match(current_question_text) or
                             LMS_QUESTION_PATTERN.match(current_question_text))
                
                if (has_prefix or len(current_question_text) > 30) and not is_header:
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
            
            seen_first_option = False
            current_question_text = text
            current_question_meta = line
            current_question_x0 = line.x0
            current_options = []
            current_correct_label = None
            last_option_index = -1
            i += lines_consumed
            continue

        if line.text.strip() in {'\uf00c', '✓', '✔', '☑', '☒'}:
            if current_options:
                closest_option = None
                closest_distance = float('inf')
                for option in current_options:
                    distance = abs(line.y0 - option.y0)
                    if distance < closest_distance:
                        closest_distance = distance
                        closest_option = option
                if closest_option:
                    closest_option.emphasized = True
                    current_correct_label = closest_option.label
            i += lines_consumed
            continue

        option_match = match_option_line(text)
        standalone_option = is_option_label_only(text)
        
        if option_match or standalone_option:
            label = (option_match.group(1) if option_match else text[0]).upper()
            option_text = option_match.group(2).strip() if option_match else ""
            if label not in {"A", "B", "C", "D", "E"}:
                i += lines_consumed
                continue
            
            seen_first_option = True
            
            if not option_text:
                # Persistent lookahead: check up to 2 lines ahead
                for offset in range(1, 3):
                    if i + offset < len(lines):
                        next_line = lines[i + offset]
                        next_text = clean_text_noise(next_line.text).strip()
                        
                        # If next_text is a valid option text (not a new question or noise)
                        if (next_text and 
                            not match_option_line(next_text) and 
                            not is_option_label_only(next_text) and 
                            not LMS_QUESTION_PATTERN.match(next_text) and 
                            not QUESTION_PATTERN.match(next_text) and
                            not QUESTION_PREFIX_ONLY_PATTERN.match(next_text) and
                            not is_lms_noise_line(next_text) and
                            next_text != '\uf00c' and
                            not re.match(r"^[A-E]$", next_text)):
                            
                            option_text = next_text
                            lines_consumed = offset + 1
                            break
            
            current_options.append(
                OptionData(
                    label=label,
                    text=repair_fragmented_text(option_text),
                    emphasized=(label == current_correct_label),
                    is_bold=line.is_bold or (lines_consumed == 2 and lines[i + 1].is_bold),
                    color_int=line.color_int,
                    page_number=line.page_number,
                    x0=line.x0,
                    y0=line.y0,
                )
            )
            last_option_index = len(current_options) - 1
            
            if len(current_options) >= 4:
                is_last_option = True
                if i + lines_consumed < len(lines):
                    next_idx = i + lines_consumed
                    next_line_text = clean_text_noise(lines[next_idx].text).strip()
                    if match_option_line(next_line_text) or is_option_label_only(next_line_text):
                        next_label = (match_option_line(next_line_text).group(1) if match_option_line(next_line_text) else next_line_text[0]).upper()
                        if next_label == 'E' and len(current_options) == 4:
                            is_last_option = False
                
                if is_last_option:
                    if not current_correct_label:
                        for lookahead_idx in range(i + lines_consumed, min(i + lines_consumed + 10, len(lines))):
                            lookahead_line = lines[lookahead_idx]
                            lookahead_text = clean_text_noise(lookahead_line.text).strip()
                            if lookahead_line.text.strip() == '\uf00c':
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
                            if re.match(r"^[A-E]$", lookahead_text):
                                current_correct_label = lookahead_text
                                for opt in current_options:
                                    if opt.label == current_correct_label: opt.emphasized = True
                                break
                            if LMS_QUESTION_PATTERN.match(lookahead_text) or QUESTION_PATTERN.match(lookahead_text) or QUESTION_PREFIX_ONLY_PATTERN.match(lookahead_text):
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
                    
                    current_question_text = None
                    current_question_meta = None
                    current_options = []
                    current_correct_label = None
                    last_option_index = -1
                    seen_first_option = False
            
            i += lines_consumed
            continue
        
        # STANDALONE ANSWER LABEL (e.g., "C" on a new line or floating at the end)
        is_floating_label = re.match(r"^[A-E]\s*$", text.upper())
        if seen_first_option and is_floating_label and not current_correct_label:
            current_correct_label = text.upper().strip()
            # Mark the corresponding option as emphasized
            for opt in current_options:
                if opt.label == current_correct_label:
                    opt.emphasized = True
            i += lines_consumed
            continue

        if seen_first_option and last_option_index >= 0:
            # 1. Aligns with the original question's X-coordinate (left-aligned)
            # 2. Starts with Uppercase
            # 3. AND is NOT a small floating label
            question_keywords = ["đâu là", "phát biểu nào", "vì sao", "khi nào", "tại sao", "một", "đặc điểm", "ưu điểm", "nhược điểm", "tcp", "ip", "giao thức", "bộ định tuyến", "tính bí mật", "các phân loại"]
            is_keyword_start = any(text.lower().startswith(kw) for kw in question_keywords)
            
            # Allow some tolerance for X-alignment (e.g. 5 pixels)
            is_aligned = abs(line.x0 - current_question_x0) < 5
            
            if len(current_options) >= 3 and (is_aligned and text[0].isupper() or is_keyword_start) and len(text) > 20 and not is_option_label_only(text):
                # Start new question loop manually
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
                
                seen_first_option = False
                current_question_text = text
                current_question_meta = line
                current_question_x0 = line.x0
                current_options = []
                current_correct_label = None
                last_option_index = -1
                i += lines_consumed
                continue

            current_options[last_option_index].text += " " + text
            if line.is_bold:
                current_options[last_option_index].is_bold = True
            # Update color if the new span has a non-black color and the option didn't have one yet
            if line.color_int != 0 and current_options[last_option_index].color_int == 0:
                current_options[last_option_index].color_int = line.color_int
            i += lines_consumed
            continue

        if not seen_first_option:
            if current_question_text:
                current_question_text += " " + text
            else:
                current_question_text = text
            if current_question_meta is None:
                current_question_meta = line
        
        i += lines_consumed
    
    if current_question_text:
        question = QuestionData(
            question=current_question_text,
            page_number=current_question_meta.page_number if current_question_meta else lines[-1].page_number if lines else 1,
            x0=current_question_meta.x0 if current_question_meta else 0,
            y0=current_question_meta.y0 if current_question_meta else 0,
            options=order_options(current_options),
            answer_label=current_correct_label,
        )
        finalize_answer(question)
        questions.append(question)
    
    questions = deduplicate_questions(questions)
    
    # Auto-indexing and Cleaning
    final_questions = []
    current_idx = 1
    for q in questions:
        # Clean text again to remove all fragments
        q.question = normalize_question_text(q.question)
        
        # Validation: If question is too short or just a number, it's likely a page number (Image 3)
        if len(q.question) < 5 or q.question.isdigit():
            continue
            
        # Always use a consistent "Câu X: " prefix
        q.question = f"Câu {current_idx}: {q.question}"
        final_questions.append(q)
        current_idx += 1

    return final_questions

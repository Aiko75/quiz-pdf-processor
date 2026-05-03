import re
import unicodedata
from typing import List, Optional, Any
from .patterns import INLINE_NOISE_PATTERN
from ..models import OptionData

def _normalize_text(text: str) -> str:
    return unicodedata.normalize('NFC', text)

def clean_text_noise(text: str) -> str:
    text = INLINE_NOISE_PATTERN.sub("", text)
    return text.strip()

def repair_fragmented_text(text: str) -> str:
    if not text: return ""
    text = _normalize_text(text)
    parts = text.split()
    rebuilt = []
    for p in parts:
        if len(p) == 1 and p.isalpha() and rebuilt and len(rebuilt[-1]) == 1:
            rebuilt[-1] += p
        else:
            rebuilt.append(p)
    return " ".join(rebuilt)

def is_lms_noise_line(text: str) -> bool:
    if text.strip() == '\uf00c':
        return False
    text = _normalize_text(text)
    text_lower = text.lower().strip()
    if not text_lower:
        return True
    if len(text_lower) < 2 and text_lower not in {"a", "b", "c", "d", "e"}:
        return True
    
    # Check against global patterns
    from .patterns import FULL_NOISE_PATTERN
    if FULL_NOISE_PATTERN.match(text):
        return True
        
    exact_noise = [_normalize_text(x) for x in ["đúng", "sai", "trạng thái", "thời gian thực", "thời gian", "đạt điểm", "đã đạt"]]
    for en in exact_noise:
        if en in text_lower: return True

    if re.match(r"^\d+\s+(phút|giây|tiếng|ngày|tuần).*", text_lower):
        return True
    if re.match(r"^\d+/\d+\s*$", text_lower):
        return True
    if re.match(r"^\d+/\d+/\d+,?\s*\d+:\d+\s*[AP]M", text):
        return True
        
    lms_headers = [_normalize_text(x) for x in [
        "bảng điều khiển", "chapter", "week", "bắt đầu vào", "kết thúc lúc", 
        "khoá học của tôi", "moodle", "copyright", "developed by", "get the mobile app",
        "mail :", "@neu.edu.vn", "info cổng thông tin", "phone :", "( 100 % )",
        "studocu", "studeersnel", "is not sponsored", "scan to open", "trắc nghiệm lms",
        "đại học kinh tế quốc dân", "tổng điểm", "xem lại", "điểm của"
    ]]
    for header in lms_headers:
        if header in text_lower:
            return True
    return False

def order_options(options: List[OptionData]) -> List[OptionData]:
    expected = ["A", "B", "C", "D", "E"]
    mapping = {option.label: option for option in options}
    result = []
    for label in expected:
        if label in mapping:
            result.append(mapping[label])
    return result if result else options

def normalize_question_text(text: str) -> str:
    if not text: return ""
    text = _normalize_text(text)
    
    # 1. Strip giant LMS noise blocks (Head noise)
    noise_markers = [
        r"studocu\s+is\s+not\s+sponsored",
        r"scan\s+to\s+open",
        r"đại\s+học\s+kinh\s+tế\s+quốc\s+dân",
        r"trắc\s+nghiệm\s+lms",
        r"mạng\s+máy\s+tính\s+và\s+truyền\s+số\s+liệu",
        r"lttn\s*1\s*\(tuần\s*1\)",
        r"chương\s*1\s*:",
        r"bảng\s+điều\s+khiển",
        r"khoá\s+học\s+của\s+tôi",
        r"moodle",
        r"xem\s+lại\s+lần\s+làm\s+thử",
        r"đạt\s+điểm",
        r"tiht1122",
        r"@neu\.edu\.vn"
    ]
    for marker in noise_markers:
        # Strip everything that looks like a header block containing the marker
        if re.search(marker, text, re.IGNORECASE):
            text = re.sub(r"^.*?" + marker + r".*?(?:Câu\s*h\s*ỏ\s*i\s*|Câu\s*h\s*|Question\s*|$)", "", text, flags=re.IGNORECASE | re.DOTALL).strip()

    # 2. Repeatedly strip prefixes and interleaved numbers/fragments at the START
    while True:
        old_len = len(text)
        # Strip standard prefixes: "Câu 1:", "1.", etc.
        text = re.sub(r"^(?:Câu\s*\d+[\.:\)]?|Question\s*\d+[\.:\)]?|\d+[\.:)])\s*", "", text, flags=re.IGNORECASE).strip()
        # Strip LMS fragments: "Câu h", "Câu h ỏ i", and any numbers between them
        text = re.sub(r"^(?:\d+\s+)?(?:Câu\s*h\s*ỏ\s*i\s*|Câu\s*h\s*|Question\s*)\d*\s*", "", text, flags=re.IGNORECASE).strip()
        if len(text) == old_len:
            break
            
    return text

def extract_logical_index(text: str) -> Optional[int]:
    if not text: return None
    # Standard prefix: "Câu 123" or "Question 123"
    match = re.search(r"^(?:Câu|Question)\s*(\d+)", text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    # Weak prefix: "123." or "123)"
    match = re.search(r"^(\d+)[\.:)]", text)
    if match:
        return int(match.group(1))
    return None

def normalize_question_key(text: str) -> str:
    text = normalize_question_text(text)
    return re.sub(r"[^a-zA-Z0-9\u00C0-\u1EF9]", "", text).lower()

def pick_single_label(labels: Any) -> Optional[str]:
    if not labels: return None
    valid = sorted([str(l).upper() for l in labels if str(l).upper() in {"A", "B", "C", "D", "E"}])
    return valid[0] if len(valid) == 1 else None

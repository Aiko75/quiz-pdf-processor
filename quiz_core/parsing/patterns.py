import re

# Standard quiz PDF pattern: "Câu 1: Text" or "Câu 1. Text" or "1. Text"
QUESTION_PATTERN = re.compile(
    r"^(?:Câu\s*h\s*ỏ\s*i\s*\d+|Câu\s*\d+[\.:)]?|Question\s*\d+[\.:)]?|\d+[\.:)]|Điểm\s+khác\s+biệt)(?:\s+|$)",
    re.IGNORECASE,
)
# Standalone prefix: "Câu 1" or "Question 1" on its own line
QUESTION_PREFIX_ONLY_PATTERN = re.compile(
    r"^(?:Câu\s*\d+[\.:)]?|Question\s*\d+[\.:)]?|\d+[\.:)])\s*$",
    re.IGNORECASE,
)
# LMS PDF pattern: "Câu h ỏ i 1"
LMS_QUESTION_PATTERN = re.compile(
    r"^(?:Câu\s*h\s*ỏ\s*i\s*|Câu\s*h\s*|Question\s*)\d+",
    re.IGNORECASE,
)

UPPER_OPTION_PATTERN = re.compile(r"^([A-E])(?:[\.:\)\-]\s*|\s+)(.+)$")
LOWER_OPTION_PATTERN = re.compile(r"^([a-e])[\.:\)\-]\s*(.+)$")
# LMS options: "a." alone or with text  
LMS_OPTION_ALONE_PATTERN = re.compile(r"^([a-eA-E])\.\s*$")
LMS_OPTION_WITH_TEXT_PATTERN = re.compile(r"^([a-eA-E])\.\s+(.+)$")

HEADER_NOISE_PATTERN = re.compile(r"^(Chương\s*\d+\s*:|LTTN\s*\d+\s*:?)$", re.IGNORECASE)
INLINE_NOISE_PATTERN = re.compile(
    r"(Downloaded\s+by|binhprodotcom@gmail\.com|l[O0]M[oO]ARcPSD\|?\d*).*$",
    re.IGNORECASE,
)
FULL_NOISE_PATTERN = re.compile(
    r"^(Downloaded\s+by.*|\s*\d+\s*/\s*\d+\s*|\s*Trang\s*\d+\s*|https?://.*|\d{1,2}/\d{1,2}/\d{2,4},.*|.*Xem lại lần làm thử.*)$",
    re.IGNORECASE,
)

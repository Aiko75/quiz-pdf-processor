import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import fitz
from quiz_core.parsing.pdf_parser import extract_styled_lines

pdf_path = Path(r"d:\My_projects\Random_Essential\Quiz_Processor\docs\test\trac-nghiem-1-chu-nghia-xa-hoi-khoa-hoc-cnxhkh.pdf")
lines = extract_styled_lines(pdf_path)

noise_lines = set()
for line in lines:
    t = line.text.strip()
    if "messages." in t or "studocu" in t.lower() or "lomoarcpsd" in t.lower():
        noise_lines.add(t)

print("Unique noise lines found:")
for nl in sorted(noise_lines):
    print(repr(nl))

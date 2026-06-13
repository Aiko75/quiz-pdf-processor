import fitz
from pathlib import Path

pdf_path = Path("docs/test/trac-nghiem-1-chu-nghia-xa-hoi-khoa-hoc-cnxhkh.pdf")
doc = fitz.open(pdf_path)

page = doc[6] # Page 7
print("=== DUMPING PAGE 7 ===")
text_instances = page.get_text("blocks")
text_instances.sort(key=lambda b: (round(b[1], 1), round(b[0], 1)))
for b in text_instances:
    print(f"[{round(b[0], 1)}, {round(b[1], 1)}]: {repr(b[4].strip())}")

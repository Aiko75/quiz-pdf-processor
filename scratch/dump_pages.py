import fitz
from pathlib import Path

pdf_path = Path("docs/test/trac-nghiem-1-chu-nghia-xa-hoi-khoa-hoc-cnxhkh.pdf")
doc = fitz.open(pdf_path)

pages = [7, 10, 11, 12]

print("=== DUMPING PDF PAGES ===")
for p_num in pages:
    page = doc[p_num - 1]
    print(f"\n=================== PAGE {p_num} ===================")
    # Get text with positions
    text_instances = page.get_text("blocks")
    # Sort blocks by y coordinate, then x coordinate
    text_instances.sort(key=lambda b: (round(b[1], 1), round(b[0], 1)))
    for b in text_instances:
        print(f"[{round(b[0], 1)}, {round(b[1], 1)}]: {repr(b[4].strip())}")

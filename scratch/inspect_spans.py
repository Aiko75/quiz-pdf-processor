import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import fitz

pdf_path = Path(r"d:\My_projects\Random_Essential\Quiz_Processor\docs\test\trac-nghiem-1-chu-nghia-xa-hoi-khoa-hoc-cnxhkh.pdf")
doc = fitz.open(pdf_path)

page = doc[1]  # Page 2 (0-indexed is Page 1, so doc[1] is Page 2)
drawings = page.get_drawings()
print("Page 2 Drawings:")
for idx, d in enumerate(drawings):
    print(f"Drawing {idx}: rect={d['rect']}, fill={d.get('fill')}, color={d.get('color')}, type={d['type']}")

print("\nPage 2 Spans:")
page_dict = page.get_text("dict")
for block in page_dict.get("blocks", []):
    if block.get("type") != 0: continue
    for line in block.get("lines", []):
        for span in line.get("spans", []):
            text = span.get("text", "")
            bbox = span.get("bbox", (0, 0, 0, 0))
            # Check if this span intersects with any drawing rect
            intersecting_drawings = []
            for d_idx, d in enumerate(drawings):
                # Simple intersection test between bbox and d['rect']
                r1 = fitz.Rect(bbox)
                r2 = fitz.Rect(d['rect'])
                if r1.intersects(r2):
                    intersecting_drawings.append(d_idx)
            if intersecting_drawings:
                print(f"Span text={repr(text)}, bbox={bbox}, intersects drawings={intersecting_drawings}")

doc.close()

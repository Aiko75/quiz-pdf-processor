import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import fitz

pdf_path = Path(r"d:\My_projects\Random_Essential\Quiz_Processor\docs\test\trac-nghiem-1-chu-nghia-xa-hoi-khoa-hoc-cnxhkh.pdf")
doc = fitz.open(pdf_path)

print(f"Number of pages: {len(doc)}")
for i, page in enumerate(doc):
    annots = list(page.annots())
    drawings = page.get_drawings()
    print(f"Page {i+1}: annotations count = {len(annots)}, drawings count = {len(drawings)}")
    if annots:
        for idx, annot in enumerate(annots[:3]):
            print(f"  Annot {idx}: type={annot.type}, rect={annot.rect}, colors={annot.colors}")
    if drawings:
        for idx, draw in enumerate(drawings[:3]):
            print(f"  Drawing {idx}: type={draw['type']}, rect={draw['rect']}")
doc.close()

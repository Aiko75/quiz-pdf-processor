import docx
from pathlib import Path

doc_path = Path("docs/test/trac-nghiem-1-chu-nghia-xa-hoi-khoa-hoc-cnxhkh_co_dap_an.docx")
doc = docx.Document(doc_path)

indices = [221, 222, 223, 224, 233, 234, 235, 236, 346, 347, 348, 399, 400, 451, 452, 453]

print("=== RUNS INSPECTION ===")
for idx in indices:
    p = doc.paragraphs[idx]
    print(f"\nParagraph [{idx}]: text={repr(p.text)}")
    for r_idx, r in enumerate(p.runs):
        print(f"  Run {r_idx}: text={repr(r.text)}, bold={r.bold}, italic={r.italic}, highlight={r.font.highlight_color}, color={r.font.color.rgb if r.font.color else None}")

import docx
from pathlib import Path

docx_path = Path(r"d:\My_projects\Random_Essential\Quiz_Processor\docs\test\trac-nghiem-1-chu-nghia-xa-hoi-khoa-hoc-cnxhkh_co_dap_an.docx")
doc = docx.Document(docx_path)

print(f"Total paragraphs: {len(doc.paragraphs)}")
for idx, p in enumerate(doc.paragraphs[:100]):
    text = p.text.strip()
    if text:
        # Check if highlighted or bold
        is_bold = any(run.bold for run in p.runs)
        is_highlight = any(run.font.highlight_color is not None for run in p.runs)
        print(f"Para {idx}: {repr(text)} (bold={is_bold}, highlight={is_highlight})")

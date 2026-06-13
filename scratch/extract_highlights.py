import fitz
from pathlib import Path

pdf_path = Path("docs/test/trac-nghiem-1-chu-nghia-xa-hoi-khoa-hoc-cnxhkh.pdf")
doc = fitz.open(pdf_path)

q_nums = [38, 40, 59, 68, 77]

for q in q_nums:
    print(f"\n--- Question {q} Highlights ---")
    for page_idx, page in enumerate(doc, start=1):
        # Find drawings (highlights) on the page
        drawings = page.get_drawings()
        highlights = [d["rect"] for d in drawings if d.get("type") in ("f", "fs") and d.get("fill") is not None and sum(d["fill"]) > 1.2]
        
        # Standard annotations
        annots = page.annots()
        if annots:
            for annot in annots:
                if annot.type[0] in (8, 9, 10, 11):
                    highlights.append(annot.rect)
                    
        # Extract spans with their styles
        page_dict = page.get_text("dict")
        for block in page_dict.get("blocks", []):
            if block.get("type") != 0: continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "")
                    if not text.strip(): continue
                    
                    # Check if it intersects with any highlight
                    span_rect = fitz.Rect(span.get("bbox"))
                    is_h = False
                    for r in highlights:
                        if span_rect.intersects(r):
                            intersect_rect = span_rect & r
                            if intersect_rect.get_area() > 0.2 * span_rect.get_area():
                                is_h = True
                                break
                    
                    if is_h:
                        print(f"Page {page_idx} [H]: {repr(text)}")
                    elif "bold" in span.get("font", "").lower():
                        print(f"Page {page_idx} [B]: {repr(text)}")

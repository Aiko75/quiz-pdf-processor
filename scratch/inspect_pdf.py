import fitz
from pathlib import Path

pdf_path = Path("docs/test/trac-nghiem-1-chu-nghia-xa-hoi-khoa-hoc-cnxhkh.pdf")
doc = fitz.open(pdf_path)

keywords = [
    "Thời đại hiện nay có mấy giai đoạn chính?",
    "Nguyên nhân nào dẫn đến sự sụp đổ của CNXH ở Liên Xô và Đông Âu:",
    "Vô sản tất cả các nước và các dân tộc bị áp bức, đoàn kết lại",
    "thế giới quan duy vật Mácxít và thế giới quan tôn giáo là đối lập nhau",
    "Những tư tưởng thống trị của một thời đại bao giờ cũng chỉ là tư tưởng"
]

print("=== SEARCHING PDF FOR TARGET QUESTIONS ===")
for page_idx, page in enumerate(doc, start=1):
    text = page.get_text()
    for kw in keywords:
        if kw.lower() in text.lower():
            print(f"\n--- Page {page_idx} contains: '{kw}' ---")
            
            # Print page lines or blocks with styling info
            blocks = page.get_text("blocks")
            for block in blocks:
                b_text = block[4].strip()
                if any(kw.lower() in line.lower() for line in b_text.splitlines() for kw in keywords):
                    print("Block text:")
                    print(b_text)
                    print("-" * 40)

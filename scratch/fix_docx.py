"""
fix_docx_v2.py
==============
Sửa đổi tệp DOCX nguồn dựa trên dữ liệu đối chiếu từ PDF gốc.
Version 2: Tìm kiếm paragraph theo NỘI DUNG thay vì index cứng để tránh
lỗi dịch chuyển index khi insert/delete.

Dữ liệu đối chiếu từ PDF (đã xác minh):
  - Câu 38: A=3, B=4(H), C=5, D=6
  - Câu 40: A=Cả ba đáp án trên(H), B=..sai lầm.., C=..quan niệm.., D=..chống phá..
  - Câu 59: A=C.Mác, B=C.Mác & Ph.Ăng ghen, C=Hồ Chí Minh, D=V.I Lênin(H)
  - Câu 68: A=Sai, B=Đúng(H)
  - Câu 77: A=C.Mác, B=C.Mác & Ph.Ăng ghen(H), C=Ph.Ăng ghen, D=V.I Lênin.
  - Câu 81: messages.downloaded_by -> XÓA

(H) = đáp án đúng được highlight vàng
"""

import docx
from pathlib import Path
from docx.shared import Pt
from docx.enum.text import WD_COLOR_INDEX
import copy

DOCX_PATH = Path("docs/test/trac-nghiem-1-chu-nghia-xa-hoi-khoa-hoc-cnxhkh_co_dap_an.docx")

# =====================================================================
# Dữ liệu sửa đổi theo câu hỏi
# Mỗi câu: anchor_text (phần đầu câu hỏi để định vị), rồi danh sách đáp án
# =====================================================================
QUESTION_FIXES = [
    {
        "question_anchor": "Câu 38:",  # Tìm câu hỏi này
        "options": [
            # (option_label_prefix, new_full_text, is_correct)
            ("A. ", "A. 3", False),
            ("B. ", "B. 4", True),
            ("C. ", "C. 5", False),
            ("D. ", "D. 6", False),
        ],
        "insert_after": None  # Không cần insert thêm
    },
    {
        "question_anchor": "Câu 40:",
        "options": [
            ("A. Cả ba đáp án trên", "A. Cả ba đáp án trên", True),  # Already has text but need highlight
            ("B. ", "B. Những sai lầm của Đảng và của những người lãnh đạo cấp cao nhất Đảng Cộng sản Liên Xô.", False),
            ("C. ", "C. Quan niệm và vận dụng không đúng đắn về CNXH", False),
            # D already has full text "D. Sự chống phá..." -> keep
        ],
        "insert_after": None
    },
    {
        "question_anchor": "Câu 59:",
        "options": [
            ("A. ", "A. C.Mác", False),
            ("B. ", "B. C.Mác & Ph.Ăng ghen", False),
            # The existing "C. Mác & Ph.Ăng ghen" in DOCX is actually the B answer misplaced
            # We will rename it to C. Hồ Chí Minh
            ("C. M", "C. Hồ Chí Minh", False),
        ],
        "insert_after": {
            "after_anchor": "C. Hồ Chí Minh",
            "new_text": "D. V.I Lênin",
            "is_correct": True
        }
    },
    {
        "question_anchor": "Câu 68:",
        "options": [
            ("A. ", "A. Sai", False),
            ("B. ", "B. Đúng", True),
        ],
        "insert_after": None
    },
    {
        "question_anchor": "Câu 77:",
        "options": [
            ("A. ", "A. C.Mác", False),
            ("B. ", "B. C.Mác & Ph.Ăng ghen", True),
            # The existing "C. Mác & Ph.Ăng ghen" is misplaced B content
            ("C. M", "C. Ph.Ăng ghen", False),
        ],
        "insert_after": {
            "after_anchor": "C. Ph.Ăng ghen",
            "new_text": "D. V.I Lênin.",
            "is_correct": False
        }
    }
]

WATERMARK_ANCHOR = "Câu 81: messages"


def find_paragraph_index(doc, text_starts_with: str, start_from: int = 0) -> int:
    """Tìm index paragraph có text bắt đầu bằng text_starts_with."""
    for i in range(start_from, len(doc.paragraphs)):
        t = doc.paragraphs[i].text.strip()
        if t.startswith(text_starts_with):
            return i
    return -1


def set_paragraph_text(para, text: str, is_correct: bool):
    """Xóa runs cũ, thêm run mới với text và highlight."""
    p = para._p
    ns = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'

    for r in p.findall(f'{{{ns}}}r'):
        p.remove(r)
    for hl in p.findall(f'{{{ns}}}hyperlink'):
        p.remove(hl)

    run = para.add_run(text)
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)
    if is_correct:
        run.font.highlight_color = WD_COLOR_INDEX.YELLOW

    print(f"    [SET] '{text}' | highlight={is_correct}")


def insert_paragraph_after(doc, ref_para, text: str, is_correct: bool):
    """Chèn paragraph mới ngay sau ref_para."""
    ref_p = ref_para._p
    new_p = copy.deepcopy(ref_p)

    ns = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
    for r in new_p.findall(f'{{{ns}}}r'):
        new_p.remove(r)
    for hl in new_p.findall(f'{{{ns}}}hyperlink'):
        new_p.remove(hl)

    ref_p.addnext(new_p)

    # Tìm paragraph object mới
    new_para = None
    for para in doc.paragraphs:
        if para._p is new_p:
            new_para = para
            break

    if new_para:
        run = new_para.add_run(text)
        run.font.name = "Times New Roman"
        run.font.size = Pt(12)
        if is_correct:
            run.font.highlight_color = WD_COLOR_INDEX.YELLOW
        print(f"    [INSERT] '{text}' | highlight={is_correct}")
    else:
        print(f"    [ERROR] Không thể chèn paragraph mới")


def delete_paragraph(para):
    """Xóa paragraph."""
    text_preview = para.text[:80]
    p = para._p
    p.getparent().remove(p)
    print(f"    [DELETE] '{text_preview}'")


def main():
    print(f"[LOAD] {DOCX_PATH}")
    doc = docx.Document(DOCX_PATH)
    print(f"[INFO] Tổng số paragraph: {len(doc.paragraphs)}")

    # === BƯỚC 1: Xử lý từng câu hỏi ===
    for fix in QUESTION_FIXES:
        anchor = fix["question_anchor"]
        q_idx = find_paragraph_index(doc, anchor)

        if q_idx == -1:
            print(f"\n[SKIP] Không tìm thấy: '{anchor}'")
            continue

        print(f"\n[QUESTION] Câu tìm thấy tại [{q_idx}]: {doc.paragraphs[q_idx].text.strip()[:60]}")

        # Tìm và sửa từng đáp án trong vùng sau câu hỏi (tối đa 10 paragraph)
        for option_prefix, new_text, is_correct in fix["options"]:
            found = False
            for search_idx in range(q_idx + 1, min(q_idx + 12, len(doc.paragraphs))):
                p_text = doc.paragraphs[search_idx].text.strip()
                # Dừng nếu gặp câu hỏi tiếp theo
                if p_text and (p_text.startswith("Câu ") and ":" in p_text[:10]):
                    break
                if p_text.startswith(option_prefix):
                    set_paragraph_text(doc.paragraphs[search_idx], new_text, is_correct)
                    found = True
                    break
            if not found:
                print(f"    [NOT FOUND] Đáp án với prefix: '{option_prefix}'")

        # Insert thêm đáp án mới nếu cần
        if fix["insert_after"]:
            ins = fix["insert_after"]
            ins_anchor = ins["after_anchor"]
            ins_text = ins["new_text"]
            ins_correct = ins["is_correct"]

            ref_idx = find_paragraph_index(doc, ins_anchor, q_idx + 1)
            if ref_idx == -1:
                print(f"    [INSERT-SKIP] Không tìm thấy anchor để chèn: '{ins_anchor}'")
            else:
                # Check if D already exists after this
                next_texts = [doc.paragraphs[i].text.strip() for i in range(ref_idx + 1, min(ref_idx + 3, len(doc.paragraphs)))]
                if any(t.startswith("D. ") for t in next_texts):
                    # Already has D, update it instead
                    for i in range(ref_idx + 1, min(ref_idx + 3, len(doc.paragraphs))):
                        if doc.paragraphs[i].text.strip().startswith("D. "):
                            set_paragraph_text(doc.paragraphs[i], ins_text, ins_correct)
                            break
                else:
                    insert_paragraph_after(doc, doc.paragraphs[ref_idx], ins_text, ins_correct)

    # === BƯỚC 2: Xóa watermark Câu 81 ===
    print(f"\n[WATERMARK] Tìm và xóa câu nhiễu '{WATERMARK_ANCHOR}'...")
    wm_idx = find_paragraph_index(doc, WATERMARK_ANCHOR)
    if wm_idx != -1:
        delete_paragraph(doc.paragraphs[wm_idx])
    else:
        print(f"    [NOT FOUND] Không tìm thấy watermark (có thể đã được xóa)")

    # === BƯỚC 3: Kiểm tra kết quả ===
    print(f"\n=== KIỂM TRA SAU KHI SỬA ===")
    target_anchors = ["Câu 38:", "Câu 40:", "Câu 59:", "Câu 68:", "Câu 77:", "Câu 81:"]
    for anchor in target_anchors:
        idx = find_paragraph_index(doc, anchor)
        if idx == -1:
            print(f"\n  [{anchor}] Không tìm thấy (có thể đã bị xóa hoặc không tồn tại)")
            continue
        print(f"\n  [{idx}] {doc.paragraphs[idx].text.strip()[:70]}")
        for j in range(idx + 1, min(idx + 8, len(doc.paragraphs))):
            pt = doc.paragraphs[j].text.strip()
            if not pt:
                continue
            if pt.startswith("Câu ") and ":" in pt[:12]:
                break
            highlighted = any(r.font.highlight_color is not None for r in doc.paragraphs[j].runs)
            print(f"       [{j}] {'✓(H)' if highlighted else '    '} {pt}")

    # === BƯỚC 4: Lưu file ===
    doc.save(DOCX_PATH)
    print(f"\n[OK] Đã lưu: {DOCX_PATH}")


if __name__ == "__main__":
    main()

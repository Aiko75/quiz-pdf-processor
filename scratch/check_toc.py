import docx

def process_toc_paragraph(p, toc_replacements):
    p_xml = p._p
    r_elements = p_xml.xpath('.//w:r')
    
    text_runs = []
    for idx, r_xml in enumerate(r_elements):
        if r_xml.xpath('.//w:tab'):
            break
        text_runs.append(r_xml)
        
    if not text_runs:
        return None
        
    combined_text = "".join(docx.text.run.Run(r, p).text for r in text_runs)
    
    new_text = combined_text
    changed = False
    for old_val, new_val in toc_replacements:
        if old_val in new_text:
            new_text = new_text.replace(old_val, new_val)
            changed = True
            
    if changed:
        docx.text.run.Run(text_runs[0], p).text = new_text
        for r in text_runs[1:]:
            docx.text.run.Run(r, p).text = ""
        return new_text
    return None

def test_check_toc():
    doc = docx.Document("docs/de_an/BaoCaoDeAn_NguyenNgocVuong.docx")
    from docx.oxml.ns import nsmap
    
    body_element = doc.element.body
    sdts = body_element.xpath('.//w:sdt')
    sdt = sdts[0]
    sdt_paras = sdt.xpath('.//w:p', namespaces=nsmap)
    
    toc_replacements = [
        ("Cơ chế renderer dùng chung cùng chatbotAI tích hợp", "Cơ chế tự động kiểm tra mẫu đề (Auto-Sample Check)"),
    ]
    
    p_xml = sdt_paras[22]
    p = docx.text.paragraph.Paragraph(p_xml, doc)
    
    # Print before
    r_elements = p_xml.xpath('.//w:r')
    print("Before processing:")
    for idx, r_xml in enumerate(r_elements):
        run = docx.text.run.Run(r_xml, p)
        print(f"  Run [{idx}]: \"{run.text}\"")
        
    res = process_toc_paragraph(p, toc_replacements)
    print("After processing result:", res)
    
    # Print after
    r_elements = p_xml.xpath('.//w:r')
    print("After processing runs:")
    for idx, r_xml in enumerate(r_elements):
        run = docx.text.run.Run(r_xml, p)
        print(f"  Run [{idx}]: \"{run.text}\"")

if __name__ == "__main__":
    test_check_toc()



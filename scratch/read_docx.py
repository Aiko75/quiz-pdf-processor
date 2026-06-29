import os
import zipfile
import xml.etree.ElementTree as ET

def extract_docx_to_txt(docx_path, txt_path):
    WORD_NAMESPACE = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
    PARA = WORD_NAMESPACE + 'p'
    TEXT = WORD_NAMESPACE + 't'
    STYLE = WORD_NAMESPACE + 'pStyle'
    VAL = WORD_NAMESPACE + 'val'
    
    if not os.path.exists(docx_path):
        print(f"File not found: {docx_path}")
        return
        
    try:
        with zipfile.ZipFile(docx_path) as docx:
            xml_content = docx.read('word/document.xml')
            root = ET.fromstring(xml_content)
            
            with open(txt_path, 'w', encoding='utf-8') as f:
                for paragraph in root.iter(PARA):
                    # Check style for headings
                    style_val = ""
                    pPr = paragraph.find(WORD_NAMESPACE + 'pPr')
                    if pPr is not None:
                        pStyle = pPr.find(STYLE)
                        if pStyle is not None:
                            style_val = pStyle.get(VAL)
                    
                    texts = [node.text for node in paragraph.iter(TEXT) if node.text]
                    p_text = "".join(texts)
                    
                    if p_text.strip():
                        if style_val:
                            f.write(f"[{style_val}] {p_text}\n")
                        else:
                            f.write(f"{p_text}\n")
        print(f"Successfully extracted to {txt_path}")
    except Exception as e:
        print(f"Error reading docx: {e}")

if __name__ == "__main__":
    docx_path = r"d:\My_projects\Random_Essential\Quiz_Processor\docs\de_an\BaoCaoDeAn_NguyenNgocVuong.docx"
    txt_path = r"d:\My_projects\Random_Essential\Quiz_Processor\scratch\docx_content.txt"
    extract_docx_to_txt(docx_path, txt_path)

"""
Dump full XML of first few option paragraphs to find actual highlight storage
"""
import docx
from pathlib import Path
from lxml import etree

doc_path = Path('docs/test/trac-nghiem-1-chu-nghia-xa-hoi-khoa-hoc-cnxhkh_co_dap_an.docx')
doc = docx.Document(doc_path)

print('=== FULL XML OF PARAGRAPHS 1-5 ===\n')
for i in range(1, 6):
    para = doc.paragraphs[i]
    t = para.text.strip()
    print(f'--- Para [{i}]: "{t[:60]}" ---')
    xml = etree.tostring(para._p, pretty_print=True).decode('utf-8')
    print(xml)
    print()

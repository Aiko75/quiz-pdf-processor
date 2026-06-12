import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from quiz_core.parsing.pdf_parser import extract_styled_lines
from quiz_core.parsing.core import parse_questions

pdf_path = Path(r"d:\My_projects\Random_Essential\Quiz_Processor\docs\test\trac-nghiem-1-chu-nghia-xa-hoi-khoa-hoc-cnxhkh.pdf")
if not pdf_path.exists():
    print(f"Error: PDF file not found at {pdf_path}")
    sys.exit(1)

print("Extracting lines...")
lines = extract_styled_lines(pdf_path)

print(f"Parsed {len(lines)} lines from PDF.")
print("Parsing questions...")
questions = parse_questions(lines)

print(f"Successfully parsed {len(questions)} questions.")

print("\n--- SAMPLE QUESTIONS AND DETECTED ANSWERS ---")
for i, q in enumerate(questions[:10]):
    print(f"\nQuestion {i+1}: {q.question[:100]}...")
    print("Options:")
    for opt in q.options:
        mark = "[CORRECT]" if opt.label == q.answer_label else "         "
        highlight = "(Highlighted)" if opt.emphasized else ""
        print(f"  {mark} {opt.label}. {opt.text} {highlight}")

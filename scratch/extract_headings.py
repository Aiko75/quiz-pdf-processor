with open(r"d:\My_projects\Random_Essential\Quiz_Processor\scratch\docx_content.txt", "r", encoding="utf-8") as f:
    lines = f.readlines()

headings = []
for i, line in enumerate(lines):
    if line.startswith("[Heading") or line.startswith("[Title]") or line.startswith("[Subtitle]"):
        headings.append((i+1, line.strip()))

print(f"Total lines: {len(lines)}")
print("Headings found:")
for idx, h in headings:
    print(f"Line {idx}: {h}")

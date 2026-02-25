# Auto Handling File - Quiz PDF Processor

Ứng dụng này dùng để xử lý đề trắc nghiệm từ PDF và xuất ra 2 file DOCX:

- Bản có đáp án (giữ highlight theo file gốc: đậm/màu nếu nhận diện được)
- Bản để làm (đồng nhất font, không lộ đáp án)

Ngoài ra có chức năng kiểm tra đối chiếu tự động giữa file gốc và file output.

## Tính năng chính

- Lọc nội dung rác không liên quan (watermark, text chèn, dòng nhiễu)
- Trích xuất câu hỏi + 4 đáp án A/B/C/D
- Nhận diện đáp án từ kiểu nhấn mạnh trong file gốc:
  - 1 đáp án in đậm duy nhất, hoặc
  - 1 đáp án có màu khác biệt duy nhất
- Chống lặp câu
- Sửa một phần lỗi ký tự bị tách rời
- Xuất DOCX cho cả 2 phiên bản
- Kiểm tra chất lượng output (mismatch, thiếu highlight, highlight sai)

## Cấu trúc dự án

- `quiz_pdf_processor.py`: logic xử lý PDF, xuất DOCX, và validate
- `quiz_app.py`: app desktop Tkinter
- `requirements.txt`: dependency Python
- `dist/QuizProcessorApp.exe`: bản exe đã build
- `files/`: đặt PDF đầu vào
- `processed_quiz/`: nơi chứa kết quả DOCX

## Cài đặt

Yêu cầu Python 3.10+ (khuyến nghị 3.13 như môi trường hiện tại).

```bash
pip install -r requirements.txt
```

## Cách dùng nhanh

### 1) Dùng app desktop

```bash
python quiz_app.py
```

Trong app:

- Chọn thư mục input PDF
- Chọn thư mục output
- Bấm `1) Xử lý PDF -> DOCX`
- Bấm `2) Kiểm tra đối chiếu`

### 2) Dùng script CLI

```bash
python quiz_pdf_processor.py --input files --output processed_quiz
```

## Kiểm tra output (validate)

Trong app đã có nút kiểm tra tự động.

Nguyên tắc kiểm tra:

- Số câu trong DOCX phải khớp số câu parse từ PDF
- Bản đáp án:
  - Không thiếu highlight đáp án
  - Không highlight nhiều đáp án trong cùng 1 câu
  - Không lệch đáp án so với kết quả nhận diện
- Bản để làm: không có highlight

## Build file EXE

Đã dùng `PyInstaller` với chế độ 1 file:

```bash
python -m PyInstaller --noconfirm --clean --windowed --onefile --name QuizProcessorApp --collect-all docx quiz_app.py
```

File build ra tại:

- `dist/QuizProcessorApp.exe`

## Ghi chú

- PDF có chất lượng quá kém hoặc scan ảnh có thể giảm độ chính xác.
- Trường hợp format nguồn bất thường, nên kiểm tra nhanh vài câu sau khi xuất.
- Với bộ đề lớn, nên ưu tiên chạy validate để phát hiện sớm lỗi biên.

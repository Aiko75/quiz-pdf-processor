# Đặc tả Chi tiết Nhân Backend (Python Core)

Nhân xử lý logic của hệ thống **Quiz Processor** được đóng gói bên trong thư mục [quiz_core](file:///d:/My_projects/Random_Essential/Quiz_Processor/quiz_core). Bộ core này sử dụng ngôn ngữ Python 3.10+ cùng các thư viện mạnh mẽ như `PyMuPDF` (`fitz`) để trích xuất PDF và `python-docx` để tương tác với định dạng Microsoft Word.

---

## 1. Cơ chế Trích xuất & Phân tích Đề (Parsing Engine)

Nhiệm vụ chính của module [parsing](file:///d:/My_projects/Random_Essential/Quiz_Processor/quiz_core/parsing) là đọc tệp PDF chứa đề trắc nghiệm và chuyển đổi chúng thành cấu trúc câu hỏi lập trình được.

### A. Định nghĩa Mô hình Dữ liệu (Data Models)
* [LineData](file:///d:/My_projects/Random_Essential/Quiz_Processor/quiz_core/models.py): Đại diện cho một dòng chữ trích xuất từ PDF chứa thông tin định dạng:
  * `text`: Nội dung chuỗi.
  * `is_bold`: Có in đậm không (đọc trực tiếp từ font của span).
  * `is_highlighted`: Có được bôi màu nền (highlight) không — trường bổ sung v1.4.0 phục vụ nhận diện đáp án đúng từ file DOCX đáp án.
  * `color_int`: Giá trị màu nguyên dạng số của văn bản.
  * `page_number`, `x0`, `y0`: Vị trí trang và tọa độ phục vụ thuật toán căn lề.
* [OptionData](file:///d:/My_projects/Random_Essential/Quiz_Processor/quiz_core/models.py): Lưu thông tin một phương án lựa chọn (A, B, C, D, E).
* [QuestionData](file:///d:/My_projects/Random_Essential/Quiz_Processor/quiz_core/models.py): Chứa nội dung câu hỏi, danh sách lựa chọn và nhãn đáp án đúng phát hiện được.

### B. Mẫu Regex Nhận Diện (Patterns)
Nằm tại [patterns.py](file:///d:/My_projects/Random_Essential/Quiz_Processor/quiz_core/parsing/patterns.py), các mẫu biểu thức chính quy được thiết kế tối ưu cho nhiều dạng đề thi khác nhau:
* **Câu hỏi thông thường**: `r"^(?:Câu\s*h\s*ỏ\s*i\s*\d+|Câu\s*\d+[\.:)]?|Question\s*\d+[\.:)]?|\d+[\.:)]|Điểm\s+khác\s+biệt)(?:\s+|$)"`
* **LMS Question (Moodle/Studocu)**: Dạng ký tự rời rạc do xuất tệp bị lỗi khoảng trắng: `r"^(?:Câu\s*h\s*ỏ\s*i\s*|Câu\s*h\s*|Question\s*)\d+"`
* **Đáp án lựa chọn**:
  * Chữ in hoa thông thường: `r"^([A-E])(?:[\.:\)\-]\s*|\s+)(.+)$"`
  * LMS Option: `r"^([a-eA-E])\.\s+(.+)$"` hoặc nhãn đơn độc `r"^([a-eA-E])\.\s*$"`
* **Lọc nhiễu (patterns.py)**: Tự động loại bỏ các dòng watermark Studocu (`lOMoARcPSD|...`, `messages.downloaded_by`, `Downloaded by...`) ngay trong bước parse.

### C. Heuristic Phát Hiện Đáp Án Đúng (Correct Answer Detection)
Khi phân tích đề thi từ tệp PDF gốc có sẵn lời giải, hệ thống sử dụng thuật toán **Heuristic xếp tầng nhiều cấp độ** tại hàm `finalize_answer` để xác định đáp án đúng của từng câu:
1. **Ưu tiên 1 (Ký tự Checkmark)**: Phát hiện biểu tượng checkmark đứng cạnh dòng đáp án (`✓`, `✔`, `☑`, `\uf00c`). Thuật toán đo khoảng cách trục Y (`y0`) giữa ký tự checkmark đứng rời và các dòng đáp án để gán đáp án đúng cho dòng nằm cùng cao độ có khoảng cách nhỏ nhất.
2. **Ưu tiên 2 (Bôi vàng - Highlight)**: Phát hiện vùng tô màu nền vàng (`page.get_drawings()` + `page.annots()`) giao cắt với span văn bản của phương án. Đây là phương pháp chính xác nhất với các file DOCX/PDF có đánh dấu highlight.
3. **Ưu tiên 3 (In đậm - Bold)**: Nếu câu hỏi có đúng duy nhất **một phương án** được in đậm toàn bộ hoặc in đậm nhãn phương án trong tài liệu gốc.
4. **Ưu tiên 4 (Khác biệt màu sắc - Color anomaly)**: Nếu một phương án có màu chữ khác biệt so với các phương án còn lại. Thuật toán đếm số lượng xuất hiện của mỗi màu chữ qua `Counter` và lấy màu đơn lẻ xuất hiện đúng 1 lần làm đáp án đúng.
5. **Ưu tiên 5 (Từ khóa đáp án)**: Tìm kiếm các từ khóa đi kèm trong văn bản lựa chọn như `(đúng)`, `[correct]` hoặc `(correct)`, sau đó tự động cắt bỏ từ khóa này ra khỏi chuỗi hiển thị.
6. **Ưu tiên 6 (Đáp án ghi ở câu hỏi)**: Nếu cuối câu hỏi có kèm văn bản chỉ rõ đáp án dạng `"Đáp án: A"`, `"Key - A"`.

### D. Xử lý Nhiễu tài liệu (Noise Reduction)
Được triển khai trong [utils.py](file:///d:/My_projects/Random_Essential/Quiz_Processor/quiz_core/parsing/utils.py):
* Loại bỏ tiêu đề trang, chân trang, đường dẫn liên kết, watermark quảng cáo (ví dụ: watermark Studocu: `"Downloaded by..."`, `"Xem lại lần làm thử"`, email rác).
* Khôi phục văn bản lỗi tách rời ký tự (`repair_fragmented_text`): ghép nối các từ bị phân mảnh thành từ hoàn chỉnh bằng cách duyệt các chuỗi độ dài 1 ký tự đứng kề nhau.

---

## 2. Cơ chế Chấm Điểm & So Khớp (Grading & Matching Engine)

Nằm tại [grading/engine.py](file:///d:/My_projects/Random_Essential/Quiz_Processor/quiz_core/grading/engine.py), đây là trái tim của tính năng so sánh kết quả học tập.

### Thuật toán ghép cặp câu hỏi (Pairing Algorithms)
Khi so sánh tệp Bài làm của học sinh với tệp Đáp án chính thức, hai tệp này có thể bị đảo vị trí câu hỏi hoặc chứa cấu trúc khác nhau. Hệ thống thực hiện ghép cặp câu theo chiến lược xếp tầng tại [matching.py](file:///d:/My_projects/Random_Essential/Quiz_Processor/quiz_core/grading/matching.py):
1. **Khớp nội dung văn bản (Text Similarity)**: 
   * Rút gọn văn bản câu hỏi thành một khóa chuẩn hóa (`normalize_question_key`): loại bỏ tất cả dấu câu, khoảng trắng và chuyển về dạng viết thường không dấu.
   * So sánh khóa này giữa bài làm và đáp án. Việc này đảm bảo khớp chính xác tuyệt đối kể cả khi đề thi bị xáo trộn thứ tự các câu hỏi.
2. **Khớp số thứ tự (Number Matching)**:
   * Nếu khớp text thất bại hoặc chỉ khớp được số lượng rất ít do sai lệch từ vựng nhẹ, hệ thống sẽ trích xuất số thứ tự (ví dụ: trích số `15` từ `"Câu 15:..."`).
   * So khớp các câu có cùng số thứ tự giữa hai file.
3. **Khớp theo thứ tự tuần tự (Index fallback)**:
   * Nếu cả hai cách trên đều không cho kết quả tốt, hệ thống sẽ tự động ghép câu lần lượt theo vị trí xuất hiện (câu 1 khớp câu 1, câu 2 khớp câu 2). Hệ thống sẽ đưa ra cảnh báo trên UI.

### Xuất Báo cáo Kết quả (Grading Exporter)
Lớp [exporter.py](file:///d:/My_projects/Random_Essential/Quiz_Processor/quiz_core/grading/exporter.py) chịu trách nhiệm xuất tệp kết quả:
* **File `.docx` câu lỗi (`*_cac_cau_loi.docx`)**:
  * Ghi tổng quan điểm số ngay đầu trang.
  * Chia tệp làm 3 phần rõ rệt: *Các câu làm đúng*, *Các câu làm sai*, *Các câu chưa làm*.
  * Các câu làm sai giữ nguyên đáp án sai mà học sinh đã tô (gạch ngang và tô màu đỏ chữ) đồng thời bôi đậm và tô màu xanh lá cây đáp án đúng của hệ thống để dễ dàng tự học lại kiến thức bị hổng.

---

## 3. Cơ chế Kiểm định Cấu trúc & Feedback Loop (v1.5.0)

Đây là luồng xử lý **độc lập** với quá trình số hóa, giúp phát hiện và ghi nhận lỗi cấu trúc câu hỏi trước khi tạo đề.

### A. Kiểm định Cấu trúc (`double_check_quiz_structure`)
Được triển khai tại [validation/engine.py](file:///d:/My_projects/Random_Essential/Quiz_Processor/quiz_core/validation/engine.py):

| Loại lỗi | Mã lỗi | Mô tả |
| :--- | :--- | :--- |
| Số đáp án không hợp lệ | `option_count` | Câu hỏi có ít hơn 3 hoặc nhiều hơn 5 đáp án |
| Đáp án dính trong câu hỏi | `stuck_options` | Nhãn A./B./C. xuất hiện lẫn trong nội dung câu hỏi |
| Đáp án trống nội dung | `empty_option` | Nhãn đáp án tồn tại (ví dụ `A.`) nhưng không có text theo sau |

### B. Feedback Loop Registry (`feedback_loop.json`)
Tệp JSON lưu tại `<workspace>/feedback_loop.json`, tổ chức theo tên tệp nguồn:
```json
{
  "ten_file.docx": [
    {
      "question_index": 38,
      "type": "option_count",
      "message": "Số lượng đáp án không hợp lệ: 0",
      "source": "auto"
    },
    {
      "question_index": 15,
      "type": "manual",
      "message": "Câu hỏi bị lỗi phông chữ ở đáp án B",
      "source": "manual"
    }
  ]
}
```
* **`source: "auto"`**: Ghi nhận tự động khi chạy `--action doublecheck`.
* **`source: "manual"`**: Ghi nhận thủ công qua UI hoặc `--action add_feedback`.
* **Cơ chế deduplicate**: Hệ thống kiểm tra sự tồn tại của `question_index` + `message` trước khi ghi, tránh trùng lặp.
* **Tự động làm sạch**: Khi chạy lại double-check, các lỗi `auto` cũ được thay thế hoàn toàn bởi kết quả mới; lỗi `manual` được giữ nguyên.

### C. Kiểm định Số hóa (Validation Engine)
Nằm tại [validation/engine.py](file:///d:/My_projects/Random_Essential/Quiz_Processor/quiz_core/validation/engine.py) dùng để đối chiếu xác thực tệp xuất ra từ hệ thống:
* **Thuật toán so khớp mờ (Fuzzy matching)**: Sử dụng `difflib.get_close_matches` với ngưỡng tin cậy `cutoff=0.8` để phát hiện xem tệp `.docx` xuất ra có làm mất câu nào trong tệp `.pdf` gốc không.
* **Kiểm định highlight**: Phát hiện câu hỏi bị mất highlight đáp án, bị highlight quá nhiều đáp án, hoặc tệp DOCX có câu dư thừa không có trong PDF gốc.

---

## 4. Đặc tả Tham số CLI (quiz_cli.py)

Tệp [quiz_cli.py](file:///d:/My_projects/Random_Essential/Quiz_Processor/quiz_cli.py) đóng vai trò là cổng API nhận cuộc gọi từ bên ngoài.

### Danh sách các action hỗ trợ:

| Action | Chức năng | Tham số bắt buộc | Tham số tùy chọn |
| :--- | :--- | :--- | :--- |
| `process` | Số hóa tệp PDF -> 2 bản DOCX | `--input` (Đường dẫn PDF)<br>`--output` (Thư mục ra) | Không |
| `validate`| Kiểm định đối chiếu PDF vs DOCX | `--input` (Đường dẫn PDF)<br>`--output` (Thư mục chứa DOCX) | Không |
| `report`  | Xuất báo cáo kiểm định chất lượng | `--input` (Đường dẫn PDF)<br>`--output` (Thư mục ra) | Không |
| `grade`   | Chấm bài làm vs Đáp án | `--answer-file` (Tệp đáp án)<br>`--submission-file` (Tệp bài làm)<br>`--output` (Thư mục ra) | Không |
| `generate`| Sinh đề thi mới từ tệp đáp án nguồn | `--answer-file` (Tệp đáp án nguồn)<br>`--output` (Thư mục ra) | `--count` (Số câu ngẫu nhiên)<br>`--from-q` / `--to-q` (Khoảng câu)<br>`--gen-answer` (Tạo bản đáp án)<br>`--interactive` (Xuất JSON thi)<br>`--time-limit` (Thời gian thi)<br>`--workspace` (Thư mục làm việc)<br>`--folder` (Thư mục con thi) |
| `import`  | Nhập đề thi từ ngoài vào Exams | `--input` (Tệp JSON/DOCX/PDF) | `--title` (Tiêu đề đề thi)<br>`--time-limit` (Giới hạn phút)<br>`--workspace` (Workspace)<br>`--folder` (Thư mục con thi) |
| `preview` | Xem trước câu hỏi trực tiếp trên UI | `--input` (Tệp PDF/DOCX) | Không |
| `doublecheck` | Kiểm định cấu trúc câu hỏi *(v1.5.0)* | `--answer-file` (Tệp đáp án DOCX/PDF) | `--workspace` (Thư mục workspace để ghi feedback) |
| `add_feedback` | Thêm báo lỗi thủ công *(v1.5.0)* | `--answer-file` (Tệp đáp án nguồn)<br>`--workspace` (Workspace)<br>`--question-index` (Số câu)<br>`--message` (Nội dung lỗi) | Không |

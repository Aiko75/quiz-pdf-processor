# Auto Handling File - Quiz Processor

Ứng dụng **Quiz Processor** là công cụ xử lý đề thi trắc nghiệm toàn diện, kết hợp nhân xử lý tài liệu mạnh mẽ viết bằng **Python** và giao diện đồ họa tương tác hiện đại viết bằng **Flutter Desktop (Windows)**. 

Hệ thống hỗ trợ số hóa đề thi từ PDF/DOCX sang Word để in ấn, tạo các bài thi trực tuyến tương tác, tự động chấm điểm bài làm của học sinh, phục hồi phiên thi khi gặp sự cố và phân tích biểu đồ tiến độ học tập.

---

## 1. Tính năng chính

* **Số hóa đề thi**: Quét và trích xuất câu hỏi + 4/5 phương án lựa chọn từ tệp PDF/DOCX, loại bỏ hoàn toàn các loại watermark và văn bản rác (như quảng cáo Studocu, nhãn hệ thống).
* **Nhận diện đáp án tự động**:
  * Tự động phát hiện đáp án dựa trên phông chữ in đậm (bold), chữ có màu khác biệt (color anomaly), ký tự tick chọn (`✓`, `✔`, `\uf00c`) hoặc nhãn từ khóa đi kèm như `(đúng)`.
  * **Đặc biệt**: Nhận diện đáp án dựa trên nét vẽ làm nổi bật màu nền (background drawing highlights) của tệp PDF.
* **Xuất 2 bản tài liệu Word (DOCX)**:
  * **Bản có đáp án**: Giữ nguyên hoặc tô màu nổi bật đáp án đúng phục vụ giáo viên.
  * **Bản đề làm**: Đồng nhất định dạng phông chữ, ẩn toàn bộ dấu hiệu đáp án phục vụ học sinh làm bài thử.
* **Phòng thi trực tuyến trực quan**:
  * Làm bài thi trực tiếp trên giao diện tương tác với bộ đếm ngược thời gian.
  * **Auto-Save & Phục hồi dở dang**: Tự động lưu tiến độ thi từng giây vào tệp `current_session.json` để phục hồi lại trạng thái thi khi ứng dụng bị tắt đột ngột.
  * **Hệ thống phím tắt tùy chỉnh**: Tự do gán phím tắt làm bài thi nhanh (ví dụ: gán phím `1, 2, 3, 4` cho đáp án `A, B, C, D` và phím `6` để gắn cờ câu hỏi khó xem lại sau).
* **Chấm điểm tự động và So khớp thông minh**:
  * So khớp bài làm (PDF/DOCX) với đáp án (PDF/DOCX) dựa trên giải thuật chuẩn hóa nội dung văn bản (Text Similarity) để không bị lệch câu khi đề thi bị xáo trộn thứ tự.
  * Xuất tệp báo cáo câu lỗi (`*_cac_cau_loi.docx`): hiển thị rõ các câu làm đúng/sai, giữ nguyên lựa chọn sai của học sinh (gạch ngang màu đỏ) và chỉ ra đáp án đúng (chữ màu xanh).
* **Phân tích kết quả học tập**:
  * Xem biểu đồ phân bổ môn học và thanh tiến trình hiệu suất đạt được của từng môn.
  * Cảnh báo danh sách 5 đề thi có điểm số thấp nhất để định hướng học tập.

---

## 2. Cấu trúc thư mục dự án

```text
Quiz_Processor/
├── quiz_core/               # Nhân xử lý logic tài liệu (Python Backend)
│   ├── parsing/             # Phân tích PDF/DOCX, lọc nhiễu, nhận diện highlight
│   ├── grading/             # Chấm điểm bài thi, xuất báo cáo câu lỗi, sinh đề mới
│   ├── validation/          # Đối chiếu lỗi số hóa giữa PDF gốc và DOCX xuất ra
│   └── models.py            # Data classes định nghĩa cấu trúc dữ liệu
│
├── quiz_flutter_ui/         # Giao diện phòng thi & phân tích (Flutter Frontend)
│   ├── lib/
│   │   ├── main.dart        # Entrypoint ứng dụng Flutter
│   │   ├── screens/         # Màn hình Số hóa, Phòng thi, Kết quả, Thống kê, Cài đặt
│   │   └── services/        # BackendService, DatabaseService, SettingsService, v.v.
│   └── pubspec.yaml         # Khai báo thư viện phụ thuộc của Dart/Flutter
│
├── docs/                    # Thư mục tài liệu kỹ thuật chi tiết của hệ thống
├── dist/                    # Thư mục đầu ra chứa tệp build quiz_cli.exe của Python
├── quiz_cli.py              # CLI chính kết nối Flutter với backend Python
├── quiz_cli.spec            # Tệp cấu hình PyInstaller tối giản
├── QuizCLI.spec             # Tệp cấu hình PyInstaller đầy đủ (được khuyên dùng để build)
├── requirements.txt         # Thư viện Python phụ thuộc
└── README.md                # Tài liệu hướng dẫn sử dụng này
```

---

## 3. Cài đặt môi trường phát triển (Development)

Yêu cầu máy tính cài đặt sẵn **Python 3.10+** và **Flutter SDK (stable channel)**.

### Bước 1: Thiết lập Python Backend
Từ thư mục gốc của dự án, mở terminal và chạy:
```bash
pip install -r requirements.txt
```

### Bước 2: Thiết lập Flutter UI
Di chuyển vào thư mục giao diện và tải các thư viện Dart phụ thuộc:
```bash
cd quiz_flutter_ui
flutter pub get
```

Chạy ứng dụng ở chế độ phát triển:
```bash
flutter run
```

---

## 4. Hướng dẫn sử dụng nhanh

### A. Dùng qua Giao diện Flutter Desktop (Khuyên dùng)
Giao diện chính được chia thành các tab thông qua cột điều hướng bên trái:
1. **Số hóa & Kiểm tra**: Chọn thư mục chứa các tệp PDF gốc, bấm bắt đầu để hệ thống tự động xuất ra 2 tệp Word tương ứng trong thư mục Output. Nhấp vào biểu tượng mắt để xem trước danh sách câu hỏi.
2. **Làm bài (Phòng thi)**:
   * **Interactive Exam (Bài thi trực tuyến)**: Nhấp chuột chọn đề thi để vào phòng thi, sử dụng phím tắt hoặc chuột để làm bài, bấm gắn cờ cho câu khó.
   * **Chấm file**: Chọn tệp Đáp án chính thức và tệp Bài làm của học sinh, hệ thống sẽ tự động so sánh, chấm điểm và xuất ra tệp Word chứa danh sách câu sai.
   * **Lịch sử làm bài**: Xem lại kết quả và chi tiết câu trả lời của các lượt thi trước.
3. **Tạo đề mới**: Thiết lập sinh đề ngẫu nhiên hoặc sinh đề theo khoảng câu từ ngân hàng câu hỏi nguồn.
4. **Phân tích**: Xem biểu đồ hình quạt thống kê môn học và cảnh báo đề yếu.
5. **Cài đặt**: Chọn thư mục làm việc (Workspace), đổi màu giao diện tối (Dark Mode), điều chỉnh kích thước cửa sổ và tùy biến phím tắt.

### B. Dùng qua Script dòng lệnh (CLI Python)
Bạn cũng có thể chạy độc lập nhân xử lý Python qua CLI:
```bash
# 1) Số hóa hàng loạt tệp PDF sang Word
python quiz_cli.py --action process --input <thư_mục_hoặc_tệp_pdf> --output <thư_mục_docx>

# 2) Chấm bài thi của học sinh so với đáp án chính thức
python quiz_cli.py --action grade --submission-file <tệp_bài_làm> --answer-file <tệp_đáp_án> --output <thư_mục_kết_quả>

# 3) Sinh đề trắc nghiệm ngẫu nhiên N câu
python quiz_cli.py --action generate --answer-file <tệp_nguồn> --output <thư_mục_ra> --count 40 --interactive
```

---

## 5. Hướng dẫn đóng gói ứng dụng (Build Executables)

Để đóng gói phần mềm thành ứng dụng Windows chạy độc lập không cần cài đặt môi trường (Python/Flutter), ta cần build 2 tệp tin thực thi độc lập rồi ghép nối chúng lại.

### Phần 1: Build file `quiz_cli.exe` (Python Backend)
Sử dụng công cụ `PyInstaller` để biên dịch kịch bản Python CLI kèm theo các thư viện phụ thuộc (`pymupdf`, `python-docx`) thành một tệp `.exe` chạy trên Console:

Từ thư mục gốc của dự án, mở terminal chạy lệnh:
```bash
python -m PyInstaller --clean QuizCLI.spec
```
*Lưu ý*: Có thể sử dụng lệnh viết ngắn `pyinstaller --clean QuizCLI.spec` nếu đã cấu hình biến môi trường PATH cho PyInstaller. Tệp cấu hình `QuizCLI.spec` đã được thiết lập sẵn cờ `console=True` để có thể ghi log Standard Output phục vụ Flutter đọc dữ liệu thời gian thực.
* **Kết quả đầu ra**: Tệp `dist/quiz_cli.exe`.

### Phần 2: Build file `quiz_flutter_ui.exe` (Flutter Desktop)
Biên dịch ứng dụng Flutter sang ứng dụng Windows Native:

Di chuyển vào thư mục Flutter và thực hiện build:
```bash
cd quiz_flutter_ui
flutter build windows
```
* **Kết quả đầu ra**: Thư mục chứa ứng dụng nằm tại `build\windows\x64\runner\Release\`. Trong thư mục này sẽ có tệp chạy chính tên là `quiz_flutter_ui.exe` và các tệp tin thư viện động đi kèm.

### Phần 3: Đóng gói và liên kết hai tệp EXE (Packaging)
Để ứng dụng Flutter Desktop có thể gọi được nhân xử lý Python khi chạy độc lập:
1. Sao chép tệp tin `quiz_cli.exe` mới biên dịch được trong thư mục `dist/` (ở Phần 1).
2. Dán tệp `quiz_cli.exe` đó vào **cùng thư mục** chứa tệp `quiz_flutter_ui.exe` (đường dẫn: `quiz_flutter_ui\build\windows\x64\runner\Release\`).
3. Khởi chạy tệp `quiz_flutter_ui.exe` trong thư mục Release. Ứng dụng lúc này đã được tích hợp đầy đủ tính năng và sẵn sàng phân phối cho người dùng cuối.

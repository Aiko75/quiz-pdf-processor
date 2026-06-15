# Auto Handling File - Quiz Processor

Ứng dụng **Quiz Processor** là công cụ xử lý đề thi trắc nghiệm toàn diện, kết hợp nhân xử lý tài liệu mạnh mẽ viết bằng **Python** và giao diện đồ họa tương tác hiện đại viết bằng **Flutter Desktop (Windows)**.

Hệ thống hỗ trợ số hóa đề thi từ PDF/DOCX sang Word để in ấn, tạo các bài thi trực tuyến tương tác, tự động chấm điểm bài làm của học sinh, phục hồi phiên thi khi gặp sự cố và phân tích biểu đồ tiến độ học tập.

> **Phiên bản hiện tại: v1.5.0** — Xem [CHANGELOG_v1.5.0.docx](docs/CHANGELOG_v1.5.0.docx) để biết các tính năng mới.

---

## 1. Tính năng chính

* **Số hóa đề thi**: Quét và trích xuất câu hỏi + 4/5 phương án lựa chọn từ tệp PDF/DOCX, loại bỏ hoàn toàn các loại watermark và văn bản rác (như quảng cáo Studocu, nhãn hệ thống).
* **Nhận diện đáp án tự động** (heuristic xếp tầng):
  * Ký tự tick chọn (`✓`, `✔`, `\uf00c`).
  * **Bôi vàng (Highlight)** — Ưu tiên cao nhất trong DOCX có đánh dấu *(mới v1.5.0)*.
  * Phông chữ in đậm (bold), màu chữ khác biệt (color anomaly).
  * Từ khóa đi kèm như `(đúng)`, `[correct]`.
* **Xuất 2 bản tài liệu Word (DOCX)**:
  * **Bản có đáp án**: Tô màu nổi bật đáp án đúng phục vụ giáo viên.
  * **Bản đề làm**: Đồng nhất định dạng phông chữ, ẩn toàn bộ dấu hiệu đáp án phục vụ học sinh làm bài thử.
* **Kiểm định cấu trúc câu hỏi** *(mới v1.5.0)*:
  * Luồng kiểm định độc lập với quá trình số hóa, có thể chạy bất kỳ lúc nào.
  * Phát hiện 3 loại lỗi: số đáp án không hợp lệ, đáp án bị dính trong câu hỏi, đáp án trống nội dung.
  * **Feedback Loop**: Tự động ghi nhận lỗi vào `feedback_loop.json`, hỗ trợ cả báo lỗi thủ công.
* **Phòng thi trực tuyến trực quan**:
  * Làm bài thi trực tiếp trên giao diện tương tác với bộ đếm ngược thời gian.
  * **Auto-Save & Phục hồi dở dang**: Tự động lưu tiến độ thi từng giây vào tệp `current_session.json` để phục hồi lại trạng thái thi khi ứng dụng bị tắt đột ngột.
  * **Chế độ loại trừ đáp án (Elimination Mode)**: Gạch bỏ phương án nhiễu, phím tắt `4`.
  * **Chế độ xem cuộn toàn bộ đề**: Chuyển đổi bằng nút AppBar hoặc phím `8`.
  * **Phím tắt tùy chỉnh**: Gán phím tắt làm bài thi nhanh. Mặc định: `1/2/3/5` cho `A/B/C/D`, `6` để gắn cờ, `4` gạch bỏ, `8` xem cuộn.
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
│   ├── validation/          # Kiểm định cấu trúc câu, feedback loop, đối chiếu PDF-DOCX
│   └── models.py            # Data classes định nghĩa cấu trúc dữ liệu
│
├── quiz_flutter_ui/         # Giao diện phòng thi & phân tích (Flutter Frontend)
│   ├── lib/
│   │   ├── main.dart        # Entrypoint ứng dụng Flutter
│   │   ├── screens/         # Màn hình Số hóa, Phòng thi, Kết quả, Thống kê, Cài đặt
│   │   └── services/        # BackendService, DatabaseService, SettingsService, v.v.
│   └── pubspec.yaml         # Khai báo thư viện phụ thuộc của Dart/Flutter (v1.5.0+5)
│
├── docs/                    # Tài liệu kỹ thuật chi tiết của hệ thống
│   ├── CHANGELOG_v1.5.0.docx  # Release notes phiên bản 1.5.0
│   ├── tong_quan_he_thong.md  # Kiến trúc tổng quan hệ thống
│   ├── dac_ta_backend.md      # Đặc tả nhân xử lý Python
│   ├── dac_ta_frontend.md     # Đặc tả giao diện Flutter
│   └── co_so_du_lieu.md       # Đặc tả cơ sở dữ liệu SQLite
├── scratch/                 # Script kiểm tra & sửa lỗi file nguồn (dev-only)
│   ├── fix_docx.py          # Vá lỗi cấu trúc DOCX dựa trên feedback_loop.json
│   └── create_changelog.py  # Script tạo file DOCX release notes
├── dist/                    # Thư mục đầu ra chứa tệp build quiz_cli.exe của Python
├── quiz_cli.py              # CLI chính kết nối Flutter với backend Python
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
3. **Tạo đề mới**: Thiết lập sinh đề ngẫu nhiên hoặc sinh đề theo khoảng câu từ ngân hàng câu hỏi nguồn. Bấm **"Kiểm định cấu trúc câu"** trước khi tạo đề để phát hiện câu lỗi sớm *(v1.5.0)*.
4. **Phân tích**: Xem biểu đồ hình quạt thống kê môn học và cảnh báo đề yếu.
5. **Cài đặt**: Chọn thư mục làm việc (Workspace), đổi màu giao diện tối (Dark Mode), điều chỉnh kích thước cửa sổ và tùy biến phím tắt. Nút **"Đặt lại mặc định"** khôi phục bộ phím chuẩn `A=1, B=2, C=3, D=5, E=8, Flag=6` *(v1.5.0)*.

### B. Dùng qua Script dòng lệnh (CLI Python)
Bạn cũng có thể chạy độc lập nhân xử lý Python qua CLI:
```bash
# 1) Số hóa hàng loạt tệp PDF sang Word
python quiz_cli.py --action process --input <thư_mục_hoặc_tệp_pdf> --output <thư_mục_docx>

# 2) Chấm bài thi của học sinh so với đáp án chính thức
python quiz_cli.py --action grade --submission-file <tệp_bài_làm> --answer-file <tệp_đáp_án> --output <thư_mục_kết_quả>

# 3) Sinh đề trắc nghiệm ngẫu nhiên N câu
python quiz_cli.py --action generate --answer-file <tệp_nguồn> --output <thư_mục_ra> --count 40 --interactive

# 4) Kiểm định cấu trúc câu hỏi (v1.5.0)
python quiz_cli.py --action doublecheck --answer-file <tệp_đáp_án> --workspace <thư_mục_workspace>

# 5) Báo lỗi câu hỏi thủ công (v1.5.0)
python quiz_cli.py --action add_feedback --answer-file <tệp_đáp_án> --workspace <thư_mục_workspace> --question-index 40 --message "Câu bị mất đáp án D"
```

---

## 5. Phím tắt trong Phòng thi

| Phím | Chức năng |
|------|-----------|
| `1` / `2` / `3` / `5` | Chọn đáp án A / B / C / D |
| `8` | Chọn đáp án E |
| `6` | Gắn cờ / Bỏ cờ câu hỏi |
| `4` | Gạch bỏ / Khôi phục đáp án đang focus (Elimination Mode) |
| `8` | Chuyển đổi chế độ xem cuộn toàn bộ |
| `←` / `→` | Câu trước / Câu sau |
| `↑` / `↓` | Di chuyển focus giữa các phương án |
| `Enter` | Sang câu tiếp theo (hoặc nộp bài nếu ở câu cuối) |
| `A` `B` `C` `D` `E` | Chọn đáp án tương ứng (legacy, luôn hoạt động) |

> Phím tắt có thể tùy biến tại **Cài đặt → Phím tắt bàn phím**. Phím `4` và `8` là reserved, không nên gán lại.

---

## 6. Hướng dẫn đóng gói ứng dụng (Build Executables)

Để đóng gói phần mềm thành ứng dụng Windows chạy độc lập không cần cài đặt môi trường (Python/Flutter), ta cần build 2 tệp tin thực thi độc lập rồi ghép nối chúng lại.

### Phần 1: Build file `quiz_cli.exe` (Python Backend)
Sử dụng công cụ `PyInstaller` để biên dịch kịch bản Python CLI kèm theo các thư viện phụ thuộc (`pymupdf`, `python-docx`) thành một tệp `.exe` chạy trên Console:

Từ thư mục gốc của dự án, mở terminal chạy lệnh:
```bash
python -m PyInstaller --clean QuizCLI.spec
```
*Lưu ý*: Tệp cấu hình `QuizCLI.spec` đã được thiết lập sẵn cờ `console=True` để có thể ghi log Standard Output phục vụ Flutter đọc dữ liệu thời gian thực.
* **Kết quả đầu ra**: Tệp `dist/quiz_cli.exe`.

### Phần 2: Build file `QuizProcessor.exe` (Flutter Desktop)
Biên dịch ứng dụng Flutter sang ứng dụng Windows Native:

Di chuyển vào thư mục Flutter và thực hiện build:
```bash
cd quiz_flutter_ui
flutter build windows
```
* **Kết quả đầu ra**: Thư mục chứa ứng dụng nằm tại `build\windows\x64\runner\Release\`. Tệp chạy chính tên là `QuizProcessor.exe`.

### Phần 3: Đóng gói và liên kết hai tệp EXE (Packaging)
Để ứng dụng Flutter Desktop có thể gọi được nhân xử lý Python khi chạy độc lập:
1. Sao chép tệp tin `quiz_cli.exe` mới biên dịch được trong thư mục `dist/` (ở Phần 1).
2. Dán tệp `quiz_cli.exe` đó vào **cùng thư mục** chứa tệp `QuizProcessor.exe` (đường dẫn: `quiz_flutter_ui\build\windows\x64\runner\Release\`).
3. Khởi chạy tệp `QuizProcessor.exe` trong thư mục Release. Ứng dụng lúc này đã được tích hợp đầy đủ tính năng và sẵn sàng phân phối cho người dùng cuối.

---

## 7. Tài liệu kỹ thuật

| Tài liệu | Nội dung |
|----------|----------|
| [CHANGELOG_v1.5.0.docx](docs/CHANGELOG_v1.5.0.docx) | Release notes đầy đủ phiên bản 1.5.0 |
| [tong_quan_he_thong.md](docs/tong_quan_he_thong.md) | Kiến trúc tổng quan, sơ đồ hệ thống, lịch sử nâng cấp |
| [dac_ta_backend.md](docs/dac_ta_backend.md) | Đặc tả nhân xử lý Python, parsing, grading, validation, CLI |
| [dac_ta_frontend.md](docs/dac_ta_frontend.md) | Đặc tả giao diện Flutter, services, màn hình, phím tắt |
| [co_so_du_lieu.md](docs/co_so_du_lieu.md) | Schema SQLite, các truy vấn thống kê, versioning |

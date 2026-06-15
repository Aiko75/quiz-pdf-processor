# Đặc tả Giao diện & Logic Frontend (Flutter Client)

Phần giao diện và tương tác người dùng của **Quiz Processor** được phát triển bằng Flutter (Dart) nằm trong thư mục [quiz_flutter_ui](file:///d:/My_projects/Random_Essential/Quiz_Processor/quiz_flutter_ui). Ứng dụng được thiết kế tối ưu hóa cho môi trường Desktop (chạy trực tiếp trên Windows) với khả năng đáp ứng cao, hỗ trợ phím tắt bàn phím và giao tiếp thời gian thực với backend Python.

---

## 1. Cơ chế Quản lý Cấu hình & Trạng thái (Services)

Các dịch vụ (Services) được tổ chức theo mô hình **Singleton Pattern** để chia sẻ dữ liệu và quản lý trạng thái nhất quán trên toàn bộ ứng dụng.

### A. Quản lý Cấu hình ([SettingsService](file:///d:/My_projects/Random_Essential/Quiz_Processor/quiz_flutter_ui/lib/services/settings_service.dart))
Sử dụng thư viện `shared_preferences` để lưu trữ bền vững các cài đặt cá nhân của người dùng:
* **Trạng thái bài thi**: Tự động trộn câu hỏi (`shuffleEnabled`), tự động chuyển câu hỏi tiếp theo sau khi chọn đáp án (`autoAdvanceQuiz`), bật/tắt phím tắt bàn phím (`quizShortcutsEnabled`).
* **Không gian làm việc (`workspacePath`)**: Đường dẫn thư mục làm việc hiện tại của ứng dụng.
* **Giao diện**: Chế độ sáng/tối (`darkMode`), ghi nhớ kích thước cửa sổ (`windowWidth`, `windowHeight`).
* **Sắp xếp**: Chế độ hiển thị danh sách đề thi (`examViewMode`: dạng danh sách `list` hoặc dạng lưới `grid`).
* **Phím tắt tùy biến (`keyMappings`)**: Bản đồ ánh xạ phím bấm tùy chỉnh cho các đáp án A/B/C/D/E và gắn cờ. Default: `A=1, B=2, C=3, D=5, E=8, Flag=6`. Có thể đặt lại về mặc định qua nút **"Đặt lại mặc định"** trong màn hình Cài đặt.
* **Ghi nhớ thư mục làm việc**: Lưu trữ các thư mục được chọn gần nhất cho quá trình số hóa (`digitizeInputPath`, `digitizeOutputPath`) và sinh đề (`generateInputPath`, `generateOutputPath`).

### B. Cơ sở dữ liệu Lịch sử ([DatabaseService](file:///d:/My_projects/Random_Essential/Quiz_Processor/quiz_flutter_ui/lib/services/database_service.dart))
Sử dụng thư viện `sqflite` (và `sqflite_common_ffi` cho Windows) để kết nối tệp cơ sở dữ liệu `quiz_history.db` lưu trong thư mục Workspace. Chi tiết các truy vấn và bảng biểu xem tại [Tài liệu Cơ sở dữ liệu](file:///d:/My_projects/Random_Essential/Quiz_Processor/docs/co_so_du_lieu.md).

### C. Sao lưu & Khôi phục dữ liệu ([BackupService](file:///d:/My_projects/Random_Essential/Quiz_Processor/quiz_flutter_ui/lib/services/backup_service.dart))
* **Sao lưu (Backup)**: Nén toàn bộ thư mục Workspace (bao gồm cơ sở dữ liệu SQLite, các tệp đề thi JSON và báo cáo xuất ra) thành một tệp tin nén `.zip` với tên tệp đính kèm mốc thời gian dạng `quiz_backup_YYYY-MM-DDTHH-MM-SS.zip`.
* **Khôi phục (Restore)**: Giải nén tệp tin `.zip` đã chọn và ghi đè trực tiếp vào thư mục Workspace hiện tại (trước khi giải nén sẽ xóa sạch thư mục Workspace cũ để tránh xung đột dữ liệu).

### D. Tự động kiểm tra bản cập nhật ([UpdateService](file:///d:/My_projects/Random_Essential/Quiz_Processor/quiz_flutter_ui/lib/services/update_service.dart))
* Gửi truy vấn HTTP GET tới endpoint GitHub API: `https://api.github.com/repos/Aiko75/Auto_Handling_File/tags` để lấy danh sách các thẻ (tags) phiên bản mới nhất phát hành trên kho lưu trữ.
* Đọc thông tin phiên bản ứng dụng hiện tại qua thư viện `package_info_plus`.
* So sánh chuỗi phiên bản dạng SemVer (Semantic Versioning - ví dụ: so sánh `v1.5.0` và `v1.4.0`). Nếu có phiên bản mới hơn, ứng dụng sẽ hiển thị hộp thoại thông báo và liên kết tải về qua trình duyệt ngoại vi bằng thư viện `url_launcher`.

---

## 2. Màn hình Tạo đề & Kiểm định (Generate Screen)

Màn hình [GenerateScreen](file:///d:/My_projects/Random_Essential/Quiz_Processor/quiz_flutter_ui/lib/screens/generate_screen.dart) được thiết kế theo bố cục **2 cột**:
* **Cột trái (flex: 2)**: Chứa toàn bộ cấu hình tạo đề, có thể cuộn độc lập.
* **Cột phải (flex: 1)**: Bảng **Log Console** hiển thị tiến trình backend theo thời gian thực, hỗ trợ bôi đen/sao chép (bọc bởi `SelectionArea`).

### Tính năng Kiểm định Cấu trúc Câu hỏi (v1.5.0)
* Nút **"Kiểm định cấu trúc câu"** nằm kế nút "Bắt đầu Tạo đề", gọi `--action doublecheck` trên file đáp án nguồn.
* Kết quả kiểm định hiển thị trực tiếp trên Log Console với chi tiết từng câu lỗi: loại lỗi, số câu, nội dung câu hỏi và các đáp án nhận diện được.
* Sau khi kiểm định, thẻ kết quả (màu đỏ nếu có lỗi, màu xanh nếu hợp lệ) xuất hiện với nút **"Mở file nguồn"** và **"Hiển thị trong thư mục"** để mở DOCX nguồn sửa trực tiếp.

### Tính năng Báo lỗi Thủ công (v1.5.0)
Card **"Báo lỗi câu hỏi thủ công"** bên dưới cấu hình:
* Nhập **Số câu** (ví dụ: `40`) và **Mô tả lỗi** (ví dụ: `"Câu bị mất ảnh minh họa"`).
* Nhấn **"Gửi báo lỗi"** để append vào `feedback_loop.json` với `source: "manual"`.
* Chỉ hoạt động khi đã chọn tệp đáp án nguồn.

---

## 3. Phòng thi Trực tuyến & Cơ chế Tương tác (Quiz Taking)

Màn hình làm bài thi trực tuyến [QuizTakingScreen](file:///d:/My_projects/Random_Essential/Quiz_Processor/quiz_flutter_ui/lib/screens/quiz_taking_screen.dart) tích hợp nhiều cơ chế xử lý nâng cao:

### A. Cơ chế Auto-Save & Tự phục hồi trạng thái thi (Resiliency)
Để phòng tránh mất mát dữ liệu bài làm của người dùng khi gặp các sự cố mất điện đột ngột hoặc tắt ứng dụng ngoài ý muốn, hệ thống tích hợp bộ ghi phiên thi tự động:
* **Ghi tự động (Auto-Save)**: Mỗi khi người dùng chọn một đáp án hoặc gắn cờ câu hỏi, một bộ đếm thời gian (Periodic Timer 1 giây) sẽ kích hoạt lưu trạng thái phiên làm bài hiện tại vào tệp tin `current_session.json` nằm tại thư mục gốc Workspace. Tệp tin này ghi nhận:
  - ID của đề thi (`exam_id`).
  - Danh sách câu hỏi đã xáo trộn (`questions`).
  - Các câu trả lời đã chọn (`selected_answers`).
  - Các câu hỏi đã gắn cờ (`flagged_questions`).
  - Chỉ số câu hỏi hiện tại (`current_index`).
  - Thời gian còn lại và thời gian đã trôi qua (`time_remaining`, `total_spent`).
* **Khôi phục (Resume)**: Khi người dùng truy cập lại một đề thi, ứng dụng sẽ quét tìm tệp tin `current_session.json`. Nếu phát hiện có thông tin trùng khớp với `exam_id`, ứng dụng hiển thị hộp thoại hỏi người dùng xem có muốn **Tiếp tục bài làm dở** từ vị trí trước đó hay không. Khi người dùng nộp bài, tệp tin tạm này sẽ tự động bị xóa bỏ.

### B. Hệ thống phím tắt bàn phím tùy biến (Keyboard Shortcuts)
Sử dụng Widget `KeyboardListener` bọc ngoài màn hình làm bài thi để bắt các sự kiện nhập liệu bàn phím (`KeyEvent`):

| Phím | Chức năng |
| :--- | :--- |
| `←` / `→` | Chuyển câu trước / sau |
| `Enter` / `Numpad Enter` | Sang câu tiếp theo (hoặc nộp bài nếu ở câu cuối) |
| `A`, `B`, `C`, `D`, `E` | Chọn đáp án tương ứng (legacy hardcoded) |
| `↑` / `↓` | Di chuyển focus giữa các phương án |
| `4` | Gạch bỏ / Khôi phục phương án đang focus (Elimination Mode) |
| `8` | Chuyển đổi chế độ xem cuộn toàn bộ đề / đơn câu |
| Phím tùy chỉnh | Ánh xạ từ `keyMappings` trong Settings (mặc định: 1/2/3/5/8/6) |

> **Lưu ý**: Phím `4` và `8` là reserved — không nên gán trong `keyMappings` để tránh xung đột.

### C. Chế độ Loại trừ Đáp án (Elimination Mode — v1.4.0)
* Mỗi phương án có nút gạch ngang (`Icons.strikethrough_s`) ở phía phải.
* Phương án bị loại sẽ có độ mờ 40% và chữ gạch ngang (`line-through`).
* Khi click chọn một phương án đang bị gạch bỏ, hệ thống tự động hủy gạch bỏ và chọn đáp án đó.
* Phím `↑/↓` di chuyển focus, phím `4` bật/tắt trạng thái gạch bỏ cho phương án đang focus.

### D. Chế độ Xem cuộn Toàn bộ Đề (Continuous Scroll — v1.4.0)
* Nút chuyển đổi trên AppBar (hoặc phím `8`) để chuyển giữa **đơn câu** và **cuộn toàn bộ**.
* Trong chế độ cuộn, thẻ câu hỏi đang được chọn có viền màu tím nổi bật + thẻ trạng thái `"Đang chọn"`.

---

## 4. Màn hình Phân tích & Trực quan hóa (Analytics & Charting)

Màn hình [AnalyticsScreen](file:///d:/My_projects/Random_Essential/Quiz_Processor/quiz_flutter_ui/lib/screens/analytics_screen.dart) truy vấn dữ liệu từ lịch sử SQLite để trực quan hóa:
* **Overview Card**: Thống kê nhanh tổng số lượt thi, tỷ lệ trả lời đúng trung bình và tổng thời gian làm bài (đổi sang phút).
* **Đồ thị hình quạt (Pie Chart)**: Sử dụng thư viện `fl_chart` hiển thị tỷ trọng phân bổ số lượng bài thi đã thực hiện theo từng môn học/thư mục.
* **Thanh hiệu suất (Linear Progress Indicator)**: Biểu diễn trực quan tỷ lệ phần trăm điểm số đạt được theo từng môn để phát hiện môn học đang bị đuối.
* **Cảnh báo phần yếu (Weak areas)**: Lọc ra tối đa 5 đề thi có tỷ lệ điểm trung bình thấp nhất (dưới 50% số câu đúng) để cảnh báo học sinh cần ôn tập lại.

---

## 5. Quản lý Tập tin trong Phòng thi (Folder Navigation)

Hệ thống cung cấp một trình duyệt thư mục ảo trực quan trong tab "Bài thi trực tuyến":
* Người dùng có thể tạo thư mục mới để gom nhóm các đề thi theo môn học hoặc theo chương. Nút **"Thư mục mới"** xuất hiện cả trong giao diện trống (placeholder) và thanh công cụ.
* Có tính năng **Di chuyển đề thi (`_moveItem`)**: Cho phép đổi chỗ một đề thi JSON hoặc một thư mục con sang một thư mục con khác trong thư mục `exams/` thông qua giao diện hộp thoại lựa chọn, sử dụng API đổi tên file của hệ điều hành (`Directory.rename`/`File.rename`).
* Hỗ trợ chức năng **Nhập đề thi (`import`)**: Hỗ trợ chọn tệp `.json` từ bên ngoài để chép vào cấu trúc thư mục của Workspace, đồng thời có thể thiết lập lại tiêu đề đề thi và thời gian thi trước khi ghi vào ổ đĩa.
* Sau khi chấm bài, nút **"Mở báo cáo câu lỗi"** và **"Hiển thị trong thư mục"** cho phép mở nhanh file kết quả sai sót trong Windows Explorer.

---

## 6. Màn hình Cài đặt (Settings Screen — v1.5.0)

Màn hình [SettingsScreen](file:///d:/My_projects/Random_Essential/Quiz_Processor/quiz_flutter_ui/lib/screens/settings_screen.dart) tổ chức cấu hình thành 4 nhóm:

| Nhóm | Cài đặt |
| :--- | :--- |
| **Bài kiểm tra** | Trộn câu ngẫu nhiên, Tự động chuyển câu, Bật/tắt phím tắt, Chế độ xem danh sách |
| **Phím tắt bàn phím** | Tùy biến phím cho A/B/C/D/E/Flag. Lưu ý phím 4 (Gạch bỏ) và 8 (Cuộn) là reserved |
| **Giao diện** | Dark mode, Kích thước cửa sổ (1280×720 đến 1920×1080) |
| **Hệ thống** | Thư mục làm việc (Workspace), Mở Exams/Digits, Sao lưu Zip, Kiểm tra cập nhật |

Phần **Phím tắt bàn phím** có thêm nút **"Đặt lại mặc định"** (v1.5.0) để khôi phục về bộ phím chuẩn `A=1, B=2, C=3, D=5, E=8, Flag=6`.

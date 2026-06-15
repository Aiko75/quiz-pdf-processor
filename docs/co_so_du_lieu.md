# Đặc tả Cơ sở dữ liệu Lịch sử học tập

Ứng dụng **Quiz Processor** sử dụng một cơ sở dữ liệu **SQLite** cục bộ có tên tệp là `quiz_history.db` đặt ngay tại thư mục làm việc (Workspace) để theo dõi và đánh giá kết quả học tập của người dùng qua các lượt thi.

---

## 1. Schema Bảng Lịch sử (`history`)

Dữ liệu của tất cả các lần làm bài được lưu trữ trong một bảng duy nhất có tên là `history`.

### Chi tiết cấu trúc các cột (Columns Specification)

| Tên cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | `PRIMARY KEY AUTOINCREMENT` | Khóa chính tự động tăng định danh cho mỗi lượt thi. |
| `exam_id` | `TEXT` | `NOT NULL` | Chuỗi UUID xác định đề thi (khớp với trường `id` trong đề thi JSON). |
| `exam_title`| `TEXT` | `NOT NULL` | Tiêu đề của đề thi tại thời điểm làm bài. |
| `folder` | `TEXT` | `NULL` | Tên thư mục cha chứa đề thi (phục vụ thống kê phân nhóm theo môn học). |
| `score_correct`| `INTEGER`| `NOT NULL` | Số câu trả lời đúng mà học sinh đạt được. |
| `score_total`| `INTEGER` | `NOT NULL` | Tổng số câu hỏi của đề thi tại thời điểm làm bài. |
| `time_spent_seconds`| `INTEGER`| `NOT NULL` | Tổng thời gian làm bài thực tế tính bằng giây. |
| `timestamp` | `TEXT` | `NOT NULL` | Mốc thời gian hoàn thành bài thi lưu ở định dạng chuỗi ISO 8601 (`YYYY-MM-DDTHH:MM:SS.SSS`). |
| `answers_json`| `TEXT` | `NOT NULL` | Chuỗi JSON ghi nhận chi tiết các câu trả lời mà người dùng đã chọn (ví dụ: `{"0": "A", "1": "C", "2": "B"}`). |

---

## 2. Lịch sử Nâng cấp Schema (Database Versioning)

Cơ sở dữ liệu được quản lý phiên bản (versioning) để đảm bảo tính tương thích khi cập nhật ứng dụng:
* **Phiên bản 1 (v1)**: Khởi tạo bảng dữ liệu lịch sử cơ bản chưa có cột phân loại nhóm môn học.
* **Phiên bản 2 (v2)**: Bổ sung cột `folder` kiểu dữ liệu `TEXT` để phân loại và gom nhóm thống kê kết quả thi theo môn học hoặc theo chương mục. Lệnh nâng cấp schema thực thi tự động qua hàm `onUpgrade` của lớp [DatabaseService](file:///d:/My_projects/Random_Essential/Quiz_Processor/quiz_flutter_ui/lib/services/database_service.dart):
  ```sql
  ALTER TABLE history ADD COLUMN folder TEXT;
  ```

---

## 3. Các Truy vấn Thống kê & Phân tích (Analytics Queries)

Hệ thống sử dụng các câu lệnh SQL tối ưu để kết xuất số liệu hiển thị lên màn hình Báo cáo học tập:

### A. Thống kê tổng quan học tập (Global Statistics)
Tính toán số lượng bài thi đã làm, tỷ lệ trả lời đúng tích lũy và tổng số giờ học tập:
```sql
SELECT 
    COUNT(*) as total_attempts, 
    SUM(score_correct) as total_correct, 
    SUM(score_total) as total_questions, 
    SUM(time_spent_seconds) as total_time 
FROM history;
```

### B. Thống kê hiệu suất theo Môn học (Performance by Folder)
Phân loại kết quả làm bài theo từng thư mục môn học, tính điểm phần trăm trung bình đạt được của mỗi môn:
```sql
SELECT 
    COALESCE(folder, 'Khác') as subject, 
    COUNT(*) as attempts, 
    SUM(score_correct) as correct, 
    SUM(score_total) as total,
    AVG(CAST(score_correct AS FLOAT) / score_total) * 100 as avg_percent
FROM history 
GROUP BY folder 
ORDER BY avg_percent DESC;
```

### C. Lọc danh sách đề thi yếu cần cải thiện (Weak Exams Analysis)
Tìm kiếm tối đa 5 đề thi có tỷ lệ trả lời đúng trung bình thấp nhất (dưới 50% số câu đúng) để đưa ra khuyến nghị học tập:
```sql
SELECT 
    exam_title, 
    folder, 
    AVG(CAST(score_correct AS FLOAT) / score_total) as avg_rate
FROM history
GROUP BY exam_id
HAVING avg_rate < 0.5
ORDER BY avg_rate ASC
LIMIT 5;
```

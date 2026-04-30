# Tăng tỉ lệ nhận diện đáp án đúng trong PDF LMS

## Mục tiêu
Tài liệu này ghi lại bài toán tăng tỉ lệ nhận diện đáp án đúng từ PDF LMS, đặc biệt là các phương án đã được trao đổi trước đó để cải thiện độ chính xác của parser hiện tại.

Hiện tại hệ thống đã nhận diện được phần lớn câu hỏi và đáp án, nhưng vẫn còn một số trường hợp chưa gán được `answer_label` hoặc gán chưa chắc chắn. Mục tiêu tiếp theo là kéo tỉ lệ nhận diện đáp án đúng lên cao hơn nữa bằng cách tận dụng thêm thông tin từ PDF thay vì chỉ dựa vào text thuần.

## Hiện trạng
Parser hiện tại đã có các tín hiệu sau:
- Nhận diện câu hỏi theo format LMS.
- Nhận diện option `A/B/C/D`.
- Nhận diện ký hiệu checkmark `\uf00c`.
- Fallback theo bold.
- Fallback theo màu chữ khác biệt.

Kết quả thực tế đã rất tốt, nhưng vẫn có các câu bị miss do:
- checkmark nằm ở dòng riêng
- option bị tách dòng
- marker đáp án bị lệch block
- PDF extract ra text không đồng nhất giữa các câu

## Các phương án đã bàn

### 1. Ghép đáp án theo vị trí hình học
Dùng `page_number`, `x0`, `y0` để map checkmark về option gần nhất thay vì chỉ lấy option cuối cùng đã đọc.

Khi nào hữu ích:
- checkmark đứng riêng một dòng
- option bị xuống dòng
- layout PDF lệch nhẹ giữa các câu

### 2. Parse theo block câu hỏi
Xem mỗi câu như một block gồm:
- question text
- 4 options
- marker đáp án

Sau đó mới chốt đáp án đúng trong block đó.

Khi nào hữu ích:
- tránh checkmark của câu sau ảnh hưởng câu trước
- tránh trạng thái parser chạy tuyến tính rồi lệch context

### 3. Gom option tách dòng
Xử lý các mẫu như:
- `a.`
- dòng nội dung ngay sau đó

hoặc
- option text bị cắt qua nhiều dòng

Khi nào hữu ích:
- option đúng bị tách đôi trong extract
- ký tự PDF làm mất phần nội dung cùng dòng

### 4. Kết hợp nhiều tín hiệu để xác định đáp án
Không chỉ dựa vào checkmark, mà kết hợp:
- checkmark
- bold
- màu chữ
- khoảng cách đến marker
- vị trí line trong block

Khi nào hữu ích:
- câu không có checkmark rõ ràng
- style của đáp án đúng vẫn còn trong PDF

### 5. Hậu kiểm sau parse
Sau khi parse xong, kiểm tra lại:
- mỗi câu có đúng 4 options chưa
- có đúng 1 đáp án chưa
- answer_label có bị None không
- checkmark có bị nhảy sang câu khác không

Khi nào hữu ích:
- bắt các lỗi lệch block
- sửa lại các câu bị thiếu tín hiệu

### 6. Confidence threshold
Nếu một câu không đủ tín hiệu chắc chắn, để trạng thái unknown thay vì đoán bừa.

Khi nào hữu ích:
- ưu tiên chính xác hơn là cố gán mọi câu
- tránh sai đáp án ở các câu khó nhận diện

### 7. Chuẩn hóa glyph/font đặc biệt
Một số PDF LMS dùng font nhúng hoặc ký tự đặc biệt khiến text extraction không ổn định.
Cần map thêm:
- checkmark
- bold giả
- ký tự unicode bị split

Khi nào hữu ích:
- khi dấu hiệu đúng tồn tại trong PDF nhưng extract ra không giống text thường

## Ưu tiên triển khai
Nếu mục tiêu là tăng tỉ lệ nhận diện đáp án đúng, nên đi theo thứ tự sau:
1. Ghép đáp án theo vị trí hình học.
2. Parse theo block câu hỏi.
3. Gom option tách dòng.
4. Dùng bộ quyết định nhiều tín hiệu.
5. Hậu kiểm toàn bộ output.

## Kết luận
Để tăng tỉ lệ nhận diện đáp án đúng, hướng hiệu quả nhất không phải là thêm nhiều regex hơn, mà là tăng khả năng hiểu cấu trúc block của PDF và dùng vị trí hình học để gán marker chính xác hơn. Đây là hướng có khả năng cải thiện phần còn thiếu trong các câu chưa có `answer_label`.

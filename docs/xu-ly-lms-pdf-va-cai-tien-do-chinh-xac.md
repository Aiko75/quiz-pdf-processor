# Xử lý PDF LMS và các hướng cải tiến độ chính xác

## Mục tiêu
Tài liệu này mô tả cách hệ thống hiện tại đang xử lý PDF LMS để nhận diện câu hỏi và đáp án, đồng thời ghi lại các hướng cải tiến có thể giúp tăng tỉ lệ nhận diện đáp án đúng từ mức hiện tại lên cao hơn nữa.

## Hiện trạng
- PDF LMS có cấu trúc không chuẩn như quiz PDF thông thường.
- Câu hỏi, option và ký hiệu đánh dấu đáp án đúng không nằm trên cùng một dòng.
- Một số câu được nhận diện đúng nhờ:
  - pattern câu hỏi LMS `Câu h ỏ i N`
  - option `a. / b. / c. / d.`
  - ký hiệu đặc biệt dạng `\uf00c` để đánh dấu đáp án đúng
  - fallback từ bold / màu chữ nếu không có checkmark
- Kết quả hiện tại đã detect được khoảng `725/750` câu hỏi, tức là chất lượng đã rất cao nhưng vẫn còn một phần nhỏ bị miss hoặc gán sai đáp án.

## Cách xử lý hiện tại
1. Trích xuất line có style từ PDF bằng PyMuPDF.
2. Nhận diện PDF theo format LMS.
3. Preprocess line để loại noise và header LMS.
4. Gom option theo cụm câu hỏi.
5. Dùng nhiều tín hiệu để xác định đáp án đúng:
   - checkmark
   - bold
   - màu chữ khác biệt
6. Xuất DOCX bản có đáp án và bản luyện tập.

## Những nguyên nhân chính khiến chưa đạt 750/750
- Checkmark không luôn đi kèm trực tiếp với option, đôi khi nằm ở dòng riêng.
- Một số option bị tách thành nhiều dòng khi extract từ PDF.
- Một số câu có layout lệch nhẹ giữa các trang hoặc khối nội dung.
- Một số ký tự đặc biệt / font nhúng của LMS có thể làm mất tín hiệu style.
- Có thể có vài câu bị dính metadata hoặc bị cắt ranh giới block chưa đúng.

## Các hướng cải tiến khả thi

### 1. Ghép đáp án theo vị trí hình học
Thay vì chỉ lấy option cuối cùng trước checkmark, nên xác định option đúng dựa trên khoảng cách gần nhất theo `page_number`, `y0`, `x0`.

Lợi ích:
- Giảm lỗi lệch khi checkmark nằm xa option text.
- Tốt hơn khi PDF tách dòng phức tạp.

### 2. Parse theo block câu hỏi thay vì luồng line thuần túy
Nên coi mỗi câu là một block gồm:
- question text
- 4 options
- marker đáp án đúng

Sau đó mới chốt câu và đáp án.

Lợi ích:
- Giảm tình trạng checkmark của câu sau ảnh hưởng câu trước.
- Dễ kiểm soát boundary giữa các câu.

### 3. Hợp nhất các tín hiệu đáp án thành một bộ chấm điểm
Thay vì chỉ ưu tiên một rule, có thể dùng điểm tin cậy:
- checkmark: điểm cao nhất
- bold: điểm cao
- color khác thường: điểm trung bình
- vị trí gần marker: điểm cộng thêm

Cách này hữu ích khi một câu thiếu checkmark nhưng vẫn còn style.

### 4. Xử lý option tách dòng tốt hơn
Một số option bị chia thành:
- `a.`
- dòng nội dung bên dưới

Nên gom chúng lại trước khi quyết định câu và đáp án.

Lợi ích:
- Tránh mất option đúng do line split.
- Tăng độ ổn định khi PDF bị render xấu.

### 5. Hậu kiểm sau parse
Sau khi parse xong, kiểm tra lại toàn bộ output:
- mỗi câu có đúng 4 options chưa
- mỗi câu có đúng 1 đáp án chưa
- có câu nào answer bị None không
- có câu nào marker bị gán sang câu kế tiếp không

Lợi ích:
- Bắt các lỗi lệch logic còn sót.
- Có thể sửa tự động một số case đơn giản.

### 6. Thêm confidence threshold
Nếu một câu không đủ tín hiệu chắc chắn, đánh dấu là unknown thay vì đoán.

Lợi ích:
- Tăng độ chính xác thực tế.
- Giảm câu bị gán sai đáp án.

### 7. Chuẩn hóa font / glyph đặc biệt
Nếu LMS dùng font nhúng hoặc ký hiệu thay thế, nên map thêm:
- ký tự checkmark
- ký tự bold giả
- ký tự bị tách dấu tiếng Việt

Lợi ích:
- Giảm miss do extract text không đồng nhất.

## Khuyến nghị ưu tiên
Nếu muốn tiếp tục nâng chất lượng từ `725/750`, nên làm theo thứ tự:
1. Ghép đáp án theo vị trí hình học.
2. Parse theo block câu hỏi.
3. Gom option tách dòng chặt hơn.
4. Thêm bộ chấm điểm nhiều tín hiệu.
5. Hậu kiểm và sửa lệch.

## Kết luận
Hệ thống hiện tại đã đạt mức rất cao và phần còn thiếu chủ yếu nhiều khả năng đến từ layout PDF LMS, tách dòng, và ghép marker chưa đủ mạnh. Vẫn còn dư địa cải thiện, nhưng muốn tiến gần `750/750` thì nên tập trung vào ghép theo block và vị trí thay vì chỉ tăng regex.

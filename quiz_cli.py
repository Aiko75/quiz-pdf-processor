import sys
import json
import argparse
import traceback
from pathlib import Path

# Thêm đường dẫn hiện tại vào sys.path để đảm bảo import được các module local
sys.path.append(str(Path(__file__).parent))

from quiz_pdf_processor import (
    process_folder,
    validate_folder,
    grade_quiz_files,
    generate_quiz_from_file,
    generate_quiz_with_range,
    import_quiz_file,
)

def emit(data_type, **kwargs):
    """Gửi dữ liệu JSON ra stdout để Flutter đọc."""
    print(json.dumps({"type": data_type, **kwargs}, ensure_ascii=False))
    sys.stdout.flush()

def format_question_list(items):
    if not items:
        return "Không có"
    text = ", ".join(str(value) for value in items)
    if len(text) > 280:
        return text[:280] + " ..."
    return text

def main():
    parser = argparse.ArgumentParser(description="Quiz Processor CLI for Flutter UI")
    parser.add_argument("--action", required=True, choices=["process", "validate", "report", "grade", "generate", "import", "preview", "doublecheck", "add_feedback"])
    parser.add_argument("--input", help="Thư mục hoặc file đầu vào")
    parser.add_argument("--output", help="Thư mục đầu ra")
    parser.add_argument("--answer-file", help="File đáp án")
    parser.add_argument("--submission-file", help="File bài làm")
    parser.add_argument("--count", type=int, default=40, help="Số lượng câu tạo đề")
    parser.add_argument("--from-q", type=int, default=0, help="Câu bắt đầu")
    parser.add_argument("--to-q", type=int, default=0, help="Câu kết thúc (0 = hết)")
    parser.add_argument("--gen-answer", action="store_true", help="Tạo file đáp án kèm theo")
    parser.add_argument("--interactive", action="store_true", help="Tạo bài thi tương tác JSON")
    parser.add_argument("--time-limit", type=int, default=0, help="Giới hạn thời gian (phút)")
    parser.add_argument("--title", help="Tên bài thi")
    parser.add_argument("--workspace", help="Đường dẫn thư mục làm việc (workspace)")
    parser.add_argument("--folder", default="", help="Thư mục con đích trong workspace/exams")
    parser.add_argument("--question-index", type=int, help="Chỉ số câu hỏi báo lỗi")
    parser.add_argument("--message", help="Mô tả lỗi câu hỏi")
    
    args = parser.parse_args()
    
    try:
        output_dir = Path(args.output).resolve() if args.output else None
        
        if args.action == "process":
            input_path = Path(args.input).resolve()
            emit("log", message="=== BẮT ĐẦU XỬ LÝ PDF -> DOCX ===")
            emit("log", message=f"Input: {input_path}")
            emit("log", message=f"Output: {output_dir}")
            
            from quiz_core.parsing import process_pdf_file
            from quiz_core import process_folder
            
            if input_path.is_file():
                results = [process_pdf_file(input_path, output_dir)]
            else:
                results = process_folder(input_path, output_dir)
                
            for r in results:
                if r["status"] == "ok":
                    emit("log", message=f"[OK] {r['pdf']} -> {r['question_count']} câu")
                else:
                    emit("log", message=f"[BỎ QUA] {r['pdf']} - không nhận diện được câu hỏi")
            emit("result", status="success", message="Xử lý hoàn tất")

        elif args.action == "validate":
            input_dir = Path(args.input).resolve()
            emit("log", message="=== BẮT ĐẦU KIỂM TRA ĐỐI CHIẾU ===")
            results = validate_folder(input_dir, output_dir)
            for i in results:
                emit("log", message=f"\n--- {i.pdf_name} ---")
                emit("log", message=f"Gốc={i.original_questions}, Nhận diện={i.recognized_answers}")
                emit("log", message=f"Lệch={i.mismatch_count}, Thiếu highlight={i.no_highlight_count}, Đa highlight={i.multi_highlight_count}")
                if getattr(i, "report_file", ""):
                    emit("log", message=f"File báo cáo: {i.report_file}")
            emit("result", status="success", message="Kiểm tra hoàn tất")

        elif args.action == "report":
            input_dir = Path(args.input).resolve()
            emit("log", message="=== BẮT ĐẦU TẠO BÁO CÁO DOCX ===")
            results = validate_folder(input_dir, output_dir)
            for i in results:
                emit("log", message=f"\n--- {i.pdf_name} ---")
                rep_file = getattr(i, "report_file", "(chưa tạo được)")
                emit("log", message=f"Báo cáo: {rep_file}")
                emit("log", message=f"Tổng câu: {i.original_questions}, đúng={i.correct_count}, sai={i.wrong_count}, miss={i.missed_count}")
            emit("result", status="success", message="Tạo báo cáo hoàn tất")

        elif args.action == "grade":
            ans_file = Path(args.answer_file).resolve()
            sub_file = Path(args.submission_file).resolve()
            emit("log", message="=== BẮT ĐẦU CHẤM BÀI ===")
            emit("log", message=f"Bài làm: {sub_file}")
            emit("log", message=f"Đáp án: {ans_file}")
            
            result = grade_quiz_files(submission_file=sub_file, answer_file=ans_file, output_dir=output_dir)
            
            emit("log", message=f"Số câu so sánh: {result.compared_questions}")
            if result.pairing_strategy == "question_number":
                emit("log", message="[LƯU Ý] Hệ thống ghép câu theo số thứ tự Câu N.")
            
            emit("log", message=f"Số câu đúng: {result.correct_count}")
            emit("log", message=f"Danh sách đúng: {format_question_list(result.correct_questions)}")
            emit("log", message=f"Số câu sai: {result.wrong_count}")
            emit("log", message=f"Danh sách sai: {format_question_list(result.wrong_questions)}")
            emit("log", message=f"Số câu chưa làm: {result.unanswered_count}")
            
            if result.auto_swapped_files:
                emit("log", message="[LƯU Ý] Đã tự động đổi vai trò 2 file.")
            
            emit("log", message=f"File kết quả sai: {result.wrong_output_file}")
            emit("result", status="success", message="Chấm bài hoàn tất", score={"correct": result.correct_count, "wrong": result.wrong_count, "total": result.compared_questions, "report": result.wrong_output_file})

        elif args.action == "generate":
            ans_file = Path(args.answer_file).resolve()
            emit("log", message="=== BẮT ĐẦU TẠO ĐỀ TRẮC NGHIỆM ===")
            
            if args.from_q > 0:
                result = generate_quiz_with_range(
                    source_file=ans_file,
                    output_dir=output_dir,
                    from_question=args.from_q,
                    to_question=args.to_q if args.to_q > 0 else None,
                    interactive=args.interactive,
                    gen_answer=args.gen_answer,
                    time_limit=args.time_limit,
                    workspace=args.workspace,
                    sub_folder=args.folder
                )
            else:
                result = generate_quiz_from_file(
                    source_file=ans_file,
                    output_dir=output_dir,
                    question_count=args.count,
                    interactive=args.interactive,
                    gen_answer=args.gen_answer,
                    time_limit=args.time_limit,
                    workspace=args.workspace,
                    sub_folder=args.folder
                )
            
            emit("log", message=f"Số câu tạo thực tế: {result.generated_count}")
            emit("log", message=f"File đề tạo mới: {result.quiz_output_file}")
            emit("result", status="success", message="Tạo đề hoàn tất", file=result.quiz_output_file)

        elif args.action == "import":
            input_file = Path(args.input).resolve()
            emit("log", message="=== BẮT ĐẦU NHẬP ĐỀ ===")
            emit("log", message=f"File: {input_file}")
            json_path = import_quiz_file(
                source_file=input_file,
                title=args.title if args.title else None,
                time_limit=args.time_limit,
                workspace=args.workspace,
                sub_folder=args.folder
            )
            emit("log", message=f"Nhập thành công!")
            emit("result", status="success", message="Nhập đề hoàn tất", file=str(json_path))

        elif args.action == "preview":
            from quiz_core.parsing import extract_styled_lines, parse_questions
            input_file = Path(args.input).resolve()
            emit("log", message=f"Đang xem trước: {input_file.name}...")
            
            lines = extract_styled_lines(input_file)
            questions = parse_questions(lines)
            
            preview_data = []
            for i, q in enumerate(questions):
                preview_data.append({
                    "id": i,
                    "question": q.question,
                    "options": {opt.label: opt.text for opt in q.options},
                    "correct_answer": q.answer_label
                })
            
            emit("result", status="success", questions=preview_data)

        elif args.action == "doublecheck":
            ans_file = Path(args.answer_file).resolve()
            emit("log", message="=== BẮT ĐẦU KIỂM ĐỊNH CẤU TRÚC CÂU ===")
            emit("log", message=f"File nguồn: {ans_file}")
            
            from quiz_core.parsing import parse_questions_for_grading
            from quiz_core.validation import double_check_quiz_structure, save_auto_feedback_to_loop
            
            questions = parse_questions_for_grading(ans_file)
            if not questions:
                raise ValueError("Không đọc được câu hỏi nào từ file nguồn")
                
            errors = double_check_quiz_structure(questions)
            if args.workspace:
                save_auto_feedback_to_loop(args.workspace, errors, str(ans_file))
            
            emit("log", message=f"Tổng số câu kiểm tra: {len(questions)}")
            
            if not errors:
                emit("log", message="[OK] Cấu trúc tất cả các câu hỏi đều hợp lệ!")
                emit("result", status="success", message="Kiểm định hoàn tất. Không phát hiện lỗi cấu trúc.")
            else:
                total_errors = sum(len(e["errors"]) for e in errors)
                emit("log", message=f"[CẢNH BÁO] Phát hiện {len(errors)} câu lỗi cấu trúc (Tổng cộng {total_errors} lỗi):")
                
                for err in errors:
                    idx = err["question_index"]
                    log_idx = err["logical_index"] if err["logical_index"] is not None else idx
                    emit("log", message=f"\n--- Câu {idx} (STT trong file: {log_idx}) ---")
                    for q_err in err["errors"]:
                        emit("log", message=f"Lỗi: {q_err['message']}")
                    emit("log", message=f"Nội dung câu hỏi: {err['question_text']}")
                    emit("log", message="Các đáp án nhận diện được:")
                    for lbl, txt in sorted(err["options"].items()):
                        emit("log", message=f"  {lbl}. {txt}")
                
                emit("result", status="success", message=f"Kiểm định hoàn tất. Phát hiện {len(errors)} câu lỗi cấu trúc.")

        elif args.action == "add_feedback":
            ans_file = Path(args.answer_file).resolve()
            q_idx = int(args.question_index) if args.question_index is not None else 0
            msg = args.message if args.message else ""
            
            emit("log", message="=== BÁO LỖI CÂU HỎI THỦ CÔNG ===")
            emit("log", message=f"File nguồn: {ans_file.name}")
            emit("log", message=f"Câu số: {q_idx}")
            emit("log", message=f"Nội dung lỗi: {msg}")
            
            from quiz_core.validation import add_manual_feedback
            add_manual_feedback(args.workspace, str(ans_file), q_idx, msg)
            
            emit("log", message="[OK] Đã ghi nhận báo lỗi thành công!")
            emit("result", status="success", message="Ghi nhận báo lỗi thành công.")

    except Exception as e:
        emit("result", status="error", message=str(e), traceback=traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()

import argparse
from pathlib import Path

from quiz_core import (
    GradingResult,
    LineData,
    OptionData,
    QuestionData,
    QuizGenerateResult,
    QuizOptionState,
    QuizQuestionState,
    ValidationResult,
    generate_validation_report_for_pdf,
    build_wrong_questions_docx,
    generate_quiz_from_file,
    grade_quiz_files,
    process_folder,
    validate_folder,
)

__all__ = [
    "build_wrong_questions_docx",
    "generate_quiz_from_file",
    "grade_quiz_files",
    "generate_validation_report_for_pdf",
    "process_folder",
    "validate_folder",
    "LineData",
    "OptionData",
    "QuestionData",
    "ValidationResult",
    "QuizOptionState",
    "QuizQuestionState",
    "GradingResult",
    "QuizGenerateResult",
    "main",
]


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Lọc đề trắc nghiệm từ PDF, giữ lại câu hỏi + 4 đáp án, "
            "xuất 2 file: có đáp án và file để làm; hoặc chấm bài từ file bài làm."
        )
    )
    parser.add_argument(
        "--input",
        default="files",
        help="Thư mục chứa file PDF đầu vào (mặc định: files)",
    )
    parser.add_argument(
        "--output",
        default="processed_quiz",
        help="Thư mục output (mặc định: processed_quiz)",
    )
    parser.add_argument(
        "--grade-submission",
        help="Đường dẫn file bài làm đã tô đáp án (PDF/DOCX)",
    )
    parser.add_argument(
        "--grade-answer",
        help="Đường dẫn file đáp án (PDF/DOCX)",
    )
    args = parser.parse_args()

    output_dir = Path(args.output).resolve()

    if args.grade_submission or args.grade_answer:
        if not args.grade_submission or not args.grade_answer:
            raise ValueError(
                "Khi dùng chế độ chấm bài, cần truyền đủ --grade-submission và --grade-answer"
            )

        submission_file = Path(args.grade_submission).resolve()
        answer_file = Path(args.grade_answer).resolve()

        result = grade_quiz_files(
            submission_file=submission_file,
            answer_file=answer_file,
            output_dir=output_dir,
        )

        print("=== KẾT QUẢ CHẤM BÀI ===")
        print(f"Bài làm: {result.submission_file}")
        print(f"Đáp án: {result.answer_file}")
        print(f"Số câu so sánh: {result.compared_questions}")
        if result.pairing_strategy == "question_number":
            print("[LƯU Ý] Hệ thống ghép câu theo số thứ tự Câu N để tránh lệch do đảo vị trí câu hỏi.")
        elif result.pairing_strategy == "index":
            print(
                "[CẢNH BÁO] Không ghép đủ theo nội dung/số câu, hệ thống phải ghép theo vị trí. "
                "Kết quả có thể bị lệch."
            )
            print(
                "[CHI TIẾT] Số cặp khớp theo nội dung="
                f"{result.matched_by_text_count}, theo số câu={result.matched_by_number_count}"
            )
        print(f"Số câu đúng: {result.correct_count}")
        print(f"Danh sách câu đúng: {result.correct_questions}")
        print(f"Số câu sai: {result.wrong_count}")
        print(f"Danh sách câu sai: {result.wrong_questions}")
        print(f"Số câu chưa làm: {result.unanswered_count}")
        print(f"Danh sách câu chưa làm: {result.unanswered_questions}")
        print(f"Số câu bỏ qua: {result.skipped_count}")
        print(f"Danh sách câu bỏ qua: {result.skipped_questions}")
        if result.skipped_details:
            print("Chi tiết câu bỏ qua:")
            for detail in result.skipped_details:
                print(f"- {detail}")
        print(f"Số câu đã làm (đúng + sai): {result.answered_count}")
        if result.auto_swapped_files:
            print("[LƯU Ý] Đã tự động đổi vai trò 2 file vì phát hiện bạn chọn nhầm file đáp án/bài làm.")
        print(f"File các câu lỗi (chưa làm + sai): {result.wrong_output_file}")
        return

    input_dir = Path(args.input).resolve()
    process_folder(input_dir, output_dir)


if __name__ == "__main__":
    main()

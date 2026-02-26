import os
from pathlib import Path
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from quiz_pdf_processor import (
    build_knowledge_gap_report,
    generate_quiz_from_file,
    grade_quiz_files,
    process_folder,
    validate_folder,
)


class QuizProcessorApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Quiz PDF Processor")
        self.root.geometry("1060x690")
        self._apply_window_icon()

        self.workspace_dir = self.resolve_workspace_dir()
        input_default = self.workspace_dir / "files"
        output_default = self.workspace_dir / "processed_quiz"
        input_default.mkdir(parents=True, exist_ok=True)
        output_default.mkdir(parents=True, exist_ok=True)

        self.input_var = tk.StringVar(value=str(input_default.resolve()))
        self.output_var = tk.StringVar(value=str(output_default.resolve()))
        self.answer_file_var = tk.StringVar()
        self.submission_file_var = tk.StringVar()
        self.knowledge_files_var = tk.StringVar()
        self.ollama_model_var = tk.StringVar(value="llama3.1:8b")
        self.error_file_var = tk.StringVar()
        self.quiz_count_var = tk.IntVar(value=40)

        self._build_ui()

    def _apply_window_icon(self) -> None:
        icon_path = Path(__file__).resolve().parent / "assets" / "quiz_app.ico"
        if icon_path.exists():
            try:
                self.root.iconbitmap(str(icon_path))
            except Exception:
                pass

    def resolve_workspace_dir(self) -> Path:
        if getattr(sys, "frozen", False):
            base_dir = Path(sys.executable).resolve().parent
        else:
            base_dir = Path(__file__).resolve().parent
        return (base_dir / "quiz_workspace").resolve()

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root, padding=12)
        container.pack(fill=tk.BOTH, expand=True)

        ttk.Label(container, text="Thư mục PDF đầu vào:").grid(row=0, column=0, sticky="w")
        ttk.Entry(container, textvariable=self.input_var, width=90).grid(
            row=1, column=0, sticky="we", padx=(0, 8)
        )
        ttk.Button(container, text="Chọn...", command=self.pick_input).grid(row=1, column=1)
        ttk.Button(container, text="Mở", command=self.open_input_dir).grid(row=1, column=2)

        ttk.Label(container, text="Thư mục output:").grid(row=2, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(container, textvariable=self.output_var, width=90).grid(
            row=3, column=0, sticky="we", padx=(0, 8)
        )
        ttk.Button(container, text="Chọn...", command=self.pick_output).grid(row=3, column=1)
        ttk.Button(container, text="Mở", command=self.open_output_dir).grid(row=3, column=2)

        ttk.Label(container, text="File đáp án (PDF/DOCX):").grid(row=4, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(container, textvariable=self.answer_file_var, width=90).grid(
            row=5, column=0, sticky="we", padx=(0, 8)
        )
        ttk.Button(container, text="Chọn...", command=self.pick_answer_file).grid(row=5, column=1)
        ttk.Button(container, text="Mở", command=self.open_answer_file).grid(row=5, column=2)

        ttk.Label(container, text="File bài làm đã tô (PDF/DOCX):").grid(
            row=6, column=0, sticky="w", pady=(10, 0)
        )
        ttk.Entry(container, textvariable=self.submission_file_var, width=90).grid(
            row=7, column=0, sticky="we", padx=(0, 8)
        )
        ttk.Button(container, text="Chọn...", command=self.pick_submission_file).grid(row=7, column=1)
        ttk.Button(container, text="Mở", command=self.open_submission_file).grid(row=7, column=2)

        ttk.Label(container, text="File kiến thức (PDF/PPTX/DOCX/TXT, chọn nhiều):").grid(
            row=8, column=0, sticky="w", pady=(10, 0)
        )
        ttk.Entry(container, textvariable=self.knowledge_files_var, width=90).grid(
            row=9, column=0, sticky="we", padx=(0, 8)
        )
        ttk.Button(container, text="Chọn...", command=self.pick_knowledge_files).grid(row=9, column=1)
        ttk.Button(container, text="Mở file đầu", command=self.open_knowledge_file).grid(row=9, column=2)

        ttk.Label(container, text="Model Ollama dùng để phân tích:").grid(
            row=10, column=0, sticky="w", pady=(10, 0)
        )
        ttk.Entry(container, textvariable=self.ollama_model_var, width=40).grid(
            row=11, column=0, sticky="w"
        )

        ttk.Label(container, text="File các câu lỗi:").grid(row=12, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(container, textvariable=self.error_file_var, width=90).grid(
            row=13, column=0, sticky="we", padx=(0, 8)
        )
        ttk.Button(container, text="Mở", command=self.open_error_file).grid(row=13, column=2)

        count_frame = ttk.Frame(container)
        count_frame.grid(row=14, column=0, columnspan=3, sticky="we", pady=(10, 0))
        ttk.Label(count_frame, text="Số lượng câu tạo đề:").pack(side=tk.LEFT)
        self.quiz_count_scale = tk.Scale(
            count_frame,
            from_=1,
            to=300,
            orient=tk.HORIZONTAL,
            length=320,
            variable=self.quiz_count_var,
            showvalue=False,
        )
        self.quiz_count_scale.pack(side=tk.LEFT, padx=(8, 8))
        ttk.Entry(count_frame, textvariable=self.quiz_count_var, width=8).pack(side=tk.LEFT)

        action_frame = ttk.Frame(container)
        action_frame.grid(row=15, column=0, columnspan=3, sticky="w", pady=(12, 8))

        self.process_button = ttk.Button(
            action_frame, text="1) Xử lý PDF -> DOCX", command=self.start_process
        )
        self.process_button.pack(side=tk.LEFT, padx=(0, 8))

        self.validate_button = ttk.Button(
            action_frame, text="2) Kiểm tra đối chiếu", command=self.start_validate
        )
        self.validate_button.pack(side=tk.LEFT)

        self.grade_button = ttk.Button(
            action_frame, text="3) Chấm bài", command=self.start_grade
        )
        self.grade_button.pack(side=tk.LEFT, padx=(8, 0))

        self.generate_button = ttk.Button(
            action_frame, text="4) Tạo đề trắc nghiệm", command=self.start_generate
        )
        self.generate_button.pack(side=tk.LEFT, padx=(8, 0))

        self.open_output_button = ttk.Button(
            action_frame, text="Mở output", command=self.open_output_dir
        )
        self.open_output_button.pack(side=tk.LEFT, padx=(8, 0))

        ttk.Label(container, text="Log:").grid(row=16, column=0, sticky="w")
        self.log_text = ScrolledText(container, height=24, wrap=tk.WORD)
        self.log_text.grid(row=17, column=0, columnspan=3, sticky="nsew")

        container.columnconfigure(0, weight=1)
        container.rowconfigure(17, weight=1)

    def open_path(self, path_text: str, expect_directory: bool) -> None:
        path = Path(path_text.strip()) if path_text.strip() else None
        if path is None or not path.exists():
            messagebox.showerror("Lỗi", "Đường dẫn không tồn tại.")
            return
        if expect_directory and not path.is_dir():
            messagebox.showerror("Lỗi", "Đường dẫn phải là thư mục.")
            return
        if not expect_directory and not path.is_file():
            messagebox.showerror("Lỗi", "Đường dẫn phải là file.")
            return

        os.startfile(str(path))

    def open_input_dir(self) -> None:
        self.open_path(self.input_var.get(), expect_directory=True)

    def open_output_dir(self) -> None:
        self.open_path(self.output_var.get(), expect_directory=True)

    def open_answer_file(self) -> None:
        self.open_path(self.answer_file_var.get(), expect_directory=False)

    def open_submission_file(self) -> None:
        self.open_path(self.submission_file_var.get(), expect_directory=False)

    def open_knowledge_file(self) -> None:
        first_file = self.get_knowledge_files()[0] if self.get_knowledge_files() else ""
        if not first_file:
            messagebox.showerror("Lỗi", "Chưa chọn file kiến thức.")
            return
        self.open_path(first_file, expect_directory=False)

    def open_error_file(self) -> None:
        self.open_path(self.error_file_var.get(), expect_directory=False)

    def pick_input(self) -> None:
        selected = filedialog.askdirectory(initialdir=self.input_var.get() or ".")
        if selected:
            self.input_var.set(selected)

    def pick_output(self) -> None:
        selected = filedialog.askdirectory(initialdir=self.output_var.get() or ".")
        if selected:
            self.output_var.set(selected)

    def pick_answer_file(self) -> None:
        selected = filedialog.askopenfilename(
            title="Chọn file đáp án",
            filetypes=[("Quiz file", "*.pdf *.docx"), ("All files", "*.*")],
        )
        if selected:
            self.answer_file_var.set(selected)

    def pick_submission_file(self) -> None:
        selected = filedialog.askopenfilename(
            title="Chọn file bài làm",
            filetypes=[("Quiz file", "*.pdf *.docx"), ("All files", "*.*")],
        )
        if selected:
            self.submission_file_var.set(selected)

    def pick_knowledge_files(self) -> None:
        selected_files = filedialog.askopenfilenames(
            title="Chọn các file kiến thức",
            filetypes=[
                ("Knowledge files", "*.pdf *.docx *.pptx *.txt *.md"),
                ("All files", "*.*"),
            ],
        )
        if selected_files:
            self.knowledge_files_var.set(";".join(selected_files))

    def get_knowledge_files(self) -> list[str]:
        raw = self.knowledge_files_var.get().strip()
        if not raw:
            return []
        return [item.strip() for item in raw.split(";") if item.strip()]

    def log(self, message: str) -> None:
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def set_running(self, running: bool) -> None:
        state = tk.DISABLED if running else tk.NORMAL
        self.process_button.configure(state=state)
        self.validate_button.configure(state=state)
        self.grade_button.configure(state=state)
        self.generate_button.configure(state=state)
        self.open_output_button.configure(state=state)

    def start_process(self) -> None:
        self.run_background(self.process_action)

    def start_validate(self) -> None:
        self.run_background(self.validate_action)

    def start_grade(self) -> None:
        self.error_file_var.set("")
        answer_file = Path(self.answer_file_var.get().strip()) if self.answer_file_var.get().strip() else None
        submission_file = (
            Path(self.submission_file_var.get().strip())
            if self.submission_file_var.get().strip()
            else None
        )
        output_dir = Path(self.output_var.get().strip())
        knowledge_files = [Path(file_path) for file_path in self.get_knowledge_files()]
        ollama_model = self.ollama_model_var.get().strip() or "llama3.1:8b"

        if answer_file is None or not answer_file.exists() or not answer_file.is_file():
            messagebox.showerror("Lỗi", "File đáp án không hợp lệ.")
            return
        if submission_file is None or not submission_file.exists() or not submission_file.is_file():
            messagebox.showerror("Lỗi", "File bài làm không hợp lệ.")
            return
        for knowledge_file in knowledge_files:
            if not knowledge_file.exists() or not knowledge_file.is_file():
                messagebox.showerror("Lỗi", f"File kiến thức không hợp lệ: {knowledge_file}")
                return

        self.set_running(True)

        def worker() -> None:
            try:
                self.grade_action(submission_file, answer_file, output_dir, knowledge_files, ollama_model)
            except Exception as error:
                self.root.after(0, lambda: messagebox.showerror("Lỗi", str(error)))
            finally:
                self.root.after(0, lambda: self.set_running(False))

        threading.Thread(target=worker, daemon=True).start()

    def start_generate(self) -> None:
        answer_file = Path(self.answer_file_var.get().strip()) if self.answer_file_var.get().strip() else None
        output_dir = Path(self.output_var.get().strip())

        if answer_file is None or not answer_file.exists() or not answer_file.is_file():
            messagebox.showerror("Lỗi", "Chọn file đáp án hợp lệ để tạo đề.")
            return

        try:
            requested_count = int(self.quiz_count_var.get())
        except (TypeError, ValueError):
            messagebox.showerror("Lỗi", "Số lượng câu không hợp lệ.")
            return

        if requested_count <= 0:
            messagebox.showerror("Lỗi", "Số lượng câu phải lớn hơn 0.")
            return

        self.set_running(True)

        def worker() -> None:
            try:
                self.generate_action(answer_file, output_dir, requested_count)
            except Exception as error:
                self.root.after(0, lambda: messagebox.showerror("Lỗi", str(error)))
            finally:
                self.root.after(0, lambda: self.set_running(False))

        threading.Thread(target=worker, daemon=True).start()

    def run_background(self, action) -> None:
        input_dir = Path(self.input_var.get().strip())
        output_dir = Path(self.output_var.get().strip())

        if not input_dir.exists() or not input_dir.is_dir():
            messagebox.showerror("Lỗi", "Thư mục đầu vào không hợp lệ.")
            return

        self.set_running(True)

        def worker() -> None:
            try:
                action(input_dir, output_dir)
            except Exception as error:
                self.root.after(0, lambda: messagebox.showerror("Lỗi", str(error)))
            finally:
                self.root.after(0, lambda: self.set_running(False))

        threading.Thread(target=worker, daemon=True).start()

    def process_action(self, input_dir: Path, output_dir: Path) -> None:
        self.root.after(0, lambda: self.log("=== BẮT ĐẦU XỬ LÝ ==="))
        self.root.after(0, lambda: self.log(f"Input: {input_dir}"))
        self.root.after(0, lambda: self.log(f"Output: {output_dir}"))

        results = process_folder(input_dir, output_dir)

        for result in results:
            if result["status"] == "ok":
                self.root.after(
                    0,
                    lambda r=result: self.log(
                        f"[OK] {r['pdf']} -> {r['question_count']} câu"
                    ),
                )
            else:
                self.root.after(
                    0,
                    lambda r=result: self.log(
                        f"[BỎ QUA] {r['pdf']} - không nhận diện được câu hỏi"
                    ),
                )

        self.root.after(0, lambda: self.log("=== HOÀN TẤT XỬ LÝ ===\n"))

    def validate_action(self, input_dir: Path, output_dir: Path) -> None:
        self.root.after(0, lambda: self.log("=== BẮT ĐẦU KIỂM TRA ==="))
        self.root.after(0, lambda: self.log(f"Input: {input_dir}"))
        self.root.after(0, lambda: self.log(f"Output: {output_dir}"))

        results = validate_folder(input_dir, output_dir)

        for item in results:
            self.root.after(0, lambda i=item: self.log(f"\n--- {i.pdf_name} ---"))
            self.root.after(
                0,
                lambda i=item: self.log(
                    "original_questions="
                    f"{i.original_questions}, recognized_answers={i.recognized_answers}"
                ),
            )
            self.root.after(
                0,
                lambda i=item: self.log(
                    "answer_doc_questions="
                    f"{i.answer_doc_questions}, practice_doc_questions={i.practice_doc_questions}"
                ),
            )
            self.root.after(
                0,
                lambda i=item: self.log(
                    "mismatch="
                    f"{i.mismatch_count}, no_highlight={i.no_highlight_count}, "
                    f"multi_highlight={i.multi_highlight_count}, "
                    f"practice_has_highlight={i.practice_highlight_count}"
                ),
            )

        self.root.after(0, lambda: self.log("\n=== HOÀN TẤT KIỂM TRA ===\n"))

    def grade_action(
        self,
        submission_file: Path,
        answer_file: Path,
        output_dir: Path,
        knowledge_files: list[Path],
        ollama_model: str,
    ) -> None:
        def format_question_list(items) -> str:
            if not items:
                return "Không có"
            text = ", ".join(str(value) for value in items)
            if len(text) > 280:
                return text[:280] + " ..."
            return text

        self.root.after(0, lambda: self.log("=== BẮT ĐẦU CHẤM BÀI ==="))
        self.root.after(0, lambda: self.log(f"Bài làm: {submission_file}"))
        self.root.after(0, lambda: self.log(f"Đáp án: {answer_file}"))

        result = grade_quiz_files(
            submission_file=submission_file,
            answer_file=answer_file,
            output_dir=output_dir,
        )

        self.root.after(0, lambda: self.log(f"Số câu so sánh: {result.compared_questions}"))
        self.root.after(0, lambda: self.log(f"Số câu đã làm (đúng + sai): {result.answered_count}"))
        self.root.after(0, lambda: self.log(f"Số câu đúng: {result.correct_count}"))
        self.root.after(
            0,
            lambda: self.log(f"Danh sách câu đúng: {format_question_list(result.correct_questions)}"),
        )
        self.root.after(0, lambda: self.log(f"Số câu sai: {result.wrong_count}"))
        self.root.after(
            0,
            lambda: self.log(f"Danh sách câu sai: {format_question_list(result.wrong_questions)}"),
        )
        self.root.after(0, lambda: self.log(f"Số câu chưa làm: {result.unanswered_count}"))
        self.root.after(
            0,
            lambda: self.log(
                f"Danh sách câu chưa làm: {format_question_list(result.unanswered_questions)}"
            ),
        )
        if result.auto_swapped_files:
            self.root.after(
                0,
                lambda: self.log(
                    "[LƯU Ý] Đã tự động đổi vai trò 2 file vì phát hiện bạn chọn nhầm file đáp án/bài làm."
                ),
            )
        self.root.after(
            0,
            lambda: self.log(
                "Số câu bỏ qua (file đáp án không xác định được đúng 1 đáp án): "
                f"{result.skipped_count}"
            ),
        )
        self.root.after(
            0,
            lambda: self.log(f"Danh sách câu bỏ qua: {format_question_list(result.skipped_questions)}"),
        )
        self.root.after(
            0,
            lambda: self.log(f"File các câu lỗi (chưa làm + sai): {result.wrong_output_file}"),
        )
        self.root.after(0, lambda: self.error_file_var.set(result.wrong_output_file))

        if knowledge_files:
            self.root.after(0, lambda: self.log("Đang phân tích lỗ hổng kiến thức với Ollama..."))
            try:
                report_file = build_knowledge_gap_report(
                    grading_result=result,
                    knowledge_files=knowledge_files,
                    output_dir=output_dir,
                    model=ollama_model,
                )
                self.root.after(
                    0,
                    lambda: self.log(
                        f"File phân tích lỗ hổng kiến thức: {report_file}"
                    ),
                )
            except Exception as error:
                self.root.after(
                    0,
                    lambda: self.log(
                        "[CẢNH BÁO] Không tạo được phân tích lỗ hổng kiến thức: "
                        f"{error}"
                    ),
                )
        self.root.after(0, lambda: self.log("=== HOÀN TẤT CHẤM BÀI ===\n"))

    def generate_action(self, answer_file: Path, output_dir: Path, requested_count: int) -> None:
        self.root.after(0, lambda: self.log("=== BẮT ĐẦU TẠO ĐỀ TRẮC NGHIỆM ==="))
        self.root.after(0, lambda: self.log(f"File nguồn: {answer_file}"))
        self.root.after(0, lambda: self.log(f"Số câu yêu cầu: {requested_count}"))

        result = generate_quiz_from_file(
            source_file=answer_file,
            output_dir=output_dir,
            question_count=requested_count,
        )

        self.root.after(0, lambda: self.log(f"Số câu tạo thực tế: {result.generated_count}"))
        self.root.after(0, lambda: self.log(f"File đề tạo mới: {result.quiz_output_file}"))
        self.root.after(0, lambda: self.log("=== HOÀN TẤT TẠO ĐỀ ===\n"))


def main() -> None:
    root = tk.Tk()
    app = QuizProcessorApp(root)
    app.log("Sẵn sàng. Chọn thư mục và bấm nút để xử lý hoặc kiểm tra.")
    root.mainloop()


if __name__ == "__main__":
    main()
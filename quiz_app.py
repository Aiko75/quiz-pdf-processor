from pathlib import Path
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from quiz_pdf_processor import process_folder, validate_folder


class QuizProcessorApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Quiz PDF Processor")
        self.root.geometry("900x620")

        self.input_var = tk.StringVar(value=str((Path(__file__).parent / "files").resolve()))
        self.output_var = tk.StringVar(value=str((Path(__file__).parent / "processed_quiz").resolve()))

        self._build_ui()

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root, padding=12)
        container.pack(fill=tk.BOTH, expand=True)

        ttk.Label(container, text="Thư mục PDF đầu vào:").grid(row=0, column=0, sticky="w")
        ttk.Entry(container, textvariable=self.input_var, width=90).grid(
            row=1, column=0, sticky="we", padx=(0, 8)
        )
        ttk.Button(container, text="Chọn...", command=self.pick_input).grid(row=1, column=1)

        ttk.Label(container, text="Thư mục output:").grid(row=2, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(container, textvariable=self.output_var, width=90).grid(
            row=3, column=0, sticky="we", padx=(0, 8)
        )
        ttk.Button(container, text="Chọn...", command=self.pick_output).grid(row=3, column=1)

        action_frame = ttk.Frame(container)
        action_frame.grid(row=4, column=0, columnspan=2, sticky="w", pady=(12, 8))

        self.process_button = ttk.Button(
            action_frame, text="1) Xử lý PDF -> DOCX", command=self.start_process
        )
        self.process_button.pack(side=tk.LEFT, padx=(0, 8))

        self.validate_button = ttk.Button(
            action_frame, text="2) Kiểm tra đối chiếu", command=self.start_validate
        )
        self.validate_button.pack(side=tk.LEFT)

        ttk.Label(container, text="Log:").grid(row=5, column=0, sticky="w")
        self.log_text = ScrolledText(container, height=24, wrap=tk.WORD)
        self.log_text.grid(row=6, column=0, columnspan=2, sticky="nsew")

        container.columnconfigure(0, weight=1)
        container.rowconfigure(6, weight=1)

    def pick_input(self) -> None:
        selected = filedialog.askdirectory(initialdir=self.input_var.get() or ".")
        if selected:
            self.input_var.set(selected)

    def pick_output(self) -> None:
        selected = filedialog.askdirectory(initialdir=self.output_var.get() or ".")
        if selected:
            self.output_var.set(selected)

    def log(self, message: str) -> None:
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def set_running(self, running: bool) -> None:
        state = tk.DISABLED if running else tk.NORMAL
        self.process_button.configure(state=state)
        self.validate_button.configure(state=state)

    def start_process(self) -> None:
        self.run_background(self.process_action)

    def start_validate(self) -> None:
        self.run_background(self.validate_action)

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


def main() -> None:
    root = tk.Tk()
    app = QuizProcessorApp(root)
    app.log("Sẵn sàng. Chọn thư mục và bấm nút để xử lý hoặc kiểm tra.")
    root.mainloop()


if __name__ == "__main__":
    main()
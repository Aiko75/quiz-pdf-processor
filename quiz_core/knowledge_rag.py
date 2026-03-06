from collections import Counter
import importlib
import json
import math
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import fitz
import requests

from .models import GradingResult, KnowledgeChunk, KnowledgeGapReportResult


def _extract_text_from_docx(file_path: Path) -> str:
    docx_module = importlib.import_module("docx")
    document = docx_module.Document(file_path)
    lines = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]
    return "\n".join(lines)


def _extract_text_from_pptx(file_path: Path) -> str:
    pptx_module = importlib.import_module("pptx")
    presentation = pptx_module.Presentation(str(file_path))
    chunks: List[str] = []
    for slide in presentation.slides:
        for shape in slide.shapes:
            text = getattr(shape, "text", "")
            if text and text.strip():
                chunks.append(text.strip())
    return "\n".join(chunks)


def _extract_text_from_pdf(file_path: Path) -> str:
    document = fitz.open(file_path)
    page_texts: List[str] = []
    try:
        for page in document:
            text = page.get_text("text")
            if text and text.strip():
                page_texts.append(text.strip())
    finally:
        document.close()
    return "\n\n".join(page_texts)


def extract_text_from_knowledge_file(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        return _extract_text_from_pdf(file_path)
    if suffix == ".docx":
        return _extract_text_from_docx(file_path)
    if suffix == ".pptx":
        return _extract_text_from_pptx(file_path)
    if suffix in {".txt", ".md"}:
        return file_path.read_text(encoding="utf-8", errors="ignore")
    raise ValueError(f"Định dạng file kiến thức chưa hỗ trợ: {file_path.name}")


def _trim_text(text: str, max_chars: int) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[:max_chars] + " ..."


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[A-Za-zÀ-ỹ0-9]{3,}", text.lower())


def _chunk_text(text: str, chunk_size: int = 900, overlap: int = 180) -> List[str]:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return []

    chunks: List[str] = []
    start = 0
    step = max(1, chunk_size - overlap)
    while start < len(cleaned):
        end = min(len(cleaned), start + chunk_size)
        chunk = cleaned[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(cleaned):
            break
        start += step
    return chunks


def _collect_question_terms(grading_result: GradingResult, max_terms: int = 48) -> List[str]:
    texts: List[str] = []
    for item in grading_result.wrong_items:
        texts.append(str(item.get("question_text", "")))
    for item in grading_result.unanswered_items:
        texts.append(str(item.get("question_text", "")))

    stop_words = {
        "câu", "nào", "đâu", "là", "và", "cho", "khi", "trong", "với", "các", "một",
        "được", "không", "đúng", "sai", "về", "từ", "của", "theo", "việc", "đây", "này",
        "that", "which", "what", "where", "when", "with", "from", "have", "does",
    }

    counter: Dict[str, int] = {}
    for text in texts:
        for token in _tokenize(text):
            if token in stop_words:
                continue
            counter[token] = counter.get(token, 0) + 1

    ordered = sorted(counter.items(), key=lambda kv: kv[1], reverse=True)
    return [token for token, _ in ordered[:max_terms]]


def _normalize_ollama_base_url(ollama_url: str) -> str:
    lowered = ollama_url.strip().rstrip("/")
    for suffix in ["/api/generate", "/api/chat", "/api/embeddings"]:
        if lowered.endswith(suffix):
            return lowered[: -len(suffix)]
    return lowered


def _call_ollama_embedding(text: str, model: str, ollama_base_url: str) -> List[float]:
    payload = {
        "model": model,
        "prompt": text,
    }
    response = requests.post(
        f"{ollama_base_url}/api/embeddings",
        json=payload,
        timeout=180,
    )
    response.raise_for_status()
    data = response.json()
    embedding = data.get("embedding")
    if not isinstance(embedding, list) or not embedding:
        raise RuntimeError("Ollama embeddings không trả về vector hợp lệ.")

    vector: List[float] = []
    for value in embedding:
        try:
            vector.append(float(value))
        except Exception as error:
            raise RuntimeError("Ollama embeddings trả về vector có phần tử không hợp lệ.") from error
    return vector


def _cosine_similarity(vector_a: List[float], vector_b: List[float]) -> float:
    if len(vector_a) != len(vector_b) or not vector_a:
        return -1.0

    dot = sum(a * b for a, b in zip(vector_a, vector_b))
    norm_a = math.sqrt(sum(a * a for a in vector_a))
    norm_b = math.sqrt(sum(b * b for b in vector_b))
    if norm_a == 0 or norm_b == 0:
        return -1.0
    return dot / (norm_a * norm_b)


def _build_vectorized_chunks(
    knowledge_contents: List[Tuple[str, str]],
    embedding_model: str,
    ollama_base_url: str,
) -> List[KnowledgeChunk]:
    chunks: List[KnowledgeChunk] = []
    embedding_cache: Dict[str, List[float]] = {}

    for source_name, content in knowledge_contents:
        for index, chunk_text in enumerate(_chunk_text(content), start=1):
            cache_key = chunk_text
            if cache_key in embedding_cache:
                embedding = embedding_cache[cache_key]
            else:
                embedding = _call_ollama_embedding(chunk_text, embedding_model, ollama_base_url)
                embedding_cache[cache_key] = embedding

            chunks.append(
                KnowledgeChunk(
                    source=source_name,
                    chunk_index=index,
                    text=chunk_text,
                    embedding=embedding,
                )
            )

    return chunks


def _build_relevant_knowledge_context(
    knowledge_contents: List[Tuple[str, str]],
    query_terms: List[str],
    embedding_model: str,
    ollama_base_url: str,
    max_chars: int = 9500,
) -> str:
    if not knowledge_contents:
        return "[Nguồn: hệ thống]\nKhông có tài liệu kiến thức bổ sung. Hãy phân tích dựa trên dữ liệu bài làm."

    vector_chunks = _build_vectorized_chunks(
        knowledge_contents=knowledge_contents,
        embedding_model=embedding_model,
        ollama_base_url=ollama_base_url,
    )
    if not vector_chunks:
        return "[Nguồn: hệ thống]\nKhông có đoạn kiến thức phù hợp để tham chiếu. Hãy phân tích dựa trên dữ liệu bài làm."

    query_text = " ".join(query_terms).strip()
    if not query_text:
        query_text = "kiến thức trọng tâm của các câu sai và chưa làm"

    query_embedding = _call_ollama_embedding(query_text, embedding_model, ollama_base_url)

    scored_chunks: List[Tuple[float, KnowledgeChunk]] = []
    for chunk in vector_chunks:
        score = _cosine_similarity(query_embedding, chunk.embedding)
        scored_chunks.append((score, chunk))

    scored_chunks.sort(key=lambda item: item[0], reverse=True)
    top_chunks = scored_chunks[:24]

    lexical_counter = Counter(query_terms)
    selected_parts: List[str] = []
    for score, chunk in top_chunks:
        lexical_bonus = sum(lexical_counter.get(token, 0) for token in _tokenize(chunk.text))
        selected_parts.append(
            (
                f"[Nguồn: {chunk.source} | đoạn {chunk.chunk_index} | cosine {score:.4f} | lexical {lexical_bonus}]\n"
                f"{chunk.text}"
            )
        )

    return _trim_text("\n\n".join(selected_parts), max_chars)


def _looks_generic_analysis(text: str) -> bool:
    lowered = text.lower().strip()
    weak_patterns = [
        "đáp án không rõ ràng",
        "cung cấp thêm thông tin",
        "không đủ thông tin",
        "chưa đủ thông tin",
    ]
    if any(pattern in lowered for pattern in weak_patterns):
        return True
    return len(lowered) < 180


def _build_mistakes_payload(grading_result: GradingResult) -> Dict[str, object]:
    return {
        "wrong_questions": [
            {
                "index": item.get("index"),
                "question": item.get("question_text"),
                "selected": item.get("selected_labels"),
                "correct": item.get("correct_label"),
            }
            for item in grading_result.wrong_items
        ],
        "unanswered_questions": [
            {
                "index": item.get("index"),
                "question": item.get("question_text"),
                "correct": item.get("correct_label"),
            }
            for item in grading_result.unanswered_items
        ],
        "score_summary": {
            "compared_questions": grading_result.compared_questions,
            "correct_count": grading_result.correct_count,
            "wrong_count": grading_result.wrong_count,
            "unanswered_count": grading_result.unanswered_count,
        },
        "correct_questions": [
            {
                "index": item.get("index"),
                "question": item.get("question_text"),
                "selected": item.get("selected_labels"),
                "correct": item.get("correct_label"),
            }
            for item in grading_result.correct_items
        ],
    }


def _build_structured_knowledge_prompt(
    grading_result: GradingResult,
    knowledge_context: str,
) -> str:
    payload = _build_mistakes_payload(grading_result)
    payload_json = json.dumps(payload, ensure_ascii=False, indent=2)

    return (
        "Bạn là trợ lý học tập theo kiểu NotebookLM mini. Hãy phân tích bài làm trắc nghiệm theo TỪNG CÂU, "
        "dựa trên ngữ cảnh trích xuất trong phần tài liệu tham chiếu.\n"
        "BẮT BUỘC trả về DUY NHẤT một JSON object hợp lệ, không kèm markdown, không giải thích ngoài JSON.\n"
        "Schema JSON bắt buộc:\n"
        "{\n"
        "  \"overview\": [\"...\"],\n"
        "  \"per_question\": [\n"
        "    {\"index\": 3, \"status\": \"Sai|Chưa làm\", \"reason\": \"...\", \"knowledge_gap\": \"...\", \"fix\": \"...\"}\n"
        "  ],\n"
        "  \"strengths\": [\"...\"],\n"
        "  \"weak_topics\": [\n"
        "    {\"topic\": \"...\", \"question_indexes\": [3,4], \"note\": \"...\"}\n"
        "  ]\n"
        "}\n"
        "Ràng buộc quan trọng:\n"
        "- per_question PHẢI bao phủ đầy đủ toàn bộ câu sai + câu chưa làm trong dữ liệu chấm bài.\n"
        "- Mỗi mục per_question phải nêu lý do gắn với chính câu đó, không trả lời chung chung.\n"
        "- Có thể trích dẫn [Nguồn: ...] trong reason/fix nếu cần, nhưng vẫn phải giữ đúng schema.\n"
        "- Nếu thiếu dữ liệu, vẫn phải điền reason='chưa đủ dữ liệu cụ thể từ đề' và đề xuất fix khả dụng.\n"
        "- Không được thêm key ngoài schema ở trên.\n\n"
        "Dữ liệu chấm bài:\n"
        f"{payload_json}\n\n"
        "Tài liệu kiến thức tham chiếu:\n"
        f"{knowledge_context}\n"
    )


def _extract_json_object(text: str) -> Optional[Dict[str, object]]:
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    snippet = text[start : end + 1]
    try:
        parsed = json.loads(snippet)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        return None
    return None


def _validate_structured_analysis(data: Dict[str, object], grading_result: GradingResult) -> bool:
    per_question = data.get("per_question")
    if not isinstance(per_question, list) or not per_question:
        return False

    expected_indexes = {
        int(item.get("index"))
        for item in (grading_result.wrong_items + grading_result.unanswered_items)
        if item.get("index") is not None
    }
    found_indexes = set()
    for item in per_question:
        if not isinstance(item, dict):
            continue
        index = item.get("index")
        reason = str(item.get("reason", "")).strip()
        if isinstance(index, int):
            found_indexes.add(index)
        if _looks_generic_analysis(reason):
            return False

    if expected_indexes and not expected_indexes.issubset(found_indexes):
        return False

    return True


def _format_structured_analysis(data: Dict[str, object]) -> str:
    lines: List[str] = []

    lines.append("TỔNG QUAN")
    overview = data.get("overview", [])
    if isinstance(overview, list):
        for item in overview:
            text = str(item).strip()
            if text:
                lines.append(f"- {text}")

    lines.append("")
    lines.append("PHÂN TÍCH THEO CÂU")
    per_question = data.get("per_question", [])
    if isinstance(per_question, list):
        sortable = [item for item in per_question if isinstance(item, dict)]
        sortable.sort(key=lambda item: int(item.get("index", 10**9)))
        for item in sortable:
            index = item.get("index")
            status = str(item.get("status", "")).strip() or "Chưa rõ"
            reason = str(item.get("reason", "")).strip()
            gap = str(item.get("knowledge_gap", "")).strip()
            fix = str(item.get("fix", "")).strip()
            lines.append(f"- Câu {index} ({status})")
            if reason:
                lines.append(f"  + Lý do: {reason}")
            if gap:
                lines.append(f"  + Hổng kiến thức: {gap}")
            if fix:
                lines.append(f"  + Gợi ý sửa: {fix}")

    lines.append("")
    lines.append("ĐIỂM MẠNH")
    strengths = data.get("strengths", [])
    if isinstance(strengths, list):
        for item in strengths:
            text = str(item).strip()
            if text:
                lines.append(f"- {text}")

    lines.append("")
    lines.append("LỖ HỔNG THEO CHỦ ĐỀ")
    weak_topics = data.get("weak_topics", [])
    if isinstance(weak_topics, list):
        for item in weak_topics:
            if not isinstance(item, dict):
                continue
            topic = str(item.get("topic", "")).strip() or "Chủ đề chưa xác định"
            question_indexes = item.get("question_indexes", [])
            note = str(item.get("note", "")).strip()
            lines.append(f"- {topic} | Câu liên quan: {question_indexes}")
            if note:
                lines.append(f"  + Ghi chú: {note}")

    return "\n".join(lines).strip()


def _call_ollama_generate(prompt: str, model: str, ollama_url: str) -> str:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0,
            "num_predict": 2400,
        },
    }
    response = requests.post(ollama_url, json=payload, timeout=180)
    response.raise_for_status()
    data = response.json()
    text = str(data.get("response", "")).strip()
    if not text:
        raise RuntimeError("Ollama không trả về nội dung phân tích.")
    return text


def _normalize_label(value: object) -> Optional[str]:
    text = str(value or "").strip().upper()
    if text in {"A", "B", "C", "D"}:
        return text

    for candidate in ["A", "B", "C", "D"]:
        if candidate in text:
            return candidate
    return None


def _extract_option_map(item: Dict[str, object]) -> Dict[str, str]:
    options_raw = item.get("option_states")
    option_map: Dict[str, str] = {}
    if not isinstance(options_raw, dict):
        return option_map

    for label in ["A", "B", "C", "D"]:
        state = options_raw.get(label)
        if state is None:
            continue
        text = str(getattr(state, "text", "")).strip()
        if text:
            option_map[label] = text
    return option_map


def _build_direct_question_prompt(question_text: str, options: Dict[str, str]) -> str:
    return (
        "Bạn là trợ lý học tập trắc nghiệm.\n"
        "Nhiệm vụ: chỉ dựa vào CÂU HỎI và 4 ĐÁP ÁN bên dưới, chọn 1 đáp án đúng nhất và giải thích ngắn gọn.\n"
        "BẮT BUỘC trả về DUY NHẤT JSON object hợp lệ (không markdown, không text ngoài JSON) theo schema:\n"
        "{\n"
        "  \"selected_label\": \"A|B|C|D\",\n"
        "  \"explanation\": \"...\"\n"
        "}\n"
        "Yêu cầu:\n"
        "- explanation tối đa 4 câu, rõ ràng, nêu lý do loại trừ đáp án nhiễu nếu có.\n"
        "- Không dùng từ ngữ mơ hồ như 'không đủ thông tin' nếu đề đã có dữ liệu.\n\n"
        f"Câu hỏi: {question_text}\n"
        f"A. {options.get('A', '')}\n"
        f"B. {options.get('B', '')}\n"
        f"C. {options.get('C', '')}\n"
        f"D. {options.get('D', '')}\n"
    )


def _parse_direct_question_response(raw_response: str) -> Tuple[Optional[str], str]:
    parsed = _extract_json_object(raw_response)
    if parsed is None:
        return None, ""

    label = _normalize_label(parsed.get("selected_label"))
    explanation = str(parsed.get("explanation", "")).strip()
    if len(explanation) > 800:
        explanation = explanation[:800].rstrip() + " ..."

    return label, explanation


def _format_note(label: Optional[str], explanation: str) -> str:
    safe_explanation = explanation.strip()
    if not safe_explanation:
        safe_explanation = "Chưa lấy được lời giải thích ổn định từ mô hình ở lần gọi này."

    if label is None:
        return safe_explanation
    return f"Mô hình chọn {label}. {safe_explanation}"


def _evaluate_one_question(item: Dict[str, object], model: str, ollama_url: str) -> str:
    question_text = str(item.get("question_text", "")).strip()
    if not question_text:
        return "Không đủ dữ liệu câu hỏi để mô hình phân tích."

    options = _extract_option_map(item)
    if len(options) < 4:
        return "Không đủ 4 phương án A/B/C/D để mô hình đưa ra góc nhìn bổ sung."

    prompt = _build_direct_question_prompt(question_text=question_text, options=options)

    last_error = ""
    for _ in range(2):
        try:
            raw = _call_ollama_generate(prompt=prompt, model=model, ollama_url=ollama_url)
            label, explanation = _parse_direct_question_response(raw)
            if label is not None and explanation.strip():
                return _format_note(label=label, explanation=explanation)
            last_error = "Mô hình trả về JSON nhưng thiếu selected_label hoặc explanation hợp lệ."
        except Exception as error:
            last_error = str(error)

    if last_error:
        return f"Không lấy được phân tích ổn định từ Ollama: {last_error}"
    return "Không lấy được phân tích ổn định từ Ollama."


def build_knowledge_gap_report(
    grading_result: GradingResult,
    knowledge_files: List[Path],
    output_dir: Path,
    model: str = "llama3.1:8b",
    ollama_url: str = "http://127.0.0.1:11434/api/generate",
    embedding_model: str = "nomic-embed-text",
) -> KnowledgeGapReportResult:
    _ = knowledge_files
    _ = output_dir
    _ = embedding_model

    target_items: List[Dict[str, object]] = []
    for item in grading_result.wrong_items:
        if isinstance(item, dict):
            target_items.append(item)
    for item in grading_result.unanswered_items:
        if isinstance(item, dict):
            target_items.append(item)

    notes_by_question: Dict[int, str] = {}
    summary_lines: List[str] = []

    for item in target_items:
        index_raw = item.get("index")
        try:
            index = int(index_raw)
        except Exception:
            continue

        note = _evaluate_one_question(item=item, model=model, ollama_url=ollama_url)
        notes_by_question[index] = note
        summary_lines.append(f"- Câu {index}: {note}")

    if not summary_lines:
        summary_lines.append("- Không có câu sai/chưa làm để phân tích thêm.")

    return KnowledgeGapReportResult(
        analysis_text="\n".join(summary_lines),
        notes_by_question=notes_by_question,
    )

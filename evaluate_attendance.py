"""
evaluate_attendance.py
----------------------
Grades student summaries against the actual content of a lecture transcript.

Architecture:
  1. Parse the VTT transcript → clean speech text
  2. LLM reads the full transcript → extracts N key topics as a JSON list
  3. Embed those topics with sentence-transformers (paraphrase-MiniLM-L6-v2)
  4. For each student summary → embed sentences → cosine sim against topics
  5. Score = topics_covered / total_topics × 10
  6. Attendance granted if score >= threshold
  7. Write formatted Excel output (3 sheets)

LLM providers (set LLM_PROVIDER in .env or environment):
  groq   → GROQ_API_KEY    (free tier, default)
  openai → OPENAI_API_KEY
  ollama → OLLAMA_BASE_URL (local, no API key)

Usage:
  python evaluate_attendance.py
  python evaluate_attendance.py --transcript lecture.vtt --dataset students.xlsx
                                --output results.xlsx --threshold 5 --sim 0.40
"""

import argparse
import re
import os
import json
import urllib.request
from pathlib import Path
from datetime import datetime

# ── load .env without python-dotenv (pure stdlib) ────────────────────────────
def _load_env(*paths):
    for p in paths:
        f = Path(p)
        if f.exists():
            for line in f.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
            break

_load_env(".env", "backend/.env")


# ─────────────────────────────────────────────────────────────────────────────
# 1. VTT PARSER
# ─────────────────────────────────────────────────────────────────────────────

def parse_vtt(vtt_path: str) -> str:
    """Strip timestamps, cue numbers, and speaker labels from a WebVTT file."""
    raw  = Path(vtt_path).read_text(encoding="utf-8")
    text = re.sub(r"^WEBVTT[^\n]*\n", "", raw)
    text = re.sub(r"\d{2}:\d{2}:\d{2}\.\d{3} --> [^\n]+\n", "", text)
    text = re.sub(r"^\d+\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^[^:\n]{1,30}:\s*", "", text, flags=re.MULTILINE)
    return " ".join(ln.strip() for ln in text.splitlines() if ln.strip())


# ─────────────────────────────────────────────────────────────────────────────
# 2. LLM — TOPIC EXTRACTION
# ─────────────────────────────────────────────────────────────────────────────

MAX_LLM_WORDS = 2800   # ~3,600 tokens content + ~300 prompt ≈ under Groq 6k TPM limit

_TOPIC_PROMPT = """You are an expert educator analyzing a lecture transcript.

Read the lecture content below and extract exactly {n} key concepts or topics that were taught.

For each topic, write ONE complete descriptive sentence that captures the concept as taught in this lecture. The sentence must be specific to the actual content — not generic.

Return ONLY a valid JSON array. No explanation, no markdown fences, no text outside the JSON.

Format:
[
  {{"label": "short topic name (3-6 words)", "sentence": "One complete sentence describing this concept as taught in the lecture."}},
  ...
]

LECTURE CONTENT:
{transcript}
"""


def _prefilter_transcript(transcript: str, max_words: int = MAX_LLM_WORDS) -> str:
    """
    Use TF-IDF to select the most content-rich sentences, keeping total under
    max_words. No hardcoded vocabulary — just reduces size for the LLM call.
    Sentences are returned in their original order so context is preserved.
    """
    import nltk
    from nltk.tokenize import sent_tokenize
    from sklearn.feature_extraction.text import TfidfVectorizer
    import numpy as np

    for res in ("punkt", "punkt_tab"):
        try:
            nltk.data.find(f"tokenizers/{res}")
        except LookupError:
            nltk.download(res, quiet=True)

    sents = [s for s in sent_tokenize(transcript) if len(s.split()) >= 5]
    total_words = sum(len(s.split()) for s in sents)

    if total_words <= max_words:
        return transcript

    tfidf  = TfidfVectorizer(ngram_range=(1, 2), stop_words="english", min_df=1)
    mat    = tfidf.fit_transform(sents)
    scores = np.array(mat.sum(axis=1)).flatten()

    top_n   = max(60, max_words // 18)
    top_idx = set(scores.argsort()[-top_n:])
    selected = [sents[i] for i in sorted(top_idx)]

    result, wc = [], 0
    for s in selected:
        w = len(s.split())
        if wc + w > max_words:
            break
        result.append(s)
        wc += w

    print(f"  Pre-filtered {total_words:,} words → {wc:,} words for LLM.")
    return " ".join(result)


def extract_topics_with_llm(transcript: str, n_topics: int) -> list:
    """
    Pre-filter transcript to fit token limits, then call the LLM.
    Returns a list of dicts: [{"label": str, "sentence": str}, ...]
    """
    transcript = _prefilter_transcript(transcript)
    prompt     = _TOPIC_PROMPT.format(transcript=transcript, n=n_topics)
    provider   = os.getenv("LLM_PROVIDER", "groq").strip().lower()

    print(f"  Using LLM provider: {provider}")
    if provider == "groq":
        raw = _call_groq(prompt)
    elif provider == "openai":
        raw = _call_openai(prompt)
    elif provider == "ollama":
        raw = _call_ollama(prompt)
    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER '{provider}'. Set to: groq | openai | ollama"
        )

    return _parse_llm_topics(raw, n_topics)


def _call_groq(prompt: str) -> str:
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set. Free key at https://console.groq.com")
    from groq import Groq
    model  = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    client = Groq(api_key=api_key)
    resp   = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "Respond ONLY with valid JSON. No markdown, no explanation."},
            {"role": "user",   "content": prompt},
        ],
        max_tokens=2048,
        temperature=0.1,
    )
    return resp.choices[0].message.content


def _call_openai(prompt: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set.")
    from openai import OpenAI
    model  = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    client = OpenAI(api_key=api_key)
    resp   = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "Respond ONLY with valid JSON. No markdown, no explanation."},
            {"role": "user",   "content": prompt},
        ],
        max_tokens=2048,
        temperature=0.1,
    )
    return resp.choices[0].message.content


def _call_ollama(prompt: str) -> str:
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model    = os.getenv("OLLAMA_MODEL", "llama3.1")
    data     = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": "Respond ONLY with valid JSON. No markdown, no explanation."},
            {"role": "user",   "content": prompt},
        ],
        "stream": False,
        "options": {"num_predict": 2048, "temperature": 0.1},
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url}/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))["message"]["content"]


def _parse_llm_topics(raw: str, n_topics: int) -> list:
    """Parse the LLM JSON response into [{label, sentence}, ...]."""
    text = raw.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    data   = json.loads(text)
    result = []
    seen   = set()
    for item in data:
        label    = str(item.get("label", "")).strip()
        sentence = str(item.get("sentence", "")).strip()
        if label and sentence and label.lower() not in seen:
            seen.add(label.lower())
            result.append({"label": label, "sentence": sentence})

    return result[:n_topics]


# ─────────────────────────────────────────────────────────────────────────────
# 3. SENTENCE TRANSFORMER (lazy singleton)
# ─────────────────────────────────────────────────────────────────────────────

_model = None

def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        print("  Loading paraphrase-MiniLM-L6-v2…", flush=True)
        _model = SentenceTransformer("paraphrase-MiniLM-L6-v2")
        print("  Model ready.", flush=True)
    return _model


# ─────────────────────────────────────────────────────────────────────────────
# 4. STUDENT SCORING
# ─────────────────────────────────────────────────────────────────────────────

def score_student(summary: str, topics: list, topic_vecs,
                  sim_threshold: float = 0.40) -> dict:
    """
    Split the student summary into sentences.
    A topic is 'covered' if ANY summary sentence has cosine sim >= sim_threshold.
    Score = covered / total * 10, clamped to [0, 10].
    """
    import nltk
    from nltk.tokenize import sent_tokenize
    from sentence_transformers import util
    import numpy as np

    for res in ("punkt", "punkt_tab"):
        try:
            nltk.data.find(f"tokenizers/{res}")
        except LookupError:
            nltk.download(res, quiet=True)

    if not summary or len(summary.strip()) < 15:
        return {"score": 0, "covered": [], "missed": [t["label"] for t in topics]}

    model      = _get_model()
    summ_sents = [s for s in sent_tokenize(summary) if len(s.split()) >= 3]
    if not summ_sents:
        summ_sents = [summary]

    summ_vecs  = model.encode(summ_sents, convert_to_tensor=True)
    sim_matrix = util.cos_sim(summ_vecs, topic_vecs).cpu().numpy()
    max_sims   = sim_matrix.max(axis=0)

    covered = [topics[i]["label"] for i, s in enumerate(max_sims) if s >= sim_threshold]
    missed  = [topics[i]["label"] for i, s in enumerate(max_sims) if s <  sim_threshold]
    score   = round(len(covered) / len(topics) * 10) if topics else 0
    return {"score": max(0, min(10, score)), "covered": covered, "missed": missed}


def make_remark(covered: list, missed: list) -> str:
    if not covered and not missed:
        return "No summary provided."
    parts = []
    if covered:
        parts.append("Covers: " + ", ".join(covered[:7]))
    else:
        parts.append("Does not address any key topics from this lecture")
    if missed:
        parts.append("Missing: " + ", ".join(missed[:7]))
    return ". ".join(parts) + "."


# ─────────────────────────────────────────────────────────────────────────────
# 5. EXCEL OUTPUT
# ─────────────────────────────────────────────────────────────────────────────

def write_excel(rows: list, output_path: str, threshold: int, topics: list):
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Attendance"

    headers  = ["#", "Student Name", "Summary", "Score (0-10)", "Remarks", "Attendance"]
    hdr_font = Font(bold=True, color="FFFFFF")
    hdr_fill = PatternFill(fill_type="solid", fgColor="1D4ED8")
    green    = PatternFill(fill_type="solid", fgColor="D1FAE5")
    red      = PatternFill(fill_type="solid", fgColor="FEE2E2")

    for col, h in enumerate(headers, 1):
        c = ws.cell(row=1, column=col, value=h)
        c.font      = hdr_font
        c.fill      = hdr_fill
        c.alignment = Alignment(horizontal="center", vertical="center")

    ws.row_dimensions[1].height = 22
    for i, w in enumerate([5, 28, 55, 14, 90, 14], 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    for idx, r in enumerate(rows, 1):
        fill = green if r["attended"] else red
        vals = [idx, r["name"], r["summary"], r["score"], r["remarks"],
                "Present" if r["attended"] else "Absent"]
        for col, val in enumerate(vals, 1):
            c = ws.cell(row=idx + 1, column=col, value=val)
            c.fill      = fill
            c.alignment = Alignment(
                wrap_text=(col in (3, 5)),
                vertical="top",
                horizontal="left" if col in (3, 5) else "center",
            )

    ws.freeze_panes = "A2"

    # ── Topics Evaluated sheet ────────────────────────────────────────────────
    wt = wb.create_sheet("Topics Evaluated")
    for cell, val in [("A1", "#"), ("B1", "Label"), ("C1", "LLM-extracted sentence")]:
        wt[cell].value = val
        wt[cell].font  = Font(bold=True)
    for i, t in enumerate(topics, 2):
        wt.cell(row=i, column=1, value=i - 1)
        wt.cell(row=i, column=2, value=t["label"].title())
        wt.cell(row=i, column=3, value=t["sentence"])
    wt.column_dimensions["A"].width = 5
    wt.column_dimensions["B"].width = 35
    wt.column_dimensions["C"].width = 90

    # ── Statistics sheet ──────────────────────────────────────────────────────
    ws2    = wb.create_sheet("Statistics")
    scores  = [r["score"] for r in rows]
    present = sum(1 for r in rows if r["attended"])
    stats = [
        ("Total students",    len(rows)),
        ("Present",           present),
        ("Absent",            len(rows) - present),
        ("Attendance %",      f"{100 * present / len(rows):.1f}%"),
        ("Mean score",        f"{sum(scores) / len(scores):.2f}/10"),
        ("Highest score",     f"{max(scores)}/10"),
        ("Lowest score",      f"{min(scores)}/10"),
        ("Threshold used",    f"{threshold}/10"),
        ("Topics evaluated",  len(topics)),
        ("LLM provider",      os.getenv("LLM_PROVIDER", "groq")),
        ("Generated at",      datetime.now().strftime("%Y-%m-%d %H:%M")),
    ]
    ws2["A1"].value = "Metric"; ws2["A1"].font = Font(bold=True)
    ws2["B1"].value = "Value";  ws2["B1"].font = Font(bold=True)
    for i, (m, v) in enumerate(stats, 2):
        ws2.cell(row=i, column=1, value=m)
        ws2.cell(row=i, column=2, value=v)
    ws2.column_dimensions["A"].width = 22
    ws2.column_dimensions["B"].width = 22

    wb.save(output_path)


# ─────────────────────────────────────────────────────────────────────────────
# 6. MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description="Grade student lecture summaries using LLM topic extraction + semantic similarity."
    )
    ap.add_argument("--transcript", default="data/GMT20260425-045808_Recording.transcript.vtt",
                    help="Path to Zoom .vtt transcript file")
    ap.add_argument("--dataset",    default="data/dataset_llm.xlsx",
                    help="Excel file with student names and summaries")
    ap.add_argument("--output",     default="data/attendance_results.xlsx",
                    help="Output Excel file path")
    ap.add_argument("--threshold",  type=int,   default=5,
                    help="Min score (0-10) to grant attendance (default: 5)")
    ap.add_argument("--n_topics",   type=int,   default=15,
                    help="Number of topics for LLM to extract (default: 15)")
    ap.add_argument("--sim",        type=float, default=0.40,
                    help="Cosine similarity cutoff to count a topic as covered (default: 0.40)")
    args = ap.parse_args()

    # ── Step 1: parse transcript ──────────────────────────────────────────────
    print(f"\n[1/5] Parsing transcript: {args.transcript}")
    transcript = parse_vtt(args.transcript)
    word_count = len(transcript.split())
    print(f"      {len(transcript):,} chars  |  {word_count:,} words of speech.")

    # ── Step 2: load students ─────────────────────────────────────────────────
    print(f"\n[2/5] Loading dataset: {args.dataset}")
    import openpyxl
    wb  = openpyxl.load_workbook(args.dataset)
    ws  = wb.active
    first = [c.value for c in ws[1]]
    # Header row detection: some sheets (e.g. 22date.xlsx) have NO header row,
    # so row 1 is already a student. Treat row 1 as a header only if a cell
    # looks like a short column label.
    def _is_label(v):
        t = str(v).strip().lower() if v else ""
        return 0 < len(t) <= 40 and any(k in t for k in ("name", "summary", "submission", "text"))
    has_header = any(_is_label(v) for v in first)
    if has_header:
        nc = next((i for i, h in enumerate(first) if h and "name" in str(h).lower()), 0)
        sc = next((i for i, h in enumerate(first)
                   if h and any(k in str(h).lower() for k in ("summary", "submission"))), 1)
        start_row = 2
    else:
        nc, sc, start_row = 0, 1, 1
    students = []
    for row in ws.iter_rows(min_row=start_row, values_only=True):
        name = str(row[nc]).strip() if row[nc] else ""
        summ = str(row[sc]).strip() if len(row) > sc and row[sc] else ""
        if name:
            students.append({"name": name, "summary": summ})
    print(f"      {len(students)} students loaded.")

    # ── Step 3: LLM topic extraction ──────────────────────────────────────────
    print(f"\n[3/5] Asking LLM to extract {args.n_topics} key topics from transcript…")
    topics = extract_topics_with_llm(transcript, args.n_topics)
    print(f"      {len(topics)} topics extracted:")
    for i, t in enumerate(topics, 1):
        print(f"        {i:2}. {t['label'].title()}")
        print(f"            \"{t['sentence'][:95]}{'...' if len(t['sentence']) > 95 else ''}\"")

    # ── Step 4: embed topics ──────────────────────────────────────────────────
    print(f"\n[4/5] Scoring {len(students)} students (threshold ≥ {args.threshold}/10, sim ≥ {args.sim})…")
    from sentence_transformers import util
    topic_vecs = _get_model().encode(
        [t["sentence"] for t in topics], convert_to_tensor=True
    )

    results = []
    for i, s in enumerate(students, 1):
        ev  = score_student(s["summary"], topics, topic_vecs, args.sim)
        att = ev["score"] >= args.threshold
        results.append({
            "name":     s["name"],
            "summary":  s["summary"],
            "score":    ev["score"],
            "remarks":  make_remark(ev["covered"], ev["missed"]),
            "attended": att,
        })
        flag = "✓ Present" if att else "✗ Absent"
        print(f"  [{i:3}/{len(students)}] {s['name']:<35} {ev['score']:2}/10  {flag}")

    # ── Step 5: write Excel ───────────────────────────────────────────────────
    print(f"\n[5/5] Writing → {args.output}")
    write_excel(results, args.output, args.threshold, topics)

    present = sum(1 for r in results if r["attended"])
    scores  = [r["score"] for r in results]
    print(f"\n{'─' * 60}")
    print(f"  Students evaluated : {len(results)}")
    print(f"  Present (≥{args.threshold}/10)    : {present}  ({100 * present / len(results):.1f}%)")
    print(f"  Absent             : {len(results) - present}")
    print(f"  Mean score         : {sum(scores) / len(scores):.2f}/10")
    print(f"  Score range        : {min(scores)} – {max(scores)}")
    print(f"  Output             : {Path(args.output).resolve()}")
    print(f"{'─' * 60}\n")


if __name__ == "__main__":
    main()

# evaluate_attendance.py — Report

**File:** `evaluate_attendance.py`  
**Purpose:** Automatically grade student lecture summaries and mark attendance using LLM-based topic extraction and semantic similarity scoring.

---

## What It Does

A student submits a written summary of what they understood from a lecture. This script:
1. Reads the actual lecture transcript (Zoom `.vtt` file)
2. Asks an LLM to identify the key topics taught in that lecture
3. Compares each student's summary against those topics using semantic similarity
4. Assigns a score (0–10) and marks the student Present or Absent
5. Writes a formatted Excel report

The key design principle: **topics come from the transcript, not the summaries.** This means scores reflect how well a student captured what was actually taught — not how well they wrote compared to each other.

---

## Architecture — 5 Steps

```
Zoom .vtt file
      │
      ▼
[Step 1] parse_vtt()
      │  Strip timestamps, cue numbers, speaker labels
      │  → clean transcript text
      ▼
[Step 2] _prefilter_transcript()  +  LLM call
      │  TF-IDF selects top ~2800 content-rich words
      │  LLM reads that content → extracts N topics as JSON
      │  Each topic: { label, sentence }
      ▼
[Step 3] sentence-transformers encode topics
      │  paraphrase-MiniLM-L6-v2 embeds each topic sentence
      │  → topic_vecs  (tensor)
      ▼
[Step 4] score_student()  per student
      │  Embed each sentence of the student's summary
      │  Cosine similarity matrix: summary_sents × topics
      │  Topic "covered" if best sim ≥ threshold (default 0.40)
      │  Score = covered / total × 10
      ▼
[Step 5] write_excel()
         3-sheet Excel output
```

---

## Step-by-Step Explanation

### Step 1 — VTT Parser (`parse_vtt`)

Zoom exports lecture recordings as `.vtt` (WebVTT) files. These contain:
- A `WEBVTT` header line
- Timestamp cues: `00:01:23.456 --> 00:01:27.890`
- Cue numbers
- Speaker labels: `Speaker Name: text`

All of these are stripped using regex, leaving only the raw spoken words joined into one continuous string.

### Step 2 — LLM Topic Extraction

This is a two-part step:

**Part A — Pre-filter with TF-IDF (`_prefilter_transcript`)**

A 1-hour lecture transcript can be 15,000–20,000 words (~20,000+ tokens). The Groq free tier has a 6,000 tokens-per-minute limit. To fit within this:

1. The transcript is split into sentences (NLTK `sent_tokenize`)
2. TF-IDF scores every sentence by information density (bigram + unigram, English stopwords removed)
3. The top ~155 highest-scoring sentences are selected and returned in their original order
4. This produces ~2,800 words (~3,600 tokens), leaving room for the prompt (~300 tokens) and response (~500 tokens) — safely under 6,000

No hardcoded vocabulary is used here — TF-IDF is subject-agnostic. The purpose is purely size reduction.

**Part B — LLM call (`extract_topics_with_llm`)**

The filtered content is sent to the LLM with this instruction:

> *"Extract exactly N key concepts or topics that were taught. For each, write ONE complete descriptive sentence specific to this lecture's actual content."*

The LLM returns a JSON array:
```json
[
  { "label": "Supervised Learning", "sentence": "Supervised learning involves training a model on labeled data to predict outcomes for unseen examples." },
  { "label": "TF-IDF", "sentence": "TF-IDF converts text into numerical vectors by weighting terms by how often they appear in a document vs. the corpus." },
  ...
]
```

These topic sentences are the ground truth for scoring — grounded in what the LLM understood from the actual lecture, not a hardcoded list.

**LLM Providers supported:**

| Provider | Env var | Default model | Notes |
|---|---|---|---|
| `groq` | `GROQ_API_KEY` | `llama-3.1-8b-instant` | Free tier, default |
| `openai` | `OPENAI_API_KEY` | `gpt-4o-mini` | Paid |
| `ollama` | `OLLAMA_BASE_URL` | `llama3.1` | Local, free |

### Step 3 — Semantic Embedding

The `paraphrase-MiniLM-L6-v2` model from `sentence-transformers` encodes all N topic sentences into dense vector embeddings. These vectors capture semantic meaning — similar concepts have high cosine similarity even if worded differently.

The model is loaded once as a lazy singleton (`_get_model()`) and reused for all students in the same run.

### Step 4 — Student Scoring (`score_student`)

For each student summary:

1. The summary is split into sentences (NLTK)
2. Each sentence is embedded with the same `paraphrase-MiniLM-L6-v2` model
3. A cosine similarity matrix is computed: `(n_summary_sentences × n_topics)`
4. For each topic, the **best-matching** summary sentence's similarity is taken
5. A topic is **covered** if that best similarity ≥ `sim_threshold` (default: 0.40)
6. `score = round(topics_covered / total_topics × 10)`, clamped to [0, 10]
7. **Present** if `score ≥ threshold` (default: 5/10)

This sentence-level matching means a student does not need to write about every topic in a single sentence — any sentence in their summary that semantically aligns with a topic counts.

### Step 5 — Excel Output (`write_excel`)

Three sheets are written:

**Sheet 1: Attendance**
| # | Student Name | Summary | Score (0-10) | Remarks | Attendance |
|---|---|---|---|---|---|
| Row color: green = Present, red = Absent |

Remarks format: `"Covers: topic1, topic2. Missing: topic3, topic4."`

**Sheet 2: Topics Evaluated**

Lists every LLM-extracted topic with its index, short label, and the full source sentence used for scoring.

**Sheet 3: Statistics**

| Metric | Value |
|---|---|
| Total students | — |
| Present / Absent | — |
| Attendance % | — |
| Mean / Highest / Lowest score | — |
| Threshold used | — |
| Topics evaluated | — |
| LLM provider | — |
| Generated at | — |

---

## Command-Line Usage

```bash
# activate the project venv first
source .venv/bin/activate

# run with defaults
python evaluate_attendance.py

# run with specific files
python evaluate_attendance.py \
  --transcript data/GMT20260422-140442_Recording.transcript.vtt \
  --dataset    data/22date.xlsx \
  --output     data/attendance_results_22date_apr22.xlsx \
  --threshold  5 \
  --n_topics   15 \
  --sim        0.40
```

### Arguments

| Argument | Default | Description |
|---|---|---|
| `--transcript` | `data/GMT20260425-045808_Recording.transcript.vtt` | Path to Zoom `.vtt` file |
| `--dataset` | `data/dataset_llm.xlsx` | Excel file — name + summary columns (header row optional; auto-detected) |
| `--output` | `data/attendance_results.xlsx` | Output Excel file path |
| `--threshold` | `5` | Min score (0–10) to mark Present |
| `--n_topics` | `15` | Number of topics for LLM to extract |
| `--sim` | `0.40` | Cosine similarity cutoff to count a topic as covered |

---

## Configuration (`.env`)

The script auto-loads from `.env` or `backend/.env`:

```env
LLM_PROVIDER=groq
GROQ_API_KEY=your_key_here
GROQ_MODEL=llama-3.1-8b-instant
```

No `python-dotenv` package needed — the loader is pure stdlib.

---

## Dependencies

| Package | Purpose |
|---|---|
| `sentence-transformers` | Semantic embeddings (`paraphrase-MiniLM-L6-v2`) |
| `nltk` | Sentence tokenization (`punkt` / `punkt_tab`, auto-downloaded) |
| `scikit-learn` | TF-IDF vectorization for pre-filtering |
| `numpy` | Matrix operations |
| `openpyxl` | Excel read/write |
| `groq` | Groq API SDK (used when `LLM_PROVIDER=groq`) |
| `openai` | OpenAI SDK (used when `LLM_PROVIDER=openai`) |

All are available in `.venv`.

---

## Sample Run — Apr 22 Lecture

```
Transcript  : data/GMT20260422-140442_Recording.transcript.vtt
Dataset     : data/22date.xlsx
Students    : 138 (sheet has no header row; earlier versions skipped the first student)
Pre-filtered: 16,153 words → 2,780 words for LLM

Topics extracted by LLM:
  1. Machine Learning Basics
  2. Conventional Approach
  3. Machine Learning Paradigms
  4. Supervised Learning
  5. Unsupervised Learning
  6. Reinforcement Learning
  7. Data Collection
  8. Data Preprocessing
  9. Feature Extraction
 10. Vectorization
 11. TF-IDF
 12. Embeddings
 13. Natural Language Processing
 14. Semi-Supervised Learning
 15. Self-Supervised Learning

Results:
  Students evaluated : 137
  Present (≥5/10)    : 128  (93.4%)
  Absent             : 9
  Mean score         : 7.37/10
  Score range        : 0 – 10
  Output             : attendance_results_22date_apr22.xlsx
```

---

## Design Decisions

**Why LLM for topic extraction instead of hardcoded keywords?**
An earlier version used a fixed set of ~50 ML/programming keywords to filter sentences before clustering. This broke on lectures outside that domain and missed topics phrased differently. The LLM reads the actual content and understands what was taught — no vocabulary maintenance needed.

**Why TF-IDF pre-filtering before the LLM call?**
The Groq free tier has a 6,000 tokens-per-minute limit. A typical 1-hour lecture transcript is 15,000–20,000 words (~20,000+ tokens). TF-IDF is used purely as a size-reduction step — selecting the ~2,800 most information-dense words to pass to the LLM. It does not filter by subject matter.

**Why sentence-level cosine similarity instead of LLM scoring per student?**
Asking the LLM to score each student would mean 100+ API calls per run (one per student), taking several minutes and burning through rate limits. Sentence-transformers run locally, score all 137 students in seconds, and produce consistent reproducible results.

**Why `paraphrase-MiniLM-L6-v2`?**
It is a compact (80MB), fast model specifically trained for paraphrase and semantic similarity tasks — the exact use case here. It was already cached on disk from prior runs.

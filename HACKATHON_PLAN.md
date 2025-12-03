# BIRS NotebookLM - Hackathon Plan (Dec 5-6, 2025)

## The Pitch: Unlock 17,000 Math Lectures for the World

**Ask**: GCP credits to process BIRS's entire 15-year video archive

**Impact**: Open source searchable, AI-accessible mathematics research

---

## Why This Wins

### 1. Unique Dataset (No One Else Has This)
- **17,000 research lectures** from world's top mathematicians
- **15+ years** of BIRS workshop recordings
- **Chalk talks**: Handwritten proofs on blackboards (hardest OCR problem)
- **Not on YouTube** - locked in BIRS archive

### 2. Perfect Gemini 3 Pro Showcase
- Best-in-class math OCR (95% AIME, 0.115 Edit Distance)
- Video multimodal understanding (87.6% Video-MMMU)
- "Transforms handwritten notes into computable data" - Google's words
- **This is exactly what Gemini 3 Pro was built for**

### 3. Open Science Mission
- BIRS = Banff International Research Station (nonprofit)
- All output will be **open source** and **freely accessible**
- Benefits global mathematics research community
- Educational resource for students worldwide

### 4. Clear Metrics
- 17,000 videos × $1 = **$17,000 in credits needed**
- Measurable: OCR accuracy, search quality, user adoption
- Timeline: 6 months to process full archive

---

## Goal
Build an open-source NotebookLM alternative specialized for BIRS mathematics lecture videos, with emphasis on **chalk talks** (blackboard lectures).

## Why BIRS Videos Are Special
- **Chalk talks**: Handwritten math on blackboards (hardest OCR challenge)
- **Slide presentations**: Standard lecture format
- **Mixed format**: Speaker switches between slides and board
- **Complex math**: Theorems, proofs, equations in LaTeX notation
- **Long form**: 30-60 minute research lectures
- **Archive**: 15+ years of mathematics research videos

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    BIRS NotebookLM                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐   │
│  │   VIDEO     │     │   GEMINI    │     │   OUTPUT    │   │
│  │   INPUT     │────▶│   3 PRO     │────▶│   STORE     │   │
│  │             │     │   PREVIEW   │     │             │   │
│  └─────────────┘     └─────────────┘     └─────────────┘   │
│        │                    │                    │          │
│        │                    ▼                    │          │
│        │            ┌─────────────┐              │          │
│        │            │  STRUCTURED │              │          │
│        │            │    JSON     │              │          │
│        │            │  - metadata │              │          │
│        │            │  - transcript│             │          │
│        │            │  - equations │             │          │
│        │            │  - timestamps│             │          │
│        │            └─────────────┘              │          │
│        │                    │                    │          │
│        ▼                    ▼                    ▼          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                    FEATURES                          │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │  📝 Searchable Transcript     🔍 Q&A Chat           │   │
│  │  📊 Visual Timeline           🎙️ Audio Overview     │   │
│  │  📐 LaTeX Equations           📚 Flashcards         │   │
│  │  🏷️ Topic Tags                📋 Study Notes        │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Video Ingestion (DONE)
**Tool**: `gemini_video_analyzer.py`
- Upload video to Gemini File API
- Process with Gemini 3 Pro Preview
- Extract structured analysis

### 2. Chalk Talk OCR (KEY DIFFERENTIATOR)
**Challenge**: Handwritten math on blackboards is hardest OCR
**Solution**: Gemini 3 Pro has best-in-class document understanding
- 0.115 Edit Distance on OmniDocBench (best score)
- 95% on AIME 2025 math without tools
- Transforms "handwritten notes into computable data"

**Prompt Engineering for Chalk Talks**:
```python
CHALK_TALK_PROMPT = """
This is a mathematics chalk talk lecture on a blackboard.

For EACH board state shown, extract:
1. All mathematical expressions in LaTeX format
2. Definitions (labeled DEF or Definition)
3. Theorems (labeled THM or Theorem)
4. Proofs (key steps)
5. Diagrams (describe mathematically)

Output format:
## [MM:SS] Board State N
**Topic**: ...
**Equations**:
- $equation1$
- $equation2$
**Notes**: ...
"""
```

### 3. Structured Output Store
**Format**: JSON with sections
```json
{
  "video_id": "25w5490-57785",
  "metadata": {
    "title": "R-loop Modelling with 2D Tiles",
    "speaker": "Van Pham",
    "institution": "University of South Florida",
    "workshop": "25w5490",
    "date": "2025-11-13"
  },
  "transcript": {
    "full_text": "...",
    "segments": [
      {"start": 0, "end": 60, "text": "..."}
    ]
  },
  "visual_content": [
    {"timestamp": "05:30", "type": "slide", "title": "...", "equations": ["$...$"]}
  ],
  "equations": ["$E = mc^2$", "..."],
  "key_concepts": ["R-loops", "Wang tiles", "..."],
  "summary": "...",
  "outline": [...]
}
```

### 4. Audio Overview (Custom Built)
**Approach**: Generate podcast script with Gemini, synthesize with Google TTS
- Input: Structured JSON from Gemini analysis
- Output: 5-10 minute audio conversation about the lecture
- Two AI hosts discuss the math concepts

```python
# Step 1: Generate conversation script with Gemini
PODCAST_PROMPT = """
Create a 5-minute podcast script about this math lecture.
Two hosts: Alex (curious learner) and Sam (expert explainer).
Make complex math accessible. Include:
- Hook/intro
- Key concepts explained simply
- "Aha moment" insights
- Takeaway for listeners
Output as JSON: [{"speaker": "Alex", "text": "..."}, ...]
"""

# Step 2: Synthesize with Google Cloud TTS
from google.cloud import texttospeech
# Different voices for each host
```

### 5. Q&A Chat Interface
**RAG Architecture**:
- Embed lecture content (transcript + visual analysis)
- Vector store (ChromaDB or similar)
- Gemini 3 Pro for grounded responses

```python
def chat_about_lecture(question, lecture_context):
    prompt = f"""
    Based on this BIRS lecture content:
    {lecture_context}

    Answer this question:
    {question}

    Cite specific timestamps when referencing content.
    Use LaTeX for any mathematical notation.
    """
    return model.generate_content(prompt)
```

### 6. Flashcard Generator
Convert key concepts into study cards:
```python
FLASHCARD_PROMPT = """
Create 10 flashcards from this lecture for graduate students:
- Front: Question or concept name
- Back: Definition, theorem statement, or key insight
- Include LaTeX for equations
Output as JSON array.
"""
```

---

## Tech Stack

| Component | Tool | Why |
|-----------|------|-----|
| Video Analysis | Gemini 3 Pro Preview | Best multimodal, math OCR |
| Audio Podcast | Gemini + Google TTS | Custom built for hackathon |
| TTS | ElevenLabs / Google TTS | High quality voices |
| Vector DB | ChromaDB | Simple, local |
| Backend | FastAPI | Quick to build |
| Frontend | Gradio | Rapid prototyping |

---

## Hackathon Timeline (Dec 5-6)

### Day 1 (Dec 5) - Core Pipeline
- [ ] Morning: Set up Gemini 3 Pro with video
- [ ] Afternoon: Chalk talk OCR optimization
- [ ] Evening: Structured JSON output

### Day 2 (Dec 6) - Features
- [ ] Morning: Podcastfy integration (Audio Overview)
- [ ] Afternoon: Q&A chat interface
- [ ] Evening: Demo + polish

---

## Demo Script

1. **Upload** a BIRS chalk talk video
2. **Show** Gemini 3 Pro extracting equations from blackboard
3. **Play** AI-generated podcast discussing the lecture
4. **Ask** questions about the content
5. **Generate** flashcards for studying

---

## Differentiators vs NotebookLM

| Feature | NotebookLM | BIRS NotebookLM |
|---------|------------|-----------------|
| Input | Documents, websites | Video lectures |
| Math OCR | Basic | Optimized for chalk talks |
| LaTeX output | No | Yes |
| Video timestamps | No | Yes |
| Open source | No | Yes |
| BIRS integration | No | Yes (15+ years of lectures) |

---

## Resources

### Existing Code
- `~/vlm/gemini_video_analyzer.py` - Video analysis (READY)
- `~/vlm/birs_full_analysis.py` - Local Ollama fallback
- [bigsnarfdude/videoSummarization](https://github.com/bigsnarfdude/videoSummarization) - Flask frontend

### Open Source Tools
- [Gradio](https://gradio.app) - UI framework
- [ChromaDB](https://www.trychroma.com) - Vector store

### Documentation
- [Gemini 3 Developer Guide](https://ai.google.dev/gemini-api/docs/gemini-3)
- [Gemini 3 Pro on Vertex AI](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/3-pro)

---

## Sample Chalk Talk Videos to Test

BIRS has many chalk talk lectures. Priority test cases:
1. Pure blackboard (no slides)
2. Mixed (slides + board work)
3. Complex diagrams (commutative diagrams, graphs)
4. Dense equations (proof-heavy lectures)

---

## Success Metrics

1. **OCR Accuracy**: Can it read handwritten math?
2. **Timestamp Alignment**: Do references match video?
3. **Podcast Quality**: Is the audio overview useful?
4. **Q&A Relevance**: Does chat understand the content?
5. **User Value**: Would researchers use this?

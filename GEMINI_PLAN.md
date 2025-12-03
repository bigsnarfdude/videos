# Gemini Video Processing Plan

## Current Pipeline (Ollama - Local)

```
Video → ffmpeg extract audio → Whisper transcribe → transcript
     → ffmpeg scene detection → extract frames → VLM analyze each frame
     → LLM combine transcript + frame analysis → summary
```

**Pros:** Fully local, no API costs, privacy
**Cons:** Sequential GPU sharing, ~2-5 min processing per video

---

## Proposed Pipeline (Gemini API)

```
Video → Gemini 3 Pro (single API call) → complete analysis
```

**One API call handles:**
- Audio transcription (built-in)
- Visual content extraction (slides, equations, diagrams)
- Combined summary generation

### Model Selection

**Decision: Gemini 3 Pro Preview** (`gemini-3-pro-preview`)
- "Best model in the world for multimodal understanding"
- Best for complex math notation and equation recognition
- Worth the cost for BIRS research lectures

### Pricing (December 2025)

| Model | Input (per 1M tokens) | Output (per 1M tokens) | Quality |
|-------|----------------------|------------------------|---------|
| Gemini 3 Pro | $2.00 | $12.00 | Best |
| Gemini 2.5 Pro | $1.25 | $10.00 | Excellent |
| Gemini 2.5 Flash | $0.30 | $2.50 | Very Good |
| Gemini 2.0 Flash | $0.10 | $0.40 | Good |

**Video Token Calculation:**
- Video: ~260 tokens per second
- 30-min lecture = 1,800 seconds × 260 = ~468,000 input tokens
- Output: ~2,000-5,000 tokens for summary

**Cost per 30-min video:**
| Model | Input Cost | Output Cost | Total |
|-------|-----------|-------------|-------|
| Gemini 3 Pro | $0.94 | $0.06 | ~$1.00 |
| Gemini 2.5 Pro | $0.59 | $0.05 | ~$0.64 |
| Gemini 2.5 Flash | $0.14 | $0.01 | ~$0.15 |
| Gemini 2.0 Flash | $0.05 | $0.002 | ~$0.05 |

### Implementation Options

#### Option 1: Direct Upload (< 20MB videos)
```python
import google.generativeai as genai

genai.configure(api_key="YOUR_API_KEY")
model = genai.GenerativeModel('gemini-3-pro-preview')

video_file = genai.upload_file("lecture.mp4")
response = model.generate_content([video_file, ANALYSIS_PROMPT])
```

#### Option 2: File API (larger videos - recommended for BIRS)
```python
import google.generativeai as genai
import time

genai.configure(api_key="YOUR_API_KEY")
model = genai.GenerativeModel('gemini-3-pro-preview')

# Upload first (can take a few minutes for large files)
print("Uploading video...")
video_file = genai.upload_file("lecture.mp4")

# Wait for processing
print("Processing...")
while video_file.state.name == "PROCESSING":
    time.sleep(10)
    video_file = genai.get_file(video_file.name)

if video_file.state.name == "FAILED":
    raise ValueError(f"Video processing failed: {video_file.state.name}")

# Analyze with Gemini 3 Pro
print("Analyzing with Gemini 3 Pro...")
response = model.generate_content([video_file, ANALYSIS_PROMPT])
print(response.text)
```

#### Option 3: Hybrid (Gemini + Local Refinement)
```
Video → Gemini 3 Pro (video analysis)
     → Local Ollama gpt-oss:120b (summary refinement)
```
Use if you want Gemini's multimodal understanding + local model's reasoning.

---

## Recommended Prompt for BIRS Lectures

```python
ANALYSIS_PROMPT = """Analyze this BIRS mathematics lecture video.

Extract and provide:

## 1. METADATA (JSON format)
{
  "title": "Lecture title from slides or introduction",
  "speaker": "Speaker name",
  "institution": "If mentioned",
  "workshop": "Workshop code if visible (e.g., 25w5490)",
  "topic": "Main mathematical field",
  "key_concepts": ["list", "of", "5-10", "key", "concepts"],
  "equations": ["important equations in LaTeX"]
}

## 2. TRANSCRIPT SUMMARY
Summarize what the speaker said, focusing on:
- Main arguments and theorems presented
- Key definitions introduced
- Important examples discussed

## 3. VISUAL CONTENT
List all slides/board content with timestamps:
- [MM:SS] Slide title / Board content description
- Include any equations, diagrams, or figures shown

## 4. EXECUTIVE SUMMARY
2-3 paragraphs combining audio and visual content into a coherent summary.

## 5. LECTURE OUTLINE
Timestamped outline of the lecture structure.

## 6. KEY TAKEAWAYS
5 bullet points with the most important ideas.
"""
```

---

## Implementation Plan

### Phase 1: Basic Gemini Script
- [ ] Create `gemini_video_analyzer.py`
- [ ] Handle video upload via File API
- [ ] Process with analysis prompt
- [ ] Save output to `~/vlm_output/summaries/`

### Phase 2: Batch Processing
- [ ] Add batch mode for multiple videos
- [ ] Implement rate limiting (avoid quota issues)
- [ ] Add cost estimation before processing

### Phase 3: Hybrid Mode
- [ ] Option to refine Gemini output with local Ollama
- [ ] Compare quality: Gemini-only vs Hybrid vs Ollama-only

---

## Cost Comparison

| Approach | 30-min Video | Quality | Speed |
|----------|-------------|---------|-------|
| Ollama (local) | $0 | Good | ~2-5 min |
| Gemini 2.0 Flash | ~$0.05 | Good | ~30 sec |
| Gemini 2.5 Flash | ~$0.15 | Very Good | ~30 sec |
| Gemini 2.5 Pro | ~$0.64 | Excellent | ~1 min |
| **Gemini 3 Pro** | **~$1.00** | **Best** | **~1-2 min** |

**Decision: Use Gemini 3 Pro** (`gemini-3-pro-preview`)
- "Best model in the world for multimodal understanding"
- Best for complex math notation and equation recognition
- ~$1/video is acceptable for BIRS research quality

---

## Files to Create

1. `gemini_video_analyzer.py` - Main Gemini-based analyzer
2. `batch_analyze.py` - Process multiple videos
3. `compare_methods.py` - Quality comparison tool

---

## Environment Setup

```bash
pip install google-generativeai

# API key (store in environment or file)
export GOOGLE_API_KEY="your-api-key"
# Or use existing key from ~/pdf_reader.py
```

---

## Decision Points

1. **Cost tolerance?** - Gemini costs ~$0.04/video vs free local
2. **Speed priority?** - Gemini is 10x faster
3. **Privacy concerns?** - Videos sent to Google servers
4. **Quality requirements?** - Gemini likely better for complex math notation

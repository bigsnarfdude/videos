# BIRS NotebookLM - Implementation Plan

## Infrastructure

| Resource | Location | Purpose |
|----------|----------|---------|
| **Gemini 3 Pro** | GCP API | Video analysis, script generation |
| **nigel.birs.ca** | GPU server | Dia TTS (10GB VRAM), gpt-oss:120b |
| **Local Mac** | Development | Testing, demos |
| **4TB HDD** | nigel | Video cache, outputs |

---

## Top-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    BIRS NotebookLM Pipeline                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │  INPUT   │───▶│ ANALYZE  │───▶│ GENERATE │───▶│  OUTPUT  │  │
│  │  Video   │    │ Gemini 3 │    │  Podcast │    │  JSON+MP3│  │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘  │
│       │               │               │               │         │
│       ▼               ▼               ▼               ▼         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    COMPONENT BREAKDOWN                    │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │  C1: Video Ingestion     → Download, validate, cache     │  │
│  │  C2: Video Analysis      → Gemini 3 Pro (transcript+LaTeX)│  │
│  │  C3: Script Generation   → Gemini (podcast dialogue)     │  │
│  │  C4: Audio Synthesis     → Dia TTS on nigel              │  │
│  │  C5: Output Assembly     → JSON + MP3 packaging          │  │
│  │  C6: Web Interface       → Gradio demo UI                │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### C1: Video Ingestion (`video_ingestion.py`)
**Status**: 🟡 Partial (have download, need validation)

**Input**: BIRS video URL or file path
**Output**: Local video file path

```python
# Functions needed:
def download_video(url: str, cache_dir: str) -> str:
    """Download video from videos.birs.ca to local cache"""

def validate_video(path: str) -> dict:
    """Check format, duration, size. Return metadata."""

def get_video_metadata(url: str) -> dict:
    """Extract event_id, speaker, date from URL pattern"""
```

**Dependencies**: `requests`, `ffmpeg-python`
**Location**: Run locally or on nigel

---

### C2: Video Analysis (`video_analyzer.py`)
**Status**: ✅ DONE (`gemini_video_analyzer.py`)

**Input**: Video file path
**Output**: Structured JSON (transcript + LaTeX + metadata)

```python
# Already built - enhance with:
def analyze_video(path: str, prompt_type: str = "full") -> dict:
    """
    prompt_type options:
    - "full": transcript + visual LaTeX + metadata
    - "chalk": optimized for blackboard
    - "slides": optimized for slide presentations
    """

# Output schema:
{
    "metadata": {
        "speaker": str,
        "title": str,
        "institution": str,
        "workshop": str,
        "date": str,
        "format": "blackboard|slides|mixed",
        "location": "internal|zoom"
    },
    "transcript": {
        "full_text": str,
        "segments": [{"start": float, "end": float, "text": str}]
    },
    "visual_content": [
        {"timestamp": str, "type": str, "equations": [str], "notes": str}
    ],
    "equations": [str],  # All LaTeX extracted
    "key_concepts": [str],
    "summary": str
}
```

**Dependencies**: `google-generativeai`
**Location**: Local (API call to GCP)

---

### C3: Script Generation (`podcast_script.py`)
**Status**: 🔴 TODO

**Input**: Analysis JSON from C2
**Output**: Dialogue script with [S1]/[S2] tags

```python
def generate_podcast_script(analysis: dict, style: str = "educational") -> str:
    """
    Use Gemini to create 2-speaker dialogue about the lecture.

    style options:
    - "educational": explain concepts clearly
    - "casual": more conversational, jokes
    - "deep_dive": technical details

    Returns script like:
    "[S1] Today we're discussing quantum walks on Cayley graphs.
     [S2] That sounds complex! What's the key insight?
     [S1] Well, imagine a quantum particle... (laughs)"
    """

PODCAST_PROMPT = '''
Based on this mathematics lecture analysis, create a podcast script.

SPEAKERS:
- [S1] Alex: Curious graduate student, asks good questions
- [S2] Sam: Expert mathematician, explains clearly

GUIDELINES:
- 2-3 minutes of dialogue (about 400-500 words)
- Start with hook, end with takeaway
- Use natural speech patterns
- Include 1-2 non-verbals: (laughs), (sighs), (hmm)
- Make complex math accessible
- Reference specific equations/theorems from lecture

LECTURE ANALYSIS:
{analysis_json}

OUTPUT: Only the script, starting with [S1]
'''
```

**Dependencies**: `google-generativeai`
**Location**: Local (API call to GCP)

---

### C4: Audio Synthesis (`audio_synthesis.py`)
**Status**: 🔴 TODO

**Input**: Dialogue script with [S1]/[S2] tags
**Output**: MP3 audio file

```python
# Run on nigel.birs.ca (has GPU)

def synthesize_podcast(script: str, output_path: str) -> str:
    """
    Use Dia TTS to convert script to audio.
    Requires ~10GB VRAM on nigel.
    """
    from transformers import AutoProcessor, DiaForConditionalGeneration
    import torch

    model_id = "nari-labs/Dia-1.6B-0626"
    processor = AutoProcessor.from_pretrained(model_id)
    model = DiaForConditionalGeneration.from_pretrained(model_id)
    model = model.to("cuda")

    # Chunk script if > 2 minutes (Dia limit)
    chunks = chunk_script(script, max_words=150)
    audio_segments = []

    for chunk in chunks:
        inputs = processor(text=[chunk], return_tensors="pt").to("cuda")
        outputs = model.generate(
            **inputs,
            max_new_tokens=3072,
            guidance_scale=3.0,
            temperature=1.8,
            top_p=0.90
        )
        audio_segments.append(processor.batch_decode(outputs)[0])

    # Concatenate and save
    final_audio = concatenate_audio(audio_segments)
    save_audio(final_audio, output_path)
    return output_path

def chunk_script(script: str, max_words: int = 150) -> list:
    """Split script at speaker boundaries, respecting max length"""
```

**Dependencies**: `transformers`, `torch`, `pydub`
**Location**: **nigel.birs.ca** (GPU required)

---

### C5: Output Assembly (`output_assembly.py`)
**Status**: 🔴 TODO

**Input**: Analysis JSON + MP3 audio
**Output**: Final package (JSON + MP3 + metadata)

```python
def assemble_output(
    video_url: str,
    analysis: dict,
    audio_path: str,
    output_dir: str
) -> dict:
    """
    Create final output package:
    - {lecture_id}.json - full analysis
    - {lecture_id}.mp3 - podcast audio
    - {lecture_id}_meta.json - index metadata
    """

# Output structure:
output/
├── 25w5490-57785/
│   ├── analysis.json      # Full Gemini analysis
│   ├── podcast.mp3        # Dia-generated audio
│   ├── metadata.json      # Quick-access metadata
│   └── transcript.txt     # Plain text transcript
```

**Dependencies**: `json`, `shutil`
**Location**: Local or nigel

---

### C6: Web Interface (`app.py`)
**Status**: 🔴 TODO

**Input**: User uploads video URL or file
**Output**: Interactive display of results

```python
import gradio as gr

def process_lecture(video_input: str) -> tuple:
    """Full pipeline: video → analysis → podcast"""
    # 1. Download/validate video
    # 2. Analyze with Gemini
    # 3. Generate podcast script
    # 4. Synthesize audio (call nigel)
    # 5. Return results
    return analysis_json, audio_file, summary

demo = gr.Interface(
    fn=process_lecture,
    inputs=[
        gr.Textbox(label="BIRS Video URL", placeholder="https://videos.birs.ca/...")
    ],
    outputs=[
        gr.JSON(label="Lecture Analysis"),
        gr.Audio(label="Podcast Overview"),
        gr.Markdown(label="Summary")
    ],
    title="BIRS NotebookLM",
    description="Transform math lectures into searchable content + audio overviews"
)
```

**Dependencies**: `gradio`
**Location**: Local for demo, deploy to cloud later

---

## File Structure

```
~/vlm/
├── IMPLEMENTATION_PLAN.md    # This file
├── HACKATHON_PLAN.md         # Pitch deck
├── demo_output/              # Experiment results
│
├── src/
│   ├── __init__.py
│   ├── video_ingestion.py    # C1: Download/validate
│   ├── video_analyzer.py     # C2: Gemini analysis (DONE)
│   ├── podcast_script.py     # C3: Generate dialogue
│   ├── audio_synthesis.py    # C4: Dia TTS (runs on nigel)
│   ├── output_assembly.py    # C5: Package outputs
│   └── prompts.py            # All prompt templates
│
├── app.py                    # C6: Gradio interface
├── pipeline.py               # End-to-end orchestration
│
├── config/
│   ├── settings.py           # API keys, paths
│   └── nigel.yaml            # Remote server config
│
└── tests/
    └── test_pipeline.py
```

---

## Execution Plan

### Phase 1: Core Pipeline (Day 1 Morning)
- [ ] **C1**: Video ingestion with caching
- [ ] **C2**: Standardize JSON output schema (already works)
- [ ] **C3**: Podcast script generation prompt

### Phase 2: Audio (Day 1 Afternoon)
- [ ] **C4**: Install Dia on nigel.birs.ca
- [ ] **C4**: Test audio synthesis
- [ ] **C4**: Build remote execution wrapper

### Phase 3: Integration (Day 2 Morning)
- [ ] **C5**: Output assembly
- [ ] **Pipeline**: End-to-end test
- [ ] **C6**: Gradio demo UI

### Phase 4: Polish (Day 2 Afternoon)
- [ ] 5 diverse demo videos processed
- [ ] Error handling
- [ ] Demo script rehearsed

---

## Commands Quick Reference

```bash
# Install Dia on nigel
ssh vincent@nigel.birs.ca
pip install transformers torch accelerate
pip install git+https://github.com/nari-labs/dia.git

# Test Dia
python -c "from transformers import DiaForConditionalGeneration; print('OK')"

# Check GPU
nvidia-smi

# Run audio synthesis remotely
scp script.txt vincent@nigel.birs.ca:/tmp/
ssh vincent@nigel.birs.ca "python ~/vlm/src/audio_synthesis.py /tmp/script.txt /tmp/output.mp3"
scp vincent@nigel.birs.ca:/tmp/output.mp3 ./

# Full pipeline
python pipeline.py --url "https://videos.birs.ca/2025/25w5374/202512030901-Neshveyev.mp4"
```

---

## Success Criteria

1. **Video → JSON**: ✅ Working (Gemini 3 Pro)
2. **JSON → Script**: Generate coherent 2-3 min dialogue
3. **Script → Audio**: Natural-sounding two voices
4. **End-to-end**: < 5 minutes total processing
5. **Demo**: Process 3 different lecture types live

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Dia VRAM issue on nigel | Use smaller model or chunk audio |
| Gemini rate limits | Cache all outputs, batch carefully |
| Audio quality poor | Fall back to Google Cloud TTS |
| Network to nigel slow | Pre-install everything, cache videos |
| Demo fails live | Pre-process 5 videos as backup |

# VLM - Video Lecture Analysis with Local Models

Analyze BIRS mathematics lecture videos using local vision language models (VLMs) via Ollama.

## Features

- **Scene-based frame extraction**: Detects slide transitions, captures 4s after each change
- **Vision analysis**: Extract slide titles, equations, diagrams using ministral-3:8b
- **Summary generation**: Executive summaries, lecture outlines via gpt-oss:20b
- **Fast processing**: 0.07x realtime (21 min video in ~94 seconds)

## Scripts

### birs_full_analysis.py
Full video analysis with scene detection and statistics.

```bash
python birs_full_analysis.py /path/to/video.mp4
```

**Settings:**
- `SCENE_THRESHOLD = 0.1` - Sensitivity for slide changes
- `DELAY_AFTER_SCENE = 4` - Seconds to wait after transition
- `MIN_INTERVAL = 10` - Minimum gap between captures

### birs_video_analyzer.py
Combined audio + visual analysis (Whisper + VLM).

```bash
python birs_video_analyzer.py /path/to/video.mp4
```

## Requirements

- Python 3.8+
- ffmpeg
- Ollama with models:
  - `ministral-3:8b` (vision)
  - `gpt-oss:20b` (summary)
- Optional: Whisper for audio transcription

## Output

Results saved to `/tmp/full_analysis.json`:
- Frame-by-frame analysis
- Timestamps and statistics
- Executive summary
- Lecture outline
- Key equations/diagrams

## Performance

| Method | Frames | Time | Ratio |
|--------|--------|------|-------|
| Fixed 30s intervals | 44 | 153s | 0.12x |
| Scene detection | 15 | 94s | 0.07x |

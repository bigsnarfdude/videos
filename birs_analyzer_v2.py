#!/usr/bin/env python3
"""
BIRS Video Analyzer v2 - Structured JSON Output

Analyzes BIRS mathematics lecture videos with Gemini 3 Pro.
Outputs validated JSON with proper schema.

Usage:
    python birs_analyzer_v2.py /path/to/video.mp4
    python birs_analyzer_v2.py https://videos.birs.ca/...
"""

import google.generativeai as genai
import os
import sys
import json
import time
import argparse
import re
import requests
from datetime import datetime
from pathlib import Path

# Output directory
OUTPUT_DIR = Path.home() / "vlm" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# JSON Schema for output
OUTPUT_SCHEMA = {
    "metadata": {
        "speaker": str,
        "title": str,
        "institution": str,
        "workshop": str,
        "date": str,
        "format": str,  # "blackboard" | "slides" | "mixed"
        "location": str,  # "internal" | "zoom"
        "field": str,
        "duration_minutes": int
    },
    "transcript": {
        "segments": [{"start": float, "end": float, "text": str}],
        "full_text": str
    },
    "visual_content": [
        {"timestamp": str, "type": str, "content": str, "equations": [str]}
    ],
    "equations": [str],  # All LaTeX equations
    "definitions": [{"term": str, "definition": str}],
    "theorems": [{"name": str, "statement": str}],
    "key_concepts": [str],
    "summary": str,
    "outline": [{"timestamp": str, "topic": str}]
}

# Prompt for pure JSON output
JSON_PROMPT = '''Analyze this BIRS mathematics lecture video and return ONLY valid JSON.

Output exactly this JSON structure (no markdown, no code blocks, just JSON):

{
  "metadata": {
    "speaker": "Full name of speaker",
    "title": "Lecture title from slides or introduction",
    "institution": "Speaker's institution if mentioned",
    "workshop": "Workshop code (e.g., 25w5490)",
    "date": "YYYY-MM-DD if visible",
    "format": "blackboard or slides or mixed",
    "location": "internal or zoom",
    "field": "Mathematical field",
    "duration_minutes": 30
  },
  "transcript": {
    "segments": [
      {"start": 0.0, "end": 60.0, "text": "What the speaker said..."}
    ],
    "full_text": "Complete transcript concatenated"
  },
  "visual_content": [
    {
      "timestamp": "05:30",
      "type": "slide or board or diagram",
      "content": "Description of what's shown",
      "equations": ["$equation1$", "$equation2$"]
    }
  ],
  "equations": ["$E = mc^2$", "$\\\\int_0^1 f(x) dx$"],
  "definitions": [
    {"term": "Cayley graph", "definition": "A graph encoding..."}
  ],
  "theorems": [
    {"name": "Main Theorem", "statement": "For all G..."}
  ],
  "key_concepts": ["concept1", "concept2", "concept3"],
  "summary": "2-3 paragraph summary of the lecture content.",
  "outline": [
    {"timestamp": "00:00", "topic": "Introduction"},
    {"timestamp": "05:00", "topic": "Background"}
  ]
}

IMPORTANT:
- Return ONLY the JSON object, no markdown formatting
- Use LaTeX notation for all equations (escape backslashes as \\\\)
- Include timestamps in MM:SS format
- Extract ALL visible equations from slides/board
- Identify format (blackboard vs slides) from visual content
'''


def get_api_key():
    """Load API key from file or environment."""
    key_file = Path.home() / ".gemini_api_key"
    if key_file.exists():
        return key_file.read_text().strip()
    return os.environ.get("GEMINI_API_KEY")


def download_video(url: str, cache_dir: Path = None) -> Path:
    """Download video from URL to local cache."""
    if cache_dir is None:
        cache_dir = Path("/tmp/birs_video_cache")
    cache_dir.mkdir(exist_ok=True)

    # Extract filename from URL
    filename = url.split("/")[-1]
    local_path = cache_dir / filename

    if local_path.exists():
        print(f"Using cached video: {local_path}")
        return local_path

    print(f"Downloading: {url}")
    response = requests.get(url, stream=True)
    response.raise_for_status()

    total = int(response.headers.get('content-length', 0))
    with open(local_path, 'wb') as f:
        downloaded = 0
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
            downloaded += len(chunk)
            if total:
                pct = (downloaded / total) * 100
                print(f"\r  {pct:.1f}% ({downloaded/1e6:.1f}MB)", end="")
    print()

    return local_path


def extract_json(text: str) -> dict:
    """Extract JSON from response, handling markdown code blocks."""
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strip markdown code blocks
    if text.startswith("```"):
        # Remove opening ```json or ``` and closing ```
        lines = text.split('\n')
        if lines[0].startswith("```"):
            lines = lines[1:]  # Remove first line
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]  # Remove last line
        text = '\n'.join(lines)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

    # Try regex extraction
    patterns = [
        r'```json\s*(.*?)\s*```',
        r'```\s*(.*?)\s*```',
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                continue

    # Last resort: find JSON object
    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError("Could not extract valid JSON from response")


def analyze_video(video_path: str, model_name: str = "gemini-2.0-flash") -> dict:
    """Analyze video and return structured JSON."""

    # Handle URL input
    if video_path.startswith("http"):
        video_path = download_video(video_path)
    else:
        video_path = Path(video_path)

    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    video_name = video_path.stem
    file_size_mb = video_path.stat().st_size / 1e6

    print("=" * 60)
    print("BIRS ANALYZER v2 - Structured JSON Output")
    print("=" * 60)
    print(f"Video: {video_path.name}")
    print(f"Size: {file_size_mb:.1f} MB")
    print(f"Model: {model_name}")
    print("=" * 60)

    # Configure API
    api_key = get_api_key()
    if not api_key:
        raise ValueError("No API key found. Store in ~/.gemini_api_key")

    genai.configure(api_key=api_key)

    # Upload video
    print("\n[1/3] Uploading video...")
    start_upload = time.time()
    video_file = genai.upload_file(str(video_path))

    # Wait for processing
    while video_file.state.name == "PROCESSING":
        time.sleep(3)
        video_file = genai.get_file(video_file.name)
        print(f"  Processing: {video_file.state.name}")

    upload_time = time.time() - start_upload

    if video_file.state.name != "ACTIVE":
        raise RuntimeError(f"Upload failed: {video_file.state.name}")

    print(f"  Upload complete: {upload_time:.1f}s")

    # Analyze
    print(f"\n[2/3] Analyzing with {model_name}...")
    start_analysis = time.time()

    model = genai.GenerativeModel(model_name)
    response = model.generate_content([video_file, JSON_PROMPT])

    analysis_time = time.time() - start_analysis
    print(f"  Analysis complete: {analysis_time:.1f}s")

    # Parse JSON
    print("\n[3/3] Parsing JSON output...")
    try:
        analysis = extract_json(response.text)
        print("  JSON parsed successfully")
    except ValueError as e:
        print(f"  WARNING: {e}")
        print("  Saving raw response for debugging")
        analysis = {"raw_response": response.text, "parse_error": str(e)}

    # Add processing metadata
    result = {
        "source": {
            "video_path": str(video_path),
            "video_name": video_name,
            "file_size_mb": file_size_mb,
            "url": str(video_path) if str(video_path).startswith("http") else None
        },
        "processing": {
            "model": model_name,
            "upload_time_s": upload_time,
            "analysis_time_s": analysis_time,
            "total_time_s": upload_time + analysis_time,
            "timestamp": datetime.now().isoformat()
        },
        "analysis": analysis
    }

    # Save output
    output_path = OUTPUT_DIR / f"{video_name}.json"
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n" + "=" * 60)
    print("OUTPUT SAVED")
    print("=" * 60)
    print(f"File: {output_path}")
    print(f"Upload: {upload_time:.1f}s")
    print(f"Analysis: {analysis_time:.1f}s")
    print(f"Total: {upload_time + analysis_time:.1f}s")

    # Cleanup
    try:
        genai.delete_file(video_file.name)
    except:
        pass

    return result


def main():
    parser = argparse.ArgumentParser(description="BIRS Video Analyzer v2")
    parser.add_argument("video", help="Video file path or URL")
    parser.add_argument("--model", default="gemini-2.0-flash",
                       help="Model (default: gemini-2.0-flash)")
    parser.add_argument("--output", "-o", help="Custom output path")

    args = parser.parse_args()

    result = analyze_video(args.video, args.model)

    # Print summary
    if "analysis" in result and isinstance(result["analysis"], dict):
        meta = result["analysis"].get("metadata", {})
        print(f"\n--- Quick Summary ---")
        print(f"Speaker: {meta.get('speaker', 'Unknown')}")
        print(f"Title: {meta.get('title', 'Unknown')}")
        print(f"Format: {meta.get('format', 'Unknown')}")
        print(f"Equations: {len(result['analysis'].get('equations', []))}")


if __name__ == "__main__":
    main()

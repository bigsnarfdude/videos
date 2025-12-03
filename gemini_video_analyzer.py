#!/usr/bin/env python3
"""
BIRS Video Analyzer using Gemini 3 Pro Preview

Analyzes BIRS mathematics lecture videos with Google's best multimodal model.
Single API call handles transcription + visual analysis + summary.

Usage:
    python gemini_video_analyzer.py /path/to/video.mp4
    python gemini_video_analyzer.py /path/to/video.mp4 --model gemini-2.5-flash
"""

import google.generativeai as genai
import os
import sys
import json
import time
import argparse
from datetime import datetime

# Output directories
OUTPUT_BASE = os.path.expanduser("~/vlm_output")
SUMMARIES_DIR = os.path.join(OUTPUT_BASE, "summaries")

# Create output directories
os.makedirs(SUMMARIES_DIR, exist_ok=True)

# Analysis prompt for BIRS lectures
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
  "equations": ["important equations in LaTeX format"]
}

## 2. TRANSCRIPT SUMMARY
Summarize what the speaker said, focusing on:
- Main arguments and theorems presented
- Key definitions introduced
- Important examples discussed

## 3. VISUAL CONTENT
List key slides/board content with approximate timestamps:
- [MM:SS] Slide title / Board content description
- Include any equations, diagrams, or figures shown

## 4. EXECUTIVE SUMMARY
2-3 paragraphs combining audio and visual content into a coherent summary.

## 5. LECTURE OUTLINE
Timestamped outline of the lecture structure.

## 6. KEY TAKEAWAYS
5 bullet points with the most important ideas.
"""


def get_api_key():
    """Load API key from file or environment."""
    key_file = os.path.expanduser("~/.gemini_api_key")
    if os.path.exists(key_file):
        with open(key_file) as f:
            return f.read().strip()
    return os.environ.get("GEMINI_API_KEY")


def analyze_video(video_path, model_name="gemini-3-pro-preview"):
    """Upload and analyze a video with Gemini."""

    # Get video name for output
    video_name = os.path.splitext(os.path.basename(video_path))[0]

    print("=" * 60)
    print("BIRS VIDEO ANALYZER - Gemini API")
    print("=" * 60)
    print(f"Video: {video_path}")
    print(f"Model: {model_name}")
    print(f"Size: {os.path.getsize(video_path) / 1024 / 1024:.1f} MB")
    print("=" * 60)

    # Configure API
    api_key = get_api_key()
    if not api_key:
        print("ERROR: No API key found.")
        print("Store key in ~/.gemini_api_key or set GEMINI_API_KEY env var")
        sys.exit(1)

    genai.configure(api_key=api_key)

    # Upload video
    print("\nUploading video to Gemini...")
    start_upload = time.time()
    video_file = genai.upload_file(video_path, display_name=f"{video_name}.mp4")

    # Wait for processing
    print("Processing video...")
    while video_file.state.name == "PROCESSING":
        time.sleep(5)
        video_file = genai.get_file(video_file.name)
        print(f"  State: {video_file.state.name}")

    upload_time = time.time() - start_upload

    if video_file.state.name == "FAILED":
        print(f"ERROR: Video processing failed: {video_file.state.name}")
        sys.exit(1)

    print(f"Upload complete: {upload_time:.1f}s")
    print(f"File ID: {video_file.name}")

    # Analyze with Gemini
    print(f"\nAnalyzing with {model_name}...")
    start_analysis = time.time()

    model = genai.GenerativeModel(model_name)
    response = model.generate_content([video_file, ANALYSIS_PROMPT])

    analysis_time = time.time() - start_analysis

    print(f"Analysis complete: {analysis_time:.1f}s")

    # Display results
    print("\n" + "=" * 60)
    print("ANALYSIS RESULT")
    print("=" * 60)
    print(response.text)

    # Save results
    output = {
        "video": video_path,
        "video_name": video_name,
        "model": model_name,
        "file_id": video_file.name,
        "upload_time": upload_time,
        "analysis_time": analysis_time,
        "total_time": upload_time + analysis_time,
        "timestamp": datetime.now().isoformat(),
        "analysis": response.text
    }

    output_path = os.path.join(SUMMARIES_DIR, f"{video_name}_gemini.json")
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print("\n" + "=" * 60)
    print("STATISTICS")
    print("=" * 60)
    print(f"Upload time: {upload_time:.1f}s")
    print(f"Analysis time: {analysis_time:.1f}s")
    print(f"Total time: {upload_time + analysis_time:.1f}s")
    print(f"\nResults saved to: {output_path}")

    # Clean up uploaded file
    try:
        genai.delete_file(video_file.name)
        print("Uploaded file cleaned up")
    except:
        pass

    return output


def main():
    parser = argparse.ArgumentParser(description="Analyze BIRS lecture videos with Gemini")
    parser.add_argument("video", help="Path to video file")
    parser.add_argument("--model", default="gemini-3-pro-preview",
                       choices=["gemini-3-pro-preview", "gemini-2.5-pro", "gemini-2.5-flash"],
                       help="Gemini model to use (default: gemini-3-pro-preview)")

    args = parser.parse_args()

    if not os.path.exists(args.video):
        print(f"ERROR: Video file not found: {args.video}")
        sys.exit(1)

    analyze_video(args.video, args.model)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
BIRS Video Analyzer - Combines audio transcription with frame analysis
Uses Whisper for audio and Qwen3-VL for visual content (slides, chalkboard, equations)
"""

import os
import sys
import json
import subprocess
import base64
import tempfile
from pathlib import Path
from datetime import datetime

try:
    import ollama
except ImportError:
    print("Installing ollama package...")
    subprocess.run([sys.executable, "-m", "pip", "install", "ollama", "-q"])
    import ollama

# Configuration
FRAME_INTERVAL = 30  # Extract frame every N seconds
MAX_FRAMES = 20      # Maximum frames to analyze
WHISPER_MODEL = "large"
VISION_MODEL = "qwen3-vl:8b"
SUMMARY_MODEL = "gpt-oss:20b"  # For final summary

def run_cmd(cmd, capture=True):
    """Run shell command and return output"""
    result = subprocess.run(cmd, shell=True, capture_output=capture, text=True)
    return result.stdout.strip() if capture else result.returncode

def get_video_duration(video_path):
    """Get video duration in seconds"""
    cmd = f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{video_path}"'
    try:
        return float(run_cmd(cmd))
    except:
        return 0

def extract_frames(video_path, output_dir, interval=30, max_frames=20):
    """Extract frames at regular intervals"""
    os.makedirs(output_dir, exist_ok=True)
    duration = get_video_duration(video_path)

    # Calculate actual interval to get max_frames evenly distributed
    if duration > 0:
        actual_interval = max(interval, duration / max_frames)
    else:
        actual_interval = interval

    cmd = f'ffmpeg -i "{video_path}" -vf "fps=1/{int(actual_interval)}" -frames:v {max_frames} "{output_dir}/frame_%04d.jpg" -y 2>/dev/null'
    run_cmd(cmd, capture=False)

    frames = sorted(Path(output_dir).glob("frame_*.jpg"))
    print(f"  Extracted {len(frames)} frames (every {actual_interval:.0f}s from {duration:.0f}s video)")
    return frames

def extract_audio(video_path, output_path):
    """Extract audio as mp3"""
    cmd = f'ffmpeg -i "{video_path}" -vn -acodec libmp3lame -q:a 2 "{output_path}" -y 2>/dev/null'
    run_cmd(cmd, capture=False)
    print(f"  Extracted audio to {output_path}")
    return output_path

def transcribe_audio(audio_path):
    """Transcribe audio using Whisper"""
    print(f"  Transcribing with Whisper {WHISPER_MODEL}...")
    output_dir = "/tmp/whisper_out"
    os.makedirs(output_dir, exist_ok=True)

    # Try multiple whisper paths
    whisper_paths = [
        "/home/vincent/.local/bin/whisper",
        "whisper",
        "/usr/local/bin/whisper"
    ]

    whisper_cmd = None
    for path in whisper_paths:
        if subprocess.run(["which", path], capture_output=True).returncode == 0 or os.path.exists(path):
            whisper_cmd = path
            break

    if not whisper_cmd:
        print("  WARNING: Whisper not found, skipping transcription")
        return ""

    result = subprocess.run(
        [whisper_cmd, audio_path, "--model", WHISPER_MODEL, "--output_format", "json", "--output_dir", output_dir],
        capture_output=True, text=True
    )

    # Read the output JSON
    json_path = Path(output_dir) / (Path(audio_path).stem + ".json")
    if json_path.exists():
        with open(json_path) as f:
            data = json.load(f)
        return data.get("text", "")

    # Fallback: try txt output
    txt_path = Path(output_dir) / (Path(audio_path).stem + ".txt")
    if txt_path.exists():
        return txt_path.read_text()

    return ""

def analyze_frame(frame_path, frame_num, total_frames):
    """Analyze a single frame with Qwen3-VL"""
    with open(frame_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    prompt = """Analyze this frame from a mathematics/research lecture. Focus on:
1. Any visible slides - title and key bullet points
2. Chalkboard/whiteboard content - equations, diagrams, formulas
3. Any visible text, labels, or annotations
4. What the speaker is pointing at or explaining

Be concise. Capture all visible mathematical/technical content.
If just a speaker talking with no visual content, say "Speaker only - no slides/board visible"."""

    try:
        response = ollama.chat(
            model=VISION_MODEL,
            messages=[{
                "role": "user",
                "content": prompt,
                "images": [image_data]
            }]
        )
        return response["message"]["content"]
    except Exception as e:
        return f"Error analyzing frame: {e}"

def analyze_frames(frame_paths):
    """Analyze all frames and return combined visual analysis"""
    print(f"  Analyzing {len(frame_paths)} frames with {VISION_MODEL}...")
    analyses = []

    for i, frame_path in enumerate(frame_paths):
        print(f"    Frame {i+1}/{len(frame_paths)}...", end=" ", flush=True)
        analysis = analyze_frame(frame_path, i, len(frame_paths))

        # Calculate approximate timestamp
        timestamp_min = i * FRAME_INTERVAL // 60
        timestamp_sec = i * FRAME_INTERVAL % 60

        analyses.append({
            "frame": i + 1,
            "timestamp": f"{timestamp_min:02d}:{timestamp_sec:02d}",
            "analysis": analysis
        })

        # Truncate for display
        preview = analysis[:100].replace("\n", " ")
        if len(analysis) > 100:
            preview += "..."
        print(preview)

    return analyses

def generate_combined_summary(transcript, frame_analyses, video_info):
    """Generate comprehensive summary combining audio and visual analysis"""
    print(f"  Generating combined summary with {SUMMARY_MODEL}...")

    # Build visual content summary (skip frames with no content)
    visual_parts = []
    for a in frame_analyses:
        if "Speaker only" not in a['analysis'] and "no slides" not in a['analysis'].lower():
            visual_parts.append(f"[{a['timestamp']}] {a['analysis']}")
    visual_content = "\n\n".join(visual_parts)

    prompt = f"""Analyze this BIRS (Banff International Research Station) mathematics lecture.

VIDEO: {video_info.get('filename', 'Unknown')}
DURATION: {video_info.get('duration_seconds', 0)/60:.1f} minutes

=== AUDIO TRANSCRIPT ===
{transcript[:10000]}

=== VISUAL CONTENT (slides/chalkboard) ===
{visual_content[:6000]}

Create a comprehensive analysis:

## METADATA
Extract as JSON:
- title: Lecture title (from slides or intro)
- speaker: Speaker name
- institution: If mentioned
- topic: Main mathematical topic/field
- key_concepts: List of 5-10 key concepts
- equations: Important equations shown (LaTeX format if possible)

## EXECUTIVE SUMMARY
2-3 paragraphs summarizing what this lecture covers and main results.

## LECTURE OUTLINE
Timestamped outline combining audio AND visual content.

## KEY EQUATIONS/DIAGRAMS
List important mathematical content shown on slides/board.

## TAKEAWAYS
5 bullet points with the most important ideas."""

    try:
        response = ollama.chat(
            model=SUMMARY_MODEL,
            messages=[{"role": "user", "content": prompt}]
        )
        return response["message"]["content"]
    except Exception as e:
        return f"Error generating summary: {e}"

def analyze_video(video_path):
    """Main function to analyze a BIRS video"""
    print(f"\n{'='*60}")
    print(f"BIRS VIDEO ANALYZER")
    print(f"{'='*60}")
    print(f"Video: {video_path}")

    # Get video info
    duration = get_video_duration(video_path)
    video_info = {
        "path": video_path,
        "filename": os.path.basename(video_path),
        "duration_seconds": duration,
        "analyzed_at": datetime.now().isoformat()
    }
    print(f"Duration: {duration/60:.1f} minutes")

    # Create temp directory for working files
    with tempfile.TemporaryDirectory() as tmpdir:
        # Step 1: Extract frames
        print(f"\n[1/4] Extracting frames...")
        frames_dir = os.path.join(tmpdir, "frames")
        frame_paths = extract_frames(video_path, frames_dir, FRAME_INTERVAL, MAX_FRAMES)

        # Step 2: Extract and transcribe audio
        print(f"\n[2/4] Extracting and transcribing audio...")
        audio_path = os.path.join(tmpdir, "audio.mp3")
        extract_audio(video_path, audio_path)
        transcript = transcribe_audio(audio_path)
        print(f"  Transcript length: {len(transcript)} characters")

        # Step 3: Analyze frames with vision model
        print(f"\n[3/4] Analyzing visual content...")
        frame_analyses = analyze_frames(frame_paths)

        # Step 4: Generate combined summary
        print(f"\n[4/4] Generating combined summary...")
        summary = generate_combined_summary(transcript, frame_analyses, video_info)

    print(f"\n{'='*60}")
    print("ANALYSIS COMPLETE")
    print(f"{'='*60}\n")

    return {
        "video_info": video_info,
        "transcript": transcript,
        "frame_analyses": frame_analyses,
        "summary": summary
    }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python birs_video_analyzer.py <video_path_or_url>")
        print("Example: python birs_video_analyzer.py https://videos.birs.ca/2025/25w5490/202511121031-Pham.mp4")
        sys.exit(1)

    video_path = sys.argv[1]

    # If URL, download first
    if video_path.startswith("http"):
        print(f"Downloading video...")
        local_path = "/tmp/birs_video.mp4"
        subprocess.run(["wget", "-q", "-O", local_path, video_path])
        video_path = local_path

    result = analyze_video(video_path)

    # Print summary
    print("\n" + "="*60)
    print("COMBINED ANALYSIS")
    print("="*60 + "\n")
    print(result["summary"])

    # Save full results
    output_file = "/tmp/birs_analysis_result.json"
    with open(output_file, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\n\nFull results saved to: {output_file}")

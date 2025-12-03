#!/usr/bin/env python3
"""
BIRS NotebookLM Pipeline - End-to-End Processing

Processes a BIRS lecture video through the full pipeline:
1. Video Ingestion (download/cache)
2. Video Analysis (Gemini)
3. Podcast Script Generation (Gemini)
4. Audio Synthesis (Dia TTS on nigel)
5. Output Assembly

Usage:
    python pipeline.py https://videos.birs.ca/.../video.mp4
    python pipeline.py /path/to/video.mp4 --skip-audio
"""

import os
import sys
import json
import time
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

# Import local modules
from birs_analyzer_v2 import analyze_video
from podcast_script import generate_script, validate_script

# Configuration
OUTPUT_DIR = Path.home() / "vlm" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

NIGEL_HOST = "vincent@nigel.birs.ca"
NIGEL_DIA_ENV = "~/dia_env"
NIGEL_SCRIPT_DIR = "/tmp/birs_podcast"


def print_banner(text):
    """Print a banner."""
    print("\n" + "=" * 60)
    print(text)
    print("=" * 60)


def run_local_stages(video_path: str, model: str = "gemini-2.0-flash",
                     style: str = "educational") -> dict:
    """Run stages 1-3 locally."""

    print_banner("STAGE 1: VIDEO ANALYSIS")
    start = time.time()

    # Analyze video with Gemini
    result = analyze_video(video_path, model)

    analysis_time = time.time() - start
    print(f"Analysis completed in {analysis_time:.1f}s")

    # Extract video name for output files
    if "source" in result:
        video_name = result["source"]["video_name"]
    else:
        video_name = Path(video_path).stem

    print_banner("STAGE 2: PODCAST SCRIPT GENERATION")
    start = time.time()

    # Generate podcast script
    script = generate_script(result, style, model)
    validation = validate_script(script)

    script_time = time.time() - start
    print(f"Script generated in {script_time:.1f}s")
    print(f"Word count: {validation['stats']['word_count']}")

    if validation["issues"]:
        for issue in validation["issues"]:
            print(f"  Warning: {issue}")

    # Save script
    script_path = OUTPUT_DIR / f"{video_name}_podcast.txt"
    with open(script_path, "w") as f:
        f.write(script)
    print(f"Script saved: {script_path}")

    return {
        "video_name": video_name,
        "analysis": result,
        "script": script,
        "script_path": str(script_path),
        "timings": {
            "analysis": analysis_time,
            "script": script_time
        }
    }


def synthesize_on_nigel(script_path: str, output_name: str) -> str:
    """Run Dia TTS on nigel.birs.ca."""

    print_banner("STAGE 3: AUDIO SYNTHESIS (nigel.birs.ca)")
    start = time.time()

    # Create remote directory
    subprocess.run(
        ["ssh", NIGEL_HOST, f"mkdir -p {NIGEL_SCRIPT_DIR}"],
        check=True
    )

    # Copy script to nigel
    remote_script = f"{NIGEL_SCRIPT_DIR}/script.txt"
    print(f"Copying script to nigel...")
    subprocess.run(
        ["scp", script_path, f"{NIGEL_HOST}:{remote_script}"],
        check=True
    )

    # Create synthesis script on nigel
    remote_output = f"{NIGEL_SCRIPT_DIR}/output.wav"
    synthesis_script = f'''
import torch
from transformers import AutoProcessor, DiaForConditionalGeneration
import soundfile as sf

# Load model
print("Loading Dia model...")
model_id = "nari-labs/Dia-1.6B-0626"
processor = AutoProcessor.from_pretrained(model_id)
model = DiaForConditionalGeneration.from_pretrained(model_id).to("cuda")

# Load script
with open("{remote_script}") as f:
    script = f.read()

# Generate audio
print("Generating audio...")
inputs = processor(text=[script], return_tensors="pt").to("cuda")
outputs = model.generate(
    **inputs,
    max_new_tokens=3072,
    guidance_scale=3.0,
    temperature=1.8,
    top_p=0.90,
    top_k=45
)

# Save
audio = processor.batch_decode(outputs)
processor.save_audio(audio, "{remote_output}")
print("Done!")
'''

    # Write and run synthesis script
    remote_py = f"{NIGEL_SCRIPT_DIR}/synthesize.py"
    subprocess.run(
        ["ssh", NIGEL_HOST, f"cat > {remote_py} << 'SCRIPT'\n{synthesis_script}\nSCRIPT"],
        check=True
    )

    print("Running Dia TTS on nigel (this takes ~30-60 seconds)...")
    result = subprocess.run(
        ["ssh", NIGEL_HOST,
         f"source {NIGEL_DIA_ENV}/bin/activate && python3 {remote_py}"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        raise RuntimeError("Audio synthesis failed on nigel")

    print(result.stdout)

    # Copy audio back
    local_output = OUTPUT_DIR / f"{output_name}_podcast.wav"
    print(f"Copying audio from nigel...")
    subprocess.run(
        ["scp", f"{NIGEL_HOST}:{remote_output}", str(local_output)],
        check=True
    )

    synthesis_time = time.time() - start
    print(f"Audio synthesis completed in {synthesis_time:.1f}s")
    print(f"Audio saved: {local_output}")

    return str(local_output), synthesis_time


def assemble_output(video_name: str, analysis: dict, script: str,
                    audio_path: str = None, timings: dict = None) -> str:
    """Assemble final output package."""

    print_banner("STAGE 4: OUTPUT ASSEMBLY")

    # Create output directory for this lecture
    lecture_dir = OUTPUT_DIR / video_name
    lecture_dir.mkdir(exist_ok=True)

    # Save analysis JSON
    analysis_path = lecture_dir / "analysis.json"
    with open(analysis_path, "w") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)

    # Save podcast script
    script_path = lecture_dir / "podcast_script.txt"
    with open(script_path, "w") as f:
        f.write(script)

    # Copy audio if available
    if audio_path and Path(audio_path).exists():
        import shutil
        audio_dest = lecture_dir / "podcast.wav"
        shutil.copy(audio_path, audio_dest)

    # Create metadata
    metadata = {
        "video_name": video_name,
        "processed": datetime.now().isoformat(),
        "timings": timings,
        "files": {
            "analysis": "analysis.json",
            "script": "podcast_script.txt",
            "audio": "podcast.wav" if audio_path else None
        }
    }

    # Add lecture info from analysis
    if "analysis" in analysis and isinstance(analysis["analysis"], dict):
        meta = analysis["analysis"].get("metadata", {})
        metadata["lecture"] = {
            "speaker": meta.get("speaker"),
            "title": meta.get("title"),
            "workshop": meta.get("workshop"),
            "date": meta.get("date"),
            "field": meta.get("field")
        }

    metadata_path = lecture_dir / "metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"Output assembled: {lecture_dir}")
    print(f"  - analysis.json")
    print(f"  - podcast_script.txt")
    if audio_path:
        print(f"  - podcast.wav")
    print(f"  - metadata.json")

    return str(lecture_dir)


def run_pipeline(video_path: str, model: str = "gemini-2.0-flash",
                 style: str = "educational", skip_audio: bool = False) -> dict:
    """Run the full pipeline."""

    print_banner("BIRS NOTEBOOKLM PIPELINE")
    print(f"Input: {video_path}")
    print(f"Model: {model}")
    print(f"Style: {style}")
    print(f"Audio: {'Skip' if skip_audio else 'Generate on nigel'}")

    total_start = time.time()

    # Stages 1-2: Analysis and Script
    result = run_local_stages(video_path, model, style)

    # Stage 3: Audio Synthesis
    audio_path = None
    if not skip_audio:
        try:
            audio_path, audio_time = synthesize_on_nigel(
                result["script_path"],
                result["video_name"]
            )
            result["timings"]["audio"] = audio_time
        except Exception as e:
            print(f"Warning: Audio synthesis failed: {e}")
            print("Continuing without audio...")

    # Stage 4: Assembly
    output_dir = assemble_output(
        result["video_name"],
        result["analysis"],
        result["script"],
        audio_path,
        result["timings"]
    )

    total_time = time.time() - total_start

    print_banner("PIPELINE COMPLETE")
    print(f"Total time: {total_time:.1f}s")
    print(f"Output: {output_dir}")

    # Print summary
    if "analysis" in result["analysis"]:
        meta = result["analysis"]["analysis"].get("metadata", {})
        print(f"\n--- Lecture Info ---")
        print(f"Speaker: {meta.get('speaker', 'Unknown')}")
        print(f"Title: {meta.get('title', 'Unknown')}")
        print(f"Field: {meta.get('field', 'Unknown')}")

    return {
        "output_dir": output_dir,
        "total_time": total_time,
        "timings": result["timings"]
    }


def main():
    parser = argparse.ArgumentParser(
        description="BIRS NotebookLM Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python pipeline.py https://videos.birs.ca/2025/25w5374/202512030901-Neshveyev.mp4
  python pipeline.py /path/to/video.mp4 --skip-audio
  python pipeline.py video.mp4 --style casual --model gemini-2.0-flash
        """
    )
    parser.add_argument("video", help="Video file path or URL")
    parser.add_argument("--model", default="gemini-2.0-flash",
                       help="Gemini model (default: gemini-2.0-flash)")
    parser.add_argument("--style", choices=["educational", "casual", "deep_dive"],
                       default="educational", help="Podcast style")
    parser.add_argument("--skip-audio", action="store_true",
                       help="Skip audio synthesis (run locally without nigel)")

    args = parser.parse_args()

    result = run_pipeline(
        args.video,
        model=args.model,
        style=args.style,
        skip_audio=args.skip_audio
    )

    return result


if __name__ == "__main__":
    main()

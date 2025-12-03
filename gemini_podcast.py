#!/usr/bin/env python3
"""
BIRS NotebookLM - All-Google Pipeline

Two efficient API calls:
1. Gemini 3 Pro: Video → Analysis JSON + Podcast Script
2. Gemini TTS: Script → Male/Female Audio

Usage:
    python gemini_podcast.py video.mp4
    python gemini_podcast.py https://videos.birs.ca/.../video.mp4
"""

import os
import sys
import json
import wave
import time
import requests
from pathlib import Path

# Use new google-genai SDK for TTS
from google import genai
from google.genai import types

# Use generativeai for video analysis (better video support)
import google.generativeai as genai_legacy

CACHE_DIR = Path("/tmp/birs_video_cache")
CACHE_DIR.mkdir(exist_ok=True)

OUTPUT_DIR = Path.home() / "vlm" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def get_api_key():
    """Load API key."""
    key_file = Path.home() / ".gemini_api_key"
    if key_file.exists():
        return key_file.read_text().strip()
    return os.environ.get("GEMINI_API_KEY")


def download_video(url: str) -> Path:
    """Download video from URL to local cache."""
    filename = url.split("/")[-1]
    local_path = CACHE_DIR / filename

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


def wave_file(filename, pcm, channels=1, rate=24000, sample_width=2):
    """Save PCM data to WAV file."""
    with wave.open(str(filename), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm)


def analyze_and_script(video_path: str, api_key: str) -> dict:
    """
    CALL 1: Video → Analysis + Podcast Script (Gemini 3 Pro)
    Returns both metadata and ready-to-speak dialogue.
    """
    print("=" * 60)
    print("CALL 1: Gemini 3 Pro - Video Analysis + Script Generation")
    print("=" * 60)

    genai_legacy.configure(api_key=api_key)

    # Handle URL input
    if video_path.startswith("http"):
        video_path = str(download_video(video_path))

    # Upload video
    print(f"Uploading: {video_path}")
    start = time.time()

    video_file = genai_legacy.upload_file(video_path)

    # Wait for processing
    while video_file.state.name == "PROCESSING":
        time.sleep(2)
        video_file = genai_legacy.get_file(video_file.name)

    print(f"Upload complete: {time.time() - start:.1f}s")

    # Combined prompt for efficiency
    prompt = """Analyze this BIRS mathematics lecture video and create a podcast script.

OUTPUT FORMAT (JSON):
{
  "metadata": {
    "speaker": "Speaker Name",
    "title": "Lecture Title",
    "institution": "University/Institute",
    "field": "Mathematical Field",
    "date": "YYYY-MM-DD if visible"
  },
  "summary": "2-3 sentence summary of the lecture",
  "key_concepts": ["concept1", "concept2", "concept3"],
  "podcast_script": "Alex: [opening line]\\nSam: [response]\\nAlex: [follow-up]\\n..."
}

PODCAST SCRIPT REQUIREMENTS:
- Two speakers: Alex (curious, asks questions) and Sam (expert, explains)
- 250-350 words of natural dialogue
- NO LaTeX or math symbols - speak equations in plain English
- Example: "the limit as T approaches infinity" NOT "$\\lim_{T \\to \\infty}$"
- Calm, thoughtful tone - like an NPR interview
- Include occasional (hmm) or (laughs) for naturalness

REQUIRED BRANDED INTRO (Alex must say this EXACTLY):
"Welcome everyone! Today we're taking a deep dive into [TOPIC FROM LECTURE]."

REQUIRED BRANDED OUTRO (Sam must end with this EXACTLY):
"And that's the beauty of it. Until next time... keep exploring, keep questioning, and never stop learning."

SCRIPT STRUCTURE:
1. Alex opens with the branded intro welcoming listeners
2. Natural conversation about the lecture content
3. Sam closes with the branded outro catchphrase

Return ONLY valid JSON, no markdown."""

    print("Analyzing with Gemini 3 Pro...")
    model = genai_legacy.GenerativeModel("gemini-3-pro-preview")

    response = model.generate_content([video_file, prompt])

    # Parse JSON
    text = response.text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]

    result = json.loads(text)
    print(f"Analysis complete: {time.time() - start:.1f}s total")

    return result


def generate_audio(script: str, api_key: str, output_path: Path, premium: bool = False) -> Path:
    """
    CALL 2: Script → Audio (Gemini TTS)
    Male/female voices with natural dialogue.

    Args:
        premium: Use gemini-2.5-pro-preview-tts (higher quality, more expensive)
    """
    print("\n" + "=" * 60)
    print("CALL 2: Gemini TTS - Multi-Speaker Audio Generation")
    print("=" * 60)

    client = genai.Client(api_key=api_key)

    # Select model tier
    tts_model = "gemini-2.5-pro-preview-tts" if premium else "gemini-2.5-flash-preview-tts"

    # Format script for TTS
    tts_prompt = f"TTS the following conversation between Alex and Sam:\n{script}"

    print(f"Generating audio with {tts_model}...")
    print(f"  Script length: {len(script.split())} words")
    start = time.time()

    response = client.models.generate_content(
        model=tts_model,
        contents=tts_prompt,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
                    speaker_voice_configs=[
                        types.SpeakerVoiceConfig(
                            speaker='Alex',
                            voice_config=types.VoiceConfig(
                                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                    voice_name='Kore'  # Female
                                )
                            )
                        ),
                        types.SpeakerVoiceConfig(
                            speaker='Sam',
                            voice_config=types.VoiceConfig(
                                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                    voice_name='Charon'  # Male
                                )
                            )
                        ),
                    ]
                )
            )
        )
    )

    # Save audio
    audio_data = response.candidates[0].content.parts[0].inline_data.data
    wave_file(output_path, audio_data)

    duration = len(audio_data) / (24000 * 2)  # 24kHz, 16-bit
    print(f"Audio saved: {output_path}")
    print(f"  Duration: {duration:.1f}s")
    print(f"  Generation time: {time.time() - start:.1f}s")

    return output_path


def run_pipeline(video_path: str, premium_tts: bool = False) -> dict:
    """Run the full 2-call pipeline.

    Args:
        premium_tts: Use gemini-2.5-pro-preview-tts for higher quality audio
    """
    api_key = get_api_key()
    if not api_key:
        raise ValueError("No API key found. Store in ~/.gemini_api_key")

    video_name = Path(video_path).stem

    print("\n" + "=" * 60)
    print("BIRS NotebookLM - All-Google Pipeline")
    print("=" * 60)
    print(f"Input: {video_path}")
    print(f"Output: {OUTPUT_DIR / video_name}")
    print(f"TTS Tier: {'PRO (premium)' if premium_tts else 'Flash (budget)'}")

    total_start = time.time()

    # CALL 1: Analysis + Script
    result = analyze_and_script(video_path, api_key)

    # Save analysis JSON
    json_path = OUTPUT_DIR / f"{video_name}_analysis.json"
    with open(json_path, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {json_path}")

    # Save script separately
    script_path = OUTPUT_DIR / f"{video_name}_script.txt"
    with open(script_path, "w") as f:
        f.write(result["podcast_script"])
    print(f"Saved: {script_path}")

    # CALL 2: Audio Generation
    audio_path = OUTPUT_DIR / f"{video_name}_podcast.wav"
    generate_audio(result["podcast_script"], api_key, audio_path, premium=premium_tts)

    total_time = time.time() - total_start

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)
    print(f"Total time: {total_time:.1f}s")
    print(f"API calls: 2")
    print(f"\nOutputs:")
    print(f"  - {json_path.name}")
    print(f"  - {script_path.name}")
    print(f"  - {audio_path.name}")

    # Print summary
    meta = result.get("metadata", {})
    print(f"\n--- Lecture Info ---")
    print(f"Speaker: {meta.get('speaker', 'Unknown')}")
    print(f"Title: {meta.get('title', 'Unknown')}")
    print(f"Field: {meta.get('field', 'Unknown')}")

    return {
        "analysis": result,
        "json_path": str(json_path),
        "script_path": str(script_path),
        "audio_path": str(audio_path),
        "total_time": total_time
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python gemini_podcast.py <video_path> [--premium]")
        print("Example: python gemini_podcast.py lecture.mp4")
        print("         python gemini_podcast.py lecture.mp4 --premium  # Higher quality TTS")
        sys.exit(1)

    video_path = sys.argv[1]
    premium = "--premium" in sys.argv

    result = run_pipeline(video_path, premium_tts=premium)

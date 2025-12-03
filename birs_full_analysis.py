#!/usr/bin/env python3
"""Full BIRS video analysis with statistics"""
import ollama
import base64
import time
import subprocess
import os
import json
import sys

VIDEO = sys.argv[1] if len(sys.argv) > 1 else "/tmp/test_video.mp4"
FRAMES_DIR = "/tmp/full_analysis_frames"
VISION_MODEL = "ministral-3:8b"
SUMMARY_MODEL = "gpt-oss:120b"

print("=" * 60)
print("BIRS VIDEO FULL ANALYSIS")
print("Model:", VISION_MODEL)
print("=" * 60)

# Get video duration
result = subprocess.run(
    ["ffprobe", "-v", "error", "-show_entries", "format=duration",
     "-of", "default=noprint_wrappers=1:nokey=1", VIDEO],
    capture_output=True, text=True
)
duration = float(result.stdout.strip())
print("\nVideo duration: {:.1f} minutes".format(duration/60))

# Extract audio and transcribe with Whisper
print("\n" + "=" * 60)
print("AUDIO TRANSCRIPTION")
print("=" * 60)

AUDIO_PATH = "/tmp/birs_audio.mp3"
WHISPER_MODEL = "large"

print("Extracting audio...")
subprocess.run(
    "ffmpeg -i {} -vn -acodec libmp3lame -q:a 2 {} -y 2>/dev/null".format(VIDEO, AUDIO_PATH),
    shell=True
)

# Find whisper binary
whisper_paths = ["/home/vincent/.local/bin/whisper", "whisper", "/usr/local/bin/whisper"]
whisper_cmd = None
for path in whisper_paths:
    result_check = subprocess.run(["which", path], capture_output=True)
    if result_check.returncode == 0 or os.path.exists(path):
        whisper_cmd = path
        break

transcript = ""
whisper_time = 0
if whisper_cmd:
    # Unload Ollama models to free GPU for Whisper
    print("Unloading Ollama models to free GPU...")
    subprocess.run("ollama stop {} 2>/dev/null".format(VISION_MODEL), shell=True)
    subprocess.run("ollama stop {} 2>/dev/null".format(SUMMARY_MODEL), shell=True)
    time.sleep(2)  # Give GPU time to release memory

    print("Transcribing with Whisper {} (GPU)...".format(WHISPER_MODEL))
    whisper_start = time.time()
    whisper_result = subprocess.run(
        [whisper_cmd, AUDIO_PATH, "--model", WHISPER_MODEL, "--output_format", "json", "--output_dir", "/tmp"],
        capture_output=True, text=True
    )
    whisper_time = time.time() - whisper_start

    # Check for errors
    if whisper_result.returncode != 0:
        print("Whisper error: {}".format(whisper_result.stderr[:500]))

    # Read transcript
    json_path = "/tmp/birs_audio.json"
    if os.path.exists(json_path):
        with open(json_path) as f:
            whisper_data = json.load(f)
        transcript = whisper_data.get("text", "")
    else:
        txt_path = "/tmp/birs_audio.txt"
        if os.path.exists(txt_path):
            with open(txt_path) as f:
                transcript = f.read()

    print("Transcript: {} chars ({:.1f}s)".format(len(transcript), whisper_time))
    if transcript:
        print("Preview: {}...".format(transcript[:200]))
else:
    print("WARNING: Whisper not found, skipping transcription")

# Scene detection: find changes, then capture 4 seconds later (after slide settles)
os.makedirs(FRAMES_DIR, exist_ok=True)
SCENE_THRESHOLD = 0.1  # Lower threshold to catch slide changes
DELAY_AFTER_SCENE = 4  # Seconds to wait after scene change
MIN_INTERVAL = 10      # Minimum gap between captures

print("Detecting scene changes (threshold={})...".format(SCENE_THRESHOLD))

# Step 1: Detect scene change timestamps using shell pipe
detect_cmd = "ffmpeg -i {} -vf \"select='gt(scene,{})',showinfo\" -vsync vfr -f null - 2>&1".format(
    VIDEO, SCENE_THRESHOLD)
detect_result = subprocess.run(detect_cmd, shell=True, capture_output=True, text=True)

# Combine stdout and stderr (ffmpeg outputs to stderr)
all_output = detect_result.stdout + detect_result.stderr

# Parse scene change times
scene_times = [0.0]  # Always include start
for line in all_output.split('\n'):
    if 'pts_time:' in line:
        try:
            pts = float(line.split('pts_time:')[1].split()[0])
            scene_times.append(pts)
        except:
            pass

# Remove duplicates and sort
scene_times = sorted(set(scene_times))
print("Found {} scene changes".format(len(scene_times)))

# Step 2: Calculate capture times (4 seconds after each scene change, with min interval)
capture_times = []
last_capture = -MIN_INTERVAL
for t in scene_times:
    capture_t = t + DELAY_AFTER_SCENE
    if capture_t - last_capture >= MIN_INTERVAL and capture_t < duration:
        capture_times.append(capture_t)
        last_capture = capture_t

print("Capturing {} frames ({}s after each scene change)...".format(len(capture_times), DELAY_AFTER_SCENE))

# Step 3: Extract frames at calculated times
frame_timestamps = {}
for i, t in enumerate(capture_times):
    frame_path = os.path.join(FRAMES_DIR, "frame_{:04d}.jpg".format(i))
    subprocess.run(
        "ffmpeg -ss {:.2f} -i {} -frames:v 1 {} -y 2>/dev/null".format(t, VIDEO, frame_path),
        shell=True
    )
    frame_timestamps[i] = t

# Fallback: if got < 5 frames, use interval-based
frames_check = [f for f in os.listdir(FRAMES_DIR) if f.endswith(".jpg")]
if len(frames_check) < 5:
    print("Few scene changes found, using interval fallback (every 30s)...")
    frame_timestamps = {}
    subprocess.run(
        "ffmpeg -i {} -vf 'fps=1/30' {}/frame_%04d.jpg -y 2>/dev/null".format(VIDEO, FRAMES_DIR),
        shell=True
    )
    for i in range(100):
        frame_timestamps[i] = i * 30

frames = sorted([f for f in os.listdir(FRAMES_DIR) if f.endswith(".jpg")])
print("Extracted {} frames".format(len(frames)))

# Analyze each frame
print("\n" + "=" * 60)
print("FRAME-BY-FRAME ANALYSIS")
print("=" * 60)

frame_results = []
total_vision_time = 0
total_chars = 0

for i, frame_file in enumerate(frames):
    frame_path = os.path.join(FRAMES_DIR, frame_file)
    timestamp_sec = frame_timestamps.get(i, i * 30)  # Fallback to estimate
    timestamp = "{:02d}:{:02d}".format(int(timestamp_sec)//60, int(timestamp_sec)%60)

    with open(frame_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    print("\n[{}] Frame {}/{}...".format(timestamp, i+1, len(frames)), end=" ", flush=True)
    start = time.time()

    try:
        response = ollama.chat(
            model=VISION_MODEL,
            messages=[{
                "role": "user",
                "content": "Analyze this lecture frame. Extract: 1) Slide title 2) Key bullet points or equations 3) Any diagrams. Be concise but complete.",
                "images": [image_data]
            }]
        )
        elapsed = time.time() - start
        content = response["message"]["content"]

        total_vision_time += elapsed
        total_chars += len(content)

        frame_results.append({
            "frame": i+1,
            "timestamp": timestamp,
            "time": round(elapsed, 1),
            "chars": len(content),
            "content": content
        })

        print("{:.1f}s | {} chars".format(elapsed, len(content)))
        first_line = content.split("\n")[0][:80]
        print("    {}...".format(first_line))

    except Exception as e:
        print("Error: {}".format(e))
        frame_results.append({"frame": i+1, "timestamp": timestamp, "error": str(e)})

# Statistics
print("\n" + "=" * 60)
print("STATISTICS")
print("=" * 60)

successful = [f for f in frame_results if "content" in f]
print("\nFrames analyzed: {}/{}".format(len(successful), len(frames)))
print("Total vision time: {:.1f}s".format(total_vision_time))
print("Avg time per frame: {:.1f}s".format(total_vision_time/len(successful)))
print("Total response chars: {}".format(total_chars))
print("Avg chars per frame: {:.0f}".format(total_chars/len(successful)))

# Extract unique slide titles
print("\n" + "=" * 60)
print("DETECTED SLIDE TITLES")
print("=" * 60)

for f in successful:
    content = f["content"]
    lines = content.split("\n")
    for line in lines[:5]:
        if "title" in line.lower() or "**" in line:
            print("[{}] {}".format(f["timestamp"], line[:70]))
            break

# Generate summary
print("\n" + "=" * 60)
print("GENERATING SUMMARY with", SUMMARY_MODEL)
print("=" * 60)

all_content = "\n\n".join([
    "[{}]\n{}".format(f["timestamp"], f["content"])
    for f in successful
])

summary_prompt = """Analyze this BIRS mathematics lecture using both AUDIO TRANSCRIPT and VISUAL FRAME analysis.

=== AUDIO TRANSCRIPT ===
{}

=== VISUAL FRAME ANALYSIS ===
{}

Create:
1. **METADATA** (JSON): title, speaker, topic, key_concepts (list of 5-10)
2. **EXECUTIVE SUMMARY** (2-3 paragraphs combining what was SAID and what was SHOWN)
3. **LECTURE OUTLINE** with timestamps
4. **KEY VISUAL CONTENT**: Important equations, diagrams, slides
5. **KEY SPOKEN CONTENT**: Important quotes, explanations, definitions
6. **QUALITY ASSESSMENT**: Rate the combined audio+visual coverage (1-10)
""".format(transcript[:8000], all_content[:8000])

start = time.time()
response = ollama.chat(
    model=SUMMARY_MODEL,
    messages=[{"role": "user", "content": summary_prompt}]
)
summary_time = time.time() - start
summary = response["message"]["content"]

print("\nSummary generated in {:.1f}s".format(summary_time))
print("\n" + summary)

# Final stats
total_time = whisper_time + total_vision_time + summary_time
print("\n" + "=" * 60)
print("FINAL STATISTICS")
print("=" * 60)
print("Video duration: {:.1f} min".format(duration/60))
print("Transcript: {} chars".format(len(transcript)))
print("Frames analyzed: {}".format(len(successful)))
print("Whisper time: {:.1f}s".format(whisper_time))
print("Vision model: {}".format(VISION_MODEL))
print("Vision time: {:.1f}s ({:.1f}s/frame)".format(total_vision_time, total_vision_time/len(successful)))
print("Summary model: {}".format(SUMMARY_MODEL))
print("Summary time: {:.1f}s".format(summary_time))
print("Total processing: {:.1f}s".format(total_time))
print("Processing ratio: {:.2f}x realtime".format(total_time/duration))

# Save results
output = {
    "video": VIDEO,
    "duration_sec": duration,
    "vision_model": VISION_MODEL,
    "summary_model": SUMMARY_MODEL,
    "whisper_model": WHISPER_MODEL,
    "frames_analyzed": len(successful),
    "transcript_chars": len(transcript),
    "whisper_time": whisper_time,
    "total_vision_time": total_vision_time,
    "summary_time": summary_time,
    "transcript": transcript,
    "frame_results": frame_results,
    "summary": summary
}

with open("/tmp/full_analysis.json", "w") as f:
    json.dump(output, f, indent=2)
print("\nFull results saved to /tmp/full_analysis.json")

#!/usr/bin/env python3
"""
BIRS NotebookLM - Gradio Web Interface

Interactive demo for processing BIRS lecture videos.

Usage:
    python app.py
    python app.py --share  # Public URL for demo
"""

import gradio as gr
import json
import time
from pathlib import Path

# Import pipeline components
from birs_analyzer_v2 import analyze_video, extract_json
from podcast_script import generate_script, validate_script

OUTPUT_DIR = Path.home() / "vlm" / "output"


def format_analysis_summary(analysis: dict) -> str:
    """Format analysis as readable markdown."""

    # Handle nested structure
    if "analysis" in analysis:
        data = analysis["analysis"]
    else:
        data = analysis

    meta = data.get("metadata", {})

    summary = f"""
## Lecture Information

| Field | Value |
|-------|-------|
| **Speaker** | {meta.get('speaker', 'Unknown')} |
| **Title** | {meta.get('title', 'Unknown')} |
| **Institution** | {meta.get('institution', 'Unknown')} |
| **Workshop** | {meta.get('workshop', 'Unknown')} |
| **Field** | {meta.get('field', 'Unknown')} |
| **Format** | {meta.get('format', 'Unknown')} |

## Summary

{data.get('summary', 'No summary available')}

## Key Concepts

"""

    concepts = data.get("key_concepts", [])
    for c in concepts[:8]:
        summary += f"- {c}\n"

    # Equations
    equations = data.get("equations", [])
    if equations:
        summary += "\n## Equations Extracted\n\n"
        for eq in equations[:10]:
            summary += f"- `{eq}`\n"

    # Theorems
    theorems = data.get("theorems", [])
    if theorems:
        summary += "\n## Theorems\n\n"
        for t in theorems[:5]:
            name = t.get("name", "Theorem")
            stmt = t.get("statement", "")
            summary += f"**{name}**: {stmt}\n\n"

    return summary


def process_video(video_input: str, style: str, progress=gr.Progress()):
    """Process a video through the pipeline."""

    if not video_input:
        return None, "Please enter a video URL or path", ""

    try:
        # Stage 1: Analyze
        progress(0.1, desc="Uploading video to Gemini...")
        start = time.time()

        analysis = analyze_video(video_input)
        analysis_time = time.time() - start

        progress(0.5, desc="Generating podcast script...")

        # Stage 2: Generate script
        script = generate_script(analysis, style)
        validation = validate_script(script)

        total_time = time.time() - start

        # Format summary
        summary = format_analysis_summary(analysis)
        summary += f"\n\n---\n*Processed in {total_time:.1f}s*"

        # Validation info
        script_info = f"""
### Script Stats
- **Words**: {validation['stats']['word_count']}
- **S1 turns**: {validation['stats']['s1_turns']}
- **S2 turns**: {validation['stats']['s2_turns']}
- **Non-verbals**: {', '.join(validation['stats']['non_verbals']) if validation['stats']['non_verbals'] else 'None'}
"""

        return analysis, summary, script + "\n\n" + script_info

    except Exception as e:
        return None, f"Error: {str(e)}", ""


def load_example():
    """Load example analysis for demo."""
    example_path = OUTPUT_DIR / "sample_analysis.json"
    if example_path.exists():
        with open(example_path) as f:
            return json.load(f)
    return None


# Build interface
with gr.Blocks(
    title="BIRS NotebookLM",
    theme=gr.themes.Soft()
) as demo:

    gr.Markdown("""
    # BIRS NotebookLM

    Transform mathematics lecture videos into searchable content + AI podcast overviews.

    **Features:**
    - Extract transcripts and LaTeX equations from chalk talks
    - Generate two-speaker podcast discussions
    - Powered by Gemini 3 Pro + Dia TTS

    ---
    """)

    with gr.Row():
        with gr.Column(scale=2):
            video_input = gr.Textbox(
                label="Video URL or Path",
                placeholder="https://videos.birs.ca/2025/25w5374/202512030901-Neshveyev.mp4",
                info="Enter a BIRS video URL or local file path"
            )

            style = gr.Radio(
                choices=["educational", "casual", "deep_dive"],
                value="educational",
                label="Podcast Style",
                info="Educational: Clear explanations | Casual: Fun and accessible | Deep Dive: Technical details"
            )

            process_btn = gr.Button("Process Video", variant="primary", size="lg")

        with gr.Column(scale=1):
            gr.Markdown("""
            ### Quick Start

            1. Paste a BIRS video URL
            2. Choose podcast style
            3. Click "Process Video"

            **Sample URLs:**
            - `https://videos.birs.ca/2025/25w5374/202512030901-Neshveyev.mp4`
            - `https://videos.birs.ca/2025/25w5490/202511131030-Pham.mp4`
            """)

    with gr.Tabs():
        with gr.TabItem("Summary"):
            summary_output = gr.Markdown(label="Lecture Summary")

        with gr.TabItem("Podcast Script"):
            script_output = gr.Markdown(label="Generated Script")

        with gr.TabItem("Raw JSON"):
            json_output = gr.JSON(label="Full Analysis")

    # Wire up the interface
    process_btn.click(
        fn=process_video,
        inputs=[video_input, style],
        outputs=[json_output, summary_output, script_output]
    )

    gr.Markdown("""
    ---

    ### About

    Built for the Google DeepMind Hackathon (Dec 5-6, 2025).

    **Goal:** Process BIRS's 17,000 lecture archive to make research mathematics accessible to everyone.

    **Tech Stack:**
    - Video Analysis: Gemini 3 Pro
    - Audio Synthesis: Dia TTS (1.6B parameters)
    - Backend: Python + Gradio

    [View on GitHub](https://github.com/bigsnarfdude/birs-notebooklm)
    """)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--share", action="store_true", help="Create public URL")
    parser.add_argument("--port", type=int, default=7860, help="Port number")
    args = parser.parse_args()

    demo.launch(
        share=args.share,
        server_port=args.port,
        show_error=True
    )

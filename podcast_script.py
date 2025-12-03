#!/usr/bin/env python3
"""
BIRS Podcast Script Generator (C3)

Converts video analysis JSON into two-speaker podcast dialogue.
Output is formatted for Dia TTS with [S1]/[S2] speaker tags.

Usage:
    python podcast_script.py analysis.json
    python podcast_script.py analysis.json --style casual
"""

import google.generativeai as genai
import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# Output directory
OUTPUT_DIR = Path.home() / "vlm" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def get_api_key():
    """Load API key from file or environment."""
    key_file = Path.home() / ".gemini_api_key"
    if key_file.exists():
        return key_file.read_text().strip()
    return os.environ.get("GEMINI_API_KEY")


# Prompt templates for different styles
PROMPTS = {
    "educational": '''You are creating a podcast script about a mathematics lecture.

SPEAKERS:
- [S1] Alex: Curious graduate student, asks insightful questions
- [S2] Sam: Expert mathematician, explains concepts clearly and enthusiastically

LECTURE CONTENT:
Speaker: {speaker}
Title: {title}
Field: {field}
Summary: {summary}

Key Concepts: {concepts}

Main Equations:
{equations}

Theorems/Definitions:
{theorems}

GUIDELINES:
- Create a 2-3 minute dialogue (300-400 words)
- Start with an engaging hook about the topic
- Alex asks questions a smart student would ask
- Sam explains using analogies and clear examples
- Reference specific equations/theorems from the lecture
- Include 2-3 natural non-verbals: (laughs), (hmm), (sighs)
- End with a key takeaway or "aha moment"
- Make complex math accessible without dumbing it down

OUTPUT FORMAT:
Return ONLY the dialogue script, starting with [S1] or [S2].
Each speaker turn on a new line.
Example:
[S1] So today we're diving into quantum walks on graphs...
[S2] That's right! And what makes this fascinating is...

Generate the podcast script now:''',

    "casual": '''Create a casual, fun podcast about this math lecture.

SPEAKERS:
- [S1] Alex: Enthusiastic learner, loves "mind-blown" moments
- [S2] Sam: Math expert who makes things fun and relatable

LECTURE:
{speaker} talked about "{title}" in {field}.
Summary: {summary}
Cool equations: {equations}

STYLE:
- Very conversational, like friends chatting
- Use humor and analogies
- More (laughs) and expressions of wonder
- 250-350 words

OUTPUT: Just the dialogue with [S1]/[S2] tags.''',

    "deep_dive": '''Create a technical deep-dive podcast for advanced students.

SPEAKERS:
- [S1] Alex: PhD student, asks technical follow-ups
- [S2] Sam: Research mathematician, provides rigorous detail

LECTURE CONTENT:
Speaker: {speaker}
Title: {title}
Field: {field}

Technical Summary:
{summary}

Equations (discuss these in detail):
{equations}

Theorems and Definitions:
{theorems}

GUIDELINES:
- 400-500 words of substantive mathematical discussion
- Don't shy away from technical details
- Discuss proof strategies and key lemmas
- Reference connections to other areas
- Include precise mathematical language
- Minimal non-verbals, focus on content

OUTPUT: Dialogue script with [S1]/[S2] tags only.'''
}


def extract_lecture_content(analysis: dict) -> dict:
    """Extract relevant content from analysis JSON."""
    # Handle nested structure from birs_analyzer_v2.py
    if "analysis" in analysis:
        data = analysis["analysis"]
    else:
        data = analysis

    metadata = data.get("metadata", {})

    # Get equations (limit for prompt size)
    equations = data.get("equations", [])[:10]
    equations_str = "\n".join(f"- {eq}" for eq in equations) if equations else "None extracted"

    # Get theorems and definitions
    theorems = data.get("theorems", [])
    definitions = data.get("definitions", [])
    theorems_str = ""
    for t in theorems[:5]:
        theorems_str += f"- {t.get('name', 'Theorem')}: {t.get('statement', '')}\n"
    for d in definitions[:5]:
        theorems_str += f"- {d.get('term', 'Definition')}: {d.get('definition', '')}\n"
    if not theorems_str:
        theorems_str = "None explicitly stated"

    # Get concepts
    concepts = data.get("key_concepts", [])
    concepts_str = ", ".join(concepts[:8]) if concepts else "Not extracted"

    return {
        "speaker": metadata.get("speaker", "Unknown Speaker"),
        "title": metadata.get("title", "Mathematics Lecture"),
        "field": metadata.get("field", "Mathematics"),
        "summary": data.get("summary", "No summary available"),
        "equations": equations_str,
        "theorems": theorems_str,
        "concepts": concepts_str
    }


def generate_script(analysis: dict, style: str = "educational", model_name: str = "gemini-2.0-flash") -> str:
    """Generate podcast script from analysis."""

    # Configure API
    api_key = get_api_key()
    if not api_key:
        raise ValueError("No API key found. Store in ~/.gemini_api_key")

    genai.configure(api_key=api_key)

    # Extract content
    content = extract_lecture_content(analysis)

    # Get prompt template
    if style not in PROMPTS:
        print(f"Unknown style '{style}', using 'educational'")
        style = "educational"

    prompt = PROMPTS[style].format(**content)

    print(f"Generating {style} podcast script...")
    print(f"  Lecture: {content['title']}")
    print(f"  Speaker: {content['speaker']}")

    # Generate
    model = genai.GenerativeModel(model_name)
    response = model.generate_content(prompt)

    script = response.text.strip()

    # Clean up - ensure it starts with speaker tag
    if not script.startswith("[S"):
        lines = script.split("\n")
        for i, line in enumerate(lines):
            if line.strip().startswith("[S"):
                script = "\n".join(lines[i:])
                break

    return script


def validate_script(script: str) -> dict:
    """Validate script format for Dia TTS."""
    issues = []

    # Check for speaker tags
    s1_count = script.count("[S1]")
    s2_count = script.count("[S2]")

    if s1_count == 0:
        issues.append("No [S1] speaker tags found")
    if s2_count == 0:
        issues.append("No [S2] speaker tags found")

    # Check length
    word_count = len(script.split())
    if word_count < 100:
        issues.append(f"Script too short ({word_count} words, recommend 300+)")
    if word_count > 800:
        issues.append(f"Script may be too long for single Dia generation ({word_count} words)")

    # Check for non-verbals
    non_verbals = ["(laughs)", "(sighs)", "(hmm)", "(pauses)", "(chuckles)"]
    found_non_verbals = [nv for nv in non_verbals if nv in script.lower()]

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "stats": {
            "word_count": word_count,
            "s1_turns": s1_count,
            "s2_turns": s2_count,
            "non_verbals": found_non_verbals
        }
    }


def main():
    parser = argparse.ArgumentParser(description="Generate podcast script from video analysis")
    parser.add_argument("analysis", help="Path to analysis JSON file")
    parser.add_argument("--style", choices=["educational", "casual", "deep_dive"],
                       default="educational", help="Script style")
    parser.add_argument("--model", default="gemini-2.0-flash", help="Gemini model")
    parser.add_argument("--output", "-o", help="Output script path")

    args = parser.parse_args()

    # Load analysis
    analysis_path = Path(args.analysis)
    if not analysis_path.exists():
        print(f"Error: Analysis file not found: {analysis_path}")
        sys.exit(1)

    with open(analysis_path) as f:
        analysis = json.load(f)

    print("=" * 60)
    print("BIRS PODCAST SCRIPT GENERATOR")
    print("=" * 60)

    # Generate script
    script = generate_script(analysis, args.style, args.model)

    # Validate
    validation = validate_script(script)

    print("\n" + "=" * 60)
    print("VALIDATION")
    print("=" * 60)
    print(f"Word count: {validation['stats']['word_count']}")
    print(f"S1 turns: {validation['stats']['s1_turns']}")
    print(f"S2 turns: {validation['stats']['s2_turns']}")
    print(f"Non-verbals: {validation['stats']['non_verbals']}")

    if validation["issues"]:
        print("\nWarnings:")
        for issue in validation["issues"]:
            print(f"  - {issue}")
    else:
        print("\n✓ Script format valid for Dia TTS")

    # Save script
    if args.output:
        output_path = Path(args.output)
    else:
        # Derive from analysis filename
        stem = analysis_path.stem.replace(".json", "")
        output_path = OUTPUT_DIR / f"{stem}_podcast.txt"

    with open(output_path, "w") as f:
        f.write(script)

    print(f"\n" + "=" * 60)
    print("OUTPUT")
    print("=" * 60)
    print(f"Script saved: {output_path}")

    # Also print the script
    print("\n--- SCRIPT ---")
    print(script)
    print("--- END ---")

    return script


if __name__ == "__main__":
    main()

import google.generativeai as genai
import os
import time
import json
import re
from datetime import datetime

# --- Configuration ---
API_KEY_CONFIGURED = False
try:
    # Replace with your actual API key
    api_key = "YOUR_API_KEY"
    genai.configure(api_key=api_key)
    
    # Simple validation - check if key looks valid (not placeholder)
    if api_key and api_key != "YOUR_API_KEY" and len(api_key) > 10:
        API_KEY_CONFIGURED = True
    else:
        print("Warning: API key appears to be placeholder or invalid.")
except Exception as e:
    print(f"Error during API key configuration: {e}")
    print("Please ensure you have a valid API key set.")
    exit()

MODEL_NAME = 'gemini-2.5-flash-preview-05-20'  # Using the specified preview model

# --- Rate Limiting & Retry Configuration ---
RPM_LIMIT = 10  # Requests Per Minute
SECONDS_PER_REQUEST_MIN_DELAY = 60 / RPM_LIMIT

RPD_LIMIT = 500 # Requests Per Day
RPD_STATE_FILE = "rpd_state.json" # File to store daily request count

MAX_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 5 # Initial delay for retries, increases exponentially

# --- Folders ---
TRANSCRIPTS_FOLDER = "transcripts"
SUMMARIES_FOLDER = "summaries"

# --- RPD Counter Management ---
def load_rpd_state():
    today_str = datetime.now().strftime("%Y-%m-%d")
    try:
        if os.path.exists(RPD_STATE_FILE):
            with open(RPD_STATE_FILE, 'r') as f:
                state = json.load(f)
            if state.get("date") == today_str:
                return state.get("count", 0)
    except Exception as e:
        print(f"Warning: Could not load RPD state from {RPD_STATE_FILE}: {e}")
    return 0

def save_rpd_state(count):
    today_str = datetime.now().strftime("%Y-%m-%d")
    state = {"date": today_str, "count": count}
    try:
        with open(RPD_STATE_FILE, 'w') as f:
            json.dump(state, f)
    except Exception as e:
        print(f"Warning: Could not save RPD state to {RPD_STATE_FILE}: {e}")

# Initialize RPD count for this session
requests_made_today = load_rpd_state()

def create_math_summary_prompt(transcript_text: str) -> str:
    """Create enhanced prompt for mathematical content"""
    return f"""Analyze this mathematics PhD lecture transcript and create a comprehensive summary for academic discovery.

**CRITICAL REQUIREMENTS:**
- Extract ALL mathematical concepts, theorems, and formulas mentioned
- Preserve exact mathematical terminology and notation
- Identify the specific mathematical areas and subfields
- Note connections between different mathematical concepts
- Capture the logical progression of ideas

**FORMAT YOUR RESPONSE AS:**

## **Core Mathematical Content**
**Primary Field:** [e.g., Algebraic Geometry, Dynamical Systems, etc.]
**Subfields:** [specific areas covered]
**Level:** [undergraduate/graduate/research level]

## **Key Mathematical Concepts**
- **Theorems/Results:** [list with exact names when given]
- **Mathematical Objects:** [groups, spaces, operators, etc.]
- **Techniques/Methods:** [computational methods, proof techniques]
- **Formulas/Equations:** [key mathematical expressions mentioned]

## **Detailed Summary**
[2-3 paragraph flowing summary covering:]
- Main mathematical ideas and their development
- How concepts build upon each other
- Specific examples or applications discussed
- Novel insights or connections revealed

## **Prerequisites & Context**
**Background Needed:** [what students should know first]
**Related Areas:** [connections to other mathematical fields]
**Applications:** [practical or theoretical applications mentioned]

## **Notable Quotes/Key Insights**
[1-2 direct quotes that capture essential mathematical ideas]

**TRANSCRIPT TO ANALYZE:**
{transcript_text}

**MATHEMATICAL CONTENT SUMMARY:**"""

def create_title_prompt(transcript_text: str) -> str:
    """Create prompt for title extraction"""
    excerpt = transcript_text[:2000]
    return f"""Based on this mathematics lecture transcript excerpt, suggest a clear, descriptive title.

GUIDELINES:
- Include the main mathematical topic/area
- Mention key concepts or theorems if clear
- Keep it academic but accessible
- 5-15 words maximum

TRANSCRIPT EXCERPT:
{excerpt}

SUGGESTED TITLE (just the title, nothing else):"""

def extract_metadata(summary_text: str) -> dict:
    """Extract structured metadata from summary"""
    metadata = {
        'primary_field': '',
        'subfields': [],
        'level': '',
        'concepts': [],
        'theorems': [],
        'prerequisites': [],
        'applications': []
    }
    
    try:
        # Extract primary field
        field_match = re.search(r'\*\*Primary Field:\*\*\s*([^\n]+)', summary_text)
        if field_match:
            metadata['primary_field'] = field_match.group(1).strip()
        
        # Extract subfields
        subfields_match = re.search(r'\*\*Subfields:\*\*\s*([^\n]+)', summary_text)
        if subfields_match:
            metadata['subfields'] = [s.strip() for s in subfields_match.group(1).split(',')]
        
        # Extract level
        level_match = re.search(r'\*\*Level:\*\*\s*([^\n]+)', summary_text)
        if level_match:
            metadata['level'] = level_match.group(1).strip()
            
        # Extract concepts from Key Mathematical Concepts section
        concepts_section = re.search(r'## \*\*Key Mathematical Concepts\*\*(.*?)(?=##|$)', summary_text, re.DOTALL)
        if concepts_section:
            concepts_text = concepts_section.group(1)
            concept_items = re.findall(r'[-•*]\s*([^\n]+)', concepts_text)
            metadata['concepts'] = [item.strip() for item in concept_items]
    
    except Exception as e:
        print(f"Warning: Could not extract metadata: {e}")
    
    return metadata

def summarize_transcript(transcript_text, model_name=MODEL_NAME):
    """
    Enhanced summarization function for mathematical content
    """
    global API_KEY_CONFIGURED
    if not API_KEY_CONFIGURED:
        return "Error: API key not properly configured. Cannot generate summary."

    model = genai.GenerativeModel(model_name)
    
    # Use enhanced mathematical prompt
    prompt = create_math_summary_prompt(transcript_text)
    
    current_backoff = INITIAL_BACKOFF_SECONDS
    for attempt in range(MAX_RETRIES):
        try:
            response = model.generate_content(prompt)
            
            if hasattr(response, 'text') and response.text:
                summary_text = response.text.strip()
                
                # Clean up common prefixes
                prefixes_to_remove = [
                    "Here is a mathematical summary:",
                    "Here's a mathematical summary:",
                    "Mathematical Content Summary:",
                    "**MATHEMATICAL CONTENT SUMMARY:**",
                    "Here is a factual summary of the transcript:",
                    "Here is a summary of the transcript:",
                    "Summary of the transcript:",
                    "Here's a summary:",
                    "Summary:"
                ]
                for prefix in prefixes_to_remove:
                    if summary_text.startswith(prefix):
                        summary_text = summary_text[len(prefix):].strip()
                        break
                        
                return summary_text
                
            elif response.parts:
                full_text = "".join(part.text for part in response.parts if hasattr(part, 'text'))
                if full_text:
                    return full_text
                    
            return "Error: Summarization succeeded but API response was empty or in an unexpected format."

        except AttributeError:
            return "Error: Could not get response.text. The response object might not have a 'text' attribute or the API call failed."
        except Exception as e:
            error_name = type(e).__name__
            print(f"  Attempt {attempt + 1} of {MAX_RETRIES} failed: {error_name} - {e}")
            if attempt < MAX_RETRIES - 1:
                print(f"  Retrying in {current_backoff} seconds...")
                time.sleep(current_backoff)
                current_backoff *= 2
            else:
                return f"An error occurred after {MAX_RETRIES} retries: {error_name} - {e}"
                
    return f"Error: Summarization failed after {MAX_RETRIES} attempts."

def generate_title(transcript_text, model_name=MODEL_NAME):
    """Generate a meaningful title from transcript"""
    global API_KEY_CONFIGURED
    if not API_KEY_CONFIGURED:
        return "Mathematical Lecture"

    model = genai.GenerativeModel(model_name)
    prompt = create_title_prompt(transcript_text)
    
    try:
        response = model.generate_content(prompt)
        if hasattr(response, 'text') and response.text:
            title = response.text.strip()
            # Clean up title
            title = re.sub(r'^[*"\'`]+|[*"\'`]+$', '', title)
            if len(title) > 100:
                title = title[:97] + "..."
            return title
    except Exception as e:
        print(f"Warning: Could not generate title: {e}")
    
    return "Mathematical Lecture"

def process_all_transcripts(transcripts_dir, summaries_dir):
    """
    Enhanced processing function with JSON output and metadata extraction
    """
    global requests_made_today
    global API_KEY_CONFIGURED

    if not API_KEY_CONFIGURED:
        print("Halting processing as API Key is not configured.")
        return

    if not os.path.exists(summaries_dir):
        try:
            os.makedirs(summaries_dir)
            print(f"Created summaries directory: {summaries_dir}")
        except OSError as e:
            print(f"Error creating directory {summaries_dir}: {e}")
            return

    if not os.path.isdir(transcripts_dir):
        print(f"Error: Transcripts directory '{transcripts_dir}' not found.")
        return

    print(f"Looking for transcripts in: {os.path.abspath(transcripts_dir)}")
    print(f"Daily request limit (RPD): {RPD_LIMIT}. Requests made so far today: {requests_made_today}")

    files_to_process = [f for f in os.listdir(transcripts_dir) if f.endswith(".txt")]
    if not files_to_process:
        print(f"No .txt files found in '{transcripts_dir}'.")
        return

    results_summary = {
        'processed': 0,
        'failed': 0,
        'skipped': 0,
        'files': []
    }

    for filename in files_to_process:
        transcript_filepath = os.path.join(transcripts_dir, filename)
        base_name = os.path.splitext(filename)[0]
        
        # Output files - both JSON and TXT
        json_output_path = os.path.join(summaries_dir, f"{base_name}_SUMMARY.json")
        txt_output_path = os.path.join(summaries_dir, f"{base_name}_SUMMARY.txt")

        print(f"\n📝 Processing: {filename}")

        # Check if already exists
        if os.path.exists(json_output_path):
            print(f"  ✅ Summary already exists, skipping...")
            results_summary['skipped'] += 1
            continue

        if requests_made_today >= RPD_LIMIT:
            print(f"  RPD limit of {RPD_LIMIT} reached for today. Halting further processing.")
            save_rpd_state(requests_made_today)
            break

        try:
            with open(transcript_filepath, 'r', encoding='utf-8') as f:
                transcript_content = f.read()

            if not transcript_content.strip():
                print("  File is empty. Skipping.")
                results_summary['skipped'] += 1
                continue
            
            # Record start time for rate limiting
            call_start_time = time.time()

            # Generate summary
            summary = summarize_transcript(transcript_content)
            
            # Count request if successful
            if not summary.startswith("Error:"):
                requests_made_today += 1
                save_rpd_state(requests_made_today)
                print(f"  Requests today: {requests_made_today}/{RPD_LIMIT}")

            if summary.startswith("Error:"):
                print(f"  ❌ Summary generation failed")
                results_summary['failed'] += 1
                continue

            # Generate title (this will use another request)
            title = "Mathematical Lecture"
            if requests_made_today < RPD_LIMIT:
                title = generate_title(transcript_content)
                if not title.startswith("Error:"):
                    requests_made_today += 1
                    save_rpd_state(requests_made_today)

            # Extract metadata
            metadata = extract_metadata(summary)
            
            # Prepare JSON output
            json_data = {
                'original_filename': filename,
                'suggested_title': title,
                'summary': summary,
                'metadata': metadata,
                'processing_stats': {
                    'summary_word_count': len(summary.split()),
                    'summary_char_count': len(summary),
                    'transcript_length': len(transcript_content),
                    'compression_ratio': len(summary) / len(transcript_content) if transcript_content else 0,
                    'processed_at': datetime.now().isoformat()
                },
                'generated_at': datetime.now().isoformat(),
                'model_used': MODEL_NAME
            }

            # Save JSON output
            try:
                with open(json_output_path, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, indent=2, ensure_ascii=False)
                print(f"  💾 JSON saved: {os.path.basename(json_output_path)}")
            except Exception as e:
                print(f"  ❌ Error saving JSON: {e}")
                results_summary['failed'] += 1
                continue

            # Save readable text output
            try:
                text_output = f"""MATHEMATICS LECTURE SUMMARY
{'='*60}
Title: {title}
Original File: {filename}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{summary}

{'='*60}
Processing Stats:
- Summary Length: {len(summary.split())} words
- Compression Ratio: {len(summary) / len(transcript_content):.1%}
- Model Used: {MODEL_NAME}
"""
                
                with open(txt_output_path, 'w', encoding='utf-8') as f:
                    f.write(text_output)
                print(f"  💾 Text saved: {os.path.basename(txt_output_path)}")
            except Exception as e:
                print(f"  ❌ Error saving text: {e}")

            results_summary['processed'] += 1
            results_summary['files'].append({
                'filename': filename,
                'title': title,
                'primary_field': metadata.get('primary_field', 'Unknown'),
                'word_count': len(summary.split())
            })

            # Rate limiting delay
            call_duration = time.time() - call_start_time
            sleep_time = max(0, SECONDS_PER_REQUEST_MIN_DELAY - call_duration)
            if sleep_time > 0:
                print(f"  ⏱️ Waiting {sleep_time:.2f}s for rate limit...")
                time.sleep(sleep_time)
            else:
                time.sleep(0.1)

        except FileNotFoundError:
            print(f"  Error: File not found {transcript_filepath}")
            results_summary['failed'] += 1
        except Exception as e:
            print(f"  An error occurred processing {filename}: {e}")
            results_summary['failed'] += 1
            time.sleep(SECONDS_PER_REQUEST_MIN_DELAY)
    
    # Print final summary
    print(f"\n🎉 Processing Complete!")
    print(f"  ✅ Processed: {results_summary['processed']}")
    print(f"  ⚠️ Skipped: {results_summary['skipped']}")
    print(f"  ❌ Failed: {results_summary['failed']}")
    print(f"  📊 Total requests used today: {requests_made_today}/{RPD_LIMIT}")
    
    if results_summary['files']:
        print(f"\n📋 Successfully Processed Files:")
        for file_info in results_summary['files']:
            print(f"  • {file_info['filename']}")
            print(f"    Title: {file_info['title']}")
            print(f"    Field: {file_info['primary_field']}")
            print(f"    Summary: {file_info['word_count']} words")


if __name__ == "__main__":
    if not API_KEY_CONFIGURED:
        print("-" * 50)
        print("!!! IMPORTANT WARNING !!!")
        print("API key is not configured or is still set to the placeholder.")
        print("Please replace the API key in the script with your actual Gemini API key.")
        print("Processing will not start due to missing API key configuration.")
        print("-" * 50)
    else:
        # Ensure 'transcripts' folder exists
        if not os.path.exists(TRANSCRIPTS_FOLDER):
            os.makedirs(TRANSCRIPTS_FOLDER)
            print(f"'{TRANSCRIPTS_FOLDER}' directory created. Please add your transcript files there.")

        process_all_transcripts(TRANSCRIPTS_FOLDER, SUMMARIES_FOLDER)
        print("\nProcessing complete.")
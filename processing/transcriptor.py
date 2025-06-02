import google.generativeai as genai
import os
import time
import json
import re
from datetime import datetime, timedelta

# --- Configuration ---
API_KEY_CONFIGURED = False
try:
    # Replace with your actual API key
    api_key = "AIzaSyBP90XfkTG__X0QV9fUbfAqWXr6k5dQp9s"
    genai.configure(api_key=api_key)
    
    # Simple validation - check if key looks valid (not placeholder)
    if api_key and api_key != "YOUR_API_KEY_HERE" and len(api_key) > 10:
        API_KEY_CONFIGURED = True
    else:
        print("Warning: API key appears to be placeholder or invalid.")
except Exception as e:
    print(f"Error during API key configuration: {e}")
    print("Please ensure you have a valid API key set.")
    exit()

# --- Model Configuration ---
MODELS_TO_TRY = [
    'gemini-2.5-flash-preview-05-20'  # Original model
]

# --- Enhanced Rate Limiting & Retry Configuration ---
RPM_LIMIT = 6  # Requests Per Minute (more conservative)
SECONDS_PER_REQUEST_MIN_DELAY = 10  # 10 seconds between requests

# Quota management
RPD_LIMIT = 500  # Use full quota until we hit the actual limit
RPD_STATE_FILE = "rpd_state.json"

MAX_RETRIES = 5  # Increased retries
INITIAL_BACKOFF_SECONDS = 10  # Longer initial delay
MAX_BACKOFF_SECONDS = 300  # Max 5 minutes

# --- Folders ---
TRANSCRIPTS_FOLDER = "transcripts"
SUMMARIES_FOLDER = "summaries"
ERROR_LOG_FILE = "processing_errors.json"
SUCCESS_LOG_FILE = "processing_success.json"

# --- Enhanced Quota Management ---
def load_rpd_state():
    """Load daily request count with better error handling"""
    today_str = datetime.now().strftime("%Y-%m-%d")
    try:
        if os.path.exists(RPD_STATE_FILE):
            with open(RPD_STATE_FILE, 'r') as f:
                state = json.load(f)
            if state.get("date") == today_str:
                return state.get("count", 0), state.get("last_reset", today_str)
            else:
                # New day, reset counter
                print(f"New day detected. Resetting request count.")
                return 0, today_str
    except Exception as e:
        print(f"Warning: Could not load RPD state from {RPD_STATE_FILE}: {e}")
    return 0, today_str

def save_rpd_state(count, last_reset=None):
    """Save daily request count"""
    today_str = datetime.now().strftime("%Y-%m-%d")
    if not last_reset:
        last_reset = today_str
    
    state = {
        "date": today_str, 
        "count": count,
        "last_reset": last_reset,
        "updated_at": datetime.now().isoformat()
    }
    try:
        with open(RPD_STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save RPD state to {RPD_STATE_FILE}: {e}")

def log_success(filename, summary_length, model_used, requests_used):
    """Log successful processing"""
    success_entry = {
        "filename": filename,
        "summary_length": summary_length,
        "model_used": model_used,
        "requests_used": requests_used,
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        if os.path.exists(SUCCESS_LOG_FILE):
            with open(SUCCESS_LOG_FILE, 'r') as f:
                successes = json.load(f)
        else:
            successes = []
        
        successes.append(success_entry)
        
        with open(SUCCESS_LOG_FILE, 'w') as f:
            json.dump(successes, f, indent=2)
    except Exception as e:
        print(f"    Could not log success: {e}")

def log_error(filename, error, model_used=None):
    """Log errors for later analysis"""
    error_entry = {
        "filename": filename,
        "error": str(error),
        "error_type": type(error).__name__,
        "model_used": model_used,
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        if os.path.exists(ERROR_LOG_FILE):
            with open(ERROR_LOG_FILE, 'r') as f:
                errors = json.load(f)
        else:
            errors = []
        
        errors.append(error_entry)
        
        with open(ERROR_LOG_FILE, 'w') as f:
            json.dump(errors, f, indent=2)
    except Exception as e:
        print(f"Could not log error: {e}")

def get_processing_status():
    """Get overview of what's been processed"""
    status = {
        'successful_files': [],
        'failed_files': [],
        'total_requests_used': 0,
        'last_processed': None
    }
    
    # Load success log
    try:
        if os.path.exists(SUCCESS_LOG_FILE):
            with open(SUCCESS_LOG_FILE, 'r') as f:
                successes = json.load(f)
            status['successful_files'] = [s['filename'] for s in successes]
            if successes:
                status['last_processed'] = successes[-1]['timestamp']
                status['total_requests_used'] = successes[-1]['requests_used']
    except Exception as e:
        print(f"Could not load success log: {e}")
    
    # Load error log
    try:
        if os.path.exists(ERROR_LOG_FILE):
            with open(ERROR_LOG_FILE, 'r') as f:
                errors = json.load(f)
            status['failed_files'] = [e['filename'] for e in errors]
    except Exception as e:
        print(f"Could not load error log: {e}")
    
    return status

def check_quota_exceeded_error(error_message):
    """Check if the error is specifically about quota being exceeded"""
    quota_indicators = [
        "ResourceExhausted",
        "429",
        "quota",
        "exceeded",
        "current quota",
        "rate limit",
        "GenerateRequestsPerDayPerProjectPerModel"
    ]
    error_str = str(error_message).lower()
    return any(indicator.lower() in error_str for indicator in quota_indicators)

def get_quota_reset_time(error_message):
    """Extract quota reset time from error message if available"""
    # For daily quotas, they typically reset at midnight UTC
    tomorrow = datetime.now() + timedelta(days=1)
    reset_time = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
    return reset_time

# Initialize RPD count for this session
requests_made_today, last_reset_date = load_rpd_state()

def create_math_summary_prompt(transcript_text: str) -> str:
    """Create concise but effective prompt for mathematical content"""
    # More aggressive truncation for very long transcripts
    if len(transcript_text) > 12000:
        transcript_text = transcript_text[:12000] + "\n\n[Transcript truncated for processing]"
    
    return f"""Analyze this mathematics lecture and create a structured summary.

**Format:**
## Core Content
**Field:** [main mathematical area]
**Level:** [undergraduate/graduate/research]

## Key Topics
- [3-5 main concepts, theorems, or techniques covered]

## Summary
[2-3 focused paragraphs covering the mathematical content and its development]

## Context  
**Prerequisites:** [background knowledge needed]
**Applications:** [if mentioned in lecture]

**TRANSCRIPT:**
{transcript_text}"""

def generate_title(transcript_text, model_name='gemini-2.5-flash-preview-05-20'):
    """Generate title - DISABLED, always returns default"""
    return "Mathematical Lecture"

def try_with_different_models(func, *args, **kwargs):
    """Try the function with the configured model"""
    global requests_made_today
    
    # Skip if this is title generation (disabled)
    if func.__name__ == 'generate_title':
        return "Mathematical Lecture", "none"
    
    model_name = MODELS_TO_TRY[0]  # Only one model configured
    print(f"  Trying model: {model_name}")
    
    try:
        result = func(*args, model_name=model_name, **kwargs)
        if not result.startswith("Error:"):
            requests_made_today += 1
            save_rpd_state(requests_made_today, last_reset_date)
            return result, model_name
        else:
            print(f"  Model error: {result} - EXITING")
            exit(1)
            
    except Exception as e:
        print(f"  Model exception: {e} - EXITING")
        exit(1)

def summarize_transcript(transcript_text, model_name='gemini-2.5-flash-preview-05-20'):
    """Enhanced summarization with comprehensive error handling and better token management"""
    global API_KEY_CONFIGURED
    if not API_KEY_CONFIGURED:
        return "Error: API key not properly configured."

    try:
        model = genai.GenerativeModel(model_name)
        prompt = create_math_summary_prompt(transcript_text)
        
        current_backoff = INITIAL_BACKOFF_SECONDS
        for attempt in range(MAX_RETRIES):
            try:
                print(f"    Attempt {attempt + 1}/{MAX_RETRIES} with {model_name}")
                
                response = model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.3,
                        max_output_tokens=4096,  # INCREASED FROM 2048
                    )
                )
                
                # Check for API response issues based on finish_reason
                if hasattr(response, 'candidates') and response.candidates:
                    candidate = response.candidates[0]
                    if hasattr(candidate, 'finish_reason') and candidate.finish_reason:
                        finish_reason = candidate.finish_reason
                        
                        # Map finish_reason values to error messages
                        if finish_reason == 1:  # STOP - normal completion
                            pass  # Continue to process response
                        elif finish_reason == 2:  # MAX_TOKENS
                            # IMPROVED HANDLING FOR MAX_TOKENS - Don't exit immediately
                            if hasattr(response, 'text') and response.text and len(response.text.strip()) > 200:
                                print(f"    Warning: Response truncated but got {len(response.text)} chars - using partial response")
                                return response.text.strip()  # Return what we got instead of erroring
                            else:
                                return "Error: Response truncated - hit maximum token limit"
                        elif finish_reason == 3:  # SAFETY
                            return "Error: Content blocked by safety filters"
                        elif finish_reason == 4:  # RECITATION
                            return "Error: Content blocked for potential copyright violation"
                        elif finish_reason == 5:  # OTHER
                            return "Error: Content blocked for other reasons"
                        elif finish_reason == 6:  # BLOCKLIST
                            return "Error: Content contains forbidden terms"
                        elif finish_reason == 7:  # PROHIBITED_CONTENT
                            return "Error: Content blocked as prohibited"
                        elif finish_reason == 8:  # SPII
                            return "Error: Content blocked - contains sensitive personal information"
                        elif finish_reason == 9:  # MALFORMED_FUNCTION_CALL
                            return "Error: Invalid function call generated"
                        elif finish_reason == 0:  # FINISH_REASON_UNSPECIFIED
                            return "Error: Unspecified API issue"
                        else:
                            return f"Error: Unknown finish_reason: {finish_reason}"
                
                # Check for valid response text
                if hasattr(response, 'text') and response.text:
                    summary_text = response.text.strip()
                    
                    # Clean up common prefixes
                    prefixes_to_remove = [
                        "Here is a mathematical summary:",
                        "Here's a mathematical summary:",
                        "Mathematical Content Summary:",
                        "**MATHEMATICAL CONTENT SUMMARY:**",
                        "Here is a summary:",
                        "Summary:"
                    ]
                    for prefix in prefixes_to_remove:
                        if summary_text.startswith(prefix):
                            summary_text = summary_text[len(prefix):].strip()
                            break
                    
                    return summary_text
                    
                # No valid text in response
                return "Error: API response was empty or invalid"

            except Exception as e:
                error_name = type(e).__name__
                error_msg = str(e)
                print(f"    {error_name}: {error_msg}")
                
                # Check for quota/rate limit errors
                if check_quota_exceeded_error(error_msg):
                    return f"Error: QUOTA_EXCEEDED - {error_msg}"
                
                # Check for specific API errors
                if "400" in error_msg and "Bad Request" in error_msg:
                    return f"Error: Bad request - check prompt format"
                elif "401" in error_msg or "Unauthorized" in error_msg:
                    return f"Error: Unauthorized - check API key"
                elif "403" in error_msg or "Forbidden" in error_msg:
                    return f"Error: Forbidden - insufficient permissions"
                elif "429" in error_msg:
                    return f"Error: Rate limit exceeded"
                elif "500" in error_msg or "Internal Server Error" in error_msg:
                    return f"Error: Internal server error"
                elif "503" in error_msg or "Service Unavailable" in error_msg:
                    return f"Error: Service unavailable"
                
                # Retry for temporary errors
                if attempt < MAX_RETRIES - 1:
                    backoff_time = min(current_backoff, MAX_BACKOFF_SECONDS)
                    print(f"    Retrying in {backoff_time} seconds...")
                    time.sleep(backoff_time)
                    current_backoff *= 2
                else:
                    return f"Error: {error_name} after {MAX_RETRIES} retries - {error_msg}"
                    
    except Exception as e:
        return f"Error: Failed to initialize model {model_name}: {e}"
    
    return f"Error: Summarization failed after {MAX_RETRIES} attempts."

def basic_summary_validation(summary_text):
    """Very simple validation - only catch obvious problems"""
    if not summary_text or len(summary_text.strip()) < 50:
        return False, "Summary too short or empty"
    
    if summary_text.startswith("Error:"):
        return False, "Contains error message"
    
    word_count = len(summary_text.split())
    
    # Only fail if extremely short
    if word_count < 50:
        return False, f"Too brief ({word_count} words)"
    
    return True, f"Valid summary ({word_count} words)"

def detect_quota_exhaustion_response(summary_text):
    """Detect if this looks like a quota-exhausted response"""
    if not summary_text:
        return True
    
    word_count = len(summary_text.split())
    
    # The specific 60-80 word pattern you identified
    if 60 <= word_count <= 80:
        return True
    
    return False

def extract_metadata(summary_text):
    """Extract structured metadata from summary"""
    metadata = {
        'primary_field': '',
        'level': '',
        'concepts': [],
        'prerequisites': [],
        'applications': []
    }
    
    try:
        # Extract primary field
        field_match = re.search(r'\*\*Field:\*\*\s*([^\n]+)', summary_text)
        if field_match:
            metadata['primary_field'] = field_match.group(1).strip()
        
        # Extract level
        level_match = re.search(r'\*\*Level:\*\*\s*([^\n]+)', summary_text)
        if level_match:
            metadata['level'] = level_match.group(1).strip()
            
        # Extract concepts from Key Topics section
        topics_section = re.search(r'## Key Topics(.*?)(?=##|$)', summary_text, re.DOTALL)
        if topics_section:
            topics_text = topics_section.group(1)
            concept_items = re.findall(r'[-•*]\s*([^\n]+)', topics_text)
            metadata['concepts'] = [item.strip() for item in concept_items]
        
        # Extract prerequisites
        prereq_match = re.search(r'\*\*Prerequisites:\*\*\s*([^\n]+)', summary_text)
        if prereq_match:
            prereq_text = prereq_match.group(1).strip()
            if prereq_text and prereq_text.lower() not in ['none', 'n/a', 'not mentioned']:
                metadata['prerequisites'] = [prereq_text]
        
        # Extract applications
        app_match = re.search(r'\*\*Applications:\*\*\s*([^\n]+)', summary_text)
        if app_match:
            app_text = app_match.group(1).strip()
            if app_text and app_text.lower() not in ['none', 'n/a', 'not mentioned']:
                metadata['applications'] = [app_text]
    
    except Exception as e:
        print(f"    Warning: Could not extract metadata: {e}")
    
    return metadata

def process_all_transcripts(transcripts_dir, summaries_dir):
    """Enhanced processing with better quota management"""
    global requests_made_today, API_KEY_CONFIGURED

    if not API_KEY_CONFIGURED:
        print("ERROR: API Key is not configured. Please set your API key.")
        return

    if not os.path.exists(summaries_dir):
        try:
            os.makedirs(summaries_dir)
            print(f"Created summaries directory: {summaries_dir}")
        except OSError as e:
            print(f"ERROR: Error creating directory {summaries_dir}: {e}")
            return

    if not os.path.isdir(transcripts_dir):
        print(f"ERROR: Transcripts directory '{transcripts_dir}' not found.")
        return

    print(f"Looking for transcripts in: {os.path.abspath(transcripts_dir)}")
    print(f"Daily request limit: {RPD_LIMIT}. Used today: {requests_made_today}")

    files_to_process = [f for f in os.listdir(transcripts_dir) if f.endswith(".txt")]
    if not files_to_process:
        print(f"No .txt files found in '{transcripts_dir}'.")
        return

    # Sort files to process consistently
    files_to_process.sort()

    results_summary = {
        'processed': 0,
        'failed': 0,
        'skipped': 0,
        'quota_exceeded': 0,
        'files': []
    }

    for filename in files_to_process:
        transcript_filepath = os.path.join(transcripts_dir, filename)
        base_name = os.path.splitext(filename)[0]
        
        json_output_path = os.path.join(summaries_dir, f"{base_name}_SUMMARY.json")
        txt_output_path = os.path.join(summaries_dir, f"{base_name}_SUMMARY.txt")

        print(f"\nProcessing: {filename}")

        # Check if already processed successfully
        if os.path.exists(json_output_path):
            try:
                with open(json_output_path, 'r') as f:
                    existing_data = json.load(f)
                summary = existing_data.get('summary', '')
                is_valid, _ = basic_summary_validation(summary)
                if summary and not summary.startswith('Error:') and is_valid:
                    print(f"  Valid summary exists, skipping...")
                    results_summary['skipped'] += 1
                    continue
            except:
                print(f"  Existing file corrupted, reprocessing...")

        try:
            with open(transcript_filepath, 'r', encoding='utf-8') as f:
                transcript_content = f.read()

            if not transcript_content.strip():
                print("  File is empty, skipping...")
                results_summary['skipped'] += 1
                continue
            
            print(f"  Transcript length: {len(transcript_content)} characters")
            
            # Record start time for rate limiting
            call_start_time = time.time()

            # Try summarization with different models
            print("  Generating summary...")
            try:
                summary, model_used = try_with_different_models(summarize_transcript, transcript_content)
            except Exception as e:
                if "QUOTA_EXCEEDED" in str(e):
                    print(f"  QUOTA EXHAUSTED - HALTING")
                    print(f"  Successfully processed {results_summary['processed']} files before hitting limit")
                    results_summary['quota_exceeded'] += 1
                    break
                else:
                    print(f"  API ERROR: {e} - HALTING")
                    results_summary['failed'] += 1
                    break
            
            if summary is None:
                print(f"  All models failed")
                log_error(filename, "All models failed", "multiple")
                results_summary['failed'] += 1
                continue

            if summary.startswith("Error:"):
                if check_quota_exceeded_error(summary):
                    print(f"  QUOTA EXCEEDED - HALTING")
                    results_summary['quota_exceeded'] += 1
                    break
                else:
                    print(f"  API ERROR: {summary} - HALTING")
                    log_error(filename, summary, model_used)
                    results_summary['failed'] += 1
                    break

            print(f"  Summary generated using {model_used}")

            # Validate summary
            is_valid, validation_msg = basic_summary_validation(summary)
            print(f"  Validation: {validation_msg}")

            # Use default title (no API call)
            title = "Mathematical Lecture"
            print("  Using default title (title generation disabled)")

            # Extract metadata
            metadata = extract_metadata(summary)
            
            # Prepare outputs
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
                    'is_valid': is_valid,
                    'validation_msg': validation_msg
                },
                'generated_at': datetime.now().isoformat(),
                'model_used': model_used,
                'requests_used': requests_made_today
            }

            # Save outputs
            try:
                with open(json_output_path, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, indent=2, ensure_ascii=False)
                print(f"  JSON saved: {os.path.basename(json_output_path)}")
            except Exception as e:
                print(f"  ERROR saving JSON: {e}")
                results_summary['failed'] += 1
                continue

            # Save readable text
            try:
                text_output = f"""MATHEMATICS LECTURE SUMMARY
{'='*60}
Title: {title}
Original File: {filename}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Model Used: {model_used}
Validation: {validation_msg}

{summary}

{'='*60}
Processing Stats:
- Summary Length: {len(summary.split())} words ({len(summary)} chars)
- Compression Ratio: {len(summary) / len(transcript_content):.1%}
- Total Requests Used Today: {requests_made_today}/{RPD_LIMIT}
"""
                
                with open(txt_output_path, 'w', encoding='utf-8') as f:
                    f.write(text_output)
                print(f"  Text saved: {os.path.basename(txt_output_path)}")
            except Exception as e:
                print(f"  ERROR saving text: {e}")

            results_summary['processed'] += 1
            results_summary['files'].append({
                'filename': filename,
                'title': title,
                'primary_field': metadata.get('primary_field', 'Unknown'),
                'word_count': len(summary.split()),
                'model_used': model_used,
                'is_valid': is_valid
            })

            # Log successful processing
            log_success(filename, len(summary.split()), model_used, requests_made_today)

            # Rate limiting
            call_duration = time.time() - call_start_time
            sleep_time = max(0, SECONDS_PER_REQUEST_MIN_DELAY - call_duration)
            if sleep_time > 0:
                print(f"  Rate limiting delay: {sleep_time:.1f}s")
                time.sleep(sleep_time)

        except FileNotFoundError:
            print(f"  ERROR: File not found: {transcript_filepath}")
            results_summary['failed'] += 1
        except Exception as e:
            print(f"  ERROR processing {filename}: {e}")
            log_error(filename, str(e), "unknown")
            results_summary['failed'] += 1
    
    # Final summary
    print(f"\nProcessing Complete!")
    print(f"  Processed: {results_summary['processed']}")
    print(f"  Skipped: {results_summary['skipped']}")  
    print(f"  Failed: {results_summary['failed']}")
    print(f"  Quota Exceeded: {results_summary['quota_exceeded']}")
    print(f"  Total requests used: {requests_made_today}/{RPD_LIMIT}")
    
    if requests_made_today >= RPD_LIMIT or results_summary['quota_exceeded'] > 0:
        reset_time = get_quota_reset_time("")
        print(f"  Quota limit reached! Resets at: {reset_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"  You can resume processing tomorrow or upgrade your plan")
        if results_summary['quota_exceeded'] > 0:
            print(f"  Found quota exhaustion pattern at file #{results_summary['processed'] + 1}")
    
    if results_summary['files']:
        print(f"\nSuccessfully Processed Files:")
        valid_count = sum(1 for f in results_summary['files'] if f['is_valid'])
        print(f"Valid Summaries: {valid_count}/{len(results_summary['files'])}")
        
        # Show where quota degradation started
        degraded_files = [f for f in results_summary['files'] if not f['is_valid']]
        if degraded_files:
            print(f"Degraded responses detected starting around file #{len(results_summary['files']) - len(degraded_files) + 1}")
        
        print()
        for i, file_info in enumerate(results_summary['files']):
            status_emoji = "VALID" if file_info['is_valid'] else "REVIEW"
            print(f"  {i+1:3d}. {file_info['filename']}")
            print(f"       Title: {file_info['title']}")
            print(f"       Field: {file_info['primary_field']}")
            print(f"       Stats: {file_info['word_count']} words ({file_info['model_used']})")
            print(f"       Status: {status_emoji}")
            print()

def show_quota_status():
    """Show current quota status and processing history"""
    requests_today, last_reset = load_rpd_state()
    print(f"\nCurrent Quota Status:")
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d')}")
    print(f"  Requests used today: {requests_today}/{RPD_LIMIT}")
    print(f"  Remaining requests: {RPD_LIMIT - requests_today}")
    
    if requests_today >= RPD_LIMIT:
        reset_time = get_quota_reset_time("")
        print(f"  Quota exceeded! Resets at: {reset_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    else:
        print(f"  Quota available")
    
    # Show processing status
    status = get_processing_status()
    if status['successful_files'] or status['failed_files']:
        print(f"\nProcessing History:")
        print(f"  Successfully processed: {len(status['successful_files'])} files")
        print(f"  Failed: {len(status['failed_files'])} files")
        if status['last_processed']:
            print(f"  Last processed: {status['last_processed']}")
        
        # Show recent files
        if status['successful_files']:
            recent = status['successful_files'][-5:]
            print(f"  Recent successes: {', '.join(recent)}")
        
        if status['failed_files']:
            recent_fails = status['failed_files'][-3:]
            print(f"  Recent failures: {', '.join(recent_fails)}")

if __name__ == "__main__":
    print("Mathematics Transcript Summarizer with Enhanced Quota Management")
    print("="*70)
    
    if not API_KEY_CONFIGURED:
        print("ERROR: IMPORTANT: API key not configured!")
        print("Please set your Gemini API key in the script.")
        print("You can get one at: https://ai.google.dev/")
        exit(1)
    
    show_quota_status()
    
    # Ensure transcripts folder exists
    if not os.path.exists(TRANSCRIPTS_FOLDER):
        os.makedirs(TRANSCRIPTS_FOLDER)
        print(f"Created '{TRANSCRIPTS_FOLDER}' directory - add your transcript files here.")
    
    if input("\nStart processing? (y/N): ").lower().strip() == 'y':
        process_all_transcripts(TRANSCRIPTS_FOLDER, SUMMARIES_FOLDER)
    else:
        print("Processing cancelled.")
    
    print(f"\nDone! Check the '{SUMMARIES_FOLDER}' folder for results.")
#!/usr/bin/env python3
"""
Production Transcript Processor
A robust script with JSON output, restart capabilities, and metadata tracking
Enhanced version with better mathematical content capture
"""

import requests
import json
import os
import sys
import time
import re
from pathlib import Path
from typing import List, Optional, Dict, Any
import argparse
from datetime import datetime
import hashlib

class ProductionTranscriptProcessor:
    def __init__(self, model="gemma3:12b-it-qat", host="http://localhost:11434"):
        self.model = model
        self.host = host
        self.api_url = f"{host}/api/generate"
        self.health_url = f"{host}/api/tags"
        self.show_url = f"{host}/api/show"
        
        print(f"🔧 Initialized with model: {model}")
        print(f"🔧 Ollama host: {host}")
    
    def get_file_hash(self, file_path: str) -> str:
        """Generate hash of file for change detection"""
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    
    def get_output_paths(self, input_file: str) -> Dict[str, Path]:
        """Get all output file paths"""
        input_path = Path(input_file)
        base_name = input_path.stem
        output_dir = input_path.parent
        
        return {
            'json': output_dir / f"{base_name}_SUMMARY.json",
            'txt': output_dir / f"{base_name}_SUMMARY.txt", 
            'progress': output_dir / f".{base_name}_progress.json"
        }
    
    def load_progress(self, progress_file: Path) -> Optional[Dict[str, Any]]:
        """Load processing progress from file"""
        if not progress_file.exists():
            return None
        
        try:
            with open(progress_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Could not load progress file: {e}")
            return None
    
    def save_progress(self, progress_file: Path, progress_data: Dict[str, Any]):
        """Save processing progress"""
        try:
            with open(progress_file, 'w') as f:
                json.dump(progress_data, f, indent=2)
        except Exception as e:
            print(f"⚠️ Could not save progress: {e}")
    
    def check_prerequisites(self) -> bool:
        """Check all prerequisites before processing"""
        print("\n🔍 Checking prerequisites...")
        
        # Check Ollama service
        try:
            response = requests.get(self.health_url, timeout=10)
            if response.status_code != 200:
                print("❌ Cannot connect to Ollama service")
                print("   Run: ollama serve")  
                return False
            print("✅ Ollama service running")
        except Exception as e:
            print(f"❌ Ollama connection failed: {e}")
            print("   Make sure Ollama is installed and running: ollama serve")
            return False
        
        # Check model availability
        try:
            response = requests.post(
                self.show_url,
                json={"name": self.model},
                timeout=10
            )
            if response.status_code != 200:
                print(f"❌ Model '{self.model}' not available")
                print(f"   Run: ollama pull {self.model}")
                return False
            print(f"✅ Model {self.model} available")
        except Exception as e:
            print(f"❌ Model check failed: {e}")
            return False
        
        return True
    
    def read_transcript(self, file_path: str) -> Optional[str]:
        """Read transcript file with encoding detection"""
        print(f"\n📖 Reading: {Path(file_path).name}")
        
        if not Path(file_path).exists():
            print(f"❌ File not found: {file_path}")
            return None
        
        # Try different encodings
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as file:
                    text = file.read()
                print(f"✅ Read {len(text)} characters (encoding: {encoding})")
                return text
            except UnicodeDecodeError:
                continue
            except Exception as e:
                print(f"❌ Error reading file: {e}")
                return None
        
        print("❌ Could not decode file with any encoding")
        return None
    
    def clean_transcript(self, text: str) -> str:
        """Clean transcript text while preserving mathematical expressions"""
        print("🧹 Cleaning transcript...")
        
        original_length = len(text)
        
        # Remove common transcription artifacts but preserve mathematical notation
        text = re.sub(r'\[inaudible\]|\[unclear\]|\[pause\]|\[music\]|\[applause\]', '', text, flags=re.IGNORECASE)
        
        # Fix common transcription errors in mathematical contexts
        text = re.sub(r'\buh+\b', '', text, flags=re.IGNORECASE)  # Remove "uh", "uhh" 
        text = re.sub(r'\bum+\b', '', text, flags=re.IGNORECASE)  # Remove "um", "umm"
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        text = text.strip()
        
        # Remove empty lines but preserve paragraph structure
        lines = []
        for line in text.split('\n'):
            cleaned_line = line.strip()
            if cleaned_line:
                lines.append(cleaned_line)
            elif lines and lines[-1]:  # Preserve paragraph breaks
                lines.append('')
        
        text = '\n'.join(lines)
        
        print(f"✅ Cleaned: {original_length} → {len(text)} characters")
        return text
    
    def chunk_text(self, text: str, max_chars: int = 50000) -> List[str]:
        """Split large text optimized for 128k context window"""
        if len(text) <= max_chars:
            return [text]
        
        print(f"📄 Text is large ({len(text)} chars), splitting for 128k context...")
        
        # Try to split on natural section breaks first
        major_breaks = re.split(r'\n\s*\n\s*\n|\n\s*=+\s*\n|\n\s*-{3,}\s*\n', text)
        
        if len(major_breaks) > 1:
            chunks = []
            current_chunk = ""
            
            for section in major_breaks:
                if len(current_chunk) + len(section) + 4 <= max_chars:
                    current_chunk += section + "\n\n"
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = section + "\n\n"
            
            if current_chunk:
                chunks.append(current_chunk.strip())
            
            if all(len(chunk) <= max_chars for chunk in chunks):
                print(f"✅ Split into {len(chunks)} large chunks (natural breaks)")
                return chunks
        
        # Fallback to paragraph-based splitting with larger chunks
        paragraphs = re.split(r'\n\s*\n', text)
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            if len(current_chunk) + len(para) + 2 <= max_chars:
                current_chunk += para + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para + "\n\n"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        # Handle any remaining oversized chunks
        final_chunks = []
        for chunk in chunks:
            if len(chunk) <= max_chars:
                final_chunks.append(chunk)
            else:
                # Split very large chunks by sentences
                sentences = re.split(r'(?<=[.!?])\s+', chunk)
                temp_chunk = ""
                
                for sentence in sentences:
                    if len(temp_chunk) + len(sentence) + 1 <= max_chars:
                        temp_chunk += sentence + " "
                    else:
                        if temp_chunk:
                            final_chunks.append(temp_chunk.strip())
                        temp_chunk = sentence + " "
                
                if temp_chunk:
                    final_chunks.append(temp_chunk.strip())
        
        print(f"✅ Split into {len(final_chunks)} optimized chunks for 128k context")
        return final_chunks
    
    def create_prompt(self, text: str, chunk_info: str = "") -> str:
        """Create processing prompt optimized for mathematical content"""
        
        return f"""Analyze this mathematical/educational transcript and create a comprehensive, detailed summary{chunk_info}.

CRITICAL RULES:
- ONLY use information directly from the transcript
- Quote ALL formulas, equations, and mathematical expressions EXACTLY as stated
- Preserve the speaker's exact terminology and phrasing for key concepts
- If transcript content is unclear, note "[unclear in original]" but still quote it
- Capture the logical flow and connections between ideas
- Focus on specific mathematical details, not just general topics

Create a detailed summary with natural organization covering:

**Core Mathematical Framework:**
- Fundamental algebraic structures mentioned (quote specific algebras, groups, operators)
- Key theorems and results (with exact names and statements when given)
- Important equations and formulas (quoted exactly from transcript)

**Conceptual Development:**
- How ideas build upon each other throughout the lecture
- Specific examples and applications discussed
- Connections drawn between different mathematical areas

**Technical Details:**
- Precise mathematical constructions described
- Dimensional analysis and space descriptions
- Operator definitions and their commutation relations

**Key Insights and Claims:**
- Novel theoretical predictions or claims made
- Relationships established between different theories
- Unexpected connections revealed

Use clear headings and write in flowing paragraphs. Be comprehensive and capture the mathematical richness while maintaining readability. Quote mathematical expressions exactly as they appear in the transcript.

TRANSCRIPT:
{text}

DETAILED MATHEMATICAL SUMMARY:"""
    
    def create_synthesis_prompt(self, chunk_summaries: List[str]) -> str:
        """Create prompt for synthesizing multiple chunks with mathematical precision"""
        
        combined_summaries = "\n\n=== PART SEPARATOR ===\n\n".join(chunk_summaries)
        
        return f"""You are synthesizing summaries from different parts of the same mathematical lecture. Create ONE comprehensive, mathematically precise summary that integrates all information naturally.

SYNTHESIS RULES:
- Combine related mathematical concepts from different parts
- Preserve ALL specific formulas, equations, and expressions exactly
- Remove redundancy while keeping mathematical precision
- Create logical flow showing conceptual development
- Maintain exact mathematical terminology and notation
- If parts have different versions of same formula, include both with clarification
- Highlight key insights and theoretical connections

Create a unified summary that reads as a single, coherent mathematical exposition, not separate parts stitched together.

INDIVIDUAL PART SUMMARIES:
{combined_summaries}

UNIFIED MATHEMATICAL SUMMARY:"""

    def calculate_timeout(self, text_length: int) -> int:
        """Calculate appropriate timeout based on text length"""
        base_timeout = 60
        # Add time based on content length (1 second per 50 characters)
        calculated = base_timeout + (text_length // 50)
        # Cap between 60 and 400 seconds
        return min(max(calculated, 60), 400)
    
    def process_chunk(self, chunk: str, chunk_num: int, total_chunks: int) -> Optional[str]:
        """Process a single chunk with larger context"""
        print(f"\n📝 Processing chunk {chunk_num}/{total_chunks} ({len(chunk)} chars)...")
        
        chunk_prompt = self.create_prompt(chunk, f" (Part {chunk_num} of {total_chunks})")
        
        payload = {
            "model": self.model,
            "prompt": chunk_prompt,
            "stream": False,
            "options": {
                "num_predict": 1500,  # Increased for more detailed chunks
                "temperature": 0.05,  # Lower for more precision
                "top_p": 0.9,
                "num_ctx": 65536,
                "num_batch": 512,
                "num_gpu_layers": -1,
                "repeat_penalty": 1.1,
                "repeat_last_n": 128
            }
        }
        
        # Retry logic for chunks
        for attempt in range(2):
            try:
                timeout = self.calculate_timeout(len(chunk))
                response = requests.post(
                    self.api_url,
                    json=payload,
                    timeout=timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    summary = result.get('response', '').strip()
                    
                    if summary:
                        print(f"✅ Chunk {chunk_num} completed ({len(summary)} chars)")
                        return summary
                    else:
                        print(f"⚠️ Empty response for chunk {chunk_num}")
                else:
                    print(f"⚠️ Chunk {chunk_num} failed with status {response.status_code}")
                    
            except Exception as e:
                print(f"❌ Error processing chunk {chunk_num}: {e}")
            
            # Brief retry delay
            if attempt == 0:
                time.sleep(3)
        
        print(f"❌ Chunk {chunk_num} failed completely")
        return None
    
    def synthesize_chunked_summary(self, parts: List[Dict]) -> Optional[str]:
        """Synthesize multiple chunk summaries into one coherent summary"""
        
        if len(parts) <= 1:
            return None
            
        print(f"\n🔄 Synthesizing {len(parts)} parts into coherent summary...")
        
        # Extract just the content from successful parts
        successful_parts = [part['content'] for part in parts if part['status'] == 'completed']
        
        if not successful_parts:
            return None
            
        synthesis_prompt = self.create_synthesis_prompt(successful_parts)
        
        payload = {
            "model": self.model,
            "prompt": synthesis_prompt,
            "stream": False,
            "options": {
                "num_predict": 3500,  # Allow longer synthesis
                "temperature": 0.05,
                "top_p": 0.9,
                "num_ctx": 65536,
                "num_batch": 512,
                "num_gpu_layers": -1,
                "repeat_penalty": 1.1,
                "repeat_last_n": 128
            }
        }
        
        for attempt in range(3):
            try:
                print(f"🧠 Generating synthesis (attempt {attempt + 1}/3)...")
                
                timeout = self.calculate_timeout(len(synthesis_prompt))
                response = requests.post(
                    self.api_url,
                    json=payload,
                    timeout=timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    synthesis = result.get('response', '').strip()
                    
                    if synthesis:
                        print(f"✅ Synthesis completed: {len(synthesis)} characters")
                        return synthesis
                
            except Exception as e:
                print(f"❌ Synthesis attempt {attempt + 1} failed: {e}")
                
            if attempt < 2:
                time.sleep(3)
        
        print("⚠️ Synthesis failed, will use individual parts")
        return None
    
    def generate_summary(self, text: str, progress_file: Path) -> Optional[Dict[str, Any]]:
        """Generate summary with synthesis for chunked content"""
        
        # Load existing progress
        progress = self.load_progress(progress_file) or {
            'chunks': {},
            'total_chunks': 0,
            'completed_chunks': 0,
            'failed_chunks': [],
            'started_at': datetime.now().isoformat()
        }
        
        # Check if we need chunking - increased threshold
        if len(text) > 60000:  # Increased from 25000
            chunks = self.chunk_text(text, max_chars=50000)  # Increased from 20000
            progress['total_chunks'] = len(chunks)
            
            chunk_summaries = []
            
            for i, chunk in enumerate(chunks, 1):
                chunk_key = f"chunk_{i}"
                
                # Skip if already processed
                if chunk_key in progress['chunks']:
                    print(f"📋 Chunk {i} already completed, skipping...")
                    chunk_summaries.append({
                        'part': i,
                        'content': progress['chunks'][chunk_key]['summary'],
                        'status': 'completed'
                    })
                    continue
                
                # Process chunk
                summary = self.process_chunk(chunk, i, len(chunks))
                
                if summary:
                    progress['chunks'][chunk_key] = {
                        'summary': summary,
                        'length': len(summary),
                        'processed_at': datetime.now().isoformat()
                    }
                    chunk_summaries.append({
                        'part': i,
                        'content': summary,
                        'status': 'completed'
                    })
                    progress['completed_chunks'] += 1
                else:
                    progress['failed_chunks'].append(i)
                    chunk_summaries.append({
                        'part': i,
                        'content': f"[Processing failed]",
                        'status': 'failed'
                    })
                
                # Save progress after each chunk
                self.save_progress(progress_file, progress)
                
                # Brief pause between chunks
                if i < len(chunks):
                    time.sleep(1)
            
            # Try to synthesize if we have multiple successful parts
            synthesis = None
            if len([p for p in chunk_summaries if p['status'] == 'completed']) > 1:
                synthesis = self.synthesize_chunked_summary(chunk_summaries)
            
            # Prepare final result
            if chunk_summaries:
                combined_parts = []
                for chunk_data in chunk_summaries:
                    combined_parts.append({
                        'part_number': chunk_data['part'],
                        'content': chunk_data['content'],
                        'status': chunk_data['status'],
                        'word_count': len(chunk_data['content'].split())
                    })
                
                result = {
                    'type': 'chunked',
                    'parts': combined_parts,
                    'total_parts': len(chunks),
                    'successful_parts': len([p for p in combined_parts if p['status'] == 'completed']),
                    'failed_parts': len([p for p in combined_parts if p['status'] == 'failed']),
                    'processing_stats': progress
                }
                
                # Add synthesis if available
                if synthesis:
                    result['synthesized_summary'] = {
                        'content': synthesis,
                        'word_count': len(synthesis.split()),
                        'created_at': datetime.now().isoformat()
                    }
                
                return result
        
        else:
            # Single text processing with enhanced parameters
            prompt = self.create_prompt(text)
            timeout = self.calculate_timeout(len(text))
            
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": 3000,  # Increased for more detailed output
                    "temperature": 0.05,  # Lower for more precision
                    "top_p": 0.9,
                    "num_ctx": 65536,
                    "num_batch": 512,
                    "num_gpu_layers": -1,
                    "repeat_penalty": 1.1,  # Lower to allow mathematical repetition
                    "repeat_last_n": 128   # Longer context for consistency
                }
            }
            
            for attempt in range(3):
                try:
                    print(f"🤖 Generating summary (attempt {attempt + 1}/3, timeout: {timeout}s)...")
                    
                    response = requests.post(
                        self.api_url,
                        json=payload,
                        timeout=timeout
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        summary = result.get('response', '').strip()
                        
                        if summary:
                            print(f"✅ Generated summary: {len(summary)} characters")
                            return {
                                'type': 'single',
                                'content': summary,
                                'word_count': len(summary.split()),
                                'processing_stats': {
                                    'attempts': attempt + 1,
                                    'processed_at': datetime.now().isoformat()
                                }
                            }
                    
                except Exception as e:
                    print(f"❌ Error on attempt {attempt + 1}: {e}")
                
                if attempt < 2:
                    time.sleep(5 + attempt * 2)
        
        return None
    
    def save_outputs(self, summary_data: Dict[str, Any], metadata: Dict[str, Any], output_paths: Dict[str, Path]):
        """Save both JSON and text outputs"""
        
        # Prepare JSON output
        json_output = {
            'metadata': metadata,
            'summary': summary_data,
            'generated_at': datetime.now().isoformat(),
            'model_used': self.model,
            'version': '2.1'  # Updated version
        }
        
        # Save JSON
        try:
            with open(output_paths['json'], 'w', encoding='utf-8') as f:
                json.dump(json_output, f, indent=2, ensure_ascii=False)
            print(f"💾 JSON saved: {output_paths['json'].name}")
        except Exception as e:
            print(f"❌ Error saving JSON: {e}")
            return False
        
        # Generate and save text format
        try:
            text_content = self.format_text_output(json_output)
            with open(output_paths['txt'], 'w', encoding='utf-8') as f:
                f.write(text_content)
            print(f"💾 Text saved: {output_paths['txt'].name}")
        except Exception as e:
            print(f"❌ Error saving text: {e}")
            return False
        
        return True
    
    def format_text_output(self, json_data: Dict[str, Any]) -> str:
        """Format JSON data as readable text"""
        
        metadata = json_data['metadata']
        summary = json_data['summary']
        
        text_parts = [
            "MATHEMATICAL TRANSCRIPT SUMMARY",
            "=" * 50,
            f"Original file: {metadata['original_filename']}",
            f"Generated by: {json_data['model_used']}",
            f"Processed on: {json_data['generated_at'][:19].replace('T', ' ')}",
            f"File hash: {metadata['file_hash'][:12]}...",
            "CONTENT EXTRACTED FROM TRANSCRIPT ONLY - NO ADDITIONS",
            "=" * 50,
            ""
        ]
        
        if summary['type'] == 'chunked':
            # Show synthesized summary first if available
            if 'synthesized_summary' in summary:
                text_parts.append("INTEGRATED COMPREHENSIVE SUMMARY")
                text_parts.append("=" * 60)
                text_parts.append("")
                text_parts.append(summary['synthesized_summary']['content'])
                text_parts.append("")
                text_parts.append("=" * 60)
                text_parts.append("")
            
            text_parts.append(f"INDIVIDUAL PARTS ({summary['total_parts']} parts processed)")
            text_parts.append("=" * 60)
            text_parts.append("")
            
            for part in summary['parts']:
                text_parts.append(f"PART {part['part_number']}:")
                if part['status'] == 'completed':
                    text_parts.append(part['content'])
                else:
                    text_parts.append(f"[Part {part['part_number']} processing failed]")
                text_parts.append("")
        else:
            text_parts.append("SUMMARY:")
            text_parts.append("-" * 20)
            text_parts.append(summary['content'])
            text_parts.append("")
        
        # Add footer
        text_parts.extend([
            "=" * 50,
            f"Summary of: {metadata['original_filename']}",
            f"Compression: {metadata['compression_ratio']:.1%}",
            "Verify important details against original transcript"
        ])
        
        return "\n".join(text_parts)
    
    def process_transcript(self, file_path: str, force_restart: bool = False) -> bool:
        """Complete processing pipeline with restart capability"""
        
        print(f"\n{'='*60}")
        print(f"🎯 PROCESSING: {Path(file_path).name}")
        print(f"{'='*60}")
        
        # Get output paths
        output_paths = self.get_output_paths(file_path)
        
        # Check if already completed (unless force restart)
        if not force_restart and output_paths['json'].exists():
            try:
                with open(output_paths['json'], 'r') as f:
                    existing = json.load(f)
                
                # Check if file changed
                current_hash = self.get_file_hash(file_path)
                if existing.get('metadata', {}).get('file_hash') == current_hash:
                    print("✅ File already processed with same content")
                    print(f"📄 Existing outputs: {output_paths['json'].name}, {output_paths['txt'].name}")
                    return True
                else:
                    print("📝 File content changed, reprocessing...")
            except:
                print("⚠️ Could not read existing output, reprocessing...")
        
        # Check prerequisites
        if not self.check_prerequisites():
            return False
        
        # Read and clean file
        text = self.read_transcript(file_path)
        if not text:
            return False
        
        clean_text = self.clean_transcript(text)
        if not clean_text:
            print("❌ No content after cleaning")
            return False
        
        # Generate summary with progress tracking
        summary_data = self.generate_summary(clean_text, output_paths['progress'])
        if not summary_data:
            return False
        
        # Prepare metadata
        metadata = {
            'original_filename': Path(file_path).name,
            'original_length': len(text),
            'cleaned_length': len(clean_text),
            'summary_length': 0,  # Will be calculated
            'file_hash': self.get_file_hash(file_path),
            'compression_ratio': 0,  # Will be calculated
            'processing_type': summary_data['type']
        }
        
        # Calculate summary length
        if summary_data['type'] == 'chunked':
            if 'synthesized_summary' in summary_data:
                metadata['summary_length'] = len(summary_data['synthesized_summary']['content'])
            else:
                metadata['summary_length'] = sum(len(part['content']) for part in summary_data['parts'])
        else:
            metadata['summary_length'] = len(summary_data['content'])
        
        metadata['compression_ratio'] = metadata['summary_length'] / metadata['cleaned_length']
        
        # Save outputs
        if not self.save_outputs(summary_data, metadata, output_paths):
            return False
        
        # Clean up progress file
        try:
            if output_paths['progress'].exists():
                output_paths['progress'].unlink()
        except:
            pass
        
        # Success summary
        print(f"\n🎉 SUCCESS!")
        print(f"📊 Original: {metadata['original_length']} characters")
        print(f"📊 Cleaned: {metadata['cleaned_length']} characters")
        print(f"📊 Summary: {metadata['summary_length']} characters")
        print(f"📊 Compression: {metadata['compression_ratio']:.1%}")
        if summary_data['type'] == 'chunked':
            print(f"📊 Parts: {summary_data['successful_parts']}/{summary_data['total_parts']} successful")
            if 'synthesized_summary' in summary_data:
                print("📊 Synthesized: Yes")
        print(f"💾 Outputs: {output_paths['json'].name}, {output_paths['txt'].name}")
        
        return True

def main():
    """Main function with enhanced options"""
    parser = argparse.ArgumentParser(
        description="Enhanced Production Transcript Processor with mathematical content optimization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python script.py transcript.txt
  python script.py -m llama3:8b transcript.txt
  python script.py --restart transcript.txt
  python script.py --host http://remote:11434 transcript.txt

Features:
  - Enhanced mathematical content capture
  - JSON output with metadata
  - Resume failed processing
  - Progress tracking
  - Change detection
  - Synthesis of chunked summaries

Make sure Ollama is running: ollama serve
        """
    )
    
    parser.add_argument("file", help="Transcript file to process")
    parser.add_argument("-m", "--model", default="gemma3:12b-it-qat", 
                       help="Ollama model (default: gemma3:12b-it-qat)")
    parser.add_argument("--host", default="http://localhost:11434",
                       help="Ollama host URL (default: http://localhost:11434)")
    parser.add_argument("--restart", action="store_true",
                       help="Force restart processing (ignore existing outputs)")
    
    args = parser.parse_args()
    
    # Validate file
    if not Path(args.file).exists():
        print(f"❌ File not found: {args.file}")
        sys.exit(1)
    
    # Initialize processor
    processor = ProductionTranscriptProcessor(model=args.model, host=args.host)
    
    # Process file
    success = processor.process_transcript(args.file, force_restart=args.restart)
    
    if success:
        print(f"\n✨ All done! Check the JSON and TXT files.")
        sys.exit(0)
    else:
        print(f"\n💥 Processing failed. Check the output above for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()
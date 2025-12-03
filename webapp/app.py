#!/usr/bin/env python3
"""
BIRS NotebookLM - Flask Web App
3-Panel Interface: Sources | Chat | Outputs
"""

import os
import json
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename

# Import our pipeline
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from gemini_podcast import run_pipeline, get_api_key

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max
app.config['UPLOAD_FOLDER'] = Path(__file__).parent / 'uploads'
app.config['OUTPUT_FOLDER'] = Path.home() / 'vlm' / 'output'
app.config['CATALOG_FILE'] = Path(__file__).parent / 'data' / 'birs_videos.json'

# Ensure folders exist
app.config['UPLOAD_FOLDER'].mkdir(parents=True, exist_ok=True)

# Load video catalog (lazy load for performance)
_video_catalog = None

def get_catalog():
    """Load video catalog lazily."""
    global _video_catalog
    if _video_catalog is None and app.config['CATALOG_FILE'].exists():
        with open(app.config['CATALOG_FILE']) as f:
            _video_catalog = json.load(f)
    return _video_catalog or []

# Store processing state
processing_state = {
    'sources': [],  # List of uploaded videos
    'outputs': {},  # video_name -> {analysis, script, audio}
    'chat_history': []
}


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/upload', methods=['POST'])
def upload_video():
    """Upload a video source."""
    if 'video' not in request.files:
        return jsonify({'error': 'No video file'}), 400

    file = request.files['video']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    filename = secure_filename(file.filename)
    filepath = app.config['UPLOAD_FOLDER'] / filename
    file.save(filepath)

    # Add to sources
    source = {
        'name': filename,
        'path': str(filepath),
        'status': 'uploaded'
    }
    processing_state['sources'].append(source)

    return jsonify({'success': True, 'source': source})


@app.route('/api/sources', methods=['GET'])
def get_sources():
    """Get all uploaded sources."""
    return jsonify(processing_state['sources'])


@app.route('/api/process', methods=['POST'])
def process_video():
    """Process a video through the pipeline."""
    data = request.json
    video_name = data.get('video_name')
    premium = data.get('premium', False)

    # Find the source
    source = None
    for s in processing_state['sources']:
        if s['name'] == video_name:
            source = s
            break

    if not source:
        return jsonify({'error': 'Video not found'}), 404

    try:
        source['status'] = 'processing'

        # Run pipeline (this will take ~2 min)
        result = run_pipeline(source['path'], premium_tts=premium)

        source['status'] = 'complete'

        # Store outputs
        video_stem = Path(video_name).stem
        processing_state['outputs'][video_stem] = {
            'analysis': result.get('analysis', {}),
            'script_path': str(app.config['OUTPUT_FOLDER'] / f'{video_stem}_script.txt'),
            'audio_path': str(app.config['OUTPUT_FOLDER'] / f'{video_stem}_podcast.wav'),
            'json_path': str(app.config['OUTPUT_FOLDER'] / f'{video_stem}_analysis.json')
        }

        return jsonify({'success': True, 'outputs': processing_state['outputs'][video_stem]})

    except Exception as e:
        source['status'] = 'error'
        return jsonify({'error': str(e)}), 500


@app.route('/api/outputs/<video_name>', methods=['GET'])
def get_outputs(video_name):
    """Get outputs for a processed video."""
    if video_name in processing_state['outputs']:
        return jsonify(processing_state['outputs'][video_name])
    return jsonify({'error': 'Not found'}), 404


@app.route('/api/audio/<video_name>')
def get_audio(video_name):
    """Serve audio file."""
    audio_path = app.config['OUTPUT_FOLDER'] / f'{video_name}_podcast.wav'
    if audio_path.exists():
        return send_file(audio_path, mimetype='audio/wav')
    return jsonify({'error': 'Audio not found'}), 404


@app.route('/api/script/<video_name>')
def get_script(video_name):
    """Get script text."""
    script_path = app.config['OUTPUT_FOLDER'] / f'{video_name}_script.txt'
    if script_path.exists():
        return script_path.read_text()
    return jsonify({'error': 'Script not found'}), 404


@app.route('/api/chat', methods=['POST'])
def chat():
    """Chat about the lecture content."""
    data = request.json
    message = data.get('message', '')
    video_name = data.get('video_name')

    # For now, return the analysis summary
    # TODO: Integrate with Gemini for Q&A
    if video_name and video_name in processing_state['outputs']:
        analysis = processing_state['outputs'][video_name].get('analysis', {})
        summary = analysis.get('summary', 'No summary available')

        response = f"Based on the lecture: {summary}"
    else:
        response = "Please process a video first to chat about it."

    processing_state['chat_history'].append({
        'user': message,
        'assistant': response
    })

    return jsonify({'response': response})


@app.route('/api/catalog', methods=['GET'])
def browse_catalog():
    """Browse video catalog with search and filters."""
    catalog = get_catalog()

    # Get query params
    q = request.args.get('q', '').lower()
    field = request.args.get('field', '')
    year = request.args.get('year', '')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))

    # Filter
    results = catalog
    if q:
        results = [v for v in results if
                   q in v['title'].lower() or
                   q in v['speaker']['name'].lower() or
                   q in v.get('content', {}).get('abstract', '').lower()]
    if field:
        results = [v for v in results if v['content']['field'] == field]
    if year:
        results = [v for v in results if v['workshop']['year'] == int(year)]

    # Paginate
    total = len(results)
    start = (page - 1) * per_page
    end = start + per_page

    return jsonify({
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page,
        'videos': results[start:end]
    })


@app.route('/api/catalog/fields', methods=['GET'])
def get_fields():
    """Get all available fields."""
    catalog = get_catalog()
    fields = sorted(set(v['content']['field'] for v in catalog))
    return jsonify(fields)


@app.route('/api/catalog/years', methods=['GET'])
def get_years():
    """Get all available years."""
    catalog = get_catalog()
    years = sorted(set(v['workshop']['year'] for v in catalog), reverse=True)
    return jsonify(years)


@app.route('/api/catalog/add', methods=['POST'])
def add_from_catalog():
    """Add a video from catalog as a source."""
    data = request.json
    video_id = data.get('video_id')

    catalog = get_catalog()
    video = next((v for v in catalog if v['id'] == video_id), None)

    if not video:
        return jsonify({'error': 'Video not found'}), 404

    source = {
        'name': video['title'],
        'path': video['files']['video_url'],
        'speaker': video['speaker']['name'],
        'field': video['content']['field'],
        'year': video['workshop']['year'],
        'status': 'ready',
        'from_catalog': True
    }
    processing_state['sources'].append(source)

    return jsonify({'success': True, 'source': source})


if __name__ == '__main__':
    print("Starting BIRS NotebookLM Web App...")
    print(f"Upload folder: {app.config['UPLOAD_FOLDER']}")
    print(f"Output folder: {app.config['OUTPUT_FOLDER']}")
    app.run(debug=True, port=5000)

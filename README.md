# BIRS Video Archive Search

A better way to search and browse video lectures from the Banff International Research Station (BIRS).

## What This Is

BIRS has over 16,000+ recorded mathematics lectures from workshops dating back to 2003, but they're difficult to find on the current website. This project makes those videos searchable and browsable with a modern interface.

## Features

- **Search across 10,986+ videos** - Search by title, speaker, abstract, concepts, and even transcripts
- **Filter by category** - Browse by mathematical field (Topology, Statistics, ML, etc.)
- **Year filtering** - Find videos from specific workshop years (2020-2024)
- **Transcripts and summaries** - View AI-generated transcripts and summaries for ~3,000 videos
- **Direct video links** - Links to original videos hosted at videos.birs.ca
- **MP3 downloads** - Audio-only versions available at audio.birs.ca

## Project Structure

```
videos/
├── birs_video_search/      # Web interface
│   ├── index.html         # Main search page
│   └── static/            # JavaScript, CSS, and video data
├── processing/            # Scripts for transcript/summary generation
├── mp3/                   # Audio extraction tools
└── plan.md               # Development roadmap
```

## Running Locally

1. Navigate to the search interface:
   ```bash
   cd birs_video_search
   ```

2. Start a local web server:
   ```bash
   python -m http.server
   ```

3. Open http://localhost:8000 in your browser

## Data Processing

The `processing/` directory contains scripts used to:
- Extract audio from videos
- Generate transcripts using Gemini API
- Create AI summaries of lecture content
- Extract mathematical concepts and metadata

## Why This Exists

The current BIRS website makes it hard to find specific videos. Researchers often need to:
- Find talks by specific speakers
- Search for videos on particular mathematical topics
- Access transcripts when audio is unclear
- Browse related content

This interface solves those problems with better search and filtering.

## Technical Details

- **Frontend**: Vanilla JavaScript with Fuse.js for fuzzy search
- **Data**: Static JSON file with video metadata
- **Transcripts**: Generated using Google's Gemini API
- **Hosting**: Can be served as static files

## Contributing

Feel free to submit issues or pull requests. Main areas for improvement:
- Adding more transcripts
- Improving search relevance
- Better mobile experience
- Video player integration

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Note: This is an unofficial interface for accessing publicly available BIRS videos. All video content belongs to BIRS and the respective speakers.

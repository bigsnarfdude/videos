LECTURE_SCHEMA = {
    "id": "unique_identifier (string)",
    "title": "Lecture title (string)",
    "speaker": {
        "name": "Speaker full name (string)",
        "affiliation": "Institution (string)",
        "bio_url": "Optional biography link (string)"
    },
    "workshop": {
        "code": "Workshop code (string, e.g., 24w5258)",
        "title": "Workshop full title (string)",
        "type": "Workshop type (string, e.g., 5-day|2-day|frg|rit|summer)",
        "year": "Year (integer)",
        "dates": "Dates (string, e.g., Aug 26-30, 2024)"
    },
    "content": {
        "abstract": "Lecture description/abstract (string)",
        "topics": ["tag1 (string)", "tag2 (string)", "tag3 (string)"],
        "field": "Primary mathematical field (string)",
        "difficulty": "Difficulty level (string, e.g., undergraduate|graduate|research)",
        "duration_minutes": "Duration in minutes (integer)",
        "language": "Language code (string, e.g., en)"
    },
    "files": {
        "video_url": "Video URL (string)",
        "video_size_mb": "Video size in MB (integer)",
        "thumbnail_url": "Optional thumbnail URL (string)",
        "transcript_url": "Optional transcript URL (string)",
        "slides_url": "Optional slide deck URL (string)"
    },
    "metadata": {
        "recorded_date": "Recorded date (string, YYYY-MM-DD)",
        "upload_date": "Upload date (string, YYYY-MM-DD)",
        "quality": "Video quality (string, e.g., 1080p|720p|480p)",
        "view_count": "View count (integer)",
        "featured": "Featured status (boolean)"
    }
}

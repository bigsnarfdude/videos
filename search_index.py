#!/usr/bin/env python3
"""
BIRS Lecture Search Index

Simple search functionality for processed lectures.
Uses SQLite FTS5 for full-text search.

Usage:
    # Build index from processed lectures
    python search_index.py build

    # Search lectures
    python search_index.py search "quantum walks"
    python search_index.py search --speaker "Neshveyev"
    python search_index.py search --field "algebra"
"""

import sqlite3
import json
import argparse
from pathlib import Path
from typing import List, Dict, Optional

OUTPUT_DIR = Path.home() / "vlm" / "output"
DB_PATH = OUTPUT_DIR / "lectures.db"


def init_db():
    """Initialize SQLite database with FTS5."""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    # Main lectures table
    c.execute('''
        CREATE TABLE IF NOT EXISTS lectures (
            id TEXT PRIMARY KEY,
            video_name TEXT,
            speaker TEXT,
            title TEXT,
            institution TEXT,
            workshop TEXT,
            field TEXT,
            date TEXT,
            format TEXT,
            summary TEXT,
            transcript TEXT,
            equations TEXT,
            concepts TEXT,
            json_path TEXT
        )
    ''')

    # FTS5 virtual table for full-text search
    c.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS lectures_fts USING fts5(
            id,
            speaker,
            title,
            summary,
            transcript,
            concepts,
            content='lectures',
            content_rowid='rowid'
        )
    ''')

    # Triggers to keep FTS in sync
    c.execute('''
        CREATE TRIGGER IF NOT EXISTS lectures_ai AFTER INSERT ON lectures BEGIN
            INSERT INTO lectures_fts(rowid, id, speaker, title, summary, transcript, concepts)
            VALUES (new.rowid, new.id, new.speaker, new.title, new.summary, new.transcript, new.concepts);
        END
    ''')

    conn.commit()
    return conn


def index_lecture(conn: sqlite3.Connection, json_path: Path) -> bool:
    """Index a single lecture from its JSON file."""
    try:
        with open(json_path) as f:
            data = json.load(f)

        # Handle nested structure
        if "analysis" in data:
            analysis = data["analysis"]
            source = data.get("source", {})
        else:
            analysis = data
            source = {}

        meta = analysis.get("metadata", {})

        # Extract fields
        lecture = {
            "id": json_path.stem,
            "video_name": source.get("video_name", json_path.stem),
            "speaker": meta.get("speaker", ""),
            "title": meta.get("title", ""),
            "institution": meta.get("institution", ""),
            "workshop": meta.get("workshop", ""),
            "field": meta.get("field", ""),
            "date": meta.get("date", ""),
            "format": meta.get("format", ""),
            "summary": analysis.get("summary", ""),
            "transcript": analysis.get("transcript", {}).get("full_text", ""),
            "equations": json.dumps(analysis.get("equations", [])),
            "concepts": ", ".join(analysis.get("key_concepts", [])),
            "json_path": str(json_path)
        }

        c = conn.cursor()
        c.execute('''
            INSERT OR REPLACE INTO lectures
            (id, video_name, speaker, title, institution, workshop, field, date, format, summary, transcript, equations, concepts, json_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', tuple(lecture.values()))

        conn.commit()
        return True

    except Exception as e:
        print(f"Error indexing {json_path}: {e}")
        return False


def build_index():
    """Build search index from all processed lectures."""
    print("Building search index...")

    conn = init_db()

    # Find all JSON files
    json_files = list(OUTPUT_DIR.glob("*.json"))
    json_files += list(OUTPUT_DIR.glob("*/analysis.json"))

    indexed = 0
    for json_path in json_files:
        if index_lecture(conn, json_path):
            print(f"  Indexed: {json_path.name}")
            indexed += 1

    conn.close()
    print(f"\nIndexed {indexed} lectures")
    print(f"Database: {DB_PATH}")


def search(query: str, speaker: str = None, field: str = None,
           workshop: str = None, limit: int = 20) -> List[Dict]:
    """Search lectures."""

    if not DB_PATH.exists():
        print("No index found. Run 'python search_index.py build' first.")
        return []

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Build query
    if query:
        # Full-text search
        sql = '''
            SELECT l.*, bm25(lectures_fts) as score
            FROM lectures l
            JOIN lectures_fts ON l.id = lectures_fts.id
            WHERE lectures_fts MATCH ?
        '''
        params = [query]
    else:
        sql = "SELECT *, 0 as score FROM lectures WHERE 1=1"
        params = []

    # Add filters
    if speaker:
        sql += " AND speaker LIKE ?"
        params.append(f"%{speaker}%")

    if field:
        sql += " AND field LIKE ?"
        params.append(f"%{field}%")

    if workshop:
        sql += " AND workshop LIKE ?"
        params.append(f"%{workshop}%")

    sql += " ORDER BY score LIMIT ?"
    params.append(limit)

    c.execute(sql, params)
    results = [dict(row) for row in c.fetchall()]

    conn.close()
    return results


def print_results(results: List[Dict]):
    """Pretty print search results."""
    if not results:
        print("No results found.")
        return

    print(f"\nFound {len(results)} result(s):\n")
    print("-" * 60)

    for i, r in enumerate(results, 1):
        print(f"{i}. {r['title']}")
        print(f"   Speaker: {r['speaker']}")
        print(f"   Field: {r['field']}")
        print(f"   Workshop: {r['workshop']}")
        if r['concepts']:
            print(f"   Concepts: {r['concepts'][:80]}...")
        print(f"   Summary: {r['summary'][:150]}...")
        print("-" * 60)


def main():
    parser = argparse.ArgumentParser(description="BIRS Lecture Search")
    subparsers = parser.add_subparsers(dest="command")

    # Build command
    subparsers.add_parser("build", help="Build search index")

    # Search command
    search_parser = subparsers.add_parser("search", help="Search lectures")
    search_parser.add_argument("query", nargs="?", default="", help="Search query")
    search_parser.add_argument("--speaker", help="Filter by speaker name")
    search_parser.add_argument("--field", help="Filter by mathematical field")
    search_parser.add_argument("--workshop", help="Filter by workshop code")
    search_parser.add_argument("--limit", type=int, default=20, help="Max results")

    args = parser.parse_args()

    if args.command == "build":
        build_index()
    elif args.command == "search":
        results = search(
            args.query,
            speaker=args.speaker,
            field=args.field,
            workshop=args.workshop,
            limit=args.limit
        )
        print_results(results)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

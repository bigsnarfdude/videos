#!/usr/bin/env python3
"""
Complete BIRS Video Data Extractor
Extracts video metadata from BIRS workshop pages with correct URLs
"""

import json
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time

def extract_workshop_videos(workshop_url):
    """Extract video data from a BIRS workshop page"""
    try:
        print(f"  Fetching: {workshop_url}")
        response = requests.get(workshop_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        videos = []
        
        # Find all video links
        video_links = soup.find_all('a', href=re.compile(r'/videos/watch/'))
        
        # Extract video titles from the page
        video_titles = extract_video_titles_from_page(soup)
        
        for i, link in enumerate(video_links):
            video_data = extract_video_metadata(link, workshop_url, video_titles, i)
            if video_data:
                videos.append(video_data)
                
        return videos
    except Exception as e:
        print(f"  Error extracting from {workshop_url}: {e}")
        return []

def extract_video_titles_from_page(soup):
    """Extract video titles from page content"""
    titles = []
    
    # Look for patterns like 'Video: Title Name' or '"Title Name"'
    video_text_elements = soup.find_all(string=re.compile(r'Video:'))
    
    for element in video_text_elements:
        text = element.strip()
        if 'Video:' in text:
            parts = text.split('Video:', 1)
            if len(parts) > 1:
                title = parts[1].strip()
                title = re.sub(r'^["\']|["\']$', '', title)  # Remove quotes
                title = re.sub(r'\s+', ' ', title)  # Normalize whitespace
                if title and title != "Watch video":
                    titles.append(title)
    
    # Also look for lecture titles in paragraphs
    paragraphs = soup.find_all('p')
    for p in paragraphs:
        text = p.get_text().strip()
        if '"' in text and 20 < len(text) < 200:
            quoted_match = re.search(r'"([^"]{20,150})"', text)
            if quoted_match:
                titles.append(quoted_match.group(1))
    
    return titles

def extract_video_metadata(video_link, workshop_url, video_titles, index):
    """Extract metadata from a single video link"""
    try:
        href = video_link.get('href')
        link_text = video_link.get_text().strip()
        
        # Parse workshop info
        workshop_match = re.search(r'/(\d{2}w\d{4})/', workshop_url)
        workshop_code = workshop_match.group(1) if workshop_match else ""
        year = int(f"20{workshop_code[:2]}") if workshop_code else 2024
        
        # Extract speaker and timestamp from filename
        filename_match = re.search(r'/(\d{12})-([^.]+)\.html', href)
        if filename_match:
            timestamp, speaker_lastname = filename_match.groups()
            recorded_date = datetime.strptime(timestamp, "%Y%m%d%H%M").strftime("%Y-%m-%d")
            
            # Improve speaker name formatting
            speaker_name = speaker_lastname.replace('-', ' ').title()
            if len(speaker_name.split()) == 1:
                speaker_name = f"Dr. {speaker_name}"
        else:
            recorded_date = f"{year}-01-01"
            speaker_name = "Unknown Speaker"
        
        # Determine video title
        if index < len(video_titles) and video_titles[index]:
            title = video_titles[index]
        elif link_text and link_text != "Watch video":
            title = link_text
        else:
            # Look for title in surrounding context
            parent = video_link.find_parent()
            if parent:
                parent_text = parent.get_text().strip()
                quoted_match = re.search(r'"([^"]{10,150})"', parent_text)
                if quoted_match:
                    title = quoted_match.group(1)
                else:
                    title = f"Lecture by {speaker_name}"
            else:
                title = f"Lecture by {speaker_name}"
        
        # Create CORRECT video URL (this was the main issue)
        video_filename = href.split('/')[-1].replace('.html', '.mp4')
        video_url = f"https://videos.birs.ca/{year}/{workshop_code}/{video_filename}"
        
        # Create comprehensive video metadata
        video_data = {
            "id": f"birs_{workshop_code}_{filename_match.group(1) if filename_match else f'vid_{index:03d}'}",
            "title": title,
            "speaker": {
                "name": speaker_name,
                "affiliation": "TBD",
                "bio_url": ""
            },
            "workshop": {
                "code": workshop_code,
                "title": extract_workshop_title(workshop_url),
                "type": "5-day",
                "year": year,
                "dates": f"Workshop {year}"
            },
            "content": {
                "abstract": title,
                "topics": extract_topics_from_title(title),
                "field": extract_field_from_title(title),
                "difficulty": "research",
                "duration_minutes": 60,
                "language": "en"
            },
            "files": {
                "video_url": video_url,
                "video_size_mb": 0,
                "thumbnail_url": "",
                "transcript_url": "",
                "slides_url": ""
            },
            "metadata": {
                "recorded_date": recorded_date,
                "upload_date": recorded_date,
                "quality": "720p",
                "view_count": 0,
                "featured": index < 3
            }
        }
        
        return video_data
        
    except Exception as e:
        print(f"  Error extracting video metadata: {e}")
        return None

def extract_workshop_title(workshop_url):
    """Extract workshop title from the main workshop page"""
    try:
        main_url = workshop_url.replace('/videos', '')
        response = requests.get(main_url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        title_element = soup.find('h1')
        if title_element:
            title = title_element.get_text().strip()
            title = re.sub(r'^\d{2}w\d{4}:\s*', '', title)  # Remove workshop code prefix
            return title
    except:
        pass
    
    # Fallback
    workshop_match = re.search(r'/(\d{2}w\d{4})/', workshop_url)
    if workshop_match:
        return f"Workshop {workshop_match.group(1)}"
    
    return "Unknown Workshop"

def extract_topics_from_title(title):
    """Extract relevant mathematical topics from the title"""
    math_keywords = [
        "analysis", "algebra", "geometry", "topology", "statistics",
        "probability", "optimization", "differential", "integral",
        "quantum", "machine learning", "data science", "computational",
        "wave", "fluid", "dynamics", "stochastic", "numerical",
        "spectral", "manifold", "operator", "equation"
    ]
    
    title_lower = title.lower()
    topics = [keyword for keyword in math_keywords if keyword in title_lower]
    return topics[:3]

def extract_field_from_title(title):
    """Classify the mathematical field based on title keywords"""
    title_lower = title.lower()
    
    field_keywords = {
        "Analysis": ["analysis", "differential", "integral", "functional", "harmonic", "spectral", "operator"],
        "Geometry": ["geometry", "geometric", "manifold", "topology", "topological"],
        "Statistics": ["statistics", "statistical", "probability", "stochastic", "inference"],
        "Computer Science": ["algorithm", "computational", "machine learning", "data science", "optimization"],
        "Physics": ["quantum", "physics", "wave", "particle", "fluid", "dynamics"],
        "Number Theory": ["number theory", "arithmetic", "prime", "algebraic number"],
        "Algebra": ["algebra", "algebraic", "group", "ring", "field", "representation"]
    }
    
    for field, keywords in field_keywords.items():
        if any(keyword in title_lower for keyword in keywords):
            return field
    
    return "Mathematics"

def main():
    """Main execution function"""
    print("Complete BIRS Video Data Extractor")
    print("=" * 40)
    
    # Workshop URLs to process
    workshop_urls = [
        "https://www.birs.ca/events/2024/5-day-workshops/24w5207/videos",
        "https://www.birs.ca/events/2024/5-day-workshops/24w5263/videos",
        "https://www.birs.ca/events/2024/5-day-workshops/24w5314/videos",
        "https://www.birs.ca/events/2024/5-day-workshops/24w5283/videos",
        "https://www.birs.ca/events/2024/5-day-workshops/24w5284/videos"
    ]
    
    all_videos = []
    
    for url in workshop_urls:
        print(f"\nProcessing: {url}")
        videos = extract_workshop_videos(url)
        all_videos.extend(videos)
        print(f"  Found {len(videos)} videos")
        time.sleep(1)  # Be respectful to the server
    
    # Save the complete, corrected data
    output_file = "complete_birs_videos.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_videos, f, indent=2, ensure_ascii=False)
    
    print(f"\nSuccessfully extracted {len(all_videos)} videos")
    print(f"Data saved to: {output_file}")
    
    # Display sample results
    print("\nSample videos:")
    print("-" * 60)
    for i, video in enumerate(all_videos[:3]):
        print(f"{i+1}. {video['title']}")
        print(f"   Speaker: {video['speaker']['name']}")
        print(f"   URL: {video['files']['video_url']}")
        print(f"   Field: {video['content']['field']}")
        print(f"   Workshop: {video['workshop']['code']}")
        print()
    
    # Verify URL format
    print("URL Verification:")
    sample_url = all_videos[0]['files']['video_url'] if all_videos else ""
    expected_pattern = r"https://videos\.birs\.ca/\d{4}/\d{2}w\d{4}/\d{12}-[^/]+\.mp4"
    if re.match(expected_pattern, sample_url):
        print("Video URLs are correctly formatted")
    else:
        print("Video URL format may be incorrect")
        print(f"   Sample: {sample_url}")

if __name__ == "__main__":
    main()
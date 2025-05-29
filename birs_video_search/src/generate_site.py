import os
import json
import requests
from bs4 import BeautifulSoup
import re # For parsing dates and codes

# --- Constants ---
VIDEO_DATA_OUTPUT_PATH = 'static/videos.json' # Relative to project_root
# Example BIRS workshop URL (replace with a list or dynamic source later)
BIRS_WORKSHOP_URLS = [
    'https://www.birs.ca/events/2023/5-day-workshops/23w5001/schedule', # Focus on this one
    # 'https://www.birs.ca/events/2024/5-day-workshops/24w5007' # Comment out for now
]

# --- Helper Functions ---
def find_potential_video_links(soup, workshop_url_base):
    """Finds and prints potential video links on the page for debugging."""
    found_links = []
    for link_tag in soup.select('a[href]'):
        href = link_tag.get('href', '')
        link_text = link_tag.get_text(strip=True).lower()
        
        is_video_link = False
        if ".mp4" in href:
            is_video_link = True
        elif "video.birs.ca" in href or "play.birs.ca" in href:
            is_video_link = True
        elif any(keyword in link_text for keyword in ["video", "mp4", "recording", "watch", "play"]):
            is_video_link = True

        if is_video_link:
            # Resolve relative URLs
            if href.startswith('//'): # Protocol relative
                 href = f"https:{href}"
            elif href.startswith('/'):
                href = f"https://www.birs.ca{href}"
            elif not href.startswith('http'):
                href = f"{workshop_url_base}/{href}"
            
            found_links.append(href)
            
    if found_links:
        print(f"  DEBUG: Found potential video links:")
        for link in found_links:
            print(f"    - {link}")
    else:
        print(f"  DEBUG: No potential video links found using common patterns.")
    return found_links


def generate_video_id(index):
    """Generates a unique ID for each video."""
    return f"birs_lec_{index:03d}"

def extract_text_or_default(element, default="N/A"):
    """Extracts text from a BeautifulSoup element or returns a default."""
    return element.get_text(strip=True) if element else default

# --- Data Scraping Logic ---
def scrape_single_workshop(workshop_url, video_id_counter_start):
    """
    Scrapes video information from a single BIRS workshop page.
    Returns a list of video data dictionaries and the next video_id_counter.
    """
    videos_data = []
    video_id_counter = video_id_counter_start
    print(f"Scraping workshop: {workshop_url}")
    try:
        response = requests.get(workshop_url, timeout=20) # Increased timeout
        response.raise_for_status()  # Raise an exception for HTTP errors
        soup = BeautifulSoup(response.content, 'html.parser')

        workshop_url_base = workshop_url.rsplit('/', 1)[0]
        find_potential_video_links(soup, workshop_url_base) # DEBUGGING STEP

        # Extract workshop details
        workshop_title_tag = soup.select_one("h1.page-title, h2.node-title") # Added h2.node-title as fallback
        workshop_title = extract_text_or_default(workshop_title_tag)
        
        # Try to extract workshop code and year from URL or title
        workshop_code_match = re.search(r'(\d{2}w\d{4})', workshop_url)
        workshop_code = workshop_code_match.group(1) if workshop_code_match else "N/A"
        
        year_match = re.search(r'/(\d{4})/', workshop_url)
        workshop_year = int(year_match.group(1)) if year_match else "N/A"

        workshop_dates_tag = soup.select_one(".event-dates") # This selector might need adjustment
        workshop_dates = extract_text_or_default(workshop_dates_tag)
        if workshop_dates == "N/A" and workshop_title_tag: # Fallback for dates
             date_sibling = workshop_title_tag.find_next_sibling('div')
             if date_sibling:
                 workshop_dates = extract_text_or_default(date_sibling.select_one("p"))


        # Find video entries (this is highly dependent on BIRS page structure)
        # Common pattern: videos are often in 'div's with class 'streamed-video-event' or similar
        # Or listed in tables. We need to inspect the actual BIRS page structure.
        # For this example, let's assume a structure. This will likely need refinement.
        
        # Attempt to find video entries. Selectors will need to be verified.
        # Look for divs that seem to contain video information.
        # More specific selectors based on observed BIRS structure.
        # Primary target: Drupal views for event schedules / talk lists.
        video_blocks = soup.select('div.view-id-event_schedule_and_materials div.views-row')
        if not video_blocks:
             # Fallback: look for a common container for talks, then individual talk items
            event_talks_container = soup.select_one('#event-talks-view-container')
            if not event_talks_container:
                event_talks_container = soup.select_one('#event-schedule')
            if not event_talks_container:
                event_talks_container = soup.select_one('.event-schedule-view')
            
            if event_talks_container:
                video_blocks = event_talks_container.select('.event-talk-item, .talk-details, tr') # Common classes for talk items or table rows

        if not video_blocks:
             # Wider search for tables that might contain schedules
            tables = soup.select('table.event-schedule, table.schedule, table.views-table')
            for table in tables:
                rows = table.select('tbody tr')
                if rows: # Check if any row looks like it has video info
                    header_texts = [th.get_text().lower() for th in table.select('thead th')]
                    if any(hdr in ['video', 'talk', 'speaker'] for hdr in header_texts):
                         video_blocks.extend(rows)
            if not video_blocks: # If still no blocks, try the original broader selectors as a last resort
                 video_blocks = soup.select('.view-content .views-row, div.event-schedule table tbody tr')


        for entry in video_blocks:
            video_title = "N/A"
            speaker_name = "N/A"
            speaker_affiliation = "N/A" # Placeholder
            abstract = "N/A" # Placeholder
            video_url_path = None
            
            # Attempt to find title, speaker, video link within the block
            # Refined selectors:
            title_tag = entry.select_one('.talk-title a, .event-talk-title a, .field-name-node-title a, h4 a, h3 a')
            if not title_tag: # If title is not a link, try to get it from common strong/b tags or specific divs
                title_tag = entry.select_one('.talk-title, .event-talk-title, .field-name-node-title, strong, b')

            video_title = extract_text_or_default(title_tag)

            speaker_tag = entry.select_one('.talk-speaker a, .field-name-field-event-speakers a, .event-speaker a, .speaker-name a')
            if not speaker_tag: # If speaker is not a link
                 speaker_tag = entry.select_one('.talk-speaker, .field-name-field-event-speakers, .event-speaker, .speaker-name')
            
            speaker_name = extract_text_or_default(speaker_tag)
            # Clean up speaker name if it contains "Speaker(s):" prefix
            if speaker_name.lower().startswith("speaker(s):"):
                speaker_name = speaker_name[len("speaker(s):"):].strip()


            # Video link: Look for specific text, or .mp4 extension, or links from video hosting domains
            video_link_tags = entry.select('a[href]')
            for link_tag in video_link_tags:
                link_text = link_tag.get_text(strip=True).lower()
                href = link_tag['href']
                if any(keyword in link_text for keyword in ["video", "mp4", "recording", "view video", "watch video"]) or \
                   ".mp4" in href or "video.birs.ca" in href or "play.birs.ca" in href:
                    video_url_path = href
                    break # Take the first likely video link

            if not video_url_path and title_tag and 'href' in title_tag.attrs: # Fallback: if title is a link, it might be the video
                 href = title_tag['href']
                 if ".mp4" in href or "video.birs.ca" in href or "play.birs.ca" in href or "/videos/" in href : # Check if it looks like a video link
                      video_url_path = href
            
            # If video_url_path is relative, make it absolute
            if video_url_path and not video_url_path.startswith('http'):
                if video_url_path.startswith('/'):
                    video_url_path = f"https://www.birs.ca{video_url_path}"
                else: # very relative path, assume it's from the current workshop_url's directory
                    base_workshop_url = workshop_url.rsplit('/', 1)[0]
                    video_url_path = f"{base_workshop_url}/{video_url_path}"


            # Abstract: Try to find a div/p with class 'abstract', 'talk-abstract', or 'field-name-field-abstract'
            abstract_tag = entry.select_one('.abstract, .talk-abstract, .field-name-field-abstract .field-item, .node-abstract') # More specific
            if abstract_tag:
                # Handle cases where abstract is hidden in a sub-element or needs collapsing (basic extraction for now)
                abstract_text_elements = abstract_tag.select('p')
                if abstract_text_elements:
                    abstract = " ".join([p.get_text(strip=True) for p in abstract_text_elements])
                else:
                    abstract = extract_text_or_default(abstract_tag)
            if not abstract or abstract == "N/A": # Fallback to looking for paragraphs after title/speaker if no specific abstract class found
                # This is a bit fragile, assumes abstract follows other details.
                current_element = title_tag if title_tag else (speaker_tag if speaker_tag else None)
                if current_element:
                    # Look for a 'p' sibling that isn't clearly something else
                    for sibling in current_element.find_next_siblings():
                        if sibling.name == 'p' and not sibling.find('a', href=True): # Avoid paragraphs that are just links
                            potential_abstract = extract_text_or_default(sibling)
                            # Basic check to avoid grabbing short/irrelevant paragraphs
                            if len(potential_abstract) > 50: # Arbitrary length check
                                abstract = potential_abstract
                                break


            # Field & Topics: Derive from workshop or use placeholders.
            field = workshop_title # Simplified
            topics = [topic.strip() for topic in workshop_title.replace("and", ",").split(",") if topic.strip()] if workshop_title != "N/A" else [] # Slightly better topic split

            if video_url_path and video_title != "N/A" and speaker_name != "N/A": # Only add if we found a video link, title, and speaker
                videos_data.append({
                    "id": generate_video_id(video_id_counter),
                    "title": video_title,
                    "speaker": {"name": speaker_name, "affiliation": speaker_affiliation},
                    "workshop": {
                        "code": workshop_code,
                        "title": workshop_title,
                        "year": workshop_year,
                        "dates": workshop_dates
                    },
                    "content": {
                        "abstract": abstract,
                        "topics": topics,
                        "field": field
                    },
                    "files": {"video_url": video_url_path}
                })
                video_id_counter += 1
            else:
                print(f"  Skipping entry, no video URL or title found for: {extract_text_or_default(title_tag, 'Unknown Title')}")


        if not video_blocks:
            print(f"  No video blocks found using selectors for {workshop_url}. Page structure might have changed.")

    except requests.RequestException as e:
        print(f"Error fetching workshop page {workshop_url}: {e}")
    except Exception as e:
        print(f"Error parsing workshop page {workshop_url}: {e}")
    
    return videos_data, video_id_counter


def scrape_birs_workshops(workshop_urls):
    """
    Scrapes video information from a list of BIRS workshop URLs.
    """
    all_videos_data = []
    current_video_id_counter = 1
    for url in workshop_urls:
        workshop_videos, next_id_counter = scrape_single_workshop(url, current_video_id_counter)
        all_videos_data.extend(workshop_videos)
        current_video_id_counter = next_id_counter
    return all_videos_data


def generate_json_output(videos_data, output_file_path):
    """
    Writes the scraped video data to a JSON file.
    """
    try:
        with open(output_file_path, 'w') as f:
            json.dump(videos_data, f, indent=2)
        print(f"Successfully generated JSON data at {output_file_path}")
    except IOError as e:
        print(f"Error writing JSON to {output_file_path}: {e}")


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir) # This is birs_video_search/
    
    # --- Scrape Data and Generate JSON ---
    print("Starting BIRS workshop data scraping...")
    scraped_videos = scrape_birs_workshops(BIRS_WORKSHOP_URLS)
    
    json_output_full_path = os.path.join(project_root, VIDEO_DATA_OUTPUT_PATH)
    os.makedirs(os.path.dirname(json_output_full_path), exist_ok=True) # Ensure static dir exists
    generate_json_output(scraped_videos, json_output_full_path)
    print("Data scraping and JSON generation complete.")
    # --- End Scrape Data ---

    index_template_path = os.path.join(project_root, 'templates', 'index.html.template')
    output_html_path = os.path.join(project_root, 'index.html') # Output to project root

    try:
        with open(index_template_path, 'r') as f:
            index_template_content = f.read()
        
        # Directly write the template content.
        # JavaScript will handle the video card rendering using the generated videos.json.
        final_html = index_template_content 

        with open(output_html_path, 'w') as f:
            f.write(final_html)
        
        print(f"Base index.html generated successfully at {output_html_path}")
    except FileNotFoundError:
        print(f"Error: Template file not found at {index_template_path}")
    except Exception as e:
        print(f"Error generating index.html: {e}")


if __name__ == '__main__':
    main()

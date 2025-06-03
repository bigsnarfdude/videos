function cleanAbstractText(abstract) {
        if (!abstract) return "No summary available";
        
        let cleaned = abstract;
        
        // Very aggressive cleaning - remove everything from the start until we find actual content
        
        // Remove everything up to and including "## **Core Mathematical Content**" section
        cleaned = cleaned.replace(/^[\s\S]*?##\s*\*\*Core Mathematical Content\*\*[\s\S]*?(?=##\s*\*\*(?!Core|Primary|Subfields|Level)|\n\n[A-Z])/g, '');
        
        // If that didn't work, try removing just the metadata lines
        if (cleaned.includes('**Primary Field:**') || cleaned.includes('**Core Mathematical Content**')) {
            // Start over and be more aggressive
            cleaned = abstract;
            
            // Split by sections and find the first one that's not metadata
            const sections = cleaned.split(/##\s*\*\*/);
            for (let section of sections) {
                section = section.trim();
                if (section.length > 100 && 
                    !section.startsWith('Core Mathematical Content') &&
                    !section.startsWith('Primary Field') &&
                    !section.startsWith('Subfields') &&
                    !section.startsWith('Key Mathematical Concepts') &&
                    section.includes('.')) {
                    cleaned = section;
                    break;
                }
            }
        }
        
        // If we still have metadata, try finding content after "This lecture" or similar
        if (cleaned.includes('**Primary Field:**')) {
            const match = cleaned.match(/(This (?:lecture|talk|presentation)[\s\S]{50,}?)(?=\*\*|##|$)/i);
            if (match) {
                cleaned = match[1].trim();
            } else {
                // Last resort - just find any substantial text that doesn't start with formatting
                const paragraphs = cleaned.split(/\n+/);
                for (let para of paragraphs) {
                    para = para.trim();
                    if (para.length > 100 && 
                        !para.startsWith('**') && 
                        !para.startsWith('##') &&
                        !para.includes('Primary Field:') &&
                        para.includes(' ')) {
                        cleaned = para;
                        break;
                    }
                }
            }
        }
        
        // Final cleanup
        cleaned = cleaned.replace(/\*\*/g, '');  // Remove all ** markers
        cleaned = cleaned.replace(/^#+\s*/gm, '');  // Remove ## headers
        cleaned = cleaned.trim();
        
        // If we still don't have good content, provide a fallback
        if (cleaned.length < 50 || cleaned.includes('Primary Field:')) {
            return "Advanced mathematical research lecture. Click 'View Summary' for detailed content analysis.";
        }
        
        // Truncate at sentence boundary
        if (cleaned.length > 280) {
            const lastPeriod = cleaned.lastIndexOf('.', 280);
            if (lastPeriod > 100) {
                cleaned = cleaned.substring(0, lastPeriod + 1);
            } else {
                const lastSpace = cleaned.lastIndexOf(' ', 280);
                cleaned = cleaned.substring(0, lastSpace) + "...";
            }
        }
        
        return cleaned;
    }document.addEventListener("DOMContentLoaded", () => {
    const videoGrid = document.getElementById("video-grid");
    const searchBar = document.getElementById("search-bar");
    const yearFilter = document.getElementById("year-filter");
    const fieldFilter = document.getElementById("field-filter");
    const contentTypeFilter = document.getElementById("content-type-filter") || createContentTypeFilter();
    const searchResultsCountDisplay = document.getElementById("search-results-count");
    const clearFiltersButton = document.getElementById("clear-all-filters-button");
    const activeFiltersDisplay = document.getElementById("active-filters-display");
    
    let allVideos = [];
    let normalizedVideos = [];

    // Add new filter controls if they don't exist
    function createContentTypeFilter() {
        const controls = document.getElementById("search-filter-controls");
        const select = document.createElement("select");
        select.id = "content-type-filter";
        select.innerHTML = `
            <option value="">All Videos</option>
            <option value="enhanced">Enhanced (AI Summary + Transcript)</option>
        `;
        controls.appendChild(select);
        return select;
    }

    // Normalize video data for consistent handling
    function normalizeVideoData(video) {
        // Detect enhanced format vs legacy format
        if (video.transcript && video.summary_text) {
            // Enhanced format - convert to standard structure
            return {
                id: video.id || "",
                title: video.suggested_title || video.filename || "Untitled",
                speaker: {
                    name: video.speaker || "Unknown Speaker",
                    affiliation: "Unknown Institution"
                },
                workshop: {
                    code: extractWorkshopCode(video.id || ""),
                    title: extractWorkshopInfo(video.date || ""),
                    year: extractYearFromDate(video.date || ""),
                    dates: video.date || ""
                },
                content: {
                    abstract: cleanAbstractText(video.summary || "No summary available"),
                    topics: video.metadata?.subfields || [],
                    field: video.metadata?.primary_field || "Mathematics",
                    difficulty: video.metadata?.level || "Unknown",
                    transcript: video.transcript || "",
                    summary_text: video.summary_text || "",
                    concepts: video.metadata?.concepts || [],
                    theorems: video.metadata?.theorems || []
                },
                files: {
                    video_url: video.video_url || "",
                    video_size_mb: parseFileSize(video.file_size || "0M"),
                    filename: video.filename || ""
                },
                metadata: {
                    recorded_date: video.date || "",
                    processed: video.processed || false,
                    processing_stats: video.processing_stats || {},
                    model_used: video.model_used || ""
                },
                enhanced: {
                    has_transcript: !!video.transcript,
                    has_summary: !!video.summary_text,
                    compression_ratio: video.processing_stats?.compression_ratio || 0,
                    concepts_count: (video.metadata?.concepts || []).length,
                    subfields_count: (video.metadata?.subfields || []).length
                }
            };
        } else {
            // Legacy format - add enhanced flags
            return {
                ...video,
                enhanced: {
                    has_transcript: false,
                    has_summary: false,
                    compression_ratio: 0,
                    concepts_count: 0,
                    subfields_count: 0
                }
            };
        }
    }

    function extractWorkshopCode(videoId) {
        const match = videoId.match(/(\d{6})/);
        return match ? match[1] : "Unknown";
    }

    function extractYearFromDate(dateStr) {
        if (dateStr) {
            try {
                return parseInt(dateStr.substring(0, 4));
            } catch (e) {
                return 2020;
            }
        }
        return 2020;
    }

    function extractWorkshopInfo(dateStr) {
        const year = extractYearFromDate(dateStr);
        return `BIRS Workshop ${year}`;
    }

    function parseFileSize(sizeStr) {
        if (!sizeStr) return 0;
        const upper = sizeStr.toUpperCase();
        if (upper.endsWith('M')) {
            return parseInt(parseFloat(upper.slice(0, -1)));
        } else if (upper.endsWith('G')) {
            return parseInt(parseFloat(upper.slice(0, -1)) * 1024);
        } else if (upper.endsWith('K')) {
            return parseInt(parseFloat(upper.slice(0, -1)) / 1024);
        }
        return 0;
    }

    async function loadVideos() {
        try {
            console.log("Starting to load videos...");
            const response = await fetch("static/videos.json");
            allVideos = await response.json();
            
            console.log("Raw videos loaded:", allVideos.length);
            
            // Handle both single video object and array
            if (!Array.isArray(allVideos)) {
                allVideos = [allVideos];
            }
            
            // Normalize all video data
            normalizedVideos = allVideos.map(normalizeVideoData);
            
            console.log("Videos normalized:", normalizedVideos.length);
            console.log("First video abstract sample:", normalizedVideos[0]?.content?.abstract?.substring(0, 200));
            console.log("Enhanced videos:", normalizedVideos.filter(v => v.enhanced.has_summary).length);
            
            populateFilters();
            showAllVideos();
        } catch (error) {
            console.error("Error loading videos:", error);
            videoGrid.innerHTML = "<p>Error loading videos: " + error.message + "</p>";
        }
    }

    function populateFilters() {
        // Populate years
        const years = [...new Set(normalizedVideos.map(v => v.workshop.year))].sort((a,b) => b-a);
        yearFilter.innerHTML = '<option value="">All Years</option>';
        years.forEach(year => {
            const option = document.createElement("option");
            option.value = year;
            option.textContent = year;
            yearFilter.appendChild(option);
        });

        // Populate fields
        const fields = [...new Set(normalizedVideos.map(v => v.content.field))].sort();
        fieldFilter.innerHTML = '<option value="">All Fields</option>';
        fields.forEach(field => {
            const option = document.createElement("option");
            option.value = field;
            option.textContent = field;
            fieldFilter.appendChild(option);
        });
    }

    function showVideos(videos) {
        videoGrid.innerHTML = "";
        
        if (searchResultsCountDisplay) {
            searchResultsCountDisplay.textContent = `Showing ${videos.length} of ${normalizedVideos.length} videos`;
        }

        videos.forEach(video => {
            const card = document.createElement("div");
            card.className = "video-card";
            
            // Enhanced card with more information
            const enhancedBadges = [];
            if (video.enhanced.has_transcript) enhancedBadges.push('<span class="badge transcript-badge">Transcript</span>');
            if (video.enhanced.has_summary) enhancedBadges.push('<span class="badge summary-badge">AI Summary</span>');
            
            const conceptsPreview = video.content.concepts.slice(0, 3);
            const conceptsText = conceptsPreview.length > 0 ? 
                `<p><strong>Key Concepts:</strong> ${conceptsPreview.join(", ")}${video.content.concepts.length > 3 ? "..." : ""}</p>` : "";
            
            // Truncate abstract for display
            const abstractPreview = video.content.abstract.length > 200 ? 
                video.content.abstract.substring(0, 200) + "..." : video.content.abstract;
            
            card.innerHTML = `
                <div class="card-header">
                    <h3>${video.title}</h3>
                    <div class="badges">${enhancedBadges.join("")}</div>
                </div>
                <p><strong>Speaker:</strong> ${video.speaker.name}</p>
                <p><strong>Year:</strong> ${video.workshop.year} | <strong>Field:</strong> ${video.content.field}</p>
                ${video.content.difficulty !== "Unknown" ? `<p><strong>Level:</strong> ${video.content.difficulty}</p>` : ""}
                ${conceptsText}
                <p class="abstract"><strong>Abstract:</strong> ${abstractPreview}</p>
                <div class="card-actions">
                    <a href="${video.files.video_url}" target="_blank" class="btn-primary">Watch Video</a>
                    ${video.enhanced.has_transcript ? '<button class="btn-secondary" onclick="showTranscript(\'' + video.id + '\')">View Transcript</button>' : ''}
                    ${video.enhanced.has_summary ? '<button class="btn-secondary" onclick="showSummary(\'' + video.id + '\')">View Summary</button>' : ''}
                </div>
            `;
            videoGrid.appendChild(card);
        });
    }

    function showAllVideos() {
        showVideos(normalizedVideos);
        updateActiveFilters();
    }

    // Enhanced search function
    function performSearch(videos, searchTerm) {
        if (!searchTerm) return videos;
        
        const term = searchTerm.toLowerCase();
        return videos.filter(video => {
            // Search in multiple fields with different weights
            const titleMatch = video.title.toLowerCase().includes(term);
            const speakerMatch = video.speaker.name.toLowerCase().includes(term);
            const fieldMatch = video.content.field.toLowerCase().includes(term);
            const abstractMatch = video.content.abstract.toLowerCase().includes(term);
            const transcriptMatch = video.content.transcript.toLowerCase().includes(term);
            const summaryMatch = video.content.summary_text.toLowerCase().includes(term);
            const conceptsMatch = video.content.concepts.some(concept => 
                concept.toLowerCase().includes(term));
            const topicsMatch = video.content.topics.some(topic => 
                topic.toLowerCase().includes(term));
            
            return titleMatch || speakerMatch || fieldMatch || abstractMatch || 
                   transcriptMatch || summaryMatch || conceptsMatch || topicsMatch;
        });
    }

    function applyFilters() {
        const searchTerm = searchBar.value.toLowerCase().trim();
        const yearValue = yearFilter.value;
        const fieldValue = fieldFilter.value;
        const contentTypeValue = contentTypeFilter.value;

        let filtered = normalizedVideos;

        // Apply search
        if (searchTerm) {
            filtered = performSearch(filtered, searchTerm);
        }

        // Apply filters
        filtered = filtered.filter(video => {
            const matchesYear = !yearValue || video.workshop.year == yearValue;
            const matchesField = !fieldValue || video.content.field == fieldValue;
            
            let matchesContentType = true;
            if (contentTypeValue === "enhanced") {
                matchesContentType = video.enhanced.has_transcript && video.enhanced.has_summary;
            }
            
            return matchesYear && matchesField && matchesContentType;
        });

        showVideos(filtered);
        updateActiveFilters();
    }

    function updateActiveFilters() {
        const activeFilters = [];
        
        if (searchBar.value.trim()) {
            activeFilters.push({
                type: "search",
                label: `Search: "${searchBar.value.trim()}"`,
                clear: () => { searchBar.value = ""; applyFilters(); }
            });
        }
        
        if (yearFilter.value) {
            activeFilters.push({
                type: "year",
                label: `Year: ${yearFilter.value}`,
                clear: () => { yearFilter.value = ""; applyFilters(); }
            });
        }
        
        if (fieldFilter.value) {
            activeFilters.push({
                type: "field",
                label: `Field: ${fieldFilter.value}`,
                clear: () => { fieldFilter.value = ""; applyFilters(); }
            });
        }
        
        if (contentTypeFilter.value) {
            activeFilters.push({
                type: "content-type",
                label: "Enhanced Videos Only",
                clear: () => { contentTypeFilter.value = ""; applyFilters(); }
            });
        }

        // Update active filters display
        activeFiltersDisplay.innerHTML = "";
        activeFilters.forEach(filter => {
            const indicator = document.createElement("div");
            indicator.className = "active-filter-indicator";
            indicator.innerHTML = `
                ${filter.label}
                <button class="remove-filter-button" onclick="(${filter.clear.toString()})()">×</button>
            `;
            activeFiltersDisplay.appendChild(indicator);
        });
    }

    function clearAllFilters() {
        searchBar.value = "";
        yearFilter.value = "";
        fieldFilter.value = "";
        contentTypeFilter.value = "";
        applyFilters();
    }

    // Global functions for modal displays
    window.showTranscript = function(videoId) {
        const video = normalizedVideos.find(v => v.id === videoId);
        if (video && video.content.transcript) {
            const modal = document.createElement("div");
            modal.className = "modal";
            modal.innerHTML = `
                <div class="modal-content">
                    <div class="modal-header">
                        <h2>Transcript: ${video.title}</h2>
                        <span class="close" onclick="this.parentElement.parentElement.parentElement.remove()">&times;</span>
                    </div>
                    <div class="modal-body">
                        <pre class="transcript-text">${video.content.transcript}</pre>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }
    };

    window.showSummary = function(videoId) {
        const video = normalizedVideos.find(v => v.id === videoId);
        if (video && video.content.summary_text) {
            const modal = document.createElement("div");
            modal.className = "modal";
            
            // Format the summary text properly
            const formattedSummary = formatSummaryText(video.content.summary_text);
            
            modal.innerHTML = `
                <div class="modal-content">
                    <div class="modal-header">
                        <h2>AI Summary: ${video.title}</h2>
                        <span class="close" onclick="this.parentElement.parentElement.parentElement.remove()">&times;</span>
                    </div>
                    <div class="modal-body">
                        <div class="summary-text">${formattedSummary}</div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }
    };

    function formatSummaryText(summaryText) {
        if (!summaryText) return "No summary available";
        
        let formatted = summaryText;
        
        // Remove the redundant header section with equals signs
        formatted = formatted.replace(/^MATHEMATICS LECTURE SUMMARY\s*=+.*?Generated:\s*\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}/s, '');
        
        // Remove any remaining header metadata lines
        formatted = formatted.replace(/^Title:.*$/gm, '');
        formatted = formatted.replace(/^Original File:.*$/gm, '');
        formatted = formatted.replace(/^Generated:.*$/gm, '');
        
        // Clean up multiple newlines at the start
        formatted = formatted.replace(/^\s*\n+/, '');
        
        // Convert markdown headers to HTML
        formatted = formatted.replace(/^## (.*$)/gim, '<h2>$1</h2>');
        formatted = formatted.replace(/^### (.*$)/gim, '<h3>$1</h3>');
        formatted = formatted.replace(/^#### (.*$)/gim, '<h4>$1</h4>');
        
        // Convert bold text
        formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        // Convert bullet points
        formatted = formatted.replace(/^- (.*$)/gim, '<li>$1</li>');
        formatted = formatted.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
        
        // Handle long text blocks - add paragraph breaks at double newlines
        formatted = formatted.replace(/\n\n+/g, '</p><p>');
        formatted = '<p>' + formatted + '</p>';
        
        // Clean up empty paragraphs
        formatted = formatted.replace(/<p><\/p>/g, '');
        formatted = formatted.replace(/<p>\s*<\/p>/g, '');
        
        // Handle special sections that start with "**"
        formatted = formatted.replace(/\*\*([^*]+):\*\*/g, '<h4>$1:</h4>');
        
        return formatted;
    }

    // Event listeners
    searchBar.addEventListener('input', applyFilters);
    yearFilter.addEventListener('change', applyFilters);
    fieldFilter.addEventListener('change', applyFilters);
    contentTypeFilter.addEventListener('change', applyFilters);
    clearFiltersButton.addEventListener('click', clearAllFilters);

    // Initialize
    loadVideos();
});
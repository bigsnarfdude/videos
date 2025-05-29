document.addEventListener('DOMContentLoaded', () => {
    const videoGrid = document.getElementById('video-grid');
    const searchBar = document.getElementById('search-bar');
    const yearFilter = document.getElementById('year-filter');
    const fieldFilter = document.getElementById('field-filter');
    const activeFiltersDisplay = document.getElementById('active-filters-display');
    const clearAllFiltersButton = document.getElementById('clear-all-filters-button');
    const searchResultsCountDisplay = document.getElementById('search-results-count');
    const loadingIndicator = document.getElementById('loading-indicator'); // Added this
    let allVideos = [];

    function updateActiveFiltersDisplay() {
        activeFiltersDisplay.innerHTML = ''; // Clear current display

        const createFilterIndicator = (type, value, clearFunction) => {
            const indicator = document.createElement('span');
            indicator.className = 'active-filter-indicator';
            indicator.textContent = `${type}: ${value} `;
            
            const removeButton = document.createElement('button');
            removeButton.className = 'remove-filter-button';
            removeButton.textContent = 'x';
            removeButton.setAttribute('aria-label', `Remove ${type} filter ${value}`);
            removeButton.onclick = () => {
                clearFunction();
                applyFiltersAndSearch();
            };
            
            indicator.appendChild(removeButton);
            activeFiltersDisplay.appendChild(indicator);
        };

        const searchTerm = searchBar.value.trim();
        if (searchTerm) {
            createFilterIndicator('Search', searchTerm, () => { searchBar.value = ''; });
        }
        if (yearFilter.value) {
            createFilterIndicator('Year', yearFilter.options[yearFilter.selectedIndex].text, () => { yearFilter.value = ''; });
        }
        if (fieldFilter.value) {
            createFilterIndicator('Field', fieldFilter.options[fieldFilter.selectedIndex].text, () => { fieldFilter.value = ''; });
        }
    }

    clearAllFiltersButton.addEventListener('click', () => {
        searchBar.value = '';
        yearFilter.value = '';
        fieldFilter.value = '';
        applyFiltersAndSearch();
    });

    async function fetchVideos() {
        if (loadingIndicator) loadingIndicator.style.display = 'block';
        videoGrid.innerHTML = ''; // Clear previous content

        try {
            const response = await fetch('static/videos.json');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            allVideos = await response.json();
            
            if (!allVideos || allVideos.length === 0) {
                videoGrid.innerHTML = '<p>No videos available at the moment. Please check back later.</p>';
                searchResultsCountDisplay.textContent = 'No videos found.';
                // Still try to populate filters, they might be empty but function should handle it.
                // And applyFiltersAndSearch will also correctly show empty state.
            }
            populateFilters(); // Populate filters even if allVideos is empty initially
            applyFiltersAndSearch(); // This will call renderVideoCards and update counts

        } catch (error) {
            console.error("Could not fetch videos:", error);
            videoGrid.innerHTML = '<p>Error loading videos. Please try again later.</p>';
            searchResultsCountDisplay.textContent = 'Error loading videos.';
        } finally {
            if (loadingIndicator) loadingIndicator.style.display = 'none';
        }
    }

    function populateFilters() {
        const years = [...new Set(allVideos.map(video => video.workshop.year))].sort((a, b) => b - a);
        const fields = [...new Set(allVideos.map(video => video.content.field))].sort();

        years.forEach(year => {
            const option = document.createElement('option');
            option.value = year;
            option.textContent = year;
            yearFilter.appendChild(option);
        });

        fields.forEach(field => {
            const option = document.createElement('option');
            option.value = field;
            option.textContent = field;
            fieldFilter.appendChild(option);
        });
    }

    function renderVideoCards(videosToRender) {
        videoGrid.innerHTML = ''; // Clear existing videos

        const searchTerm = searchBar.value.trim();
        const selectedYear = yearFilter.value;
        const selectedField = fieldFilter.value;

        if (videosToRender.length === 0) {
            if (allVideos.length === 0) { // Initial load and videos.json was empty or failed to parse
                videoGrid.innerHTML = '<p>No videos available at the moment. Please check back later.</p>';
                searchResultsCountDisplay.textContent = 'No videos found.';
            } else if (searchTerm || selectedYear || selectedField) {
                let filterDetails = [];
                if (searchTerm) filterDetails.push(`text: "${searchTerm}"`);
                if (selectedYear) filterDetails.push(`year: "${yearFilter.options[yearFilter.selectedIndex].text}"`);
                if (selectedField) filterDetails.push(`field: "${fieldFilter.options[fieldFilter.selectedIndex].text}"`);
                videoGrid.innerHTML = `<p>No videos found matching your criteria: ${filterDetails.join(', ')}. Try a different search or clear some filters.</p>`;
                searchResultsCountDisplay.textContent = 'Found 0 videos matching your criteria.';
            } else { // No filters active, but videosToRender is empty (should not happen if allVideos has items)
                videoGrid.innerHTML = '<p>No videos found. Try adjusting your search or filters.</p>';
                searchResultsCountDisplay.textContent = 'Found 0 videos.';
            }
            return;
        }
        
        const selectedYear = yearFilter.value;
        const selectedField = fieldFilter.value;

        if (searchTerm || selectedYear || selectedField) {
            searchResultsCountDisplay.textContent = `Showing ${videosToRender.length} of ${allVideos.length} videos matching your criteria.`;
        } else {
            searchResultsCountDisplay.textContent = `Showing all ${allVideos.length} videos.`;
        }

        videosToRender.forEach(video => {
            const card = document.createElement('div');
            card.className = 'video-card';
            card.innerHTML = `
                <h3>${video.title || 'N/A'}</h3>
                <p><strong>Speaker:</strong> ${video.speaker ? video.speaker.name : 'N/A'} (${video.speaker && video.speaker.affiliation ? video.speaker.affiliation : 'N/A'})</p>
                <p><strong>Workshop:</strong> ${video.workshop ? video.workshop.title : 'N/A'} (${video.workshop ? video.workshop.code : 'N/A'}, ${video.workshop ? video.workshop.year : 'N/A'}, ${video.workshop && video.workshop.dates ? video.workshop.dates : 'N/A'})</p>
                <p><strong>Abstract:</strong> ${video.content && video.content.abstract ? video.content.abstract : 'N/A'}</p>
                <p><strong>Field:</strong> ${video.content && video.content.field ? video.content.field : 'N/A'}</p>
                <p><strong>Topics:</strong> ${video.content && video.content.topics && Array.isArray(video.content.topics) ? video.content.topics.join(', ') : 'N/A'}</p>
                <a href="${video.files && video.files.video_url ? video.files.video_url : '#'}" target="_blank">Watch Video</a>
            `;
            videoGrid.appendChild(card);
        });
    }

    function applyFiltersAndSearch() {
        const searchTerm = searchBar.value.toLowerCase();
        const selectedYear = yearFilter.value;
        const selectedField = fieldFilter.value;

        const filteredVideos = allVideos.filter(video => {
            const matchesSearch = (
                (video.title && video.title.toLowerCase().includes(searchTerm)) ||
                (video.speaker && video.speaker.name && video.speaker.name.toLowerCase().includes(searchTerm)) ||
                (video.content && video.content.abstract && video.content.abstract.toLowerCase().includes(searchTerm)) ||
                (video.workshop && video.workshop.title && video.workshop.title.toLowerCase().includes(searchTerm)) ||
                (video.workshop && video.workshop.code && video.workshop.code.toLowerCase().includes(searchTerm)) ||
                (video.content && video.content.topics && Array.isArray(video.content.topics) && video.content.topics.some(topic => topic.toLowerCase().includes(searchTerm))) ||
                (video.content && video.content.field && video.content.field.toLowerCase().includes(searchTerm))
            );
            const matchesYear = selectedYear ? (video.workshop && video.workshop.year == selectedYear) : true;
            const matchesField = selectedField ? (video.content && video.content.field == selectedField) : true;
            
            return matchesSearch && matchesYear && matchesField;
        });

        renderVideoCards(filteredVideos);
        updateActiveFiltersDisplay(); // Update active filters display
    }

    searchBar.addEventListener('input', applyFiltersAndSearch);
    yearFilter.addEventListener('change', applyFiltersAndSearch);
    fieldFilter.addEventListener('change', applyFiltersAndSearch);

    fetchVideos();
});

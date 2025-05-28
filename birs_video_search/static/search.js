document.addEventListener('DOMContentLoaded', () => {
    const videoGrid = document.getElementById('video-grid');
    const searchBar = document.getElementById('search-bar');
    const yearFilter = document.getElementById('year-filter');
    const fieldFilter = document.getElementById('field-filter');
    let allVideos = [];

    async function fetchVideos() {
        try {
            const response = await fetch('static/videos.json');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            allVideos = await response.json();
            populateFilters();
            applyFiltersAndSearch();
        } catch (error) {
            console.error("Could not fetch videos:", error);
            videoGrid.innerHTML = '<p>Error loading videos. Please try again later.</p>';
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

        if (videosToRender.length === 0) {
            videoGrid.innerHTML = '<p>No videos found matching your criteria.</p>';
            return;
        }

        videosToRender.forEach(video => {
            const card = document.createElement('div');
            card.className = 'video-card';
            card.innerHTML = `
                <h3>${video.title || 'N/A'}</h3>
                <p><strong>Speaker:</strong> ${video.speaker ? video.speaker.name : 'N/A'} (${video.speaker ? video.speaker.affiliation : 'N/A'})</p>
                <p><strong>Workshop:</strong> ${video.workshop ? video.workshop.title : 'N/A'} (${video.workshop ? video.workshop.code : 'N/A'}, ${video.workshop ? video.workshop.year : 'N/A'})</p>
                <p><strong>Abstract:</strong> ${video.content ? video.content.abstract : 'N/A'}</p>
                <p><strong>Duration:</strong> ${video.content ? video.content.duration_minutes : 'N/A'} minutes</p>
                <p><strong>Field:</strong> ${video.content ? video.content.field : 'N/A'}</p>
                <a href="${video.files ? video.files.video_url : '#'}" target="_blank">Watch Video</a>
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
                (video.content && video.content.abstract && video.content.abstract.toLowerCase().includes(searchTerm))
            );
            const matchesYear = selectedYear ? (video.workshop && video.workshop.year == selectedYear) : true;
            const matchesField = selectedField ? (video.content && video.content.field == selectedField) : true;
            
            return matchesSearch && matchesYear && matchesField;
        });

        renderVideoCards(filteredVideos);
    }

    searchBar.addEventListener('input', applyFiltersAndSearch);
    yearFilter.addEventListener('change', applyFiltersAndSearch);
    fieldFilter.addEventListener('change', applyFiltersAndSearch);

    fetchVideos();
});

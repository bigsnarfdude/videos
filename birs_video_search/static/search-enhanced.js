document.addEventListener("DOMContentLoaded", () => {
    const videoGrid = document.getElementById("video-grid");
    const searchBar = document.getElementById("search-bar");
    const yearFilter = document.getElementById("year-filter");
    const fieldFilter = document.getElementById("field-filter");
    const searchResultsCountDisplay = document.getElementById("search-results-count");
    let allVideos = [];

    async function loadVideos() {
        try {
            const response = await fetch("static/videos.json");
            allVideos = await response.json();
            console.log("Loaded", allVideos.length, "videos");
            populateFilters();
            showAllVideos();
        } catch (error) {
            console.error("Error:", error);
            videoGrid.innerHTML = "<p>Error loading videos</p>";
        }
    }

    function populateFilters() {
        // Populate years
        const years = [...new Set(allVideos.map(v => v.workshop.year))].sort((a,b) => b-a);
        years.forEach(year => {
            const option = document.createElement("option");
            option.value = year;
            option.textContent = year;
            yearFilter.appendChild(option);
        });

        // Populate fields
        const fields = [...new Set(allVideos.map(v => v.content.field))].sort();
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
            searchResultsCountDisplay.textContent = `Showing ${videos.length} of ${allVideos.length} videos`;
        }

        videos.forEach(video => {
            const card = document.createElement("div");
            card.className = "video-card";
            card.innerHTML = `
                <h3>${video.title}</h3>
                <p><strong>Speaker:</strong> ${video.speaker.name}</p>
                <p><strong>Year:</strong> ${video.workshop.year}</p>
                <p><strong>Field:</strong> ${video.content.field}</p>
                <a href="${video.files.video_url}" target="_blank">Watch Video</a>
            `;
            videoGrid.appendChild(card);
        });
    }

    function showAllVideos() {
        showVideos(allVideos);
    }

    function applyFilters() {
        const searchTerm = searchBar.value.toLowerCase();
        const yearValue = yearFilter.value;
        const fieldValue = fieldFilter.value;

        const filtered = allVideos.filter(video => {
            const matchesSearch = !searchTerm || 
                video.title.toLowerCase().includes(searchTerm) ||
                video.speaker.name.toLowerCase().includes(searchTerm) ||
                video.content.field.toLowerCase().includes(searchTerm);
            
            const matchesYear = !yearValue || video.workshop.year == yearValue;
            const matchesField = !fieldValue || video.content.field == fieldValue;
            
            return matchesSearch && matchesYear && matchesField;
        });

        showVideos(filtered);
    }

    // Add event listeners
    searchBar.addEventListener('input', applyFilters);
    yearFilter.addEventListener('change', applyFilters);
    fieldFilter.addEventListener('change', applyFilters);

    loadVideos();
});

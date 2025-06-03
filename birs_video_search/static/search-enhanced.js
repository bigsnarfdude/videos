document.addEventListener('DOMContentLoaded', function() {
            loadVideos();
            
            document.getElementById('searchInput').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    performSearch();
                }
            });
            
            // Add real-time search as user types
            document.getElementById('searchInput').addEventListener('input', function(e) {
                // Debounce the search to avoid too many rapid calls
                clearTimeout(window.searchTimeout);
                window.searchTimeout = setTimeout(function() {
                    performSearch();
                }, 300);
            });
            
            // Add event listeners for category pills
            const pills = document.querySelectorAll('.pill');
            console.log('Found', pills.length, 'category pills');
            pills.forEach(function(pill) {
                pill.addEventListener('click', function() {
                    console.log('Category pill clicked:', this.getAttribute('data-category'));
                    // Remove active class from all pills
                    document.querySelectorAll('.pill').forEach(function(p) {
                        p.classList.remove('active');
                    });
                    
                    // Add active class to clicked pill
                    this.classList.add('active');
                    
                    // Get the category and filter
                    const category = this.getAttribute('data-category');
                    filterByCategory(category);
                });
            });
            
            // Add event listeners for navigation items
            const navItems = document.querySelectorAll('.nav-item');
            console.log('Found', navItems.length, 'navigation items');
            navItems.forEach(function(item) {
                item.addEventListener('click', function() {
                    console.log('Nav item clicked:', this.getAttribute('data-view'));
                    // Remove active from all nav items
                    document.querySelectorAll('.nav-item').forEach(function(n) {
                        n.classList.remove('active');
                    });
                    
                    // Add active to clicked item
                    this.classList.add('active');
                    
                    const view = this.getAttribute('data-view');
                    filterByView(view);
                });
            });
            
            // Add event listeners for research field filters
            const fieldItems = document.querySelectorAll('.filter-item[data-field]');
            console.log('Found', fieldItems.length, 'field filter items');
            fieldItems.forEach(function(item) {
                item.addEventListener('click', function() {
                    console.log('Field filter clicked:', this.getAttribute('data-field'));
                    const field = this.getAttribute('data-field');
                    filterByField(field);
                });
            });
            
            // Add event listeners for content feature filters
            const featureItems = document.querySelectorAll('.filter-item[data-feature]');
            console.log('Found', featureItems.length, 'feature filter items');
            featureItems.forEach(function(item) {
                item.addEventListener('click', function() {
                    console.log('Feature filter clicked:', this.getAttribute('data-feature'));
                    const feature = this.getAttribute('data-feature');
                    filterByFeature(feature);
                });
            });
        });
        
        // Separate function to add year filter event listeners (called after year filters are populated)
        function addYearFilterListeners() {
            const yearItems = document.querySelectorAll('#yearFilters .filter-item');
            console.log('Found', yearItems.length, 'year filter items');
            yearItems.forEach(function(item) {
                item.addEventListener('click', function() {
                    console.log('Year filter clicked:', this.getAttribute('data-year'));
                    const year = this.getAttribute('data-year');
                    filterByYear(year === 'all' ? 'all' : parseInt(year));
                });
            });
        }
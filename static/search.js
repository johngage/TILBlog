/**
 * TILNET Client-Side Search with Flexsearch
 * Provides Ctrl+K instant search functionality
 */

(function() {
    // Configuration
    const BASE_URL = window.TILNET_BASE_URL || '/TILBlog';  // Default to your GitHub Pages URL
    
    // Global variables
    let searchIndex = null;
    let flexsearchIndex = null;
    let searchModal = null;
    let isSearchReady = false;
    
    // Initialize on page load
    document.addEventListener('DOMContentLoaded', initializeSearch);
    
    async function initializeSearch() {
        try {
            // Load search index
            const response = await fetch(`${BASE_URL}/search-index.json`);
            if (!response.ok) {
                throw new Error('Failed to load search index');
            }
            
            const data = await response.json();
            searchIndex = data.documents;
            
            // Initialize Flexsearch
            flexsearchIndex = new FlexSearch.Index({
                preset: "performance",
                tokenize: "forward",
                resolution: 9,
                cache: true
            });
            
            // Add documents to index
            searchIndex.forEach(doc => {
                const searchableText = `${doc.title} ${doc.content} ${doc.topics.join(' ')}`;
                flexsearchIndex.add(doc.id, searchableText);
            });
            
            isSearchReady = true;
            console.log(`Search index loaded: ${data.metadata.count} entries`);
            
            // Set up keyboard shortcut
            document.addEventListener('keydown', handleKeyboard);
            
            // Create search modal
            createSearchModal();
            
        } catch (error) {
            console.error('Failed to initialize search:', error);
        }
    }
    
    function createSearchModal() {
        // Create modal HTML matching Simon Willison's style
        const modal = document.createElement('div');
        modal.id = 'search-modal';
        modal.className = 'search-modal';
        modal.style.display = 'none';
        modal.innerHTML = `
            <div class="search-modal-overlay"></div>
            <div class="search-modal-content">
                <div class="search-header">
                    <input type="search" 
                           id="modal-search-input" 
                           class="search-box" 
                           placeholder="Search TIL entries..." 
                           autocomplete="off" />
                    <button class="search-close" aria-label="Close search">&times;</button>
                </div>
                <div id="modal-search-results" class="search-results"></div>
                <div class="search-footer">
                    <span class="small-text">
                        Press <kbd>Enter</kbd> to select • <kbd>Esc</kbd> to close
                    </span>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        searchModal = modal;
        
        // Set up event handlers
        const searchInput = document.getElementById('modal-search-input');
        searchInput.addEventListener('input', debounce(handleSearch, 200));
        searchInput.addEventListener('keydown', handleSearchKeydown);
        
        modal.querySelector('.search-close').addEventListener('click', closeSearch);
        modal.querySelector('.search-modal-overlay').addEventListener('click', closeSearch);
    }
    
    function handleKeyboard(e) {
        // Ctrl+K or Cmd+K to open search
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            showSearch();
        }
        
        // Escape to close
        if (e.key === 'Escape' && searchModal && searchModal.style.display !== 'none') {
            closeSearch();
        }
    }
    
    function handleSearchKeydown(e) {
        if (e.key === 'Enter') {
            // Navigate to first result
            const firstLink = searchModal.querySelector('.search-result a');
            if (firstLink) {
                window.location.href = firstLink.href;
            }
        }
    }
    
    function showSearch() {
        if (!searchModal || !isSearchReady) return;
        
        searchModal.style.display = 'flex';
        document.getElementById('modal-search-input').focus();
        document.body.style.overflow = 'hidden';
    }
    
    function closeSearch() {
        if (!searchModal) return;
        
        searchModal.style.display = 'none';
        document.body.style.overflow = '';
        
        // Clear search
        document.getElementById('modal-search-input').value = '';
        document.getElementById('modal-search-results').innerHTML = '';
    }
    
    function handleSearch(e) {
        const query = e.target.value.trim();
        const resultsContainer = document.getElementById('modal-search-results');
        
        if (!query) {
            resultsContainer.innerHTML = '';
            return;
        }
        
        // Search using Flexsearch
        const results = flexsearchIndex.search(query, {
            limit: 10,
            suggest: true
        });
        
        if (results.length === 0) {
            resultsContainer.innerHTML = `
                <div class="search-message">
                    No results found for "<strong>${escapeHtml(query)}</strong>"
                </div>
            `;
            return;
        }
        
        // Get full documents for results
        const resultDocs = results.map(id => searchIndex[id]);
        displayResults(resultDocs, resultsContainer, query);
    }
    
    function displayResults(results, container, query) {
        const html = results.map((doc, index) => {
            // Highlight matches in preview
            const highlighted = highlightMatch(doc.preview, query);
            
            // Format date
            const date = new Date(doc.created);
            const dateStr = date.toLocaleDateString('en-US', { 
                year: 'numeric', 
                month: 'short', 
                day: 'numeric' 
            });
            
            return `
                <div class="search-result" data-index="${index}">
                    <h3 class="entry-title">
                        <a href="${doc.url}">${escapeHtml(doc.title)}</a>
                    </h3>
                    <p class="entry-preview">${highlighted}</p>
                    <div class="entry-meta">
                        <span class="entry-date">${dateStr}</span>
                        ${doc.topics.length > 0 ? `
                            <span class="entry-topics">
                                ${doc.topics.map(t => 
                                    `<a href="${BASE_URL}/topic/${encodeURIComponent(t)}/" class="entry-topic">${escapeHtml(t)}</a>`
                                ).join(' ')}
                            </span>
                        ` : ''}
                    </div>
                </div>
            `;
        }).join('');
        
        container.innerHTML = html;
    }
    
    function highlightMatch(text, query) {
        if (!text || !query) return escapeHtml(text || '');
        
        const escaped = escapeHtml(text);
        const regex = new RegExp(`(${escapeRegex(query)})`, 'gi');
        return escaped.replace(regex, '<mark>$1</mark>');
    }
    
    // Utility functions
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text || '';
        return div.innerHTML;
    }
    
    function escapeRegex(string) {
        return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }
    
    // Make functions available globally if needed
    window.TILNET_SEARCH = {
        show: showSearch,
        close: closeSearch,
        isReady: () => isSearchReady
    };
})();
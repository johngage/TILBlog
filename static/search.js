// static/search.js - Complete file with all fixes

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
            
            // Handle regular search form
            handleRegularSearchForm();
            
            // Handle search page if we're on it
            if (isSearchReady) {
                handleSearchPage();
            }
            
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
    
    // Handle regular search form
    function handleRegularSearchForm() {
        const searchForm = document.querySelector('.search-form');
        const searchInput = searchForm ? searchForm.querySelector('input[type="search"]') : null;
        
        if (searchForm && searchInput) {
            // Prevent form submission
            searchForm.addEventListener('submit', function(e) {
                e.preventDefault();
                
                const query = searchInput.value.trim();
                
                if (!query) {
                    return;
                }
                
                // Open the search modal with the query
                if (isSearchReady) {
                    showSearch();
                    document.getElementById('modal-search-input').value = query;
                    // Trigger search
                    const event = new Event('input', { bubbles: true });
                    document.getElementById('modal-search-input').dispatchEvent(event);
                } else {
                    alert('Search is still loading. Please try again in a moment.');
                }
            });
        }
    }
    
    // Handle search page if we're on search.html
    function handleSearchPage() {
        // Check if we're on the search page
        if (window.location.pathname.includes('/search.html')) {
            // Get query from URL
            const urlParams = new URLSearchParams(window.location.search);
            const query = urlParams.get('q');
            
            if (query && isSearchReady) {
                // Display search results on the page
                const resultsContainer = document.getElementById('search-page-results');
                if (resultsContainer) {
                    performSearchOnPage(query, resultsContainer);
                }
            }
        }
    }
    
    // Perform search and display on search page
    function performSearchOnPage(query, container) {
        // Update the search input if it exists
        const searchInput = document.querySelector('input[name="q"]');
        if (searchInput) {
            searchInput.value = query;
        }
        
        // Update page title
        const pageTitle = document.querySelector('h2');
        if (pageTitle) {
            pageTitle.textContent = `Search results for "${query}"`;
        }
        
        // Perform search
        const results = flexsearchIndex.search(query, {
            limit: 50,  // More results for search page
            suggest: true
        });
        
        if (results.length === 0) {
            container.innerHTML = `
                <div class="search-message">
                    <p>No results found for "<strong>${escapeHtml(query)}</strong>"</p>
                    <p>Try different keywords or browse by <a href="${BASE_URL}/">topic</a>.</p>
                </div>
            `;
            return;
        }
        
        // Get full documents and display
        const resultDocs = results.map(id => searchIndex[id]);
        
        // Create HTML similar to your entry list
        const html = `
            <p class="search-summary">${results.length} results found</p>
            <ul class="entry-list">
                ${resultDocs.map(doc => `
                    <li class="entry-item">
                        <div class="entry-header">
                            <h3 class="entry-title">
                                <a href="${doc.url}">${escapeHtml(doc.title)}</a>
                            </h3>
                            
                            <div class="entry-meta">
                                <div class="entry-dates">
                                    <span class="entry-date">${new Date(doc.created).toLocaleDateString()}</span>
                                    ${doc.modified && doc.modified !== doc.created ? 
                                        `<span class="modified-indicator">(modified ${new Date(doc.modified).toLocaleDateString()})</span>` 
                                        : ''
                                    }
                                </div>
                                
                                ${doc.topics.length > 0 ? `
                                    <div class="entry-topics">
                                        ${doc.topics.map(t => 
                                            `<a href="${BASE_URL}/topic/${encodeURIComponent(t)}/" class="entry-topic">${escapeHtml(t)}</a>`
                                        ).join(' ')}
                                    </div>
                                ` : ''}
                            </div>
                        </div>
                        
                        <div class="entry-preview">
                            ${highlightMatch(doc.preview, query)}
                        </div>
                    </li>
                `).join('')}
            </ul>
        `;
        
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
    
    // Also make handleSearchSubmit available globally for the inline onclick
    window.handleSearchSubmit = function(event) {
        event.preventDefault();
        const query = event.target.q.value.trim();
        if (query && window.TILNET_SEARCH && window.TILNET_SEARCH.isReady()) {
            window.TILNET_SEARCH.show();
            document.getElementById('modal-search-input').value = query;
            document.getElementById('modal-search-input').dispatchEvent(new Event('input'));
        }
        return false;
    };
})();
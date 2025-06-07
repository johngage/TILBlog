// static/js/dark-mode.js - Complete replacement file

document.addEventListener('DOMContentLoaded', function() {
    const toggle = document.getElementById('dark-mode-toggle');
    const body = document.body;
    
    // Check for saved preference or system preference
    const darkModeMediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const storedTheme = localStorage.getItem('theme');
    
    // Set initial state
    if (storedTheme === 'dark' || (!storedTheme && darkModeMediaQuery.matches)) {
        body.classList.add('dark-mode');
        updateToggleIcon(true);
    }
    
    // Toggle handler
    toggle.addEventListener('click', function() {
        const isDark = body.classList.toggle('dark-mode');
        localStorage.setItem('theme', isDark ? 'dark' : 'light');
        updateToggleIcon(isDark);
    });
    
    // Update icon based on mode
    function updateToggleIcon(isDark) {
        const moonIcon = toggle.querySelector('.dark-mode-icon');
        const sunIcon = toggle.querySelector('.light-mode-icon');
        
        if (moonIcon && sunIcon) {
            moonIcon.style.display = isDark ? 'none' : 'inline';
            sunIcon.style.display = isDark ? 'inline' : 'none';
        } else {
            // Fallback for simple emoji toggle
            toggle.textContent = isDark ? '☀️' : '🌙';
        }
    }
    
    // Listen for system preference changes
    darkModeMediaQuery.addEventListener('change', function(e) {
        if (!localStorage.getItem('theme')) {
            if (e.matches) {
                body.classList.add('dark-mode');
            } else {
                body.classList.remove('dark-mode');
            }
            updateToggleIcon(e.matches);
        }
    });
});

// Add smooth scrolling for internal links
document.addEventListener('click', function(e) {
    if (e.target.tagName === 'A' && e.target.getAttribute('href').startsWith('#')) {
        e.preventDefault();
        const targetId = e.target.getAttribute('href').slice(1);
        const targetElement = document.getElementById(targetId);
        
        if (targetElement) {
            targetElement.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    }
});

// Add keyboard navigation improvements
document.addEventListener('keydown', function(e) {
    // Press '/' to focus search (common pattern)
    if (e.key === '/' && !e.ctrlKey && !e.metaKey) {
        const activeElement = document.activeElement;
        const isTyping = activeElement.tagName === 'INPUT' || 
                        activeElement.tagName === 'TEXTAREA' ||
                        activeElement.isContentEditable;
        
        if (!isTyping) {
            e.preventDefault();
            const searchInput = document.querySelector('.search-form input[type="search"]');
            if (searchInput) {
                searchInput.focus();
                searchInput.select();
            }
        }
    }
    
    // Press 'Escape' to blur search
    if (e.key === 'Escape') {
        const searchInput = document.querySelector('.search-form input[type="search"]');
        if (document.activeElement === searchInput) {
            searchInput.blur();
        }
    }
});

// Add loading states for better UX
window.addEventListener('beforeunload', function() {
    // Show loading state when navigating
    const body = document.body;
    body.style.opacity = '0.7';
    body.style.transition = 'opacity 0.2s ease';
});

// Improve link prefetching for faster navigation
if ('IntersectionObserver' in window) {
    const prefetchedUrls = new Set();
    
    const linkObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const link = entry.target;
                const href = link.getAttribute('href');
                
                if (href && !prefetchedUrls.has(href) && href.startsWith('/')) {
                    // Prefetch the link
                    const prefetchLink = document.createElement('link');
                    prefetchLink.rel = 'prefetch';
                    prefetchLink.href = href;
                    document.head.appendChild(prefetchLink);
                    prefetchedUrls.add(href);
                }
            }
        });
    });
    
    // Observe all internal links
    document.querySelectorAll('a[href^="/"]').forEach(link => {
        linkObserver.observe(link);
    });
}
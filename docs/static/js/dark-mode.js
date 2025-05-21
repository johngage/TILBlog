// static/js/dark-mode.js
document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.getElementById('dark-mode-toggle');
  const body = document.body;
  
  // Check for saved preference
  const darkMode = localStorage.getItem('darkMode') === 'true';
  if (darkMode) {
    body.classList.add('dark-mode');
    toggle.textContent = '☀️';
  }
  
  // Add toggle functionality
  toggle.addEventListener('click', () => {
    body.classList.toggle('dark-mode');
    const isDark = body.classList.contains('dark-mode');
    localStorage.setItem('darkMode', isDark);
    toggle.textContent = isDark ? '☀️' : '🌙';
  });
});
document.addEventListener('DOMContentLoaded', function() {
    const statusElement = document.getElementById('status');
    setInterval(() => {
        statusElement.textContent = 'Running...';
    }, 1000);
});
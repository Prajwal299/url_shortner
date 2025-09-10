function shortenUrl() {
    fetch('http://3.110.114.163:5000/shorten', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: document.getElementById('url').value })
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById('result').innerText = data.short_url || data.error;
    })
    .catch(error => {
        console.error('Error:', error);
        document.getElementById('result').innerText = 'Error: Could not shorten URL';
    });
}

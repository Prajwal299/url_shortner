function shorten() {
    const url = document.getElementById('url').value;
    fetch('http://localhost:3000/shorten', {  // Update to API service in K8s
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url })
    }).then(res => res.json()).then(data => {
        document.getElementById('result').innerText = data.short_url;
    });
}
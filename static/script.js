let detectionStarted = false;

function startDetection(){
    if(!detectionStarted) {
        document.getElementById('spinner').style.display = 'flex';
        document.getElementById('videoContainer').style.display = 'block';
        
        setTimeout(() => {
            document.getElementById('spinner').style.display = 'none';
            document.getElementById('cameraFeed').src = '/video';
            document.getElementById('cameraFeed').style.display = 'block';
            document.getElementById('videoContainer').style.display = 'block';
        }, 1000);

        detectionStarted = true;
        document.getElementById('startBtn').disabled = true;
        document.getElementById('stopBtn').style.display = 'inline-block';
        loadDetections();
        detectionInterval = setInterval(loadDetections,3000);
    }
}
async function loadDetections() {
    const res = await fetch('/start-detection');
    const data = await res.json();
    const list = document.getElementById('detectionList');
    list.innerHTML = '';

    data.forEach(d => {
        const card = document.createElement('div');
        card.className = 'detection-card';

        const name = document.createElement('h3');
        name.textContent = d.class_name;
        const conf = document.createElement('span');
        conf.textContent = `Confidence: ${d.confidence}%`;
        const time = document.createElement('span');
        time.textContent = `\nDetected at: ${d.timestamp}`;

        card.appendChild(name);
        card.appendChild(conf);
        card.appendChild(document.createElement('br'));
        card.appendChild(time);

        list.appendChild(card);
    });
}

function stopDetection() {
    detectionStarted = false;
    clearInterval(detectionInterval);
    document.getElementById('cameraFeed').style.display = 'none';
    document.getElementById('cameraFeed').src = '';
    document.getElementById('videoContainer').style.display = 'none';
    document.getElementById('startBtn').disabled = false;
    document.getElementById('stopBtn').style.display = 'none';

    fetch('stop-detection');
}
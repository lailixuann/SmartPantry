let detectionStarted = false;
let snapshotInterval = null;

function startDetection() {
    if (!detectionStarted) {
        document.getElementById('spinner').style.display = 'flex';
        document.getElementById('videoContainer').style.display = 'block';
        document.getElementById('generateBtn').style.display = 'none';
        document.getElementById('generateBtn').disabled = false;
        document.getElementById('Recipes').style.display = 'none';

        setTimeout(() => {
            document.getElementById('spinner').style.display = 'none';
            document.getElementById('cameraFeed').src = '/video';
            document.getElementById('cameraFeed').style.display = 'block';
        }, 500);

        detectionStarted = true;
        document.getElementById('startBtn').disabled = true;
        document.getElementById('stopBtn').style.display = 'inline-block';

        fetch('/start-detection');

        snapshotInterval = setInterval(fetchSnapshot, 3000);
    }
}

function stopDetection() {
    fetch('/stop-detection');
    detectionStarted = false;
    clearInterval(snapshotInterval);

    document.getElementById('cameraFeed').style.display = 'none';
    document.getElementById('cameraFeed').src = '';
    document.getElementById('startBtn').disabled = false;
    document.getElementById('stopBtn').style.display = 'none';
    
    const container = document.getElementById('detection-info');
    const lastInfo = document.createElement('div');
    // lastInfo.textContent = "(Last detection results)";
    lastInfo.style.fontStyle = 'italic';
    container.appendChild(lastInfo);
}

const detectionHistory = []; // To store last 3 snapshot data

function fetchSnapshot() {
    triggerSnapshotEffect();
    fetch('/process-frame')
    .then(() => fetch('/snapshot-info'))
    .then(res => res.json())
    .then(data => {
        const list = document.getElementById('detectionList');

        // Store the latest detection result
        detectionHistory.unshift(data); // Add to the beginning
        if (detectionHistory.length > 3) detectionHistory.pop(); // Keep only last 3

        // Clear current list and re-render from detectionHistory
        list.innerHTML = '';

        detectionHistory.forEach(snapshot => {
            const card = document.createElement('div');
            card.className = 'detection-card';

            let snapshotImg = '';
            // Add snapshot image
            if (snapshot.image) {
                const img = document.createElement('img');
                snapshotImg = 'data:image/jpeg;base64,' + snapshot.image;
                img.src = snapshotImg;
                img.style.width = '100%';
                img.style.borderRadius = '8px';
                img.style.marginBottom = '0.5rem';
                card.appendChild(img);
            }

            // Add detection info
            const content = document.createElement('div');
            if (snapshot.detections && snapshot.detections.length > 0) {
                snapshot.detections.forEach(d => {
                    const name = document.createElement('h3');
                    name.textContent = d.class_name;

                    const conf = document.createElement('span');
                    conf.textContent = `Confidence: ${d.confidence}%`;

                    const time = document.createElement('span');
                    time.textContent = `Detected at: ${d.timestamp}`;

                    content.appendChild(name);
                    content.appendChild(conf);
                    content.appendChild(document.createElement('br'));
                    content.appendChild(time);
                });
            } else {
                const noDetection = document.createElement('p');
                noDetection.textContent = 'No items detected in this snapshot.';
                noDetection.style.fontStyle = 'italic';
                content.appendChild(noDetection);
            }
            card.appendChild(content);
            card.addEventListener('click', () => {
                document.getElementById('snapshotPopup').style.display = 'flex';
                document.getElementById('popupImage').src = snapshotImg;
                document.body.classList.add('no-scroll');
            })
            list.appendChild(card);
        })
        const hasDetections = detectionHistory.some(s => s.detections && s.detections.length > 0);
        document.getElementById('generateBtn').style.display = hasDetections ? 'block' : 'none';
    })
    .catch(err => {
        console.error("Snapshot fetch error:", err);
    });
}

function triggerSnapshotEffect() {
  const video = document.getElementById('cameraFeed');
  video.classList.add('flash');
  setTimeout(() => video.classList.remove('flash'), 300);
}

async function generateRecipes() {
    const res = await fetch('/generate-recipes');
    const data = await res.json();

    document.getElementById('generateBtn').disabled = true;
    document.getElementById('Recipes').style.display = 'block';
    const list = document.getElementById('recipeList');
    list.innerHTML = '';

    data.forEach(d => {
        const card = document.createElement('div');
        card.className = 'detection-card';

        const name = document.createElement('h3');
        name.textContent = d.name;

        const matched = document.createElement('span');
        matched.textContent = `Matched Ingredients: ${d.matched}`;

        card.appendChild(name);
        card.appendChild(matched);
        card.style.cursor = 'pointer';
        card.addEventListener('click', () => showRecipePopup(d.id));
        list.appendChild(card);
    });
}

async function showRecipePopup(recipeId) {
    fetch(`/recipe-details/${recipeId}`)
        .then(res => res.json())
        .then(data => {
            document.getElementById('popup-title').textContent = data.name;
            document.getElementById('popup-description').textContent = data.description;
            document.getElementById('popup-ingredients').innerHTML = data.ingredients.map(i => `<li>${i}</li>`).join('');

            try {
                const stepsArray = JSON.parse(data.steps || '[]');
                document.getElementById('popup-steps').innerHTML = stepsArray.map(s => `<li>${s}</li>`).join('');
            } catch (e) {
                console.error("Error parsing steps:", e);
                document.getElementById('popup-steps').innerHTML = '<li>Instructions not available</li>';
            }

            document.body.classList.add('no-scroll');
            document.getElementById('popup').style.display = 'flex';
        });
}

function closePopup(window) {
    document.body.classList.remove('no-scroll');
    document.getElementById(window).style.display = 'none';
}
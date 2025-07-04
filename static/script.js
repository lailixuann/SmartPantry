let detectionStarted = false;

function startDetection(){
    if(!detectionStarted) {
        document.getElementById('spinner').style.display = 'flex';
        document.getElementById('videoContainer').style.display = 'block';
        document.getElementById('generateBtn').style.display = 'none';
        document.getElementById('generateBtn').disabled = false;
        document.getElementById('Recipes').style.display = 'none';
            
        setTimeout(() => {
            document.getElementById('spinner').style.display = 'none';
            document.getElementById('cameraFeed').src = '/video';
            document.getElementById('cameraFeed').style.display = 'block';
            document.getElementById('videoContainer').style.display = 'block';
        }, 500);

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

    // test data
    // const data = [
    //     {class_name: "Chicken", confidence: "88.2", timestamp:"2000-00-00"}
    // ];

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

        if (data.length > 0) {
        document.getElementById('generateBtn').style.display = 'block';
        } else {
        document.getElementById('generateBtn').style.display = 'none';
        }
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

async function generateRecipes() {
    const res = await fetch('/generate-recipes');
    const data = await res.json();

    // test data
    // const data = [
    //     { name: "Tomato Pasta", matched: 3 },
    //     { name: "Avocado Toast", matched: 2 }
    // ];

    document.getElementById('generateBtn').disabled = true;
    document.getElementById('Recipes').style.display = 'block'
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
        
        card.addEventListener('click',() => showRecipePopup(d.id))

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
      let rawSteps = data.steps || '';
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

async function closePopup() {
    document.body.classList.remove('no-scroll');
    document.getElementById('popup').style.display = 'none';
}
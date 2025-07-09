from flask import Flask, Response, jsonify, render_template  
import cv2  
import torch  
import numpy as np  
import time
from collections import defaultdict,deque
from db_models import Detection, DetectionSession, Recipe, RecipeIngredient, db
from datetime import datetime
import base64
import sys
import os
sys.path.append(os.path.abspath('./yolov5'))  # Adjust path if needed
from utils.augmentations import letterbox
from uuid import uuid4
from collections import defaultdict

app = Flask(__name__)  

# Configure the MySQL database  
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://myuser:mypassword@localhost/object_detection_db'
print("Connected to:", app.config['SQLALCHEMY_DATABASE_URI'])
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  

db.init_app(app) 

# Create the database tables  
with app.app_context():  
    db.create_all() 

# Load the YOLOv5 model
model = torch.hub.load('./yolov5', 'custom', path = 'yolov5n/best.pt', source='local') 

confidence_history = defaultdict(lambda: deque(maxlen=5))
last_seen = {}
last_snapshot_info = {}
streaming = False
current_session_id = None
detection_buffer = defaultdict(int)
removal_buffer = defaultdict(int)

DETECTION_THRESHOLD = 2

def update_confidence(cls, confidence):
    now = time.time()
    confidence_history[cls].append(confidence)
    last_seen[cls] = now

def get_avg_confidence(cls):
    if cls not in confidence_history:
        return 0
    return sum(confidence_history[cls]) / len(confidence_history[cls])

def is_currently_detected(cls, threshold=0.5, timeout=5):
    now = time.time()
    avg_conf = get_avg_confidence(cls)
    return (now - last_seen.get(cls, 0) <= timeout and avg_conf > threshold)

def get_items():
    with app.app_context():
        items = db.session.query(Detection.class_name).filter_by(is_removed=False).all()
    return set(item[0] for item in items)

def update_db(item_name, confidence, image_path):
    with app.app_context():
        now = datetime.now()
        item = Detection.query.filter_by(class_name=item_name).first()
        if item:
            item.confidence = confidence
            item.timestamp = now
            item.is_removed = False
            item.image_path = image_path
        else:
            new_item = Detection(session_id=current_session_id, class_name=item_name, confidence=confidence, image_path=image_path, timestamp=now)
            db.session.add(new_item)
        db.session.commit()

def mark_removed(items):
    with app.app_context():
        for item in items:
            entry = Detection.query.filter_by(class_name=item, is_removed=False).first()
            if entry:
                entry.is_removed = True
        db.session.commit()

def generate(cap):
    global streaming
    while streaming:
        success, frame = cap.read()
        if not success:
            break
        frame = letterbox(frame,new_shape=(640,480))[0]
        frame = cv2.flip(frame, 1)
        _, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
    cap.release()

@app.route('/')  
def index():  
    return render_template('index.html')  

@app.route('/video')  
def video_feed():  
    global streaming 
    streaming = True
    cap = cv2.VideoCapture(0)
    return Response(generate(cap), mimetype='multipart/x-mixed-replace; boundary=frame')  

@app.route('/start-detection')
def start_detections():
    global streaming, current_session_id
    streaming = True
    with app.app_context():
        session = DetectionSession(started_at=datetime.now())
        db.session.add(session)
        db.session.flush()
        current_session_id = session.id
        db.session.commit()
    return 'Detection session starting... \nSession_id: ' + str(current_session_id)
    
@app.route('/process-frame')
def process_frame():
    global streaming, last_snapshot_info, detection_buffer, removal_buffer
    cap = cv2.VideoCapture(0)

    while streaming:
        ret, frame = cap.read()
        cap.release()

        if not ret:
            return 'Camera error', 500

        frame = cv2.flip(frame, 1)
        frame = letterbox(frame,new_shape=(640,480))[0]
        rgb = frame[..., ::-1]

        results = model(rgb)
        detections = results.xyxy[0]

        detection_list = []
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        seen_classes = set()

        for *xyxy, conf, cls in detections:
            if conf > 0.45:
                class_name = model.names[int(cls)]
                seen_classes.add(class_name)

                label = f"{class_name} ({int(conf * 100)}%)"
                cv2.rectangle(frame, (int(xyxy[0]), int(xyxy[1])), (int(xyxy[2]), int(xyxy[3])), (0, 255, 0), 2)
                cv2.putText(frame, label, (int(xyxy[0]), int(xyxy[1]) - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                detection_list.append({
                    "class_name": class_name,
                    "confidence": round(conf.item() * 100, 1),
                    "timestamp": current_time
                })
                detection_buffer[class_name] += 1
                removal_buffer[class_name] = 0

                if detection_buffer[class_name] >= DETECTION_THRESHOLD:
                    img_filename = f"{uuid4().hex}.jpg"
                    img_path = os.path.join('static/snapshots', img_filename)
                    os.makedirs('static/snapshots', exist_ok=True)
                    cv2.imwrite(img_path, frame)

                    image_path_for_db = f"/static/snapshots/{img_filename}"
                    update_db(class_name, float(conf),image_path=image_path_for_db)

        existing_items = get_items()
        for item in existing_items:
            if item not in seen_classes:
                removal_buffer[item] += 1
                if removal_buffer[item] >= DETECTION_THRESHOLD:
                    mark_removed([item])
                    detection_buffer[item] = 0
            else:
                removal_buffer[item] = 0  # reset if detected again

        _, buffer = cv2.imencode('.jpg', frame)
        img_base64 = base64.b64encode(buffer).decode('utf-8')

        last_snapshot_info = {
            "detections": detection_list,
            "image": img_base64
        }
        return jsonify(last_snapshot_info)

@app.route('/snapshot-info')
def snapshot_info():
    global last_snapshot_info
    return jsonify(last_snapshot_info)

@app.route('/stop-detection')
def stop_detection():
    global streaming, current_session_id 
    streaming = False
    with app.app_context():
            session = db.session.get(DetectionSession, current_session_id)
            if session:
                session.ended_at = datetime.now()
                db.session.commit()
    current_session_id = None
    return 'Detection session stopped'

@app.route('/generate-recipes')
def generate_recipe():
    from recipe_recommendation import recommend_recipes
    recipes = recommend_recipes(get_items())
    return jsonify([
        {
            "id": recipe.id,
            "name": recipe.name,
            "matched": matched
        }
        for recipe, matched in recipes
    ])

@app.route('/recipe-details/<int:recipe_id>')
def get_recipe_details(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    ingredients = RecipeIngredient.query.filter_by(recipe_id=recipe_id).all()

    return jsonify({
        'name': recipe.name,
        'description': recipe.description,
        'ingredients': [i.ingredient_name for i in ingredients],
        'steps': recipe.steps,
    })


if __name__ == '__main__':  
    app.run(debug=True)  
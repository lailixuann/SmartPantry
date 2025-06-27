from flask import Flask, Response, jsonify, render_template  
import cv2  
import torch  
import numpy as np  
import time
from collections import defaultdict,deque
from db_models import Detection, Recipe, RecipeIngredient, db

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
model = torch.hub.load('./yolov5', 'custom', path = 'yolov5/best.pt', source='local') 

# Tracking ingredients state
appearance_start_time = {}
MIN_PERSISTENCE_DURATION = 2
confidence_history = defaultdict(lambda: deque(maxlen=5))
last_seen = {}
detected_items = set()
streaming = False

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
    if now - last_seen.get(cls, 0) <= timeout and avg_conf > threshold:
        return True
    return False

def get_db_items():
    items = db.session.query(Detection.class_name).all()
    return set(item[0] for item in items)

def save_to_db(new_items_conf):
    for name, conf in new_items_conf:
        new_detection = Detection(class_name=name, confidence=conf)
        db.session.add(new_detection)
        print(f"[DEBUG] Actually saving to DB: {name}, Avg Confidence: {conf:.2f}")
    db.session.commit()

def delete_from_db(items):
    for item in items:
        Detection.query.filter_by(class_name=item).delete()
    db.session.commit()

def generate_frames():  
    global streaming
    streaming = True
    cap = cv2.VideoCapture(0)

    # last_detection_time = 0
    # detection_interval = 1.0  # detect every 1s
    # MIN_PERSISTENCE_DURATION = 1.5

    try:
        while streaming:
            success, frame = cap.read()
            if not success:
                break

            frame = cv2.flip(frame, 1)
            current_time = time.time()

            current_detections = set()
            confident_detections = []

            # if current_time - last_detection_time >= detection_interval:
            #     last_detection_time = current_time

            rgb_frame = frame[..., ::-1]
            results = model(rgb_frame)
            detections = results.xyxy[0]
        ###
            # current_frame_classes = []
        ###

            for *xyxy, conf, cls in detections:
                class_name = model.names[int(cls)]
                confidence = float(conf)
            ###
                # current_frame_classes.append(class_name)
            ###
                # Track when class first appeared
                if class_name not in appearance_start_time:
                    appearance_start_time[class_name] = current_time
                else:
                    duration = current_time - appearance_start_time[class_name]
                    if duration >= MIN_PERSISTENCE_DURATION and confidence > 0.5:
                        confident_detections.append((class_name, confidence))
                        current_detections.add(class_name)

                # Draw the box and label in real-time
                label = f"{class_name} ({int(confidence * 100)}%)"
                cv2.rectangle(frame, (int(xyxy[0]), int(xyxy[1])), (int(xyxy[2]), int(xyxy[3])), (0, 255, 0), 2)
                cv2.putText(frame, label, (int(xyxy[0]), int(xyxy[1]) - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            # Reset timer for items no longer detected
            current_frame_classes = [model.names[int(cls)] for *_, cls in detections]
            for known in list(appearance_start_time.keys()):
                if known not in current_frame_classes:
                    del appearance_start_time[known]

            with app.app_context():
                existing_items = get_db_items()
                new_items = [(cls, conf) for cls, conf in confident_detections if cls not in existing_items]
                removed_items = existing_items - current_detections

                # print("[DEBUG] existing_items in DB:", existing_items)
                # print("[DEBUG] new_items to save:", new_items)

                if new_items:
                    save_to_db(new_items)
                    print("[DEBUG] Trying to save: ", new_items)
                
                if streaming and removed_items:
                    delete_from_db(removed_items)

            # Encode and yield the frame
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    finally:
        cap.release()

@app.route('/')  
def index():  
    return render_template('index.html')  

@app.route('/video')  
def video():  
    global streaming 
    streaming = True
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')  

@app.route('/start-detection')
def get_detections():
    detection_results = Detection.query.order_by(Detection.timestamp.desc()).limit(10).all()
    return jsonify([
        {
            'class_name': d.class_name,
            'confidence': round((d.confidence * 100), 2),
            'timestamp': d.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        } for d in detection_results
    ])

@app.route('/stop-detection')
def stop_video():
    global streaming 
    streaming = False
    return 'Video stopped'

if __name__ == '__main__':  
    app.run(debug=True)  
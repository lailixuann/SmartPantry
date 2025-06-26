from flask import Flask, Response, jsonify, render_template  
from flask_sqlalchemy import SQLAlchemy  
import cv2  
import torch  
import numpy as np  
import time
from collections import defaultdict,deque
from datetime import datetime

app = Flask(__name__)  

# Configure the MySQL database  
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:@localhost/object_detection_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  
db = SQLAlchemy(app)  

# Define Detection model  
class Detection(db.Model):  
    id = db.Column(db.Integer, primary_key=True)  
    class_name = db.Column(db.String(50))  
    confidence = db.Column(db.Float)  
    timestamp = db.Column(db.DateTime, server_default=db.func.current_timestamp())  

    def __repr__(self):  
        return f"<Detection(class_name='{self.class_name}', confidence={self.confidence})>"  

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
    items = Detection.query.with_entities(Detection.class_name).distinct().all()
    return set(item.class_name for item in items)

# def new_items(detected_items, existing_items):
#     return detected_items - existing_items

def save_to_db(new_items_conf):
    for name, conf in new_items_conf:
        new_detection = Detection(class_name=name, confidence=conf)
        db.session.add(new_detection)
    db.session.commit()

# def detect_objects(frame):  
    # results = model(frame)  # Runs object detection  
    # detections = detect_objects_from_results(results)  
    # return detections  

# def detect_objects_from_results(results):  
    # detections = []  
    # for *box, conf, cls in results.xyxy[0]:  
    #     class_name = model.names[int(cls)]  
    #     confidence = conf.item()  
    #     detections.append((class_name, confidence))  
    #     new_detection = Detection(class_name=class_name, confidence=confidence)  
    #     db.session.add(new_detection)  
    # db.session.commit()
    # return detections

def generate_frames():  
    cap = cv2.VideoCapture(0)
    try:
        while True:
            success, frame = cap.read()
            if not success:
                break

            current_time = time.time()
            rgb_frame = frame[..., ::-1]

            results = model(rgb_frame)
            detections = results.xyxy[0]

            current_detections = set()
            confident_detections = []

            for *xyxy, conf, cls in detections:
                class_name = model.names[int(cls)]
                confidence = float(conf)
                update_confidence(class_name, confidence)

                if is_currently_detected(class_name):
                    avg_conf = get_avg_confidence(class_name)
                    if avg_conf > 0.5:
                        confident_detections.append((class_name, avg_conf))
                        current_detections.add(class_name)

                        label = f"{class_name} ({int(avg_conf * 100)}%)"
                        cv2.rectangle(frame, (int(xyxy[0]), int(xyxy[1])), (int(xyxy[2]), int(xyxy[3])), (0, 255, 0), 2)
                        cv2.putText(frame, label, (int(xyxy[0]), int(xyxy[1]) - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            # Add new items only
            existing_items = get_db_items()
            new_items = [(cls, conf) for cls, conf in confident_detections if cls not in existing_items]

            if new_items:
                with app.app_context():
                    save_to_db(new_items)
                        
            # Encode and yield the frame
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()

            # print("Streaming frame at", time.time())
            # Yield frame
            yield (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            
    finally:
        cap.release()

@app.route('/')  
def index():  
    return render_template('index.html')  

@app.route('/video')  
def video():  
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')  

@app.route('/start-detections')
def get_detections():
    detection_results = Detection.query.order_by(Detection.timestamp.desc()).limit(10).all()
    return jsonify([
        {
            'class_name': d.class_name,
            'confidence': d.confidence,
            'timestamp': d.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        } for d in detection_results
    ])

if __name__ == '__main__':  
    app.run(debug=True)  
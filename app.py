from flask import Flask, Response, jsonify, render_template  
from flask_sqlalchemy import SQLAlchemy  
import cv2  
import torch  
import numpy as np  

app = Flask(__name__)  

# Configure your MySQL database  
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://username:password@localhost/object_detection_db'  
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  
db = SQLAlchemy(app)  

# Define a Detection model  
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

# Load your object detection model (replace this with your model)  
# Assuming you have a pre-trained model path for YOLO or similar  
model = torch.hub.load('ultralytics/yolov5', 'yolov5s')  

def detect_objects(frame):  
    results = model(frame)  # Runs object detection  
    detections = []  

    # Process results  
    for *box, conf, cls in results.xyxy[0]:  # Get predictions  
        x1, y1, x2, y2 = map(int, box)  
        class_name = model.names[int(cls)]  
        confidence = conf.item()  
        detections.append((class_name, confidence))  
        
        # Save the detection to the database  
        new_detection = Detection(class_name=class_name, confidence=confidence)  
        db.session.add(new_detection)  

    db.session.commit()  # Commit to database  
    return detections  

def generate_frames():  
    cap = cv2.VideoCapture(0)  # Use the default camera  

    while True:  
        success, frame = cap.read()  
        if not success:  
            break  

        # Object detection  
        detections = detect_objects(frame)  

        # Display results on frame  
        for class_name, confidence in detections:  
            cv2.putText(frame, f"{class_name}: {confidence:.2f}", (10, 30 + detections.index((class_name, confidence)) * 30),  
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)  

        _, buffer = cv2.imencode('.jpg', frame)  
        frame = buffer.tobytes()  

        # Yield the output frame in the format required by Flask  
        yield (b'--frame\r\n'  
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')  

@app.route('/video_feed')  
def video_feed():  
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')  

@app.route('/')  
def index():  
    return render_template('index.html')  

if __name__ == '__main__':  
    app.run(debug=True)  
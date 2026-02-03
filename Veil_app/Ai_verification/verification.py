import cv2
import numpy as np
import os
from django.conf import settings

# Paths to your models (Make sure these match your project structure)
MODEL_DIR = os.path.join(settings.BASE_DIR, "Veil_app", "Ai_verification")
FACE_PROTO = os.path.join(MODEL_DIR, "opencv_face_detector.pbtxt")
FACE_MODEL = os.path.join(MODEL_DIR, "opencv_face_detector_uint8.pb")
GENDER_PROTO = os.path.join(MODEL_DIR, "gender_deploy.prototxt")
GENDER_MODEL = os.path.join(MODEL_DIR, "gender_net.caffemodel")

# Load models once when the server starts

_face_net = None
_gender_net = None
# face_net = cv2.dnn.readNet(FACE_MODEL, FACE_PROTO)
# gender_net = cv2.dnn.readNet(GENDER_MODEL, GENDER_PROTO)

def get_models():
    global _face_net, _gender_net

    if _face_net is None:
        _face_net = cv2.dnn.readNet(FACE_MODEL, FACE_PROTO)

    if _gender_net is None:
        _gender_net = cv2.dnn.readNet(GENDER_MODEL, GENDER_PROTO)

    return _face_net, _gender_net


def verify_gender_ai(image_bytes):
    """
    Takes raw bytes from a request, processes them in memory,
    and returns a verification result.
    """
    # 1. Convert bytes to OpenCV format  (IN-MEMORY)

    face_net, gender_net = get_models()
    nparr = np.frombuffer(image_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if frame is None:
        return {"status": "error", "message": "Invalid image"}

    h, w = frame.shape[:2]
    blob = cv2.dnn.blobFromImage(frame, 1.0, (300, 300), [104, 117, 123], True, False)
    face_net.setInput(blob)
    detections = face_net.forward()

    found_faces = []

    for i in range(detections.shape[2]):
        confidence = detections[0, 0, i, 2]
        if confidence > 0.8:  # Set your threshold
            x1 = int(detections[0, 0, i, 3] * w)
            y1 = int(detections[0, 0, i, 4] * h)
            x2 = int(detections[0, 0, i, 5] * w)
            y2 = int(detections[0, 0, i, 6] * h)
            found_faces.append((x1, y1, x2, y2))

    if len(found_faces) > 1:
        return {
            "status": "failed",
            "message": "Multiple faces detected"
        }
    
    if len(found_faces) == 0:
        return {"status": "failed", "message": "No face detected"}

    # Process the single detected face
    x1, y1, x2, y2 = found_faces[0]
    face = frame[max(0, y1):min(y2, h), max(0, x1):min(x2, w)]

    # Guard against empty face crop
    if face.size == 0:
         return {"status": "failed", "message": "Invalid face region"}
    
    # Predict Gender
    blob_gender = cv2.dnn.blobFromImage(face, 1.0, (227, 227), (78.42, 87.76, 114.89), False)
    gender_net.setInput(blob_gender)
    preds = gender_net.forward()
    
    gender_confidence = float(preds[0].max())
    gender = 'male' if preds[0].argmax() == 0 else 'female'
    
    if gender_confidence < 0.7:
        return {
            "status": "failed",
            "message": "Low confidence"
        }

    return {
        "status": "success",
        "gender": gender,
        "confidence": gender_confidence
    }
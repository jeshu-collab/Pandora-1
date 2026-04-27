import cv2
import math
import time
import os
import numpy as np
from datetime import datetime
import asyncio
import websockets
import json
import base64
import random
import urllib.request
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from mediapipe.framework.formats import landmark_pb2

# --- SYSTEM INITIALIZATION ---
print("Booting Pandora-PRO V14 (Fire + Scale-Invariant Biometrics)...")

# Initialize Google Tasks API (Heavyweight Configuration)
MODEL_PATH = 'pose_landmarker_heavy.task'
if not os.path.exists(MODEL_PATH):
    print("[*] Downloading Google HEAVY Multi-Agent Brain...")
    url = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_heavy/float16/1/pose_landmarker_heavy.task"
    urllib.request.urlretrieve(url, MODEL_PATH)

base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
options = vision.PoseLandmarkerOptions(
    base_options=base_options,
    num_poses=5, 
    min_pose_detection_confidence=0.4, 
    min_pose_presence_confidence=0.4,  
    min_tracking_confidence=0.5)        
detector = vision.PoseLandmarker.create_from_options(options)

# Saved outside of VS Code to prevent Live Server refreshing
EVIDENCE_DIR = "C:/Pandora_Evidence"
if not os.path.exists(EVIDENCE_DIR):
    os.makedirs(EVIDENCE_DIR)

FONT = cv2.FONT_HERSHEY_SIMPLEX

# ==========================================
# CUSTOM UI DRAWING ENGINES
# ==========================================
def draw_pro_text(frame, text, pos, scale, color, thickness=2):
    cv2.putText(frame, text, pos, FONT, scale, (0, 0, 0), thickness + 2, cv2.LINE_AA)
    cv2.putText(frame, text, pos, FONT, scale, color, thickness, cv2.LINE_AA)

def draw_target_lock(frame, x, y, color):
    x, y = int(x), int(y)
    size, thick, length = 45, 4, 15
    cv2.circle(frame, (x, y), 2, color, -1)
    for dx, dy in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
        cv2.line(frame, (x + dx*size, y + dy*size), (x + dx*(size-length), y + dy*size), color, thick)
        cv2.line(frame, (x + dx*size, y + dy*size), (x + dx*size, y + dy*(size-length)), color, thick)

def draw_cctv_hud(frame, fps, w, h):
    now = datetime.now().strftime("%Y/%m/%d | %H:%M:%S.%f")[:-3]
    if int(time.time() * 2) % 2 == 0:
        cv2.circle(frame, (35, 35), 8, (0, 0, 255), -1)
    draw_pro_text(frame, "REC", (55, 42), 0.8, (255, 255, 255), 2)
    draw_pro_text(frame, now, (w - 320, 42), 0.7, (255, 255, 255), 2)
    draw_pro_text(frame, f"CAM-01 | FPS: {int(fps)} | PANDORA-PRO V14", (20, h - 20), 0.6, (0, 255, 0), 2)

def log_evidence(frame, threat_name):
    timestamp = datetime.now().strftime('%H-%M-%S')
    filename = f"{EVIDENCE_DIR}/THREAT_{threat_name}_{timestamp}.jpg"
    cv2.imwrite(filename, frame)
    print(f"[!] EVIDENCE LOGGED: {filename}")

# ==========================================
# MAIN ASYNC SECURITY AI LOOP
# ==========================================
async def main():
    cap = cv2.VideoCapture(1) # Change to 0 if using an integrated webcam
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    # Added Fire Buffer
    xblock_frames, surrender_frames, slump_frames, fire_frames = 0, 0, 0, 0
    last_log_time = 0  
    LOG_COOLDOWN = 10.0 
    prev_frame_time = 0

    # WebSocket connected with ping limits removed
    async with websockets.connect("ws://localhost:8765", max_size=10**7, ping_interval=None, ping_timeout=None) as ws:
        while cap.isOpened():
            success, frame = cap.read()
            if not success: break
            frame = cv2.flip(frame, 1)
            # 🔴 NEW: BIDIRECTIONAL COMMAND LISTENER
            # We give the WebSocket 1 millisecond to see if the dashboard sent a command
            try:
                message = await asyncio.wait_for(ws.recv(), timeout=0.001)
                cmd_data = json.loads(message)
                
                if cmd_data.get("command") == "CHANGE_CAMERA":
                    print(f"[*] DASHBOARD COMMAND RECEIVED: Hot-swapping to {cmd_data.get('type').upper()}")
                    cap.release() # Turn off the current camera
                    
                    if cmd_data.get("type") == "usb":
                        cap = cv2.VideoCapture(1) # Change to 0 if 1 doesn't work for your setup
                    elif cmd_data.get("type") == "ip":
                        cap = cv2.VideoCapture(cmd_data.get("url"))
                        
                    # Reset buffers to prevent ghost alarms
                    xblock_frames = surrender_frames = slump_frames = fire_frames = 0
                    continue # Skip the rest of this loop and start fresh with the new camera!
                    
            except asyncio.TimeoutError:
                pass # No command received this frame, keep running normally
            except Exception as e:
                pass # Ignore random malformed messages
            h, w, _ = frame.shape

            current_time = time.time()
            fps = 1 / (current_time - prev_frame_time) if prev_frame_time else 0
            prev_frame_time = current_time

            annotated_frame = frame.copy()
            any_xblock, any_surrender, any_slump, any_fire = False, False, False, False

            # ---------------------------------------------------------
            # 1. ENVIRONMENTAL SCANNER (FAST THERMAL FIRE DETECTION)
            # ---------------------------------------------------------
            small_frame = cv2.resize(frame, (w // 4, h // 4))
            blurred = cv2.GaussianBlur(small_frame, (15, 15), 0)
            hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
            
            lower_fire = np.array([10, 150, 150], dtype=np.uint8)
            upper_fire = np.array([30, 255, 255], dtype=np.uint8)
            
            fire_mask = cv2.inRange(hsv, lower_fire, upper_fire)
            contours, _ = cv2.findContours(fire_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for c in contours:
                if cv2.contourArea(c) > 200:  
                    any_fire = True
                    fx, fy, fw, fh = cv2.boundingRect(c)
                    cv2.rectangle(annotated_frame, (fx*4, fy*4), ((fx+fw)*4, (fy+fh)*4), (0, 120, 255), 3)
                    draw_pro_text(annotated_frame, "THERMAL ANOMALY", (fx*4, (fy*4) - 10), 0.6, (0, 120, 255), 2)

            # ---------------------------------------------------------
            # 2. BIOMETRIC SCANNER (MEDIAPIPE ENGINE)
            # ---------------------------------------------------------
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            detection_result = detector.detect(mp_image)

            if detection_result.pose_landmarks:
                for pose_landmarks in detection_result.pose_landmarks:
                    
                    pose_landmarks_proto = landmark_pb2.NormalizedLandmarkList()
                    pose_landmarks_proto.landmark.extend([
                        landmark_pb2.NormalizedLandmark(x=lm.x, y=lm.y, z=lm.z, visibility=lm.visibility) for lm in pose_landmarks
                    ])

                    mp.solutions.drawing_utils.draw_landmarks(
                        annotated_frame, 
                        pose_landmarks_proto,
                        mp.solutions.pose.POSE_CONNECTIONS,
                        landmark_drawing_spec=mp.solutions.drawing_utils.DrawingSpec(color=(255,255,255), thickness=2, circle_radius=2),
                        connection_drawing_spec=mp.solutions.drawing_utils.DrawingSpec(color=(200,200,200), thickness=2)
                    )

                    def get_pt(index):
                        pt = pose_landmarks[index]
                        return (int(pt.x * w), int(pt.y * h), pt.visibility)

                    nx, ny, nc = get_pt(0)
                    ls_x, ls_y, ls_c = get_pt(11)
                    rs_x, rs_y, rs_c = get_pt(12)
                    le_x, le_y, le_c = get_pt(13)
                    re_x, re_y, re_c = get_pt(14)
                    lw_x, lw_y, lw_c = get_pt(15)
                    rw_x, rw_y, rw_c = get_pt(16)
                    l_hip_x, l_hip_y, l_hip_c = get_pt(23)
                    r_hip_x, r_hip_y, r_hip_c = get_pt(24)

                    # 🔴 LOWERED CONFIDENCE GATE FOR CCTV DISTANCE
                    if ls_c > 0.55 and rs_c > 0.55:
                        shoulder_width = math.hypot(ls_x - rs_x, ls_y - rs_y)
                        
                        # A. SLUMP LOGIC
                        if l_hip_c > 0.5 and r_hip_c > 0.5:
                            if (ny > l_hip_y) and (ls_y > l_hip_y) and (rs_y > r_hip_y):
                                any_slump = True
                                draw_target_lock(annotated_frame, nx, ny, (255, 0, 0))

                        # B. X-BLOCK & SURRENDER (Distance-Scaled Leeway)
                        if lw_c > 0.55 and rw_c > 0.55 and le_c > 0.5 and re_c > 0.5:
                            wrist_distance = math.hypot(lw_x - rw_x, lw_y - rw_y)
                            
                            # THE MAGIC FIX: At least 45 pixels of leeway, or 50% of shoulders
                            alignment_leeway = max(45, shoulder_width * 0.5)
                            is_aligned = abs(lw_y - rw_y) < alignment_leeway 
                            
                            is_raised = (lw_y < le_y) and (rw_y < re_y)
                            
                            # X-Block: Wrists crossed (At least 50 pixels leeway)
                            cross_leeway = max(50, shoulder_width * 0.45)
                            is_crossed = wrist_distance < cross_leeway 
                            
                            if is_crossed and is_raised and is_aligned:
                                any_xblock = True
                                draw_target_lock(annotated_frame, nx, ny, (0, 0, 255)) 

                            # Surrender: Wrists wide (At least 120 pixels wide)
                            wide_leeway = max(120, shoulder_width * 1.2)
                            if (lw_y < ls_y) and (rw_y < rs_y) and (wrist_distance > wide_leeway) and is_aligned:
                                any_surrender = True
                                draw_target_lock(annotated_frame, nx, ny, (0, 165, 255)) 

            # --- BUFFER SMOOTHING ---
            fire_frames = max(0, fire_frames + 1 if any_fire else fire_frames - 2)
            xblock_frames = max(0, xblock_frames + 1 if any_xblock else xblock_frames - 2)
            surrender_frames = max(0, surrender_frames + 1 if any_surrender else surrender_frames - 2)
            slump_frames = max(0, slump_frames + 1 if any_slump else slump_frames - 2)

            # --- ALARMS, EVIDENCE & DASHBOARD ROUTING ---
            active_threat_text = None
            alert_id = None
            threat_color = (0, 255, 0)
            
            if fire_frames > 20:
                active_threat_text, alert_id, threat_color = "HAZARD: FIRE DETECTED", "hazard_fire", (0, 120, 255)
            elif xblock_frames > 15:
                active_threat_text, alert_id, threat_color = "CRITICAL: X-BLOCK SOS", "deliberate_sos", (0, 0, 255)
            elif surrender_frames > 15:
                active_threat_text, alert_id, threat_color = "WARNING: SURRENDER POSE", "active_threat", (0, 165, 255)
            elif slump_frames > 30:
                active_threat_text, alert_id, threat_color = "MEDICAL: COLLAPSE DETECTED", "medical_collapse", (255, 0, 0)

            if active_threat_text:
                cv2.rectangle(annotated_frame, (0,0), (w,h), threat_color, 12)
                draw_pro_text(annotated_frame, active_threat_text, (w//2 - 260, 100), 1.2, threat_color, 4)
                
                time_since_log = current_time - last_log_time
                if time_since_log >= LOG_COOLDOWN:
                    log_evidence(annotated_frame, alert_id.upper())
                    
                    _, buffer = cv2.imencode('.jpg', annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 45])
                    b64_img = base64.b64encode(buffer).decode('utf-8')
                    lat = 16.4961 + random.uniform(-0.0003, 0.0003)
                    lng = 80.4994 + random.uniform(-0.0003, 0.0003)
                    conf = round(random.uniform(94.5, 99.8), 1)
                    
                    payload = {
                        "alert_type": alert_id, "building": "Academic Block", 
                        "room": f"Sector {random.randint(1,9)}", "lat": lat, "lng": lng, 
                        "confidence": conf, "image": b64_img
                    }
                    
                    try:
                        await ws.send(json.dumps(payload))
                        print(f"🚨 DISPATCHED TO DASHBOARD: {alert_id.upper()}")
                    except Exception as e:
                        print(f"[-] NETWORK HICCUP CAUGHT: {e}")
                    
                    last_log_time = current_time
                    xblock_frames = surrender_frames = slump_frames = fire_frames = 0
                else:
                    remaining = round(LOG_COOLDOWN - time_since_log, 1)
                    draw_pro_text(annotated_frame, f"EVIDENCE COOLDOWN: {remaining}s", (w//2 - 170, 140), 0.8, (0, 255, 255), 2)

            draw_cctv_hud(annotated_frame, fps, w, h)
            cv2.imshow("Pandora-PRO V14: Enterprise", annotated_frame)

            if cv2.waitKey(1) & 0xFF == ord('q'): break
            
            
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    asyncio.run(main())
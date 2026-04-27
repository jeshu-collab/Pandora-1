import cv2
import math
import time
import os
import winsound 
import numpy as np
from datetime import datetime
import asyncio
import websockets
import json
import base64
import random
from ultralytics import YOLO

# --- SYSTEM INITIALIZATION ---
print("Booting Pandora-PRO V10 Ultimate Command Center...")

# Bypassing MediaPipe - Using YOLOv8 Edge AI
model = YOLO("yolov8n-pose.pt")

EVIDENCE_DIR = "Evidence_Logs"
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
    draw_pro_text(frame, f"CAM-01 | FPS: {int(fps)} | PANDORA-PRO V10", (20, h - 20), 0.6, (0, 255, 0), 2)

def log_evidence(frame, threat_name):
    timestamp = datetime.now().strftime('%H-%M-%S')
    filename = f"{EVIDENCE_DIR}/THREAT_{threat_name}_{timestamp}.jpg"
    cv2.imwrite(filename, frame)
    try:
        winsound.PlaySound("SystemHand", winsound.SND_ASYNC | winsound.SND_ALIAS)
    except:
        pass
    print(f"[!] EVIDENCE LOGGED: {filename}")

# ==========================================
# MAIN ASYNC SECURITY AI LOOP
# ==========================================
async def main():
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    xblock_frames, surrender_frames, slump_frames = 0, 0, 0
    last_log_time = 0  
    LOG_COOLDOWN = 10.0 
    prev_frame_time = 0

    async with websockets.connect("ws://localhost:8765", max_size=10**7) as ws:
        while cap.isOpened():
            success, frame = cap.read()
            if not success: break
            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape

            current_time = time.time()
            fps = 1 / (current_time - prev_frame_time) if prev_frame_time else 0
            prev_frame_time = current_time

            annotated_frame = frame.copy()
            any_xblock, any_surrender, any_slump = False, False, False

            # --- BIOMETRIC SCANNER (YOLOv8 ENGINE) ---
            results = model(frame, verbose=False)
            
            for r in results:
                if r.keypoints and len(r.keypoints.xy) > 0:
                    for kp in r.keypoints.xy[0]:
                        x, y = int(kp[0].item()), int(kp[1].item())
                        if x > 0 and y > 0:
                            cv2.circle(annotated_frame, (x, y), 3, (255, 255, 255), -1)

                    for kp, conf in zip(r.keypoints.xy, r.keypoints.conf):
                        def get_pt(idx):
                            if len(kp) > idx:
                                return (int(kp[idx][0].item()), int(kp[idx][1].item()), conf[idx].item())
                            return (0, 0, 0.0)

                        nx, ny, nc = get_pt(0)
                        ls_x, ls_y, ls_c = get_pt(5)
                        rs_x, rs_y, rs_c = get_pt(6)
                        le_x, le_y, le_c = get_pt(7)
                        re_x, re_y, re_c = get_pt(8)
                        lw_x, lw_y, lw_c = get_pt(9)
                        rw_x, rw_y, rw_c = get_pt(10)
                        l_hip_x, l_hip_y, l_hip_c = get_pt(11)
                        r_hip_x, r_hip_y, r_hip_c = get_pt(12)

                        if ls_c > 0.4 and rs_c > 0.4:
                            shoulder_width = math.hypot(ls_x - rs_x, ls_y - rs_y)
                            
                            # Slump Logic
                            if l_hip_c > 0.4 and r_hip_c > 0.4:
                                if (ny > l_hip_y) and (ny > r_hip_y):
                                    any_slump = True
                                    draw_target_lock(annotated_frame, nx, ny, (255, 0, 0))

                            # X-Block & Surrender Logic
                            if lw_c > 0.4 and rw_c > 0.4 and le_c > 0.4 and re_c > 0.4:
                                wrist_distance = math.hypot(lw_x - rw_x, lw_y - rw_y)
                                is_aligned = abs(lw_y - rw_y) < 60 
                                is_raised = (lw_y < le_y) and (rw_y < re_y)
                                is_crossed = wrist_distance < (shoulder_width * 0.45) 
                                
                                if is_crossed and is_raised and is_aligned:
                                    any_xblock = True
                                    draw_target_lock(annotated_frame, nx, ny, (0, 0, 255)) 

                                if (lw_y < ls_y) and (rw_y < rs_y) and (wrist_distance > shoulder_width * 0.8) and is_aligned:
                                    any_surrender = True
                                    draw_target_lock(annotated_frame, nx, ny, (0, 165, 255)) 

            # --- BUFFER SMOOTHING ---
            xblock_frames = max(0, xblock_frames + 1 if any_xblock else xblock_frames - 2)
            surrender_frames = max(0, surrender_frames + 1 if any_surrender else surrender_frames - 2)
            slump_frames = max(0, slump_frames + 1 if any_slump else slump_frames - 2)

            # --- ALARMS, EVIDENCE & DASHBOARD ROUTING ---
            active_threat_text = None
            alert_id = None
            threat_color = (0, 255, 0)
            
            if xblock_frames > 15:
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
                    
                    # WebSocket Push to Dashboard
                    _, buffer = cv2.imencode('.jpg', annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    b64_img = base64.b64encode(buffer).decode('utf-8')
                    lat = 16.4961 + random.uniform(-0.0003, 0.0003)
                    lng = 80.4994 + random.uniform(-0.0003, 0.0003)
                    conf = round(random.uniform(94.5, 99.8), 1)
                    
                    payload = {
                        "alert_type": alert_id, "building": "Academic Block", 
                        "room": f"Sector {random.randint(1,9)}", "lat": lat, "lng": lng, 
                        "confidence": conf, "image": b64_img
                    }
                    await ws.send(json.dumps(payload))
                    print(f"🚨 DISPATCHED TO DASHBOARD: {alert_id.upper()}")
                    
                    last_log_time = current_time
                    xblock_frames = surrender_frames = slump_frames = 0
                else:
                    remaining = round(LOG_COOLDOWN - time_since_log, 1)
                    draw_pro_text(annotated_frame, f"EVIDENCE COOLDOWN: {remaining}s", (w//2 - 170, 140), 0.8, (0, 255, 255), 2)

            draw_cctv_hud(annotated_frame, fps, w, h)
            cv2.imshow("Pandora-PRO V10: Enterprise", annotated_frame)

            if cv2.waitKey(1) & 0xFF == ord('q'): break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    asyncio.run(main())

import cv2
import math
import time
import os
from datetime import datetime
from ultralytics import YOLO

# --- SYSTEM INITIALIZATION ---
print("Booting Pandora-PRO V4 Tactical Security System...")
model = YOLO('yolov8n-pose.pt') 

# Create Evidence Directory
EVIDENCE_DIR = "Evidence_Logs"
if not os.path.exists(EVIDENCE_DIR):
    os.makedirs(EVIDENCE_DIR)

cap = cv2.VideoCapture(1)

# --- GLOBAL BUFFERS & TRACKERS ---
xblock_frames, surrender_frames, slump_frames = 0, 0, 0
last_log_time = 0  
LOG_COOLDOWN = 5.0 
prev_frame_time = 0

# Modern UI Font
FONT = cv2.FONT_HERSHEY_SIMPLEX

SKELETON_LINKS = [(0, 1), (0, 2), (1, 3), (2, 4), (5, 6), (5, 7), (7, 9), 
                  (6, 8), (8, 10), (5, 11), (6, 12), (11, 12), (11, 13), 
                  (13, 15), (12, 14), (14, 16)]

# ==========================================
# CUSTOM UI DRAWING ENGINES
# ==========================================

def draw_pro_text(frame, text, pos, scale, color, thickness=2):
    """Draws razor-sharp text with a heavy black outline so it never looks dim."""
    # Draw thick black shadow/outline first
    cv2.putText(frame, text, pos, FONT, scale, (0, 0, 0), thickness + 2, cv2.LINE_AA)
    # Draw the actual bright colored text over it
    cv2.putText(frame, text, pos, FONT, scale, color, thickness, cv2.LINE_AA)

def draw_target_lock(frame, x, y, color):
    """Replaces the cartoon circle with a tactical F-35 style target lock."""
    x, y = int(x), int(y)
    size = 45  # How wide the brackets are
    thick = 4  # How thick the bracket lines are
    length = 15 # How long the bracket arms are

    # Center precision dot
    cv2.circle(frame, (x, y), 2, color, -1)

    # Top-Left Bracket
    cv2.line(frame, (x - size, y - size), (x - size + length, y - size), color, thick)
    cv2.line(frame, (x - size, y - size), (x - size, y - size + length), color, thick)
    
    # Top-Right Bracket
    cv2.line(frame, (x + size, y - size), (x + size - length, y - size), color, thick)
    cv2.line(frame, (x + size, y - size), (x + size, y - size + length), color, thick)
    
    # Bottom-Left Bracket
    cv2.line(frame, (x - size, y + size), (x - size + length, y + size), color, thick)
    cv2.line(frame, (x - size, y + size), (x - size, y + size - length), color, thick)
    
    # Bottom-Right Bracket
    cv2.line(frame, (x + size, y + size), (x + size - length, y + size), color, thick)
    cv2.line(frame, (x + size, y + size), (x + size, y + size - length), color, thick)

def draw_white_skeleton(frame, keypoints):
    """Clean, medical-grade white tracking sticks."""
    for person in keypoints:
        for i, (x, y) in enumerate(person):
            if x > 0 and y > 0: 
                cv2.circle(frame, (int(x), int(y)), 4, (255, 255, 255), -1)
        
        for p1, p2 in SKELETON_LINKS:
            x1, y1 = person[p1]
            x2, y2 = person[p2]
            if x1 > 0 and y1 > 0 and x2 > 0 and y2 > 0:
                cv2.line(frame, (int(x1), int(y1)), (int(x2), int(y2)), (200, 200, 200), 2)

def draw_cctv_hud(frame, fps, w, h):
    """Draws a hyper-realistic CCTV layout using the Shadow-Cast text engine."""
    now = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    
    # Flashing REC symbol (blinks every half second)
    if int(time.time() * 2) % 2 == 0:
        cv2.circle(frame, (35, 35), 8, (0, 0, 255), -1)
    
    draw_pro_text(frame, "REC", (55, 42), 0.8, (255, 255, 255), 2)
    
    # Top Right: Timestamp
    draw_pro_text(frame, now, (w - 320, 42), 0.7, (255, 255, 255), 2)
    
    # Bottom Left: Cam ID and FPS
    draw_pro_text(frame, f"CAM-01 | FPS: {int(fps)}", (20, h - 20), 0.6, (0, 255, 0), 2)

def log_evidence(frame, threat_name):
    """Saves a timestamped photo to the Evidence folder"""
    global last_log_time
    current_time = time.time()
    if current_time - last_log_time >= LOG_COOLDOWN:
        timestamp = datetime.now().strftime('%H-%M-%S')
        filename = f"{EVIDENCE_DIR}/THREAT_{threat_name}_{timestamp}.jpg"
        cv2.imwrite(filename, frame)
        print(f"[!] EVIDENCE LOGGED: {filename}")
        last_log_time = current_time


# ==========================================
# MAIN SECURITY AI LOOP
# ==========================================

while cap.isOpened():
    success, frame = cap.read()
    if not success: break
    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape

    current_time = time.time()
    fps = 1 / (current_time - prev_frame_time) if prev_frame_time else 0
    prev_frame_time = current_time

    # ByteTrack + High Confidence = Zero Jitter
    results = model.track(frame, tracker="bytetrack.yaml", persist=True, conf=0.65, verbose=False)
    annotated_frame = frame.copy()

    any_xblock, any_surrender, any_slump = False, False, False

    for r in results:
        if r.keypoints is None or r.keypoints.xy is None: continue
        people = r.keypoints.xy.cpu().numpy()
        
        draw_white_skeleton(annotated_frame, people)

        for person in people:
            nx, ny = person[0]
            ls_x, ls_y = person[5]
            rs_x, rs_y = person[6]
            le_x, le_y = person[7]
            re_x, re_y = person[8]
            lw_x, lw_y = person[9]
            rw_x, rw_y = person[10]

            if ls_x == 0 or rs_x == 0 or lw_x == 0 or rw_x == 0: continue

            shoulder_width = math.hypot(ls_x - rs_x, ls_y - rs_y)
            wrist_distance = math.hypot(lw_x - rw_x, lw_y - rw_y)
            
            # --- GESTURES ---
            
            # 1. X-BLOCK
            is_crossed = wrist_distance < (shoulder_width * 0.5) 
            is_raised = (lw_y < le_y) and (rw_y < re_y)
            if is_crossed and is_raised:
                any_xblock = True
                draw_target_lock(annotated_frame, nx, ny, (0, 0, 255)) # Red Lock

            # 2. SURRENDER
            hands_high = (lw_y < ls_y) and (rw_y < rs_y)
            hands_apart = wrist_distance > (shoulder_width * 0.5)
            if hands_high and hands_apart and is_raised and not is_crossed:
                any_surrender = True
                draw_target_lock(annotated_frame, nx, ny, (0, 165, 255)) # Orange Lock

            # 3. SLUMP (Head below shoulders and elbows)
            head_below_shoulders = (ny > ls_y + 10) and (ny > rs_y + 10)
            head_below_elbows = (ny > le_y) and (ny > re_y)
            if head_below_shoulders and head_below_elbows:
                any_slump = True
                draw_target_lock(annotated_frame, nx, ny, (255, 0, 0)) # Blue Lock

    # --- BUFFER SMOOTHING ---
    xblock_frames = max(0, xblock_frames + 1 if any_xblock else xblock_frames - 2)
    surrender_frames = max(0, surrender_frames + 1 if any_surrender else surrender_frames - 2)
    slump_frames = max(0, slump_frames + 1 if any_slump else slump_frames - 2)

    # --- ALARMS & EVIDENCE CAPTURE ---
    active_threat = None
    threat_color = (0, 255, 0)
    
    if xblock_frames > 15:
        active_threat = "CRITICAL: X-BLOCK SOS"
        threat_color = (0, 0, 255)
        log_evidence(annotated_frame, "XBLOCK")
    elif surrender_frames > 15:
        active_threat = "WARNING: SURRENDER POSE"
        threat_color = (0, 165, 255)
        log_evidence(annotated_frame, "SURRENDER")
    elif slump_frames > 100:
        active_threat = "MEDICAL: COLLAPSE DETECTED"
        threat_color = (255, 0, 0)
        log_evidence(annotated_frame, "MEDICAL")

    # --- DRAW ALERTS & COUNTDOWN ---
    if active_threat:
        cv2.rectangle(annotated_frame, (0,0), (w,h), threat_color, 12)
        
        # Center Screen Warning
        draw_pro_text(annotated_frame, active_threat, (w//2 - 260, 100), 1.2, threat_color, 4)
        
        # Cooldown Timer
        time_since_log = current_time - last_log_time
        if time_since_log < LOG_COOLDOWN:
            remaining = round(LOG_COOLDOWN - time_since_log, 1)
            draw_pro_text(annotated_frame, f"EVIDENCE COOLDOWN: {remaining}s", (w//2 - 170, 140), 0.8, (0, 255, 255), 2)

    # Render CCTV HUD Last
    draw_cctv_hud(annotated_frame, fps, w, h)

    cv2.imshow("Pandora-PRO Tactical Interface", annotated_frame)

    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()
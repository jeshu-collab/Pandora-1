import cv2
import mediapipe as mp
import math

# Boot up the AI
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(min_detection_confidence=0.7, min_tracking_confidence=0.7) # Added tracking confidence for stability
mp_drawing = mp.solutions.drawing_utils

cap = cv2.VideoCapture(1)
print("Pandora-1 Vision Engine Online. High-Accuracy Mode Active...")

# --- THE TIME BUFFERS ---
xblock_frames = 0
surrender_frames = 0
slump_frames = 0

while cap.isOpened():
    success, frame = cap.read()
    if not success: break

    frame = cv2.flip(frame, 1)
    h, w, c = frame.shape

    results = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

    if results.pose_landmarks:
        # Draw skeleton (dimmed down so it's less distracting)
        mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                                  mp_drawing.DrawingSpec(color=(100,100,100), thickness=2, circle_radius=2),
                                  mp_drawing.DrawingSpec(color=(200,200,200), thickness=2, circle_radius=2))

        landmarks = results.pose_landmarks.landmark
        nose = landmarks[0]
        left_shoulder = landmarks[11]
        right_shoulder = landmarks[12]
        left_elbow = landmarks[13]
        right_elbow = landmarks[14]
        left_wrist = landmarks[15]
        right_wrist = landmarks[16]
        
        n_y = int(nose.y * h)
        ls_x, ls_y = int(left_shoulder.x * w), int(left_shoulder.y * h)
        rs_x, rs_y = int(right_shoulder.x * w), int(right_shoulder.y * h)
        le_y, re_y = int(left_elbow.y * h), int(right_elbow.y * h)
        lw_x, lw_y = int(left_wrist.x * w), int(left_wrist.y * h)
        rw_x, rw_y = int(right_wrist.x * w), int(right_wrist.y * h)

        # --- THE MATH & FILTERS ---
        shoulder_width = math.hypot(ls_x - rs_x, ls_y - rs_y)
        wrist_distance = math.hypot(lw_x - rw_x, lw_y - rw_y)
        
        # GESTURE 1: X-BLOCK
        # Wrists are close, and both wrists are above the elbows
        is_crossed = wrist_distance < (shoulder_width * 0.5) 
        is_raised = (lw_y < le_y) and (rw_y < re_y)
        is_xblock = is_crossed and is_raised

        # GESTURE 2: SURRENDER (Upgraded Math)
        # Wrists are above shoulders, wrists are above elbows, and hands are apart
        hands_high = (lw_y < ls_y) and (rw_y < rs_y)
        hands_apart = wrist_distance > (shoulder_width * 0.5) # Hands just need to be apart, not super wide
        is_surrender = hands_high and hands_apart and is_raised

        # GESTURE 3: THE SLUMP
        is_slumped = (n_y > ls_y) and (n_y > rs_y)

        # --- THE FORGIVENESS BUFFERS (Anti-Jitter) ---
        # If true, add 1. If false, subtract 2. 
        # This prevents 1-frame glitches from ruining the tracking!
        
        if is_xblock: xblock_frames += 1
        else: xblock_frames =0

        if is_surrender: surrender_frames += 1
        else: surrender_frames = 0

        if is_slumped: slump_frames += 1
        else: slump_frames -= 4

       # Cap the buffers so they don't drop below 0 (but let them count to infinity!)
        xblock_frames = max(0, xblock_frames) 
        surrender_frames = max(0, surrender_frames)
        slump_frames = max(0, slump_frames)

        # --- TRIGGER THE ALERTS ---
        
        # X-Block (Triggers at 100)
        if xblock_frames > 100:
            cv2.putText(frame, "THREAT: X-BLOCK SOS!", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 4)
            cv2.rectangle(frame, (0,0), (w,h), (0, 0, 255), 8)
            
        # Surrender (Triggers at 100)
        elif surrender_frames > 100:
            cv2.putText(frame, "WARNING: SURRENDER DETECTED", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 165, 255), 4)
            cv2.rectangle(frame, (0,0), (w,h), (0, 165, 255), 8)
            
        # Slump (Triggers at 100)
        elif slump_frames > 100:
            cv2.putText(frame, "MEDICAL: SLUMP / COLLAPSE", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 0, 0), 4)
            cv2.rectangle(frame, (0,0), (w,h), (255, 0, 0), 8)

        # Clean Debug UI
        cv2.putText(frame, f"X-Block: {xblock_frames}/100 | Surrender: {surrender_frames}/100 | Slump: {slump_frames}/100", 
                    (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    cv2.imshow("Pandora-1: Multi-Threat Mode", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()
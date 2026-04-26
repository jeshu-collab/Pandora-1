import cv2
import mediapipe as mp
import math

# Boot up the AI
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(min_detection_confidence=0.7)
mp_drawing = mp.solutions.drawing_utils

# Turn on the Camera
cap = cv2.VideoCapture(0)
print("Pandora-1 Vision Engine Online. Multi-Threat Mode Active...")

# --- THE TIME BUFFERS ---
# We now track the hold time for all three gestures separately
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
        mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)

        # 1. Grab Joints (Added the Nose for the Slump detection)
        landmarks = results.pose_landmarks.landmark
        nose = landmarks[0]
        left_shoulder = landmarks[11]
        right_shoulder = landmarks[12]
        left_elbow = landmarks[13]
        right_elbow = landmarks[14]
        left_wrist = landmarks[15]
        right_wrist = landmarks[16]
        
        # Convert to screen pixels
        n_y = int(nose.y * h)
        ls_x, ls_y = int(left_shoulder.x * w), int(left_shoulder.y * h)
        rs_x, rs_y = int(right_shoulder.x * w), int(right_shoulder.y * h)
        le_y, re_y = int(left_elbow.y * h), int(right_elbow.y * h)
        lw_x, lw_y = int(left_wrist.x * w), int(left_wrist.y * h)
        rw_x, rw_y = int(right_wrist.x * w), int(right_wrist.y * h)

        # --- THE MATH & FILTERS ---
        shoulder_width = math.hypot(ls_x - rs_x, ls_y - rs_y)
        wrist_distance = math.hypot(lw_x - rw_x, lw_y - rw_y)
        
        # GESTURE 1: X-BLOCK (Untouched)
        is_crossed = wrist_distance < (shoulder_width * 0.6)
        is_raised = (lw_y < le_y) and (rw_y < re_y)

        # GESTURE 2: SURRENDER
        # Wrists above elbows, elbows above shoulders, and NOT crossed.
        is_surrender = (lw_y < le_y < ls_y) and (rw_y < re_y < rs_y) and not is_crossed

        # GESTURE 3: THE SLUMP
        # Nose drops below BOTH shoulders. 
        is_slumped = (n_y > ls_y) and (n_y > rs_y)

        # --- UPDATE TIME BUFFERS ---
        if is_crossed and is_raised:
            xblock_frames += 1
        else: xblock_frames = 0

        if is_surrender:
            surrender_frames += 1
        else: surrender_frames = 0

        if is_slumped:
            slump_frames += 1
        else: slump_frames = 0

        # --- TRIGGER THE ALERTS ---
        # We check the buffers and send a specific UI alert
        
        # 1. X-Block (100 frames) -> Red Threat
        if xblock_frames > 100:
            cv2.putText(frame, "THREAT: X-BLOCK SOS!", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 4)
            cv2.rectangle(frame, (0,0), (w,h), (0, 0, 255), 8) # Red Border
            
        # 2. Surrender (100 frames) -> Orange Threat
        elif surrender_frames > 100:
            cv2.putText(frame, "WARNING: SURRENDER DETECTED", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 165, 255), 4)
            cv2.rectangle(frame, (0,0), (w,h), (0, 165, 255), 8) # Orange Border
            
        # 3. Slump (100 frames) -> Blue Medical Alert
        # (Requires a longer hold time so it doesn't trigger if you just bend over to tie your shoe)
        elif slump_frames > 100:
            cv2.putText(frame, "MEDICAL: SLUMP / COLLAPSE", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 0, 0), 4)
            cv2.rectangle(frame, (0,0), (w,h), (255, 0, 0), 8) # Blue Border

        # Debug text to see what the AI is thinking
        cv2.putText(frame, f"Buffers - X: {xblock_frames} | Surrender: {surrender_frames} | Slump: {slump_frames}", 
                    (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    cv2.imshow("Pandora-1: Multi-Threat Mode", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()
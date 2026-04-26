import cv2
import mediapipe as mp
import math

# Boot up the AI
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(min_detection_confidence=0.7)
mp_drawing = mp.solutions.drawing_utils

# Turn on the Camera
cap = cv2.VideoCapture(0)
print("Pandora-1 Vision Engine Online. CCTV Mode Active...")

# --- THE TIME BUFFER VARIABLE ---
consecutive_frames = 0  # This will count how long you hold the pose

while cap.isOpened():
    success, frame = cap.read()
    if not success: break

    frame = cv2.flip(frame, 1)
    h, w, c = frame.shape

    results = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

    if results.pose_landmarks:
        mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)

        # 1. Grab ALL the necessary joints
        landmarks = results.pose_landmarks.landmark
        left_shoulder = landmarks[11]
        right_shoulder = landmarks[12]
        left_elbow = landmarks[13]
        right_elbow = landmarks[14]
        left_wrist = landmarks[15]
        right_wrist = landmarks[16]
        
        # Convert to screen pixels
        ls_x, ls_y = int(left_shoulder.x * w), int(left_shoulder.y * h)
        rs_x, rs_y = int(right_shoulder.x * w), int(right_shoulder.y * h)
        le_y, re_y = int(left_elbow.y * h), int(right_elbow.y * h) # Only need Y for elbows
        lw_x, lw_y = int(left_wrist.x * w), int(left_wrist.y * h)
        rw_x, rw_y = int(right_wrist.x * w), int(right_wrist.y * h)

        # --- THE MATH & FILTERS ---
        
        # Filter 1: Dynamic Scaling (Measure shoulder width)
        shoulder_width = math.hypot(ls_x - rs_x, ls_y - rs_y)
        wrist_distance = math.hypot(lw_x - rw_x, lw_y - rw_y)
        
        # Check: Are the wrists crossed? (Distance is less than half the shoulder width)
        is_crossed = wrist_distance < (shoulder_width * 0.6)

        # Filter 2: The Elbow Rule (Are wrists physically HIGHER than elbows? Remember Y is smaller at the top)
        is_raised = (lw_y < le_y) and (rw_y < re_y)

        # Filter 3: The Time Buffer
        if is_crossed and is_raised:
            consecutive_frames += 1  # Add a frame to the counter
            
            # Draw a yellow warning box while it "charges up"
            cv2.putText(frame, f"ANALYZING... {consecutive_frames}/100", (20, 80), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 3)
        else:
            consecutive_frames = 0   # Reset if they drop their arms

        # --- THE TRIGGER ---
        # If they hold the pose for 100 frames (roughly 0.5 to 1 second)
        if consecutive_frames > 100:
            cv2.putText(frame, "CRITICAL: X-BLOCK SOS VERIFIED!", (20, 140), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 4)
            # You can also draw a massive red box around the frame here for effect
            cv2.rectangle(frame, (0,0), (w,h), (0, 0, 255), 10)

        # Print data to screen for debugging
        cv2.putText(frame, f"Crossed: {is_crossed} | Raised: {is_raised}", (20, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    cv2.imshow("Pandora-1: CCTV Mode", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()
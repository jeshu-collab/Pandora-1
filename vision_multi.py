import cv2
import math
from ultralytics import YOLO

# 1. Boot up the YOLOv8 Brain 
# (It will download a small 6MB file the very first time you run this)
print("Loading YOLOv8 Enterprise AI...")
model = YOLO('yolov8n-pose.pt') 

cap = cv2.VideoCapture(1)
print("Pandora-2 Multi-Agent Tracker Online. Scanning room...")

# --- THE GLOBAL TIME BUFFERS ---
# These track if ANYONE in the room is doing the gesture
xblock_frames = 0
surrender_frames = 0
slump_frames = 0

while cap.isOpened():
    success, frame = cap.read()
    if not success: break
    frame = cv2.flip(frame, 1)

    # 2. Hand the frame to YOLO
    results = model(frame, verbose=False) # verbose=False stops it from spamming the terminal
    
    # 3. Use YOLO's built-in drawing tool for beautiful skeletons
    annotated_frame = results[0].plot(labels=False, boxes=False)

    # Reset flags for this specific frame
    any_xblock = False
    any_surrender = False
    any_slump = False

    # 4. Loop through EVERY person YOLO found in the room
    for r in results:
        # If no keypoints are found, skip
        if r.keypoints is None or r.keypoints.xy is None: continue
        
        # Convert YOLO data to a standard Python list
        people = r.keypoints.xy.cpu().numpy()

        for person in people:
            # YOLO Joint Index (COCO Format):
            # 0: Nose | 5: L-Shoulder, 6: R-Shoulder
            # 7: L-Elbow, 8: R-Elbow | 9: L-Wrist, 10: R-Wrist
            
            nx, ny = person[0]
            ls_x, ls_y = person[5]
            rs_x, rs_y = person[6]
            le_x, le_y = person[7]
            re_x, re_y = person[8]
            lw_x, lw_y = person[9]
            rw_x, rw_y = person[10]

            # SAFETY CHECK: If a person is half off-screen, YOLO returns 0 for those joints.
            # We skip them to prevent the math from crashing.
            if ls_x == 0 or rs_x == 0 or lw_x == 0 or rw_x == 0:
                continue

            # --- THE MATH ---
            shoulder_width = math.hypot(ls_x - rs_x, ls_y - rs_y)
            wrist_distance = math.hypot(lw_x - rw_x, lw_y - rw_y)
            
            # GESTURE 1: X-BLOCK
            is_crossed = wrist_distance < (shoulder_width * 0.5) 
            is_raised = (lw_y < le_y) and (rw_y < re_y)
            
            if is_crossed and is_raised:
                any_xblock = True
                # Draw a Red circle on the face of the specific person doing the X-Block
                cv2.circle(annotated_frame, (int(nx), int(ny)), 25, (0, 0, 255), -1)

            # GESTURE 2: SURRENDER
            hands_high = (lw_y < ls_y) and (rw_y < rs_y)
            hands_apart = wrist_distance > (shoulder_width * 0.5)
            
            if hands_high and hands_apart and is_raised and not is_crossed:
                any_surrender = True
                # Draw an Orange circle on the person surrendering
                cv2.circle(annotated_frame, (int(nx), int(ny)), 25, (0, 165, 255), -1)

            # GESTURE 3: SLUMP
            if ny > ls_y and ny > rs_y:
                any_slump = True
                # Draw a Blue circle on the person collapsing
                cv2.circle(annotated_frame, (int(nx), int(ny)), 25, (255, 0, 0), -1)

    # --- THE GLOBAL FORGIVENESS BUFFERS ---
    if any_xblock: xblock_frames += 1
    else: xblock_frames -= 2

    if any_surrender: surrender_frames += 1
    else: surrender_frames -= 2

    if any_slump: slump_frames += 1
    else: slump_frames -= 2

    xblock_frames = max(0, xblock_frames) 
    surrender_frames = max(0, surrender_frames)
    slump_frames = max(0, slump_frames)

    # --- TRIGGER THE GLOBAL ALARMS ---
    h, w, _ = annotated_frame.shape
    
    if xblock_frames > 100:
        cv2.putText(annotated_frame, "CRITICAL: MULTI-AGENT X-BLOCK!", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 4)
        cv2.rectangle(annotated_frame, (0,0), (w,h), (0, 0, 255), 8)
        
    elif surrender_frames > 100:
        cv2.putText(annotated_frame, "WARNING: SURRENDER DETECTED", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 165, 255), 4)
        cv2.rectangle(annotated_frame, (0,0), (w,h), (0, 165, 255), 8)
        
    elif slump_frames > 100:
        cv2.putText(annotated_frame, "MEDICAL: COLLAPSE DETECTED", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 0, 0), 4)
        cv2.rectangle(annotated_frame, (0,0), (w,h), (255, 0, 0), 8)

    # Show the final feed
    cv2.imshow("Pandora-2: Crowd Control", annotated_frame)

    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()
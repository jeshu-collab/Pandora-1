

```markdown
# 🚨 Pandora-PRO V14: Autonomous Security & Hazard C2 Hub

**Pandora-PRO** is a high-performance, AI-driven Command and Control (C2) ecosystem designed for real-time threat detection and emergency routing. By leveraging **Edge Computing**, the system processes complex biometric and environmental data locally, while utilizing a **Cloud-based WebSocket architecture** to provide a globalized interface for emergency responders.

Developed for the VIT-AP Hackathon, Pandora-PRO bridges the gap between passive surveillance and active autonomous intervention.

---

## 🏗️ Technical Architecture

Pandora-PRO is built on a distributed tripartite architecture:

1.  **AI Edge Node (`vision.py`)**: A heavy-duty Python engine utilizing **OpenCV** and **MediaPipe**. It performs pose estimation on 5 simultaneous subjects and executes thermal HSV masking for fire detection.
2.  **Central Command Router (`server.py`)**: An asynchronous **WebSocket server** that manages bidirectional traffic. It handles the "Smart Routing" of alerts to specific departments and commands back to the edge nodes.
3.  **C2 Interactive Dashboard (`index.html`)**: A low-latency web interface that uses **Leaflet.js** for geolocation, **JS AudioContext** for synthetic alarm generation, and volatile RAM management to stream evidence without storage overhead.

---

## ✨ Key Features

* **🧠 Scale-Invariant Biometrics**: Implements dynamic leeway math. The AI scales its detection thresholds based on the subject's distance from the camera, ensuring high accuracy for both close-range and CCTV-distance monitoring.
* **🛡️ Symmetry-Lock Anti-Ghosting**: A custom geometric filter that prevents "Skeleton Stitching" (AI accidentally merging parts of two different people) in crowded environments.
* **🔥 Thermal Core Scanner**: A non-neural environmental monitor that detects the high-intensity light core of fires, ensuring fire detection remains active even if the AI pose engine is under heavy load.
* **⚡ Bidirectional Hot-Swapping**: A unique C2 feature allowing operators to remotely command the Edge Node to switch between Local USB inputs and Cloud IP/RTSP streams via a single click.
* **🔊 Persistent Siren Engine**: Department-specific audio pulses (Square wave for Police, Sine for Medical, Sawtooth for Fire) that loop continuously until a human operator physically acknowledges the incident.

---

## 🚀 Deployment & Setup

### 1. Requirements
* Python 3.9+
* Webcam (Local) or IP Camera (Remote)
* Modern Browser (Chrome/Edge/Brave)

### 2. Installation
```bash
pip install opencv-python mediapipe websockets numpy
```

### 3. Execution Sequence
1.  **Boot the Router**: `python server.py`
2.  **Boot the AI Node**: `python vision.py`
3.  **Launch C2 Dashboard**: Open `index.html`, enter `admin` to unlock the AudioContext.

---

## 🕹️ Emergency Protocol Guide

| Threat | Trigger Action | Department |
| :--- | :--- | :--- |
| **X-BLOCK SOS** | Cross wrists raised above shoulders | Security / Police |
| **SURRENDER** | Hands wide and high in the air | Security / Police |
| **COLLAPSE** | Nose and shoulders drop below hip-line | EMS / Medical |
| **FIRE HAZARD** | Thermal core detection (Brightness > 90% in HSV) | Fire Dept |

---

## 👥 Developed By
**G. Navadeep** & **T. Jaswanth**
*GOOGLE DEVELOPER SOLUTION CHALLENGE 2026*

---

## 📜 License
This project is licensed under the MIT License - see the LICENSE file for details.
```

`pip freeze > requirements.txt`

This makes it easy for judges to install everything with one command: `pip install -r requirements.txt`. Good luck, you've built an incredible system!

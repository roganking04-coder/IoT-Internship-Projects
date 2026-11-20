# Human Detection Alerter (YOLO Person Detection)

A reliable, real-time **Human Detection and Alert System** built in Python using OpenCV and YOLO (YOLOv8 Nano). Designed specifically for Windows laptops using the integrated built-in webcam, requiring zero external hardware or sensors.

Unlike general motion detectors that trigger on moving shadows, ceiling fans, or pets, this system runs deep-learning computer vision to detect **actual human beings only** (COCO Class 0: `person`).

---

## Table of Contents
1. [Overview](#overview)
2. [Why YOLO Human Detection?](#why-yolo-human-detection)
3. [Event-Based Human Capture System](#event-based-human-capture-system)
4. [Visual, Sound, and Desktop Notifications](#visual-sound-and-desktop-notifications)
5. [Project Architecture](#project-architecture)
6. [Project Structure](#project-structure)
7. [Prerequisites and Installation](#prerequisites-and-installation)
8. [How to Run the Application](#how-to-run-the-application)
9. [Command-Line Options & Configuration](#command-line-options--configuration)
10. [Automated and Live Testing Guide](#automated-and-live-testing-guide)
11. [Running on Another Windows Laptop](#running-on-another-windows-laptop)
12. [Troubleshooting Guide](#troubleshooting-guide)

---

## Overview

The **Human Detection Alerter** monitors a live video stream from your laptop's built-in webcam. When a person enters the camera's field of view, the application:
1. Detects all humans in the frame and draws bounding boxes with detection confidence percentages (e.g., `Person 88%`).
2. Captures **exactly ONE annotated snapshot** saved into `snapshots/human_YYYYMMDD_HHMMSS_mmm.jpg` immediately upon first valid detection ($\ge 75\%$).
3. Plays **one confirmation beep** (1200 Hz tone for 150 ms) *only after* the snapshot is saved.
4. Shows a **Windows desktop notification**: *"Human Detection Alert - A person was detected. Snapshot saved successfully."*
5. Suppresses repeated snapshots and sounds while the person remains in view.
6. Starts a **1.5-second quiet period countdown** when the person leaves.
7. Automatically **re-arms** after 1.5 continuous seconds without a detected human.

---

## Why YOLO Human Detection?

| Feature | Legacy Motion Detection | YOLO Human Detection (Current) |
| :--- | :--- | :--- |
| **Detection Method** | Pixel difference / MOG2 background subtraction | YOLOv8 Nano Deep Neural Network (`yolov8n.pt`) |
| **Target Filter** | Detects *any* moving pixels | Detects strictly **humans** (COCO class ID 0) |
| **Inanimate Movement** | ❌ False alarms from swaying curtains, fans, shadows | ✅ Completely ignores non-human movement |
| **Stationary People** | ❌ May vanish if standing still | ✅ Remains detected as long as visible |
| **Confidence Scoring** | None (only pixel area $\text{px}^2$) | Real-time confidence score (e.g. `85%`, `94%`) |
| **CPU Efficiency** | Low CPU | Ultra-fast (~45 ms per frame on standard laptop CPU) |

> **Note**: Legacy motion detection is still preserved as an optional mode using `--mode motion`.

---

## Event-Based Human Capture System

```
                        [MONITORING - NO HUMAN DETECTED]
                            (Green HUD Badge - ARMED)
                                       │
                      Person Detected (Confidence >= 0.75)
                                       │
                                       ▼
                     [EVENT START: 1 SNAPSHOT & ALERTS]
                        - Log event start
                        - Save 1 Annotated Snapshot (.jpg) immediately
                        - Play 1 Confirmation Beep (winsound)
                        - Show Windows Desktop Notification
                        - Mark _in_event = True
                                       │
                                       ▼
                       [EVENT ACTIVE - PERSON REMAINS]
                               (Red HUD Badge)
                        - Live feed displays bounding boxes
                        - NO extra snapshots saved
                        - NO repeated beeps or popups
                                       │
                           Person leaves camera view
                                       │
                                       ▼
                    [QUIET PERIOD COUNTDOWN (Default: 1.5s)]
                              (Amber HUD Badge)
                                       │
                ┌──────────────────────┴──────────────────────┐
                │                                             │
      Person returns before 1.5s                    Quiet for >= 1.5 continuous seconds
                │                                             │
                ▼                                             ▼
        [Same Active Event]                         [EVENT CONCLUDED - RE-ARM]
        (NO duplicate capture)                       - Log event conclusion
                                                     - Mark _in_event = False
                                                     - Return to [MONITORING - IDLE]
```

---

## Visual, Sound, and Desktop Notifications

### A. Sound Notification
- Emits a crisp, non-blocking 1200 Hz confirmation tone for 150 ms via Windows `winsound.Beep()`.
- Plays **only after** the snapshot file has been verified written to disk.
- Runs on a background thread so the camera preview never stutters.
- Toggle anytime via `--sound` or `--no-sound` (enabled by default).

### B. Desktop Notification
- Displays a native Windows notification banner using `plyer`.
- **Title**: `Human Detection Alert`
- **Message**: `A person was detected. Snapshot saved successfully. Saved: human_20261120_234955_030.jpg`
- Dispatched asynchronously in a background thread.
- Toggle anytime via `--desktop` or `--no-desktop` (enabled by default).

### C. Live Preview HUD Notifications
- 🔴 **RED BADGE**: `HUMAN DETECTED (N People)` with green bounding boxes and confidence labels.
- 🟠 **AMBER BADGE**: `EVENT ACTIVE - QUIET COUNTDOWN (X.Xs / 1.5s)` when people leave.
- 🟢 **GREEN BADGE**: `MONITORING - NO HUMAN DETECTED` when the detector is armed and waiting.

---

## Project Structure

```
C:\motion_detection_alerter\
│
├── motion_detection_alerter.py    # Main single-file application
├── test_motion_detector.py        # Automated test suite (8 scenarios)
├── requirements.txt               # Dependencies (OpenCV, Ultralytics, Torch, Plyer)
├── README.md                      # Complete user documentation
├── yolov8n.pt                     # Pretrained YOLOv8 nano model weights (~6.2 MB)
├── motion.log                     # Rotating log file (created on run)
└── snapshots/                     # Directory for captured snapshots (created on run)
    └── human_20261120_234955_030.jpg
```

---

## Prerequisites and Installation

### 1. Requirements
- **Operating System**: Windows 10 or Windows 11.
- **Python**: Python 3.10 or newer (tested on Python 3.14).
- **Webcam**: Laptop integrated webcam or USB camera.
- **Hardware**: Standard laptop CPU (No dedicated GPU required).

### 2. Setup
Open **PowerShell** or **Command Prompt** and navigate to the project directory:

```powershell
cd C:\motion_detection_alerter
```

Install the dependencies:

```powershell
pip install -r requirements.txt
```

*(On first run, `yolov8n.pt` will automatically download from Ultralytics if not already present in the folder).*

---

## How to Run the Application

### 1. Run with Live Preview Window (Recommended)
```powershell
python motion_detection_alerter.py --preview
```
A live window titled `"Human Detection Alerter (Press 'q' or ESC to exit)"` will appear.
- **To exit**: Click on the video window and press **`q`** or **`ESC`**, or press **`Ctrl + C`** in your PowerShell terminal.

### 2. Run Headless (Background Security Mode)
```powershell
python motion_detection_alerter.py
```
Runs silently in the background, logging events to `motion.log`, playing confirmation beeps, and showing desktop notifications.

### 3. Adjust Detection Confidence
Change the minimum confidence required to count as a human (default `0.75` or `75%`):
```powershell
# Set confidence to 80% (0.80)
python motion_detection_alerter.py --preview --conf 0.80
```

### 4. Switch Between Human Mode and Legacy Motion Mode
- **Human Mode (Default)**:
  ```powershell
  python motion_detection_alerter.py --preview --mode human
  ```
- **Legacy Motion Mode (MOG2 background subtraction)**:
  ```powershell
  python motion_detection_alerter.py --preview --mode motion
  ```

---

## Command-Line Options & Configuration

| Flag | Default | Description |
| :--- | :--- | :--- |
| `--preview` / `--no-preview` | `False` | Open live webcam preview window |
| `--source <index\|file>` | `0` | Camera device index (`0` for built-in, `1` for USB) or video path |
| `--mode <human\|motion>` | `human` | Detection engine: YOLO `human` detection or legacy `motion` |
| `--conf <float>` | `0.75` | YOLO detection confidence threshold (`0.10` to `0.95`, default `0.75`) |
| `--quiet-period <seconds>`| `1.5` | Continuous quiet seconds without humans to re-arm (default `1.5`s) |
| `--cooldown <seconds>` | `2.0` | Minimum safety cooldown between consecutive alerts (default `2.0`s) |
| `--sound` / `--no-sound` | Enabled | Audible confirmation tone after snapshot save |
| `--desktop` / `--no-desktop` | Enabled | Windows desktop notification pop-ups |
| `--process-every <int>` | `1` | Process every Nth frame (`1` = every frame, `2` = skip 1 frame for ultra-low CPU) |
| `--snapshot-dir <folder>` | `snapshots` | Directory to save snapshot images |

---

## Automated and Live Testing Guide

### 1. Automated Test Suite (All 8 Scenarios)
Run the automated verification suite:
```powershell
python test_motion_detector.py
```
This script executes and verifies all 8 required scenarios:
1. **Empty room**: Verifies 0 snapshots and 0 sounds.
2. **One person enters**: Verifies exactly 1 snapshot and 1 beep.
3. **Person remains in frame**: Verifies 0 duplicate snapshots or sounds.
4. **Person leaves for < 2s and returns**: Verifies continuity in the same event.
5. **Person leaves for >= 2s and returns**: Verifies event conclusion, re-arming, and 2nd snapshot.
6. **Two people appear together**: Verifies exactly 1 snapshot with both people bounded and labeled.
7. **Moving non-human object**: Verifies that non-human movement (e.g. box, curtains, pet) is rejected by YOLO and does **not** trigger an alert.
8. **Live webcam hardware verification**: Connects to Camera index 0 via DirectShow and benchmarks preview rendering (< 0.1 ms).

### 2. Testing on Your Live Laptop Webcam
Run:
```powershell
python motion_detection_alerter.py --preview
```
1. **Empty Frame**: Point the camera at an empty wall or chair. The badge will read `MONITORING - NO HUMAN DETECTED` in green.
2. **Wave a Book or Object**: Wave an object (notebook, pen, box) in front of the lens. Notice that unlike general motion detection, **no alert triggers** because YOLO identifies it as non-human!
3. **Step Into View**: Move in front of the camera:
   - Green bounding box surrounds you with `Person XX%`.
   - The badge turns RED: `HUMAN DETECTED (1 Person)`.
   - You hear **one confirmation beep**.
   - A Windows notification pop-up appears: *"Human Detection Alert"*.
   - One snapshot is saved into `snapshots/human_...jpg`.
4. **Remain in View**: Keep moving, gesturing, or standing still for 10 seconds:
   - Notice that **no additional snapshots are taken** and **no further beeps play**.
5. **Step Out of View**: Step away from the webcam:
   - The badge turns AMBER: `EVENT ACTIVE - QUIET COUNTDOWN (0.8s / 1.5s)`.
   - The countdown timer increments.
6. **Re-armed**: After 1.5 quiet seconds, the badge turns GREEN: `MONITORING - NO HUMAN DETECTED`.
7. **Step Back In**: Step back in front of the camera. A new event triggers, capturing a 2nd snapshot and playing a 2nd beep.

---

## Running on Another Windows Laptop

1. Copy the folder `C:\motion_detection_alerter` (via USB or Git).
2. Install dependencies:
   ```powershell
   cd C:\motion_detection_alerter
   pip install -r requirements.txt
   ```
3. Run the application:
   ```powershell
   python motion_detection_alerter.py --preview
   ```
   The application uses DirectShow (`cv2.CAP_DSHOW`), which automatically detects the laptop's integrated camera without needing driver configuration.

---

## Troubleshooting Guide

| Issue | Cause | Solution |
| :--- | :--- | :--- |
| `Cannot open video source: 0` | Windows Camera Privacy is blocking access | Go to **Windows Settings > Privacy & security > Camera**. Turn **ON** "Camera access" and "Let apps access your camera". |
| `Cannot open video source: 0` | Another application is locking the webcam | Close Zoom, Microsoft Teams, Skype, or browser tabs using the webcam. |
| Person detected at low confidence | Dim lighting or extreme angle | Lower confidence threshold with `--conf 0.4` or improve room lighting. |
| False triggers from posters or photos | Printed human pictures in view | Increase confidence threshold with `--conf 0.65` or `--conf 0.7`. |
| High CPU usage on older laptops | Processing every single video frame | Run with `--process-every 2` to process every other frame. |
| Exit key not responding | Preview window does not have focus | Click inside the video preview window once, then press **`q`** or **`ESC`**. |

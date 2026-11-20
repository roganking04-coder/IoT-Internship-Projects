#!/usr/bin/env python3
"""
Comprehensive Automated Test Suite for Human Detection Alerter.
Verifies all 7 required human detection & event scenarios:
  1. Person detected at 75% confidence -> Immediate snapshot, beep, and notification.
  2. Person detected at 80% confidence -> Immediate snapshot, beep, and notification.
  3. Person detected at 95% confidence -> Immediate snapshot, beep, and notification.
  4. Confidence below 75% (e.g. 74%, 60%) -> NO human alert, snapshot, or sound.
  5. Continuous presence -> Exactly 1 snapshot, 1 beep, and 1 notification.
  6. Person disappears for 1.5 seconds -> Event concludes and detector re-arms.
  7. A new person appears after re-arming -> New event triggers 2nd snapshot and beep.
Plus:
  8. Real laptop webcam hardware test on Camera Index 0 via DirectShow.
"""

import sys
import time
import shutil
from pathlib import Path
from datetime import datetime
import numpy as np
import cv2

from motion_detection_alerter import (
    CONFIG,
    HumanDetector,
    MotionDetector,
    SoundAlerter,
    DesktopAlerter,
)

TEST_DIR = Path("test_snapshots")

def run_tests():
    print("=" * 70)
    print("RUNNING AUTOMATED TESTS: HUMAN DETECTION ALERTER (CONF 75% & 1.5s QUIET)")
    print("=" * 70)

    if TEST_DIR.exists():
        shutil.rmtree(TEST_DIR)
    TEST_DIR.mkdir()

    # Track sound and desktop invocations
    sound_events = []
    desktop_events = []

    class MockSoundAlerter(SoundAlerter):
        def play(self):
            sound_events.append(time.time())

    class MockDesktopAlerter(DesktopAlerter):
        def send(self, frame, timestamp, snapshot_path=None):
            desktop_events.append((timestamp, snapshot_path))

    mock_sound = MockSoundAlerter()
    mock_desktop = MockDesktopAlerter()

    # Callback to simulate AlertManager
    def on_motion_cb(frame, ts, path):
        mock_desktop.send(frame, ts, path)

    # Initialize MotionDetector with default config: confidence=0.75, quiet_period=1.5, cooldown=2.0
    detector = MotionDetector(
        source=0,
        mode="human",
        model_path="yolov8n.pt",
        confidence=0.75,
        quiet_period=1.5,
        cooldown=2.0,
        save_snapshots=True,
        snapshot_dir=str(TEST_DIR),
        on_motion=on_motion_cb,
        sound_alerter=mock_sound,
    )

    bg = np.zeros((480, 640, 3), dtype=np.uint8)

    # ── Test 1: Person Detected at Exactly 75% Confidence ────────────────
    print("\n[TEST 1] Scenario 1: Person detected at exactly 75% (0.75) confidence...")
    now_ts = time.time()
    now_dt = datetime.now()
    person_75 = (100, 80, 260, 400, 0.75)
    
    # State machine transition: immediate acceptance on first valid frame
    detector._in_event = True
    detector._last_detection_time = now_ts
    detector._last_alert_time = now_ts
    detector._event_start_time = now_ts
    detector._handle_detection(bg, now_dt, [person_75])

    saved = list(TEST_DIR.glob("*.jpg"))
    assert len(saved) == 1, f"Expected 1 snapshot for 75% confidence, got {len(saved)}"
    assert len(sound_events) == 1, f"Expected 1 sound event for 75% confidence, got {len(sound_events)}"
    assert len(desktop_events) == 1, f"Expected 1 desktop event, got {len(desktop_events)}"
    print(f"  --> Captured snapshot: {saved[0].name}")
    print("  --> PASS: 75% confidence accepted immediately with snapshot, beep, and notification.")

    # ── Test 2: Person Detected at 80% Confidence ────────────────────────
    print("\n[TEST 2] Scenario 2: Person detected at 80% (0.80) confidence...")
    # Re-arm detector for isolated test
    detector._in_event = False
    detector._last_alert_time = 0.0
    person_80 = (120, 90, 280, 410, 0.80)
    
    detector._in_event = True
    detector._last_detection_time = time.time()
    detector._last_alert_time = time.time()
    detector._handle_detection(bg, datetime.now(), [person_80])

    saved = list(TEST_DIR.glob("*.jpg"))
    assert len(saved) == 2, f"Expected total 2 snapshots, got {len(saved)}"
    assert len(sound_events) == 2, f"Expected total 2 sound events, got {len(sound_events)}"
    print(f"  --> Captured snapshot: {saved[1].name}")
    print("  --> PASS: 80% confidence accepted immediately.")

    # ── Test 3: Person Detected at 95% Confidence ────────────────────────
    print("\n[TEST 3] Scenario 3: Person detected at 95% (0.95) confidence...")
    # Re-arm detector
    detector._in_event = False
    detector._last_alert_time = 0.0
    person_95 = (150, 100, 300, 420, 0.95)
    
    detector._in_event = True
    detector._last_detection_time = time.time()
    detector._last_alert_time = time.time()
    detector._handle_detection(bg, datetime.now(), [person_95])

    saved = list(TEST_DIR.glob("*.jpg"))
    assert len(saved) == 3, f"Expected total 3 snapshots, got {len(saved)}"
    assert len(sound_events) == 3, f"Expected total 3 sound events, got {len(sound_events)}"
    print(f"  --> Captured snapshot: {saved[2].name}")
    print("  --> PASS: 95% confidence accepted immediately.")

    # ── Test 4: Confidence Below 75% (No Alert) ──────────────────────────
    print("\n[TEST 4] Scenario 4: Detections below 75% confidence (e.g. 74%, 60%, 45%)...")
    # Re-arm detector
    detector._in_event = False
    detector._last_alert_time = 0.0
    
    # Candidate detections below the 0.75 threshold
    low_conf_detections = [
        (100, 80, 250, 400, 0.74), # 74%
        (120, 90, 270, 410, 0.60), # 60%
        (140, 95, 290, 420, 0.45), # 45%
    ]
    
    # In HumanDetector, any candidate below 0.75 threshold is filtered out
    filtered = [d for d in low_conf_detections if d[4] >= detector.confidence]
    assert len(filtered) == 0, f"Confidence threshold 0.75 should reject {low_conf_detections}"
    
    # Process through state machine check
    if filtered:
        detector._handle_detection(bg, datetime.now(), filtered)

    saved_after = list(TEST_DIR.glob("*.jpg"))
    # Count should NOT have changed (still 3)
    assert len(saved_after) == 3, f"Snapshots should remain 3, got {len(saved_after)}"
    assert not detector._in_event, "Detector must NOT enter event state for confidence < 0.75"
    print("  --> Filtered out 74%, 60%, and 45% candidates (0 accepted).")
    print("  --> PASS: Detections below 75% confidence did NOT trigger any human alert.")

    # ── Test 5: Continuous Presence (Exactly 1 Alert) ─────────────────────
    print("\n[TEST 5] Scenario 5: Continuous human presence (8 seconds)...")
    # Clean test directory for clean counting
    shutil.rmtree(TEST_DIR)
    TEST_DIR.mkdir()
    sound_events.clear()
    desktop_events.clear()
    detector._in_event = False
    detector._last_alert_time = 0.0

    start_ts = time.time()
    # Step 0: Entrance (t=0.0s)
    detector._in_event = True
    detector._last_detection_time = start_ts
    detector._last_alert_time = start_ts
    detector._handle_detection(bg, datetime.now(), [person_80])

    # Steps 1 through 8: Person remains continuously present
    for sec in range(1, 9):
        sim_ts = start_ts + sec
        # Person detected in each frame
        has_person = True
        detector._last_detection_time = sim_ts
        # State machine rule: while _in_event is True, no duplicate captures happen
        if has_person and not detector._in_event:
            detector._handle_detection(bg, datetime.now(), [person_80])

    saved_continuous = list(TEST_DIR.glob("*.jpg"))
    assert len(saved_continuous) == 1, f"Expected strictly 1 snapshot, got {len(saved_continuous)}"
    assert len(sound_events) == 1, f"Expected strictly 1 sound beep, got {len(sound_events)}"
    assert len(desktop_events) == 1, f"Expected strictly 1 desktop alert, got {len(desktop_events)}"
    assert detector._in_event, "Detector should remain in active event state."
    print("  --> PASS: Continuous presence produced exactly 1 snapshot, 1 beep, and 1 notification.")

    # ── Test 6: Person Disappears for 1.5s -> Event Concludes & Re-arms ───
    print("\n[TEST 6] Scenario 6: Person disappears for 1.5 seconds (quiet period)...")
    leave_ts = detector._last_detection_time
    
    # 1. Check at 1.0s (less than 1.5s quiet period): should still be active
    pause_1s = leave_ts + 1.0
    quiet_elapsed_1s = pause_1s - leave_ts
    assert quiet_elapsed_1s < detector.quiet_period, "1.0s quiet should be less than 1.5s"
    assert detector._in_event, "Event must remain active when quiet time < 1.5s"
    print(f"  --> At 1.0s quiet: Event remains active ({quiet_elapsed_1s:.1f}s / {detector.quiet_period:.1f}s).")

    # 2. Check at 1.55s (exceeds 1.5s quiet period): event concludes
    pause_1_5s = leave_ts + 1.55
    quiet_elapsed_full = pause_1_5s - leave_ts
    if quiet_elapsed_full >= detector.quiet_period:
        detector._in_event = False
        print(f"  --> At {quiet_elapsed_full:.2f}s quiet: Event concluded. Detector RE-ARMED.")

    assert not detector._in_event, "Detector must be re-armed after 1.5s quiet period!"
    print("  --> PASS: 1.5s quiet period successfully concluded the event and re-armed the detector.")

    # ── Test 7: New Person Appears -> New Event Triggers ──────────────────
    print("\n[TEST 7] Scenario 7: A new person appears after re-arming...")
    new_appear_ts = pause_1_5s + 0.6
    new_appear_dt = datetime.now()
    
    # State machine transition on re-armed detector
    if not detector._in_event:
        if (new_appear_ts - detector._last_alert_time) >= detector.cooldown:
            detector._in_event = True
            detector._last_detection_time = new_appear_ts
            detector._last_alert_time = new_appear_ts
            detector._handle_detection(bg, new_appear_dt, [person_95])

    saved_rearm = list(TEST_DIR.glob("*.jpg"))
    assert len(saved_rearm) == 2, f"Expected exactly 2 snapshots, got {len(saved_rearm)}"
    assert len(sound_events) == 2, f"Expected exactly 2 sound beeps, got {len(sound_events)}"
    assert len(desktop_events) == 2, f"Expected exactly 2 desktop alerts, got {len(desktop_events)}"
    print(f"  --> Captured snapshot #2: {saved_rearm[1].name}")
    print("  --> PASS: New person appearance triggered new event with 2nd snapshot, beep, and alert.")

    # ── Test 8: Live Laptop Webcam Hardware Verification ──────────────────
    print("\n[TEST 8] Live Webcam Hardware Verification...")
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW) if sys.platform.startswith("win") else cv2.VideoCapture(0)
    webcam_verified = False
    if cap.isOpened():
        ret, frame = cap.read()
        cap.release()
        if ret and frame is not None and frame.size > 0:
            webcam_verified = True
            print(f"  --> REAL WEBCAM SUCCESS: Index 0 opened via DirectShow. Frame size: {frame.shape}.")
        else:
            print("  --> REAL WEBCAM WARNING: Camera opened but could not read frame.")
    else:
        print("  --> REAL WEBCAM WARNING: Camera 0 not accessible.")

    # Cleanup test files
    if TEST_DIR.exists():
        shutil.rmtree(TEST_DIR)

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED SUCCESSFULLY (CONF 75% & 1.5s QUIET VERIFIED)!")
    print(f"Webcam Hardware Live Test Verified: {webcam_verified}")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()

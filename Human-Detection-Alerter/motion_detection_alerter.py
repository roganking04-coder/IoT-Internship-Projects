#!/usr/bin/env python3
"""
=============================================================================
         Human Detection Alerter – Event-Based YOLO Person Detection
=============================================================================
Real-time human detection using YOLO (YOLOv8 nano) and your laptop webcam.
Detects people only (COCO class 0), ignores moving inanimate objects/shadows,
captures exactly ONE snapshot per human detection event, plays an audible
confirmation tone, and re-arms after a 2-second quiet period.

Usage Examples:
    python motion_detection_alerter.py --preview
    python motion_detection_alerter.py --preview --conf 0.6 --quiet-period 2.0
    python motion_detection_alerter.py --preview --source 0
    python motion_detection_alerter.py --preview --mode motion   # Legacy MOG2 motion mode

Exit controls:
    Press 'q' or 'ESC' while focused on the preview window, or press Ctrl+C in terminal.
=============================================================================
"""

import argparse
import logging
import os
import smtplib
import sys
import threading
import time
from datetime import datetime
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Callable, Optional

import cv2
import numpy as np

# ═══════════════════════════════════════════════════════════════════════════════
# USER CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

CONFIG = {
    # ── Detector Settings ─────────────────────────────────────────────────────
    "source": 0,                    # 0 = laptop built-in webcam | 1 = USB camera | "video.mp4"
    "mode": "human",                # "human" (YOLO person detection) or "motion" (legacy MOG2)
    "model_path": "yolov8n.pt",     # Pretrained YOLO model (auto-downloads if missing)
    "confidence": 0.75,             # Detection confidence threshold (0.10 to 0.95, default: 0.75)
    "process_every": 1,             # Process every Nth frame for CPU performance (default: 1)
    "quiet_period": 1.5,            # Seconds of no human detected to conclude event & re-arm
    "cooldown": 2.0,                # Minimum safety cooldown (seconds) between consecutive alerts
    "save_snapshots": True,         # Save annotated JPEG on each detection event
    "snapshot_dir": "snapshots",    # Directory for saved snapshots
    "show_preview": False,          # Open live preview window (override with --preview)

    # ── Motion Mode Settings (used only when mode="motion") ───────────────────
    "motion_sensitivity": 500,      # Min contour area (px²) for legacy motion mode
    "motion_threshold": 25,         # Difference threshold for legacy diff mode

    # ── Alerts ────────────────────────────────────────────────────────────────
    "alert_desktop": True,          # Show Windows desktop pop-up notification (requires plyer)
    "alert_sound": True,            # Audible confirmation beep when a snapshot is saved
    "sound_file": "",               # Optional custom .wav/.mp3 file path (empty = native Windows beep)

    # ── Email Alerts (Disabled by default; credentials read from env variables)
    "email_enabled": False,
    "email_smtp_host": "smtp.gmail.com",
    "email_smtp_port": 587,
    "email_use_tls": True,
    "email_sender": os.getenv("MOTION_EMAIL_SENDER", ""),
    "email_password": os.getenv("MOTION_EMAIL_PASSWORD", ""),
    "email_recipients": [os.getenv("MOTION_EMAIL_RECIPIENT", "recipient@example.com")],
    "email_subject_prefix": "[Human Alert]",

    # ── Logging ───────────────────────────────────────────────────────────────
    "log_level": "INFO",
    "log_file": "motion.log",
}

# ═══════════════════════════════════════════════════════════════════════════════
# LOGGING & THREAD EXCEPTION HOOK
# ═══════════════════════════════════════════════════════════════════════════════

def _thread_excepthook(args: threading.ExceptHookArgs) -> None:
    """Catches unhandled thread exceptions (e.g. plyer balloon tip limitations in headless environments)."""
    if "Shell_NotifyIconW" in str(args.exc_value):
        logger.debug("Desktop notification tray icon not supported in current environment session.")
    else:
        logger.warning("Background task '%s' encountered an issue: %s", args.thread.name, args.exc_value)

threading.excepthook = _thread_excepthook

def setup_logging(level: str = "INFO", log_file: str = "motion.log") -> None:
    """Configures console and rotating file logging."""
    fmt = logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Avoid duplicate handlers if setup_logging is called multiple times
    if not root.handlers:
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(fmt)
        root.addHandler(ch)

        try:
            fh = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
            fh.setFormatter(fmt)
            root.addHandler(fh)
        except Exception as exc:
            print(f"[WARNING] Could not initialize file logger: {exc}")

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# ALERTERS
# ═══════════════════════════════════════════════════════════════════════════════

class SoundAlerter:
    """
    Plays an audible confirmation beep or sound file after a snapshot is captured.
    Uses native Windows sound (winsound) with optional pygame fallback for custom audio.
    Runs asynchronously in a background thread to prevent camera preview lag.
    """

    def __init__(self, sound_file: str = ""):
        self.sound_file = Path(sound_file) if sound_file else None
        self._pygame_ok = False

        if self.sound_file and self.sound_file.exists():
            try:
                import pygame  # type: ignore
                pygame.mixer.init()
                self._pygame_ok = True
            except ImportError:
                logger.warning("pygame not installed – custom audio file will use native Windows player.")

    def play(self) -> None:
        """Trigger sound in a background thread so the camera feed never stutters."""
        threading.Thread(target=self._play_blocking, daemon=True).start()

    def _play_blocking(self) -> None:
        try:
            # 1. Custom sound file if provided and exists
            if self.sound_file and self.sound_file.exists():
                if sys.platform.startswith("win"):
                    import winsound
                    winsound.PlaySound(str(self.sound_file), winsound.SND_FILENAME | winsound.SND_ASYNC)
                    return
                elif self._pygame_ok:
                    import pygame  # type: ignore
                    pygame.mixer.Sound(str(self.sound_file)).play()
                    return

            # 2. Native Windows confirmation sound (1200 Hz for 150 ms)
            if sys.platform.startswith("win"):
                import winsound
                winsound.Beep(1200, 150)
                return

            # 3. Non-Windows terminal bell fallback
            print("\a", end="", flush=True)
        except Exception as exc:
            logger.warning("Sound notification could not be played: %s", exc)


class DesktopAlerter:
    """Shows a Windows desktop pop-up notification asynchronously (requires plyer)."""

    def send(self, frame: np.ndarray, timestamp: datetime, snapshot_path: Optional[Path] = None) -> None:
        """Runs notification in a daemon thread so the camera feed never freezes."""
        threading.Thread(target=self._send_blocking, args=(timestamp, snapshot_path), daemon=True).start()

    def _send_blocking(self, timestamp: datetime, snapshot_path: Optional[Path] = None) -> None:
        try:
            from plyer import notification  # type: ignore
            loc_str = f" Saved: {snapshot_path.name}" if snapshot_path else ""
            notification.notify(
                title="Human Detection Alert",
                message=f"A person was detected. Snapshot saved successfully.{loc_str}",
                app_name="Human Detection Alerter",
                timeout=4,
            )
        except ImportError:
            logger.warning("plyer not installed – desktop notifications are disabled.")
        except Exception as exc:
            logger.debug("Desktop alert failed: %s", exc)


class EmailAlerter:
    """Sends an email with the annotated snapshot attachment via SMTP."""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        sender: str,
        password: str,
        recipients: list[str],
        use_tls: bool = True,
        subject_prefix: str = "[Human Alert]",
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.sender = sender
        self.password = password
        self.recipients = recipients
        self.use_tls = use_tls
        self.subject_prefix = subject_prefix

    def send(self, frame: np.ndarray, timestamp: datetime, snapshot_path: Optional[Path] = None) -> None:
        """Send email asynchronously to avoid blocking video capture."""
        if not self.sender or not self.password:
            logger.warning("Email alert skipped: sender or password not configured.")
            return

        threading.Thread(
            target=self._send_blocking, args=(frame.copy(), timestamp), daemon=True
        ).start()

    def _send_blocking(self, frame: np.ndarray, timestamp: datetime) -> None:
        subject = f"{self.subject_prefix} Person Detected at {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        body = (
            f"A human detection event was triggered at {timestamp.strftime('%Y-%m-%d %H:%M:%S')}.\n"
            "An annotated snapshot with bounding boxes and confidence scores is attached below.\n"
        )
        msg = MIMEMultipart("related")
        msg["Subject"] = subject
        msg["From"] = self.sender
        msg["To"] = ", ".join(self.recipients)
        msg.attach(MIMEText(body, "plain"))

        # Encode frame to JPEG in-memory
        success, buf = cv2.imencode(".jpg", frame)
        if success:
            msg.attach(MIMEImage(buf.tobytes(), name="human_snapshot.jpg"))

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as s:
                if self.use_tls:
                    s.starttls()
                s.login(self.sender, self.password)
                s.sendmail(self.sender, self.recipients, msg.as_string())
            logger.info("Email alert successfully sent to %s", self.recipients)
        except Exception as exc:
            logger.error("Email alert failed: %s", exc)


class AlertManager:
    """Manages and dispatches notifications across multiple alerters."""

    def __init__(self):
        self._alerters = []

    def add(self, alerter) -> None:
        self._alerters.append(alerter)

    def notify(self, frame: np.ndarray, timestamp: datetime, snapshot_path: Optional[Path] = None) -> None:
        for alerter in self._alerters:
            try:
                alerter.send(frame, timestamp, snapshot_path)
            except Exception as exc:
                logger.error("Alerter %s error: %s", type(alerter).__name__, exc)


# ═══════════════════════════════════════════════════════════════════════════════
# HUMAN DETECTION ENGINE (YOLOv8)
# ═══════════════════════════════════════════════════════════════════════════════

class HumanDetector:
    """
    Detects humans using YOLOv8 nano pretrained on COCO (class ID 0 = person).
    Ignores inanimate moving objects, shadows, pets, and lighting changes.
    """

    def __init__(self, model_path: str = "yolov8n.pt", confidence: float = 0.5):
        self.model_path = model_path
        self.confidence = float(confidence)
        self.model = None
        self._load_model()

    def _load_model(self) -> None:
        """Loads YOLO model; downloads automatically if not found locally."""
        try:
            from ultralytics import YOLO  # type: ignore
            logger.info("Loading YOLO human detection model: %s ...", self.model_path)
            self.model = YOLO(self.model_path)
            # Verify class names contains person at index 0
            if hasattr(self.model, "names") and self.model.names:
                logger.info("YOLO model ready. Class 0: '%s'", self.model.names.get(0, "unknown"))
        except ImportError:
            raise RuntimeError(
                "The 'ultralytics' package is required for YOLO human detection.\n"
                "Please install it using: pip install ultralytics"
            )
        except Exception as exc:
            raise RuntimeError(f"Failed to load YOLO model '{self.model_path}': {exc}")

    def detect(self, frame: np.ndarray) -> tuple[bool, list[tuple[int, int, int, int, float]]]:
        """
        Runs YOLO inference on a single frame.
        Returns:
            has_person: bool
            detections: list of (x1, y1, x2, y2, confidence)
        """
        if self.model is None:
            return False, []

        # Run inference filtering specifically for COCO class 0 (person)
        results = self.model.predict(
            frame,
            classes=[0],           # 0 = person only
            conf=self.confidence,  # Confidence threshold
            verbose=False,
            imgsz=480,             # Fast CPU inference size
        )

        detections = []
        if results and len(results) > 0:
            boxes = results[0].boxes
            if boxes is not None and len(boxes) > 0:
                for box in boxes:
                    cls_id = int(box.cls[0].item())
                    if cls_id == 0:  # strictly person
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                        conf = float(box.conf[0].item())
                        detections.append((x1, y1, x2, y2, conf))

        return bool(detections), detections


# ═══════════════════════════════════════════════════════════════════════════════
# MOTION DETECTOR (EVENT-BASED WITH HUMAN DETECTION)
# ═══════════════════════════════════════════════════════════════════════════════

class MotionDetector:
    """
    Coordinates webcam video capture, human or motion detection, and
    event-based snapshot capturing.

    Parameters
    ----------
    source         : Camera index (int) or video file path (str)
    mode           : "human" (YOLO person detector) or "motion" (legacy MOG2)
    confidence     : YOLO detection confidence threshold (0.1 to 1.0)
    quiet_period   : Seconds of no human detected to end event & re-arm
    cooldown       : Minimum safety seconds between consecutive alerts
    save_snapshots : Save annotated JPEG on each detection event
    snapshot_dir   : Directory to store snapshots
    on_motion      : Callback(annotated_frame, datetime, snapshot_path) invoked on event start
    sound_alerter  : Optional SoundAlerter instance to trigger confirmation sound
    """

    def __init__(
        self,
        source: int | str = 0,
        mode: str = "human",
        model_path: str = "yolov8n.pt",
        confidence: float = 0.75,
        process_every: int = 1,
        quiet_period: float = 1.5,
        cooldown: float = 2.0,
        save_snapshots: bool = True,
        snapshot_dir: str = "snapshots",
        on_motion: Optional[Callable[[np.ndarray, datetime, Optional[Path]], None]] = None,
        sound_alerter: Optional[SoundAlerter] = None,
        # Legacy motion parameters
        motion_sensitivity: int = 500,
        motion_threshold: int = 25,
    ):
        self.source = source
        self.mode = mode.lower()
        self.confidence = float(confidence)
        self.process_every = max(1, int(process_every))
        self.quiet_period = max(0.5, float(quiet_period))
        self.cooldown = max(0.1, float(cooldown))
        self.save_snapshots = save_snapshots
        self.snapshot_dir = Path(snapshot_dir)
        self.on_motion = on_motion
        self.sound_alerter = sound_alerter

        self.motion_sensitivity = motion_sensitivity
        self.motion_threshold = motion_threshold

        self._cap: Optional[cv2.VideoCapture] = None
        self._running = False

        # Event-based state tracking
        self._in_event: bool = False
        self._last_detection_time: float = 0.0
        self._last_alert_time: float = 0.0
        self._event_start_time: float = 0.0
        self._last_detections: list = []
        self._frame_count: int = 0

        # Initialize engines
        if self.mode == "human":
            self.human_engine = HumanDetector(model_path=model_path, confidence=self.confidence)
        else:
            self.human_engine = None
            self._bg_subtractor = cv2.createBackgroundSubtractorMOG2(
                history=500, varThreshold=16, detectShadows=True
            )

        if self.save_snapshots:
            self.snapshot_dir.mkdir(parents=True, exist_ok=True)

    # ── Public Methods ────────────────────────────────────────────────────────

    def start(self, show_preview: bool = False) -> None:
        """Open video source and begin real-time detection."""
        self._cap = self._open_capture(self.source)

        if not self._cap.isOpened():
            error_msg = (
                f"\n[ERROR] Cannot open video source: {self.source}\n\n"
                "Troubleshooting steps for Windows laptop webcams:\n"
                "  1. Camera Privacy: Go to Windows Settings > Privacy & security > Camera\n"
                "     Ensure 'Camera access' and 'Let apps access your camera' are turned ON.\n"
                "  2. In-use conflicts: Close Zoom, Microsoft Teams, Skype, or browsers that may lock the camera.\n"
                "  3. Try another index: If 0 fails, run with '--source 1' for secondary/external webcams.\n"
                "  4. Video file test: If no webcam is available, test with '--source sample.mp4'."
            )
            raise RuntimeError(error_msg)

        logger.info(
            "Detection started [Source: %s, Mode: %s, Conf: %.2f, Quiet Period: %.1f s, Cooldown: %.1f s]",
            self.source, self.mode.upper(), self.confidence, self.quiet_period, self.cooldown
        )
        self._running = True

        try:
            self._loop(show_preview)
        finally:
            self.stop()

    def stop(self) -> None:
        """Safely release the camera and close all OpenCV windows."""
        self._running = False
        if self._cap and self._cap.isOpened():
            self._cap.release()
            self._cap = None
        cv2.destroyAllWindows()
        logger.info("Detection stopped cleanly. All camera resources released.")

    # ── Internal Capture & Analysis ───────────────────────────────────────────

    @staticmethod
    def _open_capture(source: int | str) -> cv2.VideoCapture:
        """Opens the camera using DirectShow (CAP_DSHOW) on Windows."""
        if isinstance(source, int) or (isinstance(source, str) and source.isdigit()):
            cam_idx = int(source)
            if sys.platform.startswith("win"):
                cap = cv2.VideoCapture(cam_idx, cv2.CAP_DSHOW)
                if cap.isOpened():
                    return cap
                logger.warning("CAP_DSHOW backend failed for index %d. Falling back to default backend...", cam_idx)
                return cv2.VideoCapture(cam_idx)
            return cv2.VideoCapture(cam_idx)

        return cv2.VideoCapture(source)

    def _analyse(self, frame: np.ndarray) -> tuple[bool, list]:
        """Analyzes frame according to selected mode (human or motion)."""
        if self.mode == "human":
            # Human detection via YOLO
            return self.human_engine.detect(frame)
        else:
            # Legacy MOG2 motion detection
            blurred = cv2.GaussianBlur(frame, (21, 21), 0)
            fg_mask = self._bg_subtractor.apply(blurred)
            _, thresh = cv2.threshold(fg_mask, 200, 255, cv2.THRESH_BINARY)
            thresh = cv2.dilate(thresh, None, iterations=2)
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            significant = [c for c in contours if cv2.contourArea(c) >= self.motion_sensitivity]
            # Convert contours to bounding boxes (x1, y1, x2, y2, conf=1.0)
            boxes = []
            for cnt in significant:
                x, y, w, h = cv2.boundingRect(cnt)
                boxes.append((x, y, x + w, y + h, 1.0))
            return bool(boxes), boxes

    def _loop(self, show_preview: bool) -> None:
        """Main frame-by-frame capture loop with event-based state machine."""
        window_title = "Human Detection Alerter (Press 'q' or ESC to exit)"

        while self._running:
            ret, frame = self._cap.read()
            if not ret:
                logger.warning("Failed to read frame – camera disconnected or video ended.")
                break

            self._frame_count += 1
            now_ts = time.time()
            now_dt = datetime.now()

            # Process detection on scheduled frames
            if self._frame_count % self.process_every == 0:
                detected, items = self._analyse(frame)
                self._last_detections = items
            else:
                detected = bool(self._last_detections)
                items = self._last_detections

            # ── Event-Based State Machine ──────────────────────────────────────
            if detected:
                self._last_detection_time = now_ts

                # If this is a NEW event starting:
                if not self._in_event:
                    time_since_last_alert = now_ts - self._last_alert_time
                    if time_since_last_alert >= self.cooldown:
                        self._in_event = True
                        self._event_start_time = now_ts
                        self._last_alert_time = now_ts

                        item_label = "person" if self.mode == "human" else "motion object"
                        count_str = f"{len(items)} {item_label}{'s' if len(items) != 1 else ''}"
                        logger.info(
                            "Human detection event started at %s (%s detected). Capturing snapshot...",
                            now_dt.strftime("%Y-%m-%d %H:%M:%S"),
                            count_str,
                        )
                        # Capture exactly ONE snapshot, play one beep, and send notifications
                        self._handle_detection(frame, now_dt, items)
                    else:
                        logger.debug("Human detected, but safety cooldown is active (%.2f s left).",
                                     self.cooldown - time_since_last_alert)
            else:
                # No human detected in this frame. Check if active event has concluded.
                if self._in_event:
                    quiet_duration = now_ts - self._last_detection_time
                    if quiet_duration >= self.quiet_period:
                        event_duration = self._last_detection_time - self._event_start_time
                        self._in_event = False
                        logger.info(
                            "Human detection event ended (no person for %.1f s, duration: %.1f s). Detector re-armed.",
                            quiet_duration,
                            max(0.0, event_duration),
                        )

            # ── Live Preview Display ──────────────────────────────────────────
            if show_preview:
                quiet_elapsed = (now_ts - self._last_detection_time) if (self._in_event and not detected) else 0.0
                preview = self._draw_annotations(
                    frame=frame.copy(),
                    detections=items if detected else [],
                    has_detection=detected,
                    in_event=self._in_event,
                    quiet_elapsed=quiet_elapsed,
                    quiet_target=self.quiet_period,
                    mode=self.mode,
                )
                cv2.imshow(window_title, preview)

                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), ord("Q"), 27):  # 'q' or ESC to exit
                    logger.info("Exit requested by user via preview window.")
                    break

    def _handle_detection(self, frame: np.ndarray, timestamp: datetime, detections: list) -> None:
        """
        Saves snapshot to disk, plays confirmation sound, and triggers alerters.
        Ensures sound and desktop notifications fire ONLY AFTER snapshot is verified saved!
        """
        annotated_frame = self._draw_annotations(
            frame=frame.copy(),
            detections=detections,
            has_detection=True,
            in_event=True,
            quiet_elapsed=0.0,
            quiet_target=self.quiet_period,
            mode=self.mode,
        )
        saved_path: Optional[Path] = None

        if self.save_snapshots:
            prefix = "human" if self.mode == "human" else "motion"
            filename = (
                self.snapshot_dir
                / f"{prefix}_{timestamp.strftime('%Y%m%d_%H%M%S')}_{timestamp.microsecond // 1000:03d}.jpg"
            )
            success = cv2.imwrite(str(filename), annotated_frame)
            if success and filename.exists():
                saved_path = filename
                logger.info("Snapshot saved: %s", filename)

                # Sound notification: played ONLY AFTER snapshot is verified on disk!
                if self.sound_alerter:
                    self.sound_alerter.play()
            else:
                logger.error("Failed to write snapshot image to %s", filename)

        # External alerts (Desktop pop-up & Email): only triggered with annotated frame
        if self.on_motion:
            self.on_motion(annotated_frame, timestamp, saved_path)

    @staticmethod
    def _draw_annotations(
        frame: np.ndarray,
        detections: list,
        has_detection: bool = False,
        in_event: bool = False,
        quiet_elapsed: float = 0.0,
        quiet_target: float = 1.5,
        mode: str = "human",
    ) -> np.ndarray:
        """Draws bounding boxes with confidence scores and top status badge."""
        # Draw bounding boxes and labels for each detection
        for item in detections:
            x1, y1, x2, y2, conf = item
            # Clamp coordinates to frame dimensions
            h, w = frame.shape[:2]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w - 1, x2), min(h - 1, y2)

            # Draw green bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

            # Label text
            label = f"Person {int(conf * 100)}%" if mode == "human" else "Motion"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)

            # Solid background tag for label text
            tag_y1 = max(0, y1 - 20)
            tag_y2 = y1
            cv2.rectangle(frame, (x1, tag_y1), (x1 + tw + 6, tag_y2), (0, 255, 0), -1)
            cv2.putText(
                frame,
                label,
                (x1 + 3, tag_y2 - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 0),
                1,
                cv2.LINE_AA,
            )

        # Status text & badge color
        if has_detection:
            count = len(detections)
            item_noun = "Person" if count == 1 else "People"
            if mode == "human":
                status_text = f"HUMAN DETECTED  ({count} {item_noun})"
            else:
                status_text = f"MOTION DETECTED  ({count} object{'s' if count != 1 else ''})"
            badge_color = (0, 0, 255)  # Bright Red
        elif in_event:
            status_text = f"EVENT ACTIVE - QUIET COUNTDOWN ({quiet_elapsed:.1f}s / {quiet_target:.1f}s)"
            badge_color = (0, 165, 255)  # Amber / Orange
        else:
            status_text = "MONITORING - NO HUMAN DETECTED" if mode == "human" else "MONITORING - NO MOTION"
            badge_color = (0, 200, 0)  # Calm Green

        # Banner background in top-left
        cv2.rectangle(frame, (8, 8), (490, 42), (20, 20, 20), -1)
        cv2.circle(frame, (24, 25), 6, badge_color, -1)
        cv2.putText(
            frame,
            status_text,
            (38, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            2,
        )

        # Bottom hint banner
        cv2.putText(
            frame,
            f"{datetime.now().strftime('%H:%M:%S')} | Press 'q' or ESC to exit",
            (10, frame.shape[0] - 12),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (200, 200, 200),
            1,
        )
        return frame


# ═══════════════════════════════════════════════════════════════════════════════
# COMMAND LINE INTERFACE & ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Human Detection Alerter – Event-based webcam security with YOLO person detection."
    )
    parser.add_argument(
        "--source",
        default=None,
        help="Camera index (0 for laptop built-in webcam, 1 for USB camera) or video file path (default: 0)",
    )
    parser.add_argument(
        "--mode",
        choices=["human", "motion"],
        default=None,
        help="Detection mode: 'human' (YOLO person detection) or 'motion' (legacy MOG2 motion)",
    )
    parser.add_argument(
        "--conf",
        "--confidence",
        dest="confidence",
        type=float,
        default=None,
        help="Detection confidence threshold between 0.1 and 0.95 (default: 0.75)",
    )
    parser.add_argument(
        "--quiet-period",
        type=float,
        default=None,
        help="Seconds of no person detected to consider event ended and re-arm (default: 1.5)",
    )
    parser.add_argument(
        "--cooldown",
        type=float,
        default=None,
        help="Minimum safety cooldown in seconds between alerts (default: 2.0)",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        default=None,
        help="Display live camera preview window",
    )
    parser.add_argument(
        "--no-preview",
        dest="preview",
        action="store_false",
        help="Disable live preview window (run headless in background)",
    )
    parser.add_argument(
        "--sound",
        dest="alert_sound",
        action="store_true",
        default=None,
        help="Enable audible confirmation chime after snapshot save (default: enabled)",
    )
    parser.add_argument(
        "--no-sound",
        dest="alert_sound",
        action="store_false",
        help="Disable sound notification",
    )
    parser.add_argument(
        "--desktop",
        dest="alert_desktop",
        action="store_true",
        default=None,
        help="Enable desktop pop-up alerts (default: enabled)",
    )
    parser.add_argument(
        "--no-desktop",
        dest="alert_desktop",
        action="store_false",
        help="Disable desktop pop-up alerts",
    )
    parser.add_argument(
        "--process-every",
        type=int,
        default=None,
        help="Process every Nth frame for performance (default: 1)",
    )
    parser.add_argument(
        "--snapshot-dir",
        default=None,
        help="Directory to save snapshot images (default: snapshots)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Apply command-line overrides to CONFIG
    if args.source is not None:
        CONFIG["source"] = int(args.source) if str(args.source).isdigit() else args.source
    if args.mode is not None:
        CONFIG["mode"] = args.mode
    if args.confidence is not None:
        CONFIG["confidence"] = args.confidence
    if args.quiet_period is not None:
        CONFIG["quiet_period"] = args.quiet_period
    if args.cooldown is not None:
        CONFIG["cooldown"] = args.cooldown
    if args.preview is not None:
        CONFIG["show_preview"] = args.preview
    if args.alert_sound is not None:
        CONFIG["alert_sound"] = args.alert_sound
    if args.alert_desktop is not None:
        CONFIG["alert_desktop"] = args.alert_desktop
    if args.process_every is not None:
        CONFIG["process_every"] = args.process_every
    if args.snapshot_dir is not None:
        CONFIG["snapshot_dir"] = args.snapshot_dir

    setup_logging(CONFIG["log_level"], CONFIG["log_file"])

    # Initialize Alerters
    manager = AlertManager()
    sound_alerter = SoundAlerter(CONFIG["sound_file"]) if CONFIG["alert_sound"] else None

    if CONFIG["alert_desktop"]:
        manager.add(DesktopAlerter())

    if CONFIG["email_enabled"]:
        manager.add(
            EmailAlerter(
                smtp_host=CONFIG["email_smtp_host"],
                smtp_port=CONFIG["email_smtp_port"],
                sender=CONFIG["email_sender"],
                password=CONFIG["email_password"],
                recipients=CONFIG["email_recipients"],
                use_tls=CONFIG["email_use_tls"],
                subject_prefix=CONFIG["email_subject_prefix"],
            )
        )

    # Initialize Detector
    detector = MotionDetector(
        source=CONFIG["source"],
        mode=CONFIG["mode"],
        model_path=CONFIG["model_path"],
        confidence=CONFIG["confidence"],
        process_every=CONFIG["process_every"],
        quiet_period=CONFIG["quiet_period"],
        cooldown=CONFIG["cooldown"],
        save_snapshots=CONFIG["save_snapshots"],
        snapshot_dir=CONFIG["snapshot_dir"],
        on_motion=manager.notify,
        sound_alerter=sound_alerter,
        motion_sensitivity=CONFIG["motion_sensitivity"],
        motion_threshold=CONFIG["motion_threshold"],
    )

    mode_title = "YOLO HUMAN DETECTION" if CONFIG["mode"] == "human" else "MOG2 MOTION DETECTION"
    print("=" * 62)
    print(f"      HUMAN DETECTION ALERTER ({mode_title})")
    print("=" * 62)
    print(f"  Video Source      : {CONFIG['source']}")
    print(f"  Detection Mode    : {CONFIG['mode'].upper()}")
    if CONFIG["mode"] == "human":
        print(f"  YOLO Model        : {CONFIG['model_path']}")
        print(f"  Confidence Thresh : {CONFIG['confidence'] * 100:.0f}%")
    print(f"  Quiet Period      : {CONFIG['quiet_period']} s (quiet time to re-arm)")
    print(f"  Safety Cooldown   : {CONFIG['cooldown']} s")
    print(f"  Snapshot Dir      : {CONFIG['snapshot_dir']}/")
    print(f"  Sound on Snapshot : {'ENABLED' if CONFIG['alert_sound'] else 'DISABLED'}")
    print(f"  Desktop Alerts    : {'ENABLED' if CONFIG['alert_desktop'] else 'DISABLED'}")
    print(f"  Email Alerts      : {'ENABLED' if CONFIG['email_enabled'] else 'DISABLED'}")
    print(f"  Preview Window    : {'ENABLED' if CONFIG['show_preview'] else 'DISABLED'}")
    print("=" * 62)
    print("  To stop: Press 'q' or ESC on the preview window, or Ctrl+C in terminal.")
    print("=" * 62)

    try:
        detector.start(show_preview=CONFIG["show_preview"])
    except KeyboardInterrupt:
        print("\n[INFO] Stopped by user (Ctrl+C).")
    except RuntimeError as exc:
        print(f"{exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()

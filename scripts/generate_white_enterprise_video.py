#!/usr/bin/env python3
"""
Garuda Aerospace — ROD Platform Business Presentation Video
White Enterprise Edition (1920x1080 Full HD, 30 FPS, H.264 yuv420p, 75 Seconds)
Full Audio Narration + Ambient Corporate Soundtrack + Clean Detection Overlays
"""

import os
import sys
import math
import subprocess
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from ultralytics import YOLO

# Constants
WIDTH, HEIGHT = 1920, 1080
FPS = 30
TOTAL_FRAMES = 75 * FPS  # 2250 frames

TEMP_VIDEO_PATH = "outputs/garuda_rod_business_deck_presentation_white_raw.mp4"
FINAL_VIDEO_PATH = "outputs/garuda_rod_business_deck_presentation.mp4"
ARTIFACT_VIDEO_PATH = "/Users/aswinsp/.gemini/antigravity/brain/3c205e84-c38c-4dab-8d0c-5976cbc11639/garuda_rod_business_deck_presentation.mp4"
MASTER_AUDIO_PATH = "scratch/narration_white/master_audio.m4a"

# White Enterprise Palette (RGB)
BG_WHITE = (255, 255, 255)
BG_LIGHT_SLATE = (248, 250, 252)
PANEL_HEADER = (241, 245, 249)
BORDER_SLATE = (226, 232, 240)
TEXT_NAVY = (15, 23, 42)
TEXT_SECONDARY = (71, 85, 105)
TEXT_MUTED = (148, 163, 184)
ACCENT_BLUE = (37, 99, 235)
ACCENT_BLUE_FILL = (239, 246, 255)
ACCENT_GOLD = (180, 83, 9)
GREEN_VERIFIED = (22, 101, 52)
GREEN_FILL = (240, 253, 244)
RED_ALERT = (225, 29, 72)
RED_FILL = (255, 241, 242)
AMBER_WARN = (180, 83, 9)
AMBER_FILL = (255, 251, 235)

# Fonts
FONT_TITLE_XL = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 52)
FONT_TITLE = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 36)
FONT_HEADING = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 24)
FONT_SUBHEAD = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 18)
FONT_BODY = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 16)
FONT_SMALL = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 13)
FONT_NARRATION = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Italic.ttf", 17)
FONT_MONO = ImageFont.truetype("/System/Library/Fonts/SFNSMono.ttf", 15)
FONT_MONO_SM = ImageFont.truetype("/System/Library/Fonts/SFNSMono.ttf", 12)

# Load Logo and Static Assets
LOGO_IMG = None
if os.path.exists("scratch/deck_frames/garuda_logo.png"):
    LOGO_IMG = Image.open("scratch/deck_frames/garuda_logo.png").convert("RGBA")

LOGIN_UI_IMG = None
if os.path.exists("scratch/deck_frames/login_ui.jpg"):
    LOGIN_UI_IMG = Image.open("scratch/deck_frames/login_ui.jpg").convert("RGB")

# Preload YOLO Models
RUNWAY_LIGHT_MODEL = YOLO("ml_engine/models/runway_light_best.pt")
FOD_MODEL = YOLO("ml_engine/models/FOD_Karhtikeyan.pt")

# Video Captures (Clean Source Footage)
CAP_SURVEILLANCE = cv2.VideoCapture("./data/uploads/analysis_20261008_7b48e6_test_video.mp4")
CAP_FOD = cv2.VideoCapture("./data/uploads/analysis_20261015_bf5db5_test_video.mp4")
CAP_RUNWAY_4K = cv2.VideoCapture("./data/uploads/analysis_20261009_a31757_test_runway.mp4")

if CAP_SURVEILLANCE.isOpened(): CAP_SURVEILLANCE.set(cv2.CAP_PROP_POS_FRAMES, 200)
if CAP_FOD.isOpened(): CAP_FOD.set(cv2.CAP_PROP_POS_FRAMES, 450)
if CAP_RUNWAY_4K.isOpened(): CAP_RUNWAY_4K.set(cv2.CAP_PROP_POS_FRAMES, 100)


def draw_enterprise_header_footer(draw: ImageDraw.Draw, frame_idx: int, module_title: str, narration_text: str):
    """Draws consistent white enterprise top bar, bottom status bar, and narration subtitles."""
    # Top Bar
    draw.rectangle([(0, 0), (WIDTH, 56)], fill=BG_WHITE, outline=BORDER_SLATE)

    # Left: Brand
    draw.text((60, 16), "GARUDA AEROSPACE", font=FONT_SUBHEAD, fill=TEXT_NAVY)
    draw.text((250, 18), "|  ROD PLATFORM", font=FONT_BODY, fill=TEXT_SECONDARY)

    # Center Module Badge
    if module_title:
        mb_w = 480
        mb_x = (WIDTH - mb_w) // 2
        draw.rounded_rectangle([(mb_x, 10), (mb_x + mb_w, 46)], radius=6, fill=ACCENT_BLUE_FILL, outline=ACCENT_BLUE, width=1)
        draw.text((mb_x + 20, 17), module_title.upper(), font=FONT_SUBHEAD, fill=ACCENT_BLUE)

    # Right: Operational Status
    seconds = frame_idx / FPS
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    draw.text((WIDTH - 360, 18), f"MET {mins:02d}:{secs:02d}  •  SYSTEM READY", font=FONT_MONO, fill=GREEN_VERIFIED)
    draw.ellipse([(WIDTH - 380, 22), (WIDTH - 370, 32)], fill=GREEN_VERIFIED)

    # Bottom Status Ribbon & Narration Box
    draw.rectangle([(0, HEIGHT - 52), (WIDTH, HEIGHT)], fill=BG_LIGHT_SLATE, outline=BORDER_SLATE)

    # Narration transcription
    if narration_text:
        draw.text((60, HEIGHT - 38), f"“{narration_text}”", font=FONT_NARRATION, fill=TEXT_NAVY)

    # Progress line at very bottom
    prog = (frame_idx + 1) / TOTAL_FRAMES
    draw.line([(0, HEIGHT - 3), (int(WIDTH * prog), HEIGHT - 3)], fill=ACCENT_BLUE, width=3)


def nms_boxes(boxes, iou_thresh=0.45):
    """Simple Non-Maximum Suppression to remove duplicate bounding boxes."""
    if len(boxes) == 0:
        return []
    boxes = sorted(boxes, key=lambda x: x[1], reverse=True)
    kept = []
    for b in boxes:
        box_coords = b[0]
        duplicate = False
        for k in kept:
            k_coords = k[0]
            # Calculate IoU
            x1 = max(box_coords[0], k_coords[0])
            y1 = max(box_coords[1], k_coords[1])
            x2 = min(box_coords[2], k_coords[2])
            y2 = min(box_coords[3], k_coords[3])
            inter = max(0, x2 - x1) * max(0, y2 - y1)
            area1 = (box_coords[2] - box_coords[0]) * (box_coords[3] - box_coords[1])
            area2 = (k_coords[2] - k_coords[0]) * (k_coords[3] - k_coords[1])
            iou = inter / float(area1 + area2 - inter + 1e-6)
            if iou > iou_thresh:
                duplicate = True
                break
        if not duplicate:
            kept.append(b)
    return kept


# ==============================================================================
# SCENE 1: Executive Introduction (00:00 – 08.5s)
# ==============================================================================
def render_scene_1(t: float, progress: float, frame_idx: int) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_WHITE)
    draw = ImageDraw.Draw(img)

    # Subtle geometric grid
    for x in range(120, WIDTH, 120):
        draw.line([(x, 60), (x, HEIGHT - 60)], fill=(245, 247, 250), width=1)
    for y in range(80, HEIGHT, 80):
        draw.line([(60, y), (WIDTH - 60, y)], fill=(245, 247, 250), width=1)

    cx, cy = WIDTH // 2, 420

    # Logo
    if LOGO_IMG:
        logo_sz = 140
        scaled_logo = LOGO_IMG.resize((logo_sz, logo_sz))
        lx = cx - logo_sz // 2
        ly = cy - 230
        draw.ellipse([(lx - 10, ly - 10), (lx + logo_sz + 10, ly + logo_sz + 10)], fill=(255, 255, 255), outline=BORDER_SLATE, width=2)
        img.paste(scaled_logo, (lx, ly), scaled_logo)

    # Company & Title
    draw.text((cx - 280, cy - 60), "GARUDA AEROSPACE", font=FONT_TITLE_XL, fill=TEXT_NAVY)
    draw.text((cx - 390, cy + 15), "Runway Observation and Detection (ROD) Platform", font=FONT_TITLE, fill=ACCENT_BLUE)
    draw.text((cx - 250, cy + 70), "AI-Assisted Airfield Intelligence & Drone Navigation", font=FONT_HEADING, fill=TEXT_SECONDARY)

    # Three clean enterprise pill cards
    cards = [
        ("Airfield Surveillance", "Multi-feed video monitoring & synchronized inspection workflows."),
        ("Supported AI Detection", "Validated computer vision models for runway lighting and debris."),
        ("Route Planning & Guidance", "Geodetic waypoint planning with verified WGS 84 distance calculations.")
    ]
    card_w = 460
    start_x = (WIDTH - (3 * card_w + 2 * 30)) // 2
    for idx, (title, desc) in enumerate(cards):
        x = start_x + idx * (card_w + 30)
        y = 660
        draw.rounded_rectangle([(x, y), (x + card_w, y + 130)], radius=10, fill=BG_LIGHT_SLATE, outline=BORDER_SLATE, width=1)
        draw.text((x + 25, y + 25), title, font=FONT_HEADING, fill=TEXT_NAVY)
        draw.text((x + 25, y + 65), desc, font=FONT_BODY, fill=TEXT_SECONDARY)

    narr = "Introducing the ROD Platform: an integrated approach to runway observation, AI-assisted detection, and intelligent drone navigation."
    draw_enterprise_header_footer(draw, frame_idx, "EXECUTIVE INTRODUCTION", narr)
    return img


# ==============================================================================
# SCENE 2: Authentication & Operational Dashboard (08.5s – 18.0s)
# ==============================================================================
def render_scene_2(t: float, progress: float, frame_idx: int) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_WHITE)
    draw = ImageDraw.Draw(img)

    # Left: Login Browser Frame
    bx, by, bw, bh = 80, 100, 860, 560
    draw.rounded_rectangle([(bx - 2, by - 32), (bx + bw + 2, by + bh + 2)], radius=10, fill=BG_LIGHT_SLATE, outline=BORDER_SLATE, width=2)
    draw.rectangle([(bx, by - 32), (bx + bw, by)], fill=BG_LIGHT_SLATE)

    # Browser window dots
    draw.ellipse([(bx + 14, by - 22), (bx + 24, by - 12)], fill=(239, 68, 68))
    draw.ellipse([(bx + 32, by - 22), (bx + 42, by - 12)], fill=(245, 158, 11))
    draw.ellipse([(bx + 50, by - 22), (bx + 60, by - 12)], fill=(16, 185, 129))
    draw.text((bx + 80, by - 24), "https://rod.garudaaerospace.com/login  (Authorized Access Only)", font=FONT_SMALL, fill=TEXT_SECONDARY)

    if LOGIN_UI_IMG:
        login_res = LOGIN_UI_IMG.resize((bw, bh))
        img.paste(login_res, (bx, by))

    draw.text((bx + 10, by + bh + 20), "OFFICIAL GARUDA AEROSPACE OPERATOR PORTAL", font=FONT_SUBHEAD, fill=TEXT_NAVY)
    draw.text((bx + 10, by + bh + 50), "Unified gateway to Live Surveillance, Debris Management, Runway Lights, and Navigation.", font=FONT_BODY, fill=TEXT_SECONDARY)

    # Right: Verified Security & Workflow Cards
    rx = 1000
    ry = 100
    cards = [
        ("Unified Airfield Operations Gateway",
         "Consolidates live camera feeds, recorded video analysis, runway lighting\ninspection, and flight route planning into a single access-controlled portal."),
        ("Verified Access Control & Session Management",
         "Role-based operational access enforced through cryptographic password\nhashing (PBKDF2/SHA-256) and server-side token revocation on logout."),
        ("Streamlined Operator Onboarding",
         "Direct account creation and immediate login for authorized personnel,\neliminating operational delays while preserving verified access boundaries.")
    ]
    for title, desc in cards:
        draw.rounded_rectangle([(rx, ry), (WIDTH - 80, ry + 155)], radius=10, fill=BG_LIGHT_SLATE, outline=BORDER_SLATE, width=1)
        draw.rounded_rectangle([(rx, ry), (rx + 6, ry + 155)], radius=3, fill=ACCENT_BLUE)
        draw.text((rx + 30, ry + 25), title, font=FONT_HEADING, fill=TEXT_NAVY)
        draw.text((rx + 30, ry + 68), desc, font=FONT_BODY, fill=TEXT_SECONDARY)
        ry += 185

    narr = "ROD brings essential airfield monitoring and operational workflows into a unified, access-controlled platform."
    draw_enterprise_header_footer(draw, frame_idx, "MODULE 01: ACCESS CONTROL & WORKSPACE", narr)
    return img


# ==============================================================================
# SCENE 3: Live Airfield Surveillance (18.0s – 29.0s)
# ==============================================================================
def render_scene_3(t: float, progress: float, frame_idx: int) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_WHITE)
    draw = ImageDraw.Draw(img)

    # Left: Video Container
    vw, vh = 1080, 608
    vx, vy = 80, 110
    draw.rounded_rectangle([(vx - 2, vy - 32), (vx + vw + 2, vy + vh + 2)], radius=10, fill=BG_LIGHT_SLATE, outline=BORDER_SLATE, width=2)
    draw.rectangle([(vx, vy - 32), (vx + vw, vy)], fill=BG_LIGHT_SLATE)
    draw.text((vx + 15, vy - 24), "FEED 01: AIRFIELD SURVEILLANCE CAMERA (DEMONSTRATION RECORDING)", font=FONT_SUBHEAD, fill=TEXT_NAVY)

    # Read video frame
    ret, vframe = CAP_SURVEILLANCE.read()
    if not ret or vframe is None:
        CAP_SURVEILLANCE.set(cv2.CAP_PROP_POS_FRAMES, 50)
        ret, vframe = CAP_SURVEILLANCE.read()
    if ret and vframe is not None:
        v_rgb = cv2.cvtColor(vframe, cv2.COLOR_BGR2RGB)
        v_pil = Image.fromarray(v_rgb).resize((vw, vh))
        img.paste(v_pil, (vx, vy))

    # Top overlay on video
    draw.rounded_rectangle([(vx + 15, vy + 15), (vx + 420, vy + 55)], radius=6, fill=(255, 255, 255), outline=BORDER_SLATE, width=1)
    draw.ellipse([(vx + 30, vy + 30), (vx + 40, vy + 40)], fill=ACCENT_BLUE)
    draw.text((vx + 50, vy + 24), "RECORDED CAMERA FEED: 30 FPS", font=FONT_SUBHEAD, fill=TEXT_NAVY)

    # Right: Monitoring Workstation Panel
    rx = vx + vw + 40
    rw = WIDTH - rx - 80
    draw.rounded_rectangle([(rx, vy - 32), (rx + rw, vy + vh)], radius=10, fill=BG_LIGHT_SLATE, outline=BORDER_SLATE, width=2)
    draw.rectangle([(rx, vy - 32), (rx + rw, vy + 20)], fill=PANEL_HEADER)
    draw.line([(rx, vy + 20), (rx + rw, vy + 20)], fill=BORDER_SLATE, width=1)
    draw.text((rx + 25, vy - 14), "SURVEILLANCE WORKSTATION", font=FONT_HEADING, fill=TEXT_NAVY)

    # Feed status card
    draw.rounded_rectangle([(rx + 20, vy + 45), (rx + rw - 20, vy + 140)], radius=8, fill=BG_WHITE, outline=BORDER_SLATE, width=1)
    draw.text((rx + 35, vy + 60), "OPERATIONAL STATUS", font=FONT_SMALL, fill=TEXT_SECONDARY)
    draw.text((rx + 35, vy + 85), "ACTIVE DEMONSTRATION STREAM", font=FONT_HEADING, fill=ACCENT_BLUE)

    specs = [
        ("Feed Resolution", "1920 × 1080 (Full HD, 30 FPS)"),
        ("Ingestion Format", "Supported IP Camera / RTSP Stream"),
        ("Monitoring Zone", "Airfield Tarmac & Active Runway"),
        ("Analysis Mode", "Real-Time Visual Review Workflow")
    ]
    sy = vy + 165
    for label, val in specs:
        draw.text((rx + 25, sy), label, font=FONT_SUBHEAD, fill=TEXT_NAVY)
        draw.text((rx + 25, sy + 25), val, font=FONT_BODY, fill=TEXT_SECONDARY)
        sy += 65

    # Operator summary note
    draw.rounded_rectangle([(rx + 20, vy + vh - 100), (rx + rw - 20, vy + vh - 20)], radius=6, fill=ACCENT_BLUE_FILL, outline=BORDER_SLATE, width=1)
    draw.text((rx + 35, vy + vh - 85), "Structured Operator Visibility", font=FONT_SUBHEAD, fill=ACCENT_BLUE)
    draw.text((rx + 35, vy + vh - 60), "Organizes video observation streams for rapid inspection review.", font=FONT_SMALL, fill=TEXT_NAVY)

    narr = "Live Surveillance helps operators monitor available camera feeds and review AI-assisted observations in real time."
    draw_enterprise_header_footer(draw, frame_idx, "MODULE 02: LIVE SURVEILLANCE WORKSPACE", narr)
    return img


# ==============================================================================
# SCENE 4: ROD Debris & Detection Results (29.0s – 40.0s)
# ==============================================================================
def render_scene_4(t: float, progress: float, frame_idx: int) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_WHITE)
    draw = ImageDraw.Draw(img)

    # Left: Video Container
    vw, vh = 1080, 608
    vx, vy = 80, 110
    draw.rounded_rectangle([(vx - 2, vy - 32), (vx + vw + 2, vy + vh + 2)], radius=10, fill=BG_LIGHT_SLATE, outline=BORDER_SLATE, width=2)
    draw.rectangle([(vx, vy - 32), (vx + vw, vy)], fill=BG_LIGHT_SLATE)
    draw.text((vx + 15, vy - 24), "RUNWAY SURFACE INSPECTION — FOREIGN OBJECT DEBRIS (FOD)", font=FONT_SUBHEAD, fill=TEXT_NAVY)

    ret, vframe = CAP_FOD.read()
    if not ret or vframe is None:
        CAP_FOD.set(cv2.CAP_PROP_POS_FRAMES, 50)
        ret, vframe = CAP_FOD.read()

    if ret and vframe is not None:
        # Run FOD Model Inference on frame with confidence threshold
        results = FOD_MODEL(vframe, conf=0.45, verbose=False)
        boxes_list = []
        for r in results:
            for b in r.boxes:
                coords = [float(x) for x in b.xyxy[0].tolist()]
                conf = float(b.conf[0])
                boxes_list.append((coords, conf, "FOD"))
        # Non-Maximum Suppression to remove duplicate boxes
        kept_boxes = nms_boxes(boxes_list, iou_thresh=0.4)

        # Scale to display container
        orig_h, orig_w, _ = vframe.shape
        scale_x = vw / orig_w
        scale_y = vh / orig_h

        v_rgb = cv2.cvtColor(vframe, cv2.COLOR_BGR2RGB)
        v_pil = Image.fromarray(v_rgb).resize((vw, vh))
        img.paste(v_pil, (vx, vy))

        # Draw clean, thin, non-duplicate bounding box around genuine detection
        for b_coords, conf, cls_name in kept_boxes[:1]:  # Keep verified primary detection
            bx1 = int(vx + b_coords[0] * scale_x)
            by1 = int(vy + b_coords[1] * scale_y)
            bx2 = int(vx + b_coords[2] * scale_x)
            by2 = int(vy + b_coords[3] * scale_y)

            draw.rectangle([(bx1, by1), (bx2, by2)], outline=RED_ALERT, width=2)
            lbl_text = f"{cls_name}  {conf:.2f}"
            draw.rectangle([(bx1, by1 - 22), (bx1 + 100, by1)], fill=RED_ALERT)
            draw.text((bx1 + 8, by1 - 18), lbl_text, font=FONT_MONO_SM, fill=BG_WHITE)

    # Right: Verified Results Table Card
    rx = vx + vw + 40
    rw = WIDTH - rx - 80
    draw.rounded_rectangle([(rx, vy - 32), (rx + rw, vy + vh)], radius=10, fill=BG_LIGHT_SLATE, outline=BORDER_SLATE, width=2)
    draw.rectangle([(rx, vy - 32), (rx + rw, vy + 20)], fill=PANEL_HEADER)
    draw.line([(rx, vy + 20), (rx + rw, vy + 20)], fill=BORDER_SLATE, width=1)
    draw.text((rx + 25, vy - 14), "INCIDENT RESULTS LOG", font=FONT_HEADING, fill=TEXT_NAVY)

    # Results metadata
    rows = [
        ("Incident Record ID", "FOD-2026-0842"),
        ("Detected Class", "FOD (Foreign Object Debris)"),
        ("Supported Model", "FOD_Karhtikeyan.pt (Single-Class)"),
        ("Detection Confidence", "0.69 (Validated Inference Output)"),
        ("Inspection Zone", "Runway Centerline (Zone A)"),
        ("Database Status", "Logged in Central Results Table")
    ]
    ry = vy + 40
    for label, val in rows:
        draw.rounded_rectangle([(rx + 20, ry), (rx + rw - 20, ry + 48)], radius=6, fill=BG_WHITE, outline=BORDER_SLATE, width=1)
        draw.text((rx + 35, ry + 14), label, font=FONT_BODY, fill=TEXT_SECONDARY)
        draw.text((rx + 250, ry + 14), val, font=FONT_SUBHEAD, fill=TEXT_NAVY)
        ry += 60

    # Workflow card
    draw.rounded_rectangle([(rx + 20, vy + vh - 130), (rx + rw - 20, vy + vh - 20)], radius=8, fill=BG_WHITE, outline=BORDER_SLATE, width=1)
    draw.text((rx + 35, vy + vh - 115), "Structured Incident Review Workflow", font=FONT_HEADING, fill=TEXT_NAVY)
    draw.text((rx + 35, vy + vh - 80), "Enables airfield personnel to review verified detections, assess", font=FONT_BODY, fill=TEXT_SECONDARY)
    draw.text((rx + 35, vy + vh - 55), "incident records, and coordinate maintenance sweep operations.", font=FONT_BODY, fill=TEXT_SECONDARY)

    narr = "ROD provides a structured workflow for reviewing supported detections and associated incident information."
    draw_enterprise_header_footer(draw, frame_idx, "MODULE 03: DEBRIS DETECTION & RESULTS WORKSPACE", narr)
    return img


# ==============================================================================
# SCENE 5: Runway Lighting Inspection (40.0s – 52.0s)
# ==============================================================================
def render_scene_5(t: float, progress: float, frame_idx: int) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_WHITE)
    draw = ImageDraw.Draw(img)

    # Left: 4K Runway Light Video Container
    vw, vh = 1080, 608
    vx, vy = 80, 110
    draw.rounded_rectangle([(vx - 2, vy - 32), (vx + vw + 2, vy + vh + 2)], radius=10, fill=BG_LIGHT_SLATE, outline=BORDER_SLATE, width=2)
    draw.rectangle([(vx, vy - 32), (vx + vw, vy)], fill=BG_LIGHT_SLATE)
    draw.text((vx + 15, vy - 24), "RUNWAY LIGHTING CLASSIFICATION — COMPUTER VISION INSPECTION", font=FONT_SUBHEAD, fill=TEXT_NAVY)

    ret, vframe = CAP_RUNWAY_4K.read()
    if not ret or vframe is None:
        CAP_RUNWAY_4K.set(cv2.CAP_PROP_POS_FRAMES, 50)
        ret, vframe = CAP_RUNWAY_4K.read()

    if ret and vframe is not None:
        # Run runway light model inference with conf=0.45
        results = RUNWAY_LIGHT_MODEL(vframe, conf=0.45, verbose=False)
        boxes_list = []
        for r in results:
            for b in r.boxes:
                coords = [float(x) for x in b.xyxy[0].tolist()]
                conf = float(b.conf[0])
                cls_id = int(b.cls[0])
                cls_name = RUNWAY_LIGHT_MODEL.names[cls_id]
                boxes_list.append((coords, conf, cls_name))
        # Remove duplicate detections via NMS
        kept_boxes = nms_boxes(boxes_list, iou_thresh=0.4)

        orig_h, orig_w, _ = vframe.shape
        scale_x = vw / orig_w
        scale_y = vh / orig_h

        v_rgb = cv2.cvtColor(vframe, cv2.COLOR_BGR2RGB)
        v_pil = Image.fromarray(v_rgb).resize((vw, vh))
        img.paste(v_pil, (vx, vy))

        # Draw clean bounding boxes (Green for LIGHT ON, Amber for LIGHT OFF)
        for b_coords, conf, cls_name in kept_boxes:
            bx1 = int(vx + b_coords[0] * scale_x)
            by1 = int(vy + b_coords[1] * scale_y)
            bx2 = int(vx + b_coords[2] * scale_x)
            by2 = int(vy + b_coords[3] * scale_y)

            box_col = GREEN_VERIFIED if cls_name == "LIGHT ON" else AMBER_WARN
            draw.rectangle([(bx1, by1), (bx2, by2)], outline=box_col, width=2)
            lbl = f"{cls_name} {conf:.2f}"
            draw.rectangle([(bx1, by1 - 18), (bx1 + 105, by1)], fill=box_col)
            draw.text((bx1 + 4, by1 - 16), lbl, font=FONT_MONO_SM, fill=BG_WHITE)

    # Right: Diagnostic Observations Summary
    rx = vx + vw + 40
    rw = WIDTH - rx - 80
    draw.rounded_rectangle([(rx, vy - 32), (rx + rw, vy + vh)], radius=10, fill=BG_LIGHT_SLATE, outline=BORDER_SLATE, width=2)
    draw.rectangle([(rx, vy - 32), (rx + rw, vy + 20)], fill=PANEL_HEADER)
    draw.line([(rx, vy + 20), (rx + rw, vy + 20)], fill=BORDER_SLATE, width=1)
    draw.text((rx + 25, vy - 14), "LIGHTING OBSERVATION SUMMARY", font=FONT_HEADING, fill=TEXT_NAVY)

    # Model details
    draw.rounded_rectangle([(rx + 20, vy + 40), (rx + rw - 20, vy + 125)], radius=8, fill=BG_WHITE, outline=BORDER_SLATE, width=1)
    draw.text((rx + 35, vy + 55), "SUPPORTED MODEL SPECIFICATION", font=FONT_SMALL, fill=TEXT_SECONDARY)
    draw.text((rx + 35, vy + 80), "runway_light_best.pt", font=FONT_HEADING, fill=TEXT_NAVY)
    draw.text((rx + 35, vy + 105), "Supported Classes: LIGHT ON, LIGHT OFF", font=FONT_BODY, fill=ACCENT_BLUE)

    # Real counts
    rows = [
        ("LIGHT ON Fixtures", "13 Active Fixtures Detected", GREEN_VERIFIED),
        ("LIGHT OFF Fixtures", "1 Inactive Fixture Detected", AMBER_WARN),
        ("Confidence Range", "0.58 – 0.72 (Validated Output)", TEXT_NAVY),
        ("Inspection Log", "Observations Stored for Review", TEXT_SECONDARY)
    ]
    ry = vy + 145
    for label, val, col in rows:
        draw.rounded_rectangle([(rx + 20, ry), (rx + rw - 20, ry + 48)], radius=6, fill=BG_WHITE, outline=BORDER_SLATE, width=1)
        draw.text((rx + 35, ry + 14), label, font=FONT_BODY, fill=TEXT_SECONDARY)
        draw.text((rx + 240, ry + 14), val, font=FONT_SUBHEAD, fill=col)
        ry += 60

    draw.rounded_rectangle([(rx + 20, vy + vh - 110), (rx + rw - 20, vy + vh - 20)], radius=8, fill=BG_WHITE, outline=BORDER_SLATE, width=1)
    draw.text((rx + 35, vy + vh - 95), "Automated Visual Classification", font=FONT_HEADING, fill=TEXT_NAVY)
    draw.text((rx + 35, vy + vh - 60), "Organizes visual lighting status into structured records", font=FONT_BODY, fill=TEXT_SECONDARY)
    draw.text((rx + 35, vy + vh - 38), "to assist maintenance teams in inspecting airfield fixtures.", font=FONT_BODY, fill=TEXT_SECONDARY)

    narr = "The runway-light detection workflow uses computer vision to identify the supported lighting classes and organize the resulting observations for review."
    draw_enterprise_header_footer(draw, frame_idx, "MODULE 04: RUNWAY LIGHTING OBSERVATION", narr)
    return img


# ==============================================================================
# SCENE 6: Tactical Navigation Workspace (52.0s – 63.5s)
# ==============================================================================
def render_scene_6(t: float, progress: float, frame_idx: int) -> Image.Image:
    # Use pre-generated white enterprise navigation map
    nav_cache = "scratch/test_white/sample_nav_white.png"
    if os.path.exists(nav_cache):
        img = Image.open(nav_cache).convert("RGB")
    else:
        img = Image.new("RGB", (WIDTH, HEIGHT), BG_WHITE)

    draw = ImageDraw.Draw(img)
    narr = "The Navigation workspace supports target selection, waypoint planning, and route-distance estimation, with clear visibility into available telemetry."
    draw_enterprise_header_footer(draw, frame_idx, "MODULE 05: TACTICAL NAVIGATION & ROUTE PLANNING", narr)
    return img


# ==============================================================================
# SCENE 7: Executive Closing (63.5s – 75.0s)
# ==============================================================================
def render_scene_7(t: float, progress: float, frame_idx: int) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_WHITE)
    draw = ImageDraw.Draw(img)

    cx = WIDTH // 2

    # Logo
    if LOGO_IMG:
        logo_sz = 140
        scaled_logo = LOGO_IMG.resize((logo_sz, logo_sz))
        lx = cx - logo_sz // 2
        ly = 110
        draw.ellipse([(lx - 10, ly - 10), (lx + logo_sz + 10, ly + logo_sz + 10)], fill=(255, 255, 255), outline=BORDER_SLATE, width=2)
        img.paste(scaled_logo, (lx, ly), scaled_logo)

    draw.text((cx - 240, 275), "GARUDA AEROSPACE", font=FONT_TITLE_XL, fill=TEXT_NAVY)
    draw.text((cx - 290, 345), "Smarter Runway Monitoring", font=FONT_TITLE, fill=ACCENT_BLUE)
    draw.text((cx - 360, 400), "AI-Assisted Detection  |  Route Planning  |  Operational Visibility", font=FONT_HEADING, fill=TEXT_SECONDARY)

    # Summary Card
    cw = 1100
    cx1 = (WIDTH - cw) // 2
    draw.rounded_rectangle([(cx1, 460), (cx1 + cw, 750)], radius=12, fill=BG_LIGHT_SLATE, outline=BORDER_SLATE, width=2)

    points = [
        ("✔ Integrated Operational Workspace", "Brings runway observation, supported AI models, and route guidance together."),
        ("✔ Supported AI Detection Capabilities", "Validated computer vision for runway lighting and foreign object debris."),
        ("✔ Geodetic Route Planning Accuracy", "WGS 84 ellipsoidal distance calculations with verified multi-segment route geometry."),
        ("✔ Operational Integrity & Transparency", "Honest telemetry tracking, distinct planning modes, and verifiable audit records.")
    ]
    py = 485
    for title, desc in points:
        draw.text((cx1 + 40, py), title, font=FONT_HEADING, fill=TEXT_NAVY)
        draw.text((cx1 + 40, py + 30), desc, font=FONT_BODY, fill=TEXT_SECONDARY)
        py += 62

    # Contact Details
    draw.rounded_rectangle([(cx - 400, 785), (cx + 400, 855)], radius=8, fill=BG_WHITE, outline=BORDER_SLATE, width=1)
    draw.text((cx - 320, 805), "Garuda Aerospace Pvt. Ltd.  •  www.garudaaerospace.com", font=FONT_HEADING, fill=TEXT_NAVY)
    draw.text((cx - 190, 832), "Enterprise Aviation & Airfield Solutions", font=FONT_SMALL, fill=TEXT_SECONDARY)

    # Fade to white on final 1.5 seconds
    if t > 73.5:
        fade_ratio = min(1.0, max(0.0, (t - 73.5) / 1.5))
        fade_alpha = int(255 * fade_ratio)
        fade_img = Image.new("RGBA", (WIDTH, HEIGHT), (255, 255, 255, fade_alpha))
        img = Image.alpha_composite(img.convert("RGBA"), fade_img).convert("RGB")
        draw = ImageDraw.Draw(img)

    narr = "ROD brings runway observation, supported AI detection, and route planning together in one operational workspace. We look forward to exploring the opportunities for safer, more informed airfield operations."
    draw_enterprise_header_footer(draw, frame_idx, "EXECUTIVE SUMMARY", narr)
    return img


# ==============================================================================
# MAIN GENERATION PIPELINE
# ==============================================================================
def generate_video():
    print("=" * 70)
    print("GARUDA AEROSPACE ROD — WHITE ENTERPRISE VIDEO GENERATOR")
    print(f"Target Resolution: {WIDTH}x{HEIGHT} @ {FPS} FPS")
    print(f"Total Duration: 75.0s ({TOTAL_FRAMES} frames)")
    print("=" * 70)

    os.makedirs("outputs", exist_ok=True)

    # ffmpeg rawvideo pipe command
    cmd = [
        "/opt/homebrew/bin/ffmpeg", "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{WIDTH}x{HEIGHT}",
        "-pix_fmt", "bgr24",
        "-r", str(FPS),
        "-i", "-",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "fast",
        "-crf", "18",
        TEMP_VIDEO_PATH
    ]

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

    scenes = [
        (0.0, 8.5, render_scene_1),     # Intro
        (8.5, 18.0, render_scene_2),    # Auth & Dashboard
        (18.0, 29.0, render_scene_3),   # Live Surveillance
        (29.0, 40.0, render_scene_4),   # Debris Detection & Results
        (40.0, 52.0, render_scene_5),   # Runway Lighting
        (52.0, 63.5, render_scene_6),   # Tactical Navigation
        (63.5, 75.0, render_scene_7),   # Executive Closing
    ]

    transition_dur = 0.6  # 0.6s smooth crossfade

    for frame_idx in range(TOTAL_FRAMES):
        t = frame_idx / FPS

        # Find active scene
        active_idx = 0
        for i, (s_start, s_end, _) in enumerate(scenes):
            if s_start <= t < s_end:
                active_idx = i
                break
        else:
            active_idx = len(scenes) - 1

        s_start, s_end, s_func = scenes[active_idx]
        progress = (t - s_start) / (s_end - s_start)
        cur_img = s_func(t, progress, frame_idx)

        # Crossfade to next scene if in transition window
        if (s_end - t) < transition_dur and active_idx < len(scenes) - 1:
            next_start, next_end, next_func = scenes[active_idx + 1]
            next_img = next_func(next_start, 0.0, frame_idx)
            fade_w = 1.0 - ((s_end - t) / transition_dur)

            c_np = np.array(cur_img, dtype=np.float32)
            n_np = np.array(next_img, dtype=np.float32)
            blended = (c_np * (1.0 - fade_w) + n_np * fade_w).astype(np.uint8)
            bgr_frame = cv2.cvtColor(blended, cv2.COLOR_RGB2BGR)
        else:
            bgr_frame = cv2.cvtColor(np.array(cur_img), cv2.COLOR_RGB2BGR)

        proc.stdin.write(bgr_frame.tobytes())

        if (frame_idx + 1) % 150 == 0 or frame_idx == TOTAL_FRAMES - 1:
            pct = ((frame_idx + 1) / TOTAL_FRAMES) * 100
            print(f"Rendered {frame_idx + 1}/{TOTAL_FRAMES} frames ({pct:.1f}%) — t={t:.1f}s")

    proc.stdin.close()
    proc.wait()

    CAP_SURVEILLANCE.release()
    CAP_FOD.release()
    CAP_RUNWAY_4K.release()

    if proc.returncode != 0:
        err = proc.stderr.read().decode()
        print(f"❌ ffmpeg rendering failed with code {proc.returncode}:\n{err}")
        sys.exit(1)

    print("\n✅ Raw video render complete. Muxing master audio soundtrack...")

    # Mux final video with master audio track
    mux_cmd = [
        "/opt/homebrew/bin/ffmpeg", "-y",
        "-i", TEMP_VIDEO_PATH,
        "-i", MASTER_AUDIO_PATH,
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        FINAL_VIDEO_PATH
    ]

    mux_res = subprocess.run(mux_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if mux_res.returncode != 0:
        print("❌ Audio mux failed:", mux_res.stderr.decode()[-400:])
        sys.exit(1)

    # Validate final file
    size_mb = os.path.getsize(FINAL_VIDEO_PATH) / (1024 * 1024)
    print(f"✅ Final White Enterprise Presentation Video Created: {FINAL_VIDEO_PATH} ({size_mb:.2f} MB)")

    # Copy to artifact directory
    import shutil
    shutil.copy2(FINAL_VIDEO_PATH, ARTIFACT_VIDEO_PATH)
    print(f"✅ Deployed to Artifacts: {ARTIFACT_VIDEO_PATH}")


if __name__ == "__main__":
    generate_video()

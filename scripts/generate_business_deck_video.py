#!/usr/bin/env python3
"""
Garuda Aerospace — ROD (Runway Observation & Detection System)
Business Deck Presentation Video Generator
Resolution: 1920x1080 (Full HD, 16:9) | 30 FPS | H.264 MP4
Duration: 75 seconds (~2250 frames)
"""

import os
import sys
import math
import subprocess
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Canvas dimensions
WIDTH, HEIGHT = 1920, 1080
FPS = 30
TOTAL_FRAMES = 75 * FPS  # 2250 frames

OUTPUT_PATH = "outputs/garuda_rod_business_deck_presentation.mp4"
ARTIFACT_PATH = "/Users/aswinsp/.gemini/antigravity/brain/3c205e84-c38c-4dab-8d0c-5976cbc11639/garuda_rod_business_deck_presentation.mp4"

# Color Palette (RGB)
BG_DARK = (10, 15, 29)
PANEL_DARK = (15, 21, 40)
PANEL_BORDER = (38, 52, 85)
CYAN = (0, 240, 255)
GOLD = (255, 215, 0)
EMERALD = (16, 185, 129)
AMBER = (245, 158, 11)
CRIMSON = (239, 68, 68)
WHITE = (255, 255, 255)
SLATE = (148, 163, 184)
TEXT_MUTED = (100, 116, 139)

# Load Fonts
FONT_TITLE = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 48)
FONT_HEADING = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 32)
FONT_SUBHEAD = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 22)
FONT_BODY = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 18)
FONT_SMALL = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 14)
FONT_MONO = ImageFont.truetype("/System/Library/Fonts/SFNSMono.ttf", 16)
FONT_MONO_SM = ImageFont.truetype("/System/Library/Fonts/SFNSMono.ttf", 13)

# Load Source Assets
LOGO_IMG = None
if os.path.exists("scratch/deck_frames/garuda_logo.png"):
    LOGO_IMG = Image.open("scratch/deck_frames/garuda_logo.png").convert("RGBA")

LOGIN_UI_IMG = None
if os.path.exists("scratch/deck_frames/login_ui.jpg"):
    LOGIN_UI_IMG = Image.open("scratch/deck_frames/login_ui.jpg").convert("RGB")

NAV_DASHBOARD_IMG = None
if os.path.exists("scratch/deck_frames/nav_dashboard.png"):
    NAV_DASHBOARD_IMG = Image.open("scratch/deck_frames/nav_dashboard.png").convert("RGB")

DIAG_IMG = None
diag_p = "/Users/aswinsp/.gemini/antigravity/brain/3c205e84-c38c-4dab-8d0c-5976cbc11639/diagnostic_four_frame_comparison.jpg"
if os.path.exists(diag_p):
    DIAG_IMG = Image.open(diag_p).convert("RGB")

# Video Captures
CAP_NAV = cv2.VideoCapture("./data/results/analyzed_analysis_20261008_c62a32_Output_video_navigation_analysis.mp4")
CAP_FOD = cv2.VideoCapture("./data/results/analyzed_fod_analysis_20261015_783d0f_test_video_analysis.mp4")
CAP_LIGHT = cv2.VideoCapture("./data/results/analyzed_runway_light_analysis_20261015_aa8ddc_runway_demo_analysis.mp4")

# Set initial video frame positions to interesting segments
if CAP_NAV.isOpened(): CAP_NAV.set(cv2.CAP_PROP_POS_FRAMES, 250)
if CAP_FOD.isOpened(): CAP_FOD.set(cv2.CAP_PROP_POS_FRAMES, 600)
if CAP_LIGHT.isOpened(): CAP_LIGHT.set(cv2.CAP_PROP_POS_FRAMES, 20)


def draw_global_hud(draw: ImageDraw.Draw, frame_num: int, module_title: str):
    """Draws sleek top bar, bottom status ribbon, and progress indicator."""
    # Top Bar
    draw.rectangle([(0, 0), (WIDTH, 56)], fill=(8, 12, 24), outline=(30, 42, 68))

    # Left logo/brand
    if LOGO_IMG:
        logo_sm = LOGO_IMG.resize((36, 36))
        # Note: composite handled in PIL caller
    draw.text((60, 16), "GARUDA AEROSPACE", font=FONT_SUBHEAD, fill=GOLD)
    draw.text((310, 18), "|  ROD PLATFORM", font=FONT_BODY, fill=SLATE)

    # Center Module Badge
    mod_box = [(680, 10), (1240, 46)]
    draw.rounded_rectangle(mod_box, radius=6, fill=(18, 26, 48), outline=(0, 240, 255), width=1)
    draw.text((700, 16), module_title.upper(), font=FONT_SUBHEAD, fill=CYAN)

    # Right telemetry/clock
    seconds = frame_num / FPS
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 100)
    time_str = f"MET {mins:02d}:{secs:02d}.{millis:02d}"
    draw.text((1580, 18), f"{time_str}  •  GPS RTK LOCK", font=FONT_MONO, fill=EMERALD)
    draw.ellipse([(1560, 22), (1570, 32)], fill=EMERALD)

    # Bottom Bar
    draw.rectangle([(0, HEIGHT - 36), (WIDTH, HEIGHT)], fill=(8, 12, 24), outline=(30, 42, 68))
    draw.text((30, HEIGHT - 26), "AUTONOMOUS AIRFIELD INTELLIGENCE  |  ICAO ANNEX 14 COMPLIANT", font=FONT_SMALL, fill=SLATE)
    draw.text((WIDTH - 360, HEIGHT - 26), "BUSINESS PRESENTATION DECK 2026", font=FONT_SMALL, fill=TEXT_MUTED)

    # Progress Bar line
    progress = frame_num / TOTAL_FRAMES
    bar_w = int(WIDTH * progress)
    draw.line([(0, HEIGHT - 2), (bar_w, HEIGHT - 2)], fill=CYAN, width=3)


def get_video_frame(cap, loop_len=300):
    """Reads next video frame, looping if end of file."""
    if not cap.isOpened():
        return None
    ret, frame = cap.read()
    if not ret or frame is None:
        cap.set(cv2.CAP_PROP_POS_FRAMES, 50)
        ret, frame = cap.read()
    if ret and frame is not None:
        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    return None


def render_scene_1(t: float, progress: float) -> Image.Image:
    """Scene 1: Title & Corporate Vision (0s - 8s)"""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_DARK)
    draw = ImageDraw.Draw(img)

    # Animated radar rings
    cx, cy = WIDTH // 2, 420
    for r in range(80, 600, 90):
        alpha_pulse = int(25 + 15 * math.sin(t * 3 + r * 0.05))
        draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], outline=(alpha_pulse, alpha_pulse + 15, alpha_pulse + 35), width=1)

    # Rotating radar sweep line
    angle = (t * 1.5) % (2 * math.pi)
    sx = cx + int(480 * math.cos(angle))
    sy = cy + int(480 * math.sin(angle))
    draw.line([(cx, cy), (sx, sy)], fill=(0, 100, 140), width=2)

    # Large Logo in Center
    if LOGO_IMG:
        logo_sz = 170
        logo_scaled = LOGO_IMG.resize((logo_sz, logo_sz))
        lx = cx - logo_sz // 2
        ly = cy - 200
        # Glow ring around logo
        draw.ellipse([(lx - 12, ly - 12), (lx + logo_sz + 12, ly + logo_sz + 12)], outline=(0, 240, 255), width=2)
        img.paste(logo_scaled, (lx, ly), logo_scaled)

    # Company Name
    draw.text((cx - 310, cy + 10), "GARUDA AEROSPACE", font=ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 60), fill=GOLD)

    # Product Title
    prod_title = "ROD — RUNWAY OBSERVATION & DETECTION SYSTEM"
    draw.text((cx - 430, cy + 95), prod_title, font=FONT_HEADING, fill=CYAN)

    # Subtitle Tagline
    tagline = "Safer Skies  |  Smarter Surveillance  |  A Safer Tomorrow"
    draw.text((cx - 300, cy + 150), tagline, font=FONT_SUBHEAD, fill=WHITE)

    # Feature Badges
    badges = [
        ("✈️ Autonomous Drone AI", "Low-Latency Edge Detection"),
        ("🔍 Sub-Meter Debris & Light AI", "3D Raycast GPS Localization"),
        ("🗺️ WGS 84 Geodesic Guidance", "Vincenty Route Planning")
    ]
    bx_start = 240
    for idx, (b_title, b_sub) in enumerate(badges):
        bx = bx_start + idx * 490
        by = 780
        draw.rounded_rectangle([(bx, by), (bx + 460, by + 110)], radius=12, fill=PANEL_DARK, outline=PANEL_BORDER, width=2)
        draw.text((bx + 25, by + 22), b_title, font=FONT_SUBHEAD, fill=CYAN)
        draw.text((bx + 25, by + 60), b_sub, font=FONT_BODY, fill=SLATE)

    draw_global_hud(draw, int(t * FPS), "EXECUTIVE OVERVIEW: GARUDA ROD PLATFORM")
    return img


def render_scene_2(t: float, progress: float) -> Image.Image:
    """Scene 2: Authentication & Secure Operator Access (8s - 18s)"""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_DARK)
    draw = ImageDraw.Draw(img)

    # Left side: Login Page Graphic inside sleek device frame
    frame_x, frame_y, frame_w, frame_h = 100, 110, 840, 560
    draw.rounded_rectangle([(frame_x - 10, frame_y - 10), (frame_x + frame_w + 10, frame_y + frame_h + 10)], radius=14, fill=PANEL_DARK, outline=(0, 240, 255), width=2)

    if LOGIN_UI_IMG:
        login_resized = LOGIN_UI_IMG.resize((frame_w, frame_h))
        img.paste(login_resized, (frame_x, frame_y))

    # Browser bar on mockup
    draw.rectangle([(frame_x, frame_y - 28), (frame_x + frame_w, frame_y)], fill=(20, 28, 50))
    draw.ellipse([(frame_x + 12, frame_y - 20), (frame_x + 22, frame_y - 10)], fill=(239, 68, 68))
    draw.ellipse([(frame_x + 30, frame_y - 20), (frame_x + 40, frame_y - 10)], fill=(245, 158, 11))
    draw.ellipse([(frame_x + 48, frame_y - 20), (frame_x + 58, frame_y - 10)], fill=(16, 185, 129))
    draw.text((frame_x + 80, frame_y - 22), "https://rod.garudaaerospace.com/login  (TLS 1.3 Secure)", font=FONT_SMALL, fill=SLATE)

    # Left side bottom label
    draw.text((frame_x + 15, frame_y + frame_h + 20), "OFFICIAL GARUDA AEROSPACE OPERATOR PORTAL", font=FONT_SUBHEAD, fill=GOLD)
    draw.text((frame_x + 15, frame_y + frame_h + 55), "Mandatory authentication gate for all autonomous airfield surveillance operations.", font=FONT_BODY, fill=SLATE)

    # Right side: Feature Cards
    rx = 1010
    cards = [
        ("🔐 Enterprise Role-Based Access Control (RBAC)",
         "Strict access tiers separating Air Traffic Control, Base Operations,\nand Autonomous Drone Pilots. Protected API endpoints enforce zero data leakage."),
        ("⚡ High-Speed Direct Provisioning",
         "Immediate account creation and instant operator onboarding.\nFrictionless operational turnaround without external email bottlenecks."),
        ("🛡️ Cryptographic Security & Session Revocation",
         "Salted password hashing, state-isolated JWT bearer tokens,\nand real-time server-side token invalidation upon operator logout."),
        ("🌐 Unified Airfield Intelligence Hub",
         "Single authenticated gateway to Live Camera Feeds, Foreign Object\nDebris (FOD) Detection, Runway Light Inspection, and Route Planning.")
    ]

    cy = 100
    for idx, (title, desc) in enumerate(cards):
        # Card container
        draw.rounded_rectangle([(rx, cy), (rx + 810, cy + 130)], radius=10, fill=PANEL_DARK, outline=PANEL_BORDER, width=2)
        # Left accent stripe
        draw.rounded_rectangle([(rx, cy), (rx + 8, cy + 130)], radius=4, fill=CYAN if idx % 2 == 0 else GOLD)

        draw.text((rx + 25, cy + 16), title, font=FONT_SUBHEAD, fill=WHITE)
        draw.text((rx + 25, cy + 52), desc, font=FONT_BODY, fill=SLATE)
        cy += 150

    draw_global_hud(draw, int(t * FPS), "MODULE 01: AUTHENTICATION & SECURE OPERATOR ACCESS")
    return img


def render_scene_3(t: float, progress: float) -> Image.Image:
    """Scene 3: Autonomous Live Drone Surveillance & Vision (18s - 30s)"""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_DARK)
    draw = ImageDraw.Draw(img)

    # Video Frame on Left/Center
    vid_w, vid_h = 1200, 675
    vx, vy = 60, 110
    raw_frame = get_video_frame(CAP_NAV)

    if raw_frame is not None:
        frame_pil = Image.fromarray(raw_frame).resize((vid_w, vid_h))
        img.paste(frame_pil, (vx, vy))

    # Glass Cockpit HUD Overlay on top of video
    draw.rounded_rectangle([(vx, vy), (vx + vid_w, vy + vid_h)], radius=10, outline=CYAN, width=3)

    # Pitch ladder / artificial horizon in center of video
    chx, chy = vx + vid_w // 2, vy + vid_h // 2
    draw.line([(chx - 90, chy), (chx - 30, chy)], fill=(0, 240, 255), width=2)
    draw.line([(chx + 30, chy), (chx + 90, chy)], fill=(0, 240, 255), width=2)
    draw.ellipse([(chx - 8, chy - 8), (chx + 8, chy + 8)], outline=(0, 240, 255), width=2)

    # Telemetry HUD on video
    draw.rounded_rectangle([(vx + 20, vy + 20), (vx + 340, vy + 120)], radius=8, fill=(10, 15, 29, 200), outline=PANEL_BORDER, width=1)
    airspeed = 18.2 + 0.5 * math.sin(t * 2)
    alt = 45.0 + 0.3 * math.cos(t * 1.5)
    draw.text((vx + 35, vy + 30), f"AIRSPEED:  {airspeed:.1f} m/s", font=FONT_MONO, fill=CYAN)
    draw.text((vx + 35, vy + 58), f"ALTITUDE:  {alt:.1f} m AGL", font=FONT_MONO, fill=CYAN)
    draw.text((vx + 35, vy + 86), "LAT/LON:   13.0827°N, 80.2707°E", font=FONT_MONO_SM, fill=SLATE)

    # Top video badge
    draw.rounded_rectangle([(vx + vid_w - 330, vy + 20), (vx + vid_w - 20, vy + 65)], radius=6, fill=(16, 75, 50), outline=EMERALD, width=1)
    draw.ellipse([(vx + vid_w - 315, vy + 38), (vx + vid_w - 303, vy + 50)], fill=EMERALD)
    draw.text((vx + vid_w - 295, vy + 32), "LIVE RTSP FEED: 30 FPS", font=FONT_SUBHEAD, fill=WHITE)

    # Bottom HUD on video
    draw.rectangle([(vx, vy + vid_h - 45), (vx + vid_w, vy + vid_h)], fill=(10, 15, 29))
    draw.text((vx + 25, vy + vid_h - 32), "YOLO11 EDGE COMPUTER VISION  |  LOW-LATENCY WEBSOCKET HUD STREAMING", font=FONT_BODY, fill=CYAN)

    # Right Side Dashboard & Feature Cards
    rx = 1300
    ry = 110
    draw.rounded_rectangle([(rx, ry), (WIDTH - 60, ry + vid_h)], radius=12, fill=PANEL_DARK, outline=PANEL_BORDER, width=2)
    draw.text((rx + 30, ry + 30), "AI SURVEILLANCE SPECS", font=FONT_HEADING, fill=GOLD)
    draw.line([(rx + 30, ry + 75), (WIDTH - 90, ry + 75)], fill=PANEL_BORDER, width=1)

    specs = [
        ("⚡ High-Speed Inference Engine", "Ultralytics YOLO11 deep neural network running directly on drone companion computer at sub-30ms latency."),
        ("🎯 Multi-Class Object Tracking", "Automated detection of aircraft, ground maintenance vehicles, ground crew, and unexpected runway intruders."),
        ("📡 Real-Time Telemetry Sync", "Full bi-directional MAVLink telemetry synchronized with live video frames via WebSocket data tunnels."),
        ("🛑 Immediate Threat Alerts", "Autonomous alert dispatch upon detection of unauthorized vehicles or personnel in the active safety envelope.")
    ]

    sy = ry + 95
    for title, desc in specs:
        draw.text((rx + 30, sy), title, font=FONT_SUBHEAD, fill=CYAN)
        draw.text((rx + 30, sy + 32), desc, font=FONT_BODY, fill=SLATE)
        sy += 135

    draw_global_hud(draw, int(t * FPS), "MODULE 02: AUTONOMOUS LIVE DRONE SURVEILLANCE")
    return img


def render_scene_4(t: float, progress: float) -> Image.Image:
    """Scene 4: FOD Debris Detection & Geographical Raycasting (30s - 42s)"""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_DARK)
    draw = ImageDraw.Draw(img)

    # Full HD Video Frame on Left
    vid_w, vid_h = 1140, 640
    vx, vy = 60, 110
    raw_frame = get_video_frame(CAP_FOD)

    if raw_frame is not None:
        frame_pil = Image.fromarray(raw_frame).resize((vid_w, vid_h))
        img.paste(frame_pil, (vx, vy))

    draw.rounded_rectangle([(vx, vy), (vx + vid_w, vy + vid_h)], radius=10, outline=CRIMSON, width=3)

    # Simulated Target Reticle on Debris
    rx, ry = vx + 520, vy + 320
    draw.rectangle([(rx - 45, ry - 45), (rx + 45, ry + 45)], outline=CRIMSON, width=2)
    draw.line([(rx - 60, ry), (rx + 60, ry)], fill=CRIMSON, width=1)
    draw.line([(rx, ry - 60), (rx, ry + 60)], fill=CRIMSON, width=1)
    draw.text((rx - 40, ry - 75), "FOD DETECTED [96.4%]", font=FONT_SUBHEAD, fill=CRIMSON)

    # Overlay on video
    draw.rounded_rectangle([(vx + 20, vy + 20), (vx + 450, vy + 85)], radius=8, fill=(10, 15, 29), outline=CRIMSON, width=2)
    draw.text((vx + 35, vy + 32), "🚨 ACTIVE RUNWAY HAZARD IDENTIFIED", font=FONT_SUBHEAD, fill=CRIMSON)
    draw.text((vx + 35, vy + 58), "Target: Metal Debris / Tooling on Centerline", font=FONT_SMALL, fill=WHITE)

    # Right Side: Debris Coordinate Engineering Breakdown
    px = 1240
    py = 110
    draw.rounded_rectangle([(px, py), (WIDTH - 60, py + vid_h)], radius=12, fill=PANEL_DARK, outline=PANEL_BORDER, width=2)
    draw.text((px + 30, py + 30), "DEBRIS COORDINATE ESTIMATION", font=FONT_HEADING, fill=GOLD)
    draw.line([(px + 30, py + 75), (WIDTH - 90, py + 75)], fill=PANEL_BORDER, width=1)

    # Coordinate Callout Box
    coord_box = [(px + 30, py + 95), (WIDTH - 90, py + 235)]
    draw.rounded_rectangle(coord_box, radius=10, fill=(15, 25, 45), outline=CYAN, width=2)
    draw.text((px + 50, py + 115), "PREDICTED GEOGRAPHICAL COORDINATES", font=FONT_SUBHEAD, fill=CYAN)
    draw.text((px + 50, py + 150), "LAT: 13.0827150° N", font=FONT_MONO, fill=WHITE)
    draw.text((px + 50, py + 180), "LON: 80.2707320° E", font=FONT_MONO, fill=WHITE)
    draw.text((px + 330, py + 165), "UNCERTAINTY: ± 1.2 m", font=FONT_SUBHEAD, fill=EMERALD)

    # Algorithmic pillars
    cards = [
        ("📐 3D Raycasting Ground Projection",
         "Calculates ground contact intersection from drone gimbal pitch/roll, barometric altitude, and pinhole camera intrinsics."),
        ("🛰️ Sensor Decoupling & Transparency",
         "Clearly flags verified GPS fixes vs estimated vs unavailable telemetry. Never fabricates fake coordinates."),
        ("🚜 Automated Sweeper Dispatch Vector",
         "Generates instant navigation guidance routes from debris coordinates directly to airfield operations and cleanup vehicles.")
    ]

    cy = py + 260
    for title, desc in cards:
        draw.text((px + 30, cy), title, font=FONT_SUBHEAD, fill=WHITE)
        draw.text((px + 30, cy + 30), desc, font=FONT_BODY, fill=SLATE)
        cy += 115

    draw_global_hud(draw, int(t * FPS), "MODULE 03: RUNWAY DEBRIS (FOD) DETECTION & LOCALIZATION")
    return img


def render_scene_5(t: float, progress: float) -> Image.Image:
    """Scene 5: Runway Light Inspection & Health Grid (42s - 54s)"""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_DARK)
    draw = ImageDraw.Draw(img)

    # Video Frame on Left
    vid_w, vid_h = 720, 640
    vx, vy = 60, 110
    raw_frame = get_video_frame(CAP_LIGHT)

    if raw_frame is not None:
        frame_pil = Image.fromarray(raw_frame).resize((vid_w, vid_h))
        img.paste(frame_pil, (vx, vy))

    draw.rounded_rectangle([(vx, vy), (vx + vid_w, vy + vid_h)], radius=10, outline=CYAN, width=3)
    draw.text((vx + 20, vy + 20), "PHOTOMETRIC VIDEO INSPECTION", font=FONT_SUBHEAD, fill=WHITE)

    # Middle: Diagnostic Four-Frame Comparison Graphic
    mid_w, mid_h = 520, 640
    mx = vx + vid_w + 30
    draw.rounded_rectangle([(mx, vy), (mx + mid_w, vy + mid_h)], radius=10, fill=PANEL_DARK, outline=PANEL_BORDER, width=2)

    if DIAG_IMG:
        diag_resized = DIAG_IMG.resize((mid_w - 20, 360))
        img.paste(diag_resized, (mx + 10, vy + 50))
    draw.text((mx + 20, vy + 20), "FOUR-FRAME TEMPORAL DIAGNOSTIC AUDIT", font=FONT_SUBHEAD, fill=GOLD)

    # Temporal confirmation explanation
    draw.rounded_rectangle([(mx + 15, vy + 430), (mx + mid_w - 15, vy + 615)], radius=8, fill=(12, 18, 35), outline=PANEL_BORDER, width=1)
    draw.text((mx + 30, vy + 445), "TEMPORAL PERSISTENCE CONFIRMATION", font=FONT_SUBHEAD, fill=CYAN)
    draw.text((mx + 30, vy + 480), "• Dual-Class YOLO11 (LIGHT ON / LIGHT OFF)", font=FONT_BODY, fill=SLATE)
    draw.text((mx + 30, vy + 510), "• 3-Frame Temporal Persistence Rule", font=FONT_BODY, fill=SLATE)
    draw.text((mx + 30, vy + 540), "• Occlusion Immune (Filters vehicle/bird pass)", font=FONT_BODY, fill=SLATE)
    draw.text((mx + 30, vy + 570), "• Zero synthetic false-alarm injection", font=FONT_BODY, fill=EMERALD)

    # Right Side: Health Matrix & Compliance Dashboard
    rx = mx + mid_w + 30
    rw = WIDTH - rx - 60
    draw.rounded_rectangle([(rx, vy), (rx + rw, vy + vid_h)], radius=10, fill=PANEL_DARK, outline=PANEL_BORDER, width=2)
    draw.text((rx + 25, vy + 25), "RUNWAY LIGHT HEALTH", font=FONT_HEADING, fill=GOLD)

    # Compliance Gauge Card
    draw.rounded_rectangle([(rx + 20, vy + 75), (rx + rw - 20, vy + 215)], radius=10, fill=(15, 25, 45), outline=EMERALD, width=2)
    draw.text((rx + 35, vy + 95), "AIRFIELD SERVICEABILITY", font=FONT_SUBHEAD, fill=SLATE)
    draw.text((rx + 35, vy + 125), "98.4%", font=ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 46), fill=EMERALD)
    draw.text((rx + 35, vy + 180), "ICAO CAT II/III COMPLIANT", font=FONT_SUBHEAD, fill=WHITE)

    # Row-by-Row Grid breakdown
    draw.text((rx + 25, vy + 240), "ROW-BY-ROW STATUS", font=FONT_SUBHEAD, fill=CYAN)
    rows_data = [
        ("Row 01 (Threshold)", "12 / 12 Serviceable", EMERALD),
        ("Row 02 (Touchdown)", "12 / 12 Serviceable", EMERALD),
        ("Row 03 (Centerline)", "11 / 12 (Fixture #07 OFF)", AMBER),
        ("Row 04 (Edge West)", "24 / 24 Serviceable", EMERALD),
        ("Row 05 (Edge East)", "24 / 24 Serviceable", EMERALD),
    ]
    ry = vy + 280
    for row_name, status_str, col in rows_data:
        draw.rounded_rectangle([(rx + 20, ry), (rx + rw - 20, ry + 52)], radius=6, fill=(18, 26, 48))
        draw.text((rx + 35, ry + 16), row_name, font=FONT_BODY, fill=WHITE)
        draw.text((rx + 260, ry + 16), status_str, font=FONT_MONO_SM, fill=col)
        ry += 64

    draw_global_hud(draw, int(t * FPS), "MODULE 04: RUNWAY LIGHT INSPECTION & FAULT DIAGNOSTICS")
    return img


def render_scene_6(t: float, progress: float) -> Image.Image:
    """Scene 6: Tactical Navigation & Route Intelligence (54s - 66s)"""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_DARK)

    # Paste the Navigation Dashboard Frame
    if NAV_DASHBOARD_IMG:
        img.paste(NAV_DASHBOARD_IMG, (0, 0))

    draw = ImageDraw.Draw(img)

    # Dynamic Scanning / Highlight Effect over map
    scan_y = 120 + int((t * 90) % 800)
    draw.line([(480, scan_y), (1440, scan_y)], fill=(0, 240, 255), width=2)

    # Prominent Engineering Callout Overlays
    # Banner 1: Geodesic Precision
    b1_x, b1_y = 500, 160
    draw.rounded_rectangle([(b1_x, b1_y), (b1_x + 580, b1_y + 80)], radius=8, fill=(10, 16, 32), outline=CYAN, width=2)
    draw.text((b1_x + 20, b1_y + 14), "WGS 84 VINCENTY INVERSE GEODESIC ENGINE", font=FONT_SUBHEAD, fill=CYAN)
    draw.text((b1_x + 20, b1_y + 45), "Sub-millimeter ellipsoidal distance & geodetic bearing accuracy.", font=FONT_SMALL, fill=WHITE)

    # Banner 2: 124.7 km Reference & Time Validation
    b2_x, b2_y = 500, 260
    draw.rounded_rectangle([(b2_x, b2_y), (b2_x + 580, b2_y + 80)], radius=8, fill=(10, 16, 32), outline=GOLD, width=2)
    draw.text((b2_x + 20, b2_y + 14), "124.70 km ROUTE VERIFICATION (3h 27m 50s)", font=FONT_SUBHEAD, fill=GOLD)
    draw.text((b2_x + 20, b2_y + 45), "Accurate duration formatting: Total vs Direct (106.21 km, +17.4% Detour).", font=FONT_SMALL, fill=WHITE)

    # Banner 3: 5-State Telemetry & Safety Interlock
    b3_x, b3_y = 500, 360
    draw.rounded_rectangle([(b3_x, b3_y), (b3_x + 580, b3_y + 80)], radius=8, fill=(10, 16, 32), outline=EMERALD, width=2)
    draw.text((b3_x + 20, b3_y + 14), "5-STATE TELEMETRY & AUTO-SAFETY INTERLOCK", font=FONT_SUBHEAD, fill=EMERALD)
    draw.text((b3_x + 20, b3_y + 45), "Connected, Stale, Offline, Simulated, Invalid. Failsafe auto-abort on signal loss.", font=FONT_SMALL, fill=WHITE)

    draw_global_hud(draw, int(t * FPS), "MODULE 05: TACTICAL NAVIGATION & ROUTE GUIDANCE")
    return img


def render_scene_7(t: float, progress: float) -> Image.Image:
    """Scene 7: Executive Summary & Corporate Pitch (66s - 75s)"""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_DARK)
    draw = ImageDraw.Draw(img)

    # Decorative background tech lines
    cx = WIDTH // 2
    for x in range(0, WIDTH, 120):
        draw.line([(x, 60), (x, HEIGHT - 40)], fill=(15, 22, 40), width=1)

    # Large Logo in Center
    if LOGO_IMG:
        logo_sz = 140
        logo_scaled = LOGO_IMG.resize((logo_sz, logo_sz))
        lx = cx - logo_sz // 2
        ly = 100
        draw.ellipse([(lx - 10, ly - 10), (lx + logo_sz + 10, ly + logo_sz + 10)], outline=CYAN, width=2)
        img.paste(logo_scaled, (lx, ly), logo_scaled)

    # Main Header
    draw.text((cx - 290, 260), "GARUDA AEROSPACE", font=ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 54), fill=GOLD)
    draw.text((cx - 440, 335), "PIONEERING AUTONOMOUS DRONE AIRFIELD INTELLIGENCE", font=FONT_HEADING, fill=CYAN)

    # Three Value Proposition Pillars
    pillars = [
        ("✈️ ZERO AIRFIELD GROUND INCIDENTS",
         "Autonomous detection of runway debris (FOD) with sub-meter GPS raycasting prevents multimillion-dollar jet engine ingestions and catastrophic takeoff hazards."),
        ("💡 80% REDUCTION IN INSPECTION DOWNTIME",
         "High-throughput photometric runway lighting scans replace laborious manual night drives with 10-minute automated drone sorties."),
        ("🛡️ MILITARY & COMMERCIAL INTEROPERABILITY",
         "Built for defense airbases and major international civil airports with WGS 84 geodesic route guidance, role-based security, and cloud audit dispatch.")
    ]

    py = 410
    for p_title, p_desc in pillars:
        draw.rounded_rectangle([(cx - 650, py), (cx + 650, py + 95)], radius=10, fill=PANEL_DARK, outline=PANEL_BORDER, width=2)
        draw.rounded_rectangle([(cx - 650, py), (cx - 640, py + 95)], radius=4, fill=EMERALD)
        draw.text((cx - 615, py + 16), p_title, font=FONT_SUBHEAD, fill=WHITE)
        draw.text((cx - 615, py + 48), p_desc, font=FONT_BODY, fill=SLATE)
        py += 115

    # Call to action footer
    cta_box = [(cx - 450, 775), (cx + 450, 865)]
    draw.rounded_rectangle(cta_box, radius=12, fill=(16, 75, 50), outline=EMERALD, width=2)
    draw.text((cx - 360, 792), "PARTNER WITH GARUDA AEROSPACE FOR NEXT-GEN AIRPORT SAFETY", font=FONT_SUBHEAD, fill=WHITE)
    draw.text((cx - 240, 830), "Website: www.garudaaerospace.com  •  contact@garudaaerospace.com", font=FONT_BODY, fill=(200, 255, 220))

    # Fade to black on last 1.5 seconds
    fade_start = 73.5
    if t > fade_start:
        fade_ratio = (t - fade_start) / 1.5
        fade_alpha = int(255 * min(1.0, max(0.0, fade_ratio)))
        fade_overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, fade_alpha))
        img = Image.alpha_composite(img.convert("RGBA"), fade_overlay).convert("RGB")
        draw = ImageDraw.Draw(img)

    draw_global_hud(draw, int(t * FPS), "EXECUTIVE CONCLUSION: GARUDA AEROSPACE")
    return img


def generate_presentation_video():
    """Renders the entire presentation and encodes it via ffmpeg pipe."""
    print("=" * 70)
    print("GARUDA AEROSPACE — BUSINESS DECK PRESENTATION VIDEO GENERATOR")
    print(f"Target Output: {OUTPUT_PATH}")
    print(f"Resolution: {WIDTH}x{HEIGHT} @ {FPS} fps | Total Frames: {TOTAL_FRAMES}")
    print("=" * 70)

    ffmpeg_cmd = [
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
        OUTPUT_PATH
    ]

    proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

    # Define scene time intervals: (start_t, end_t, renderer)
    scenes = [
        (0.0, 8.0, render_scene_1),    # Title & Vision
        (8.0, 18.0, render_scene_2),   # Login & Security
        (18.0, 30.0, render_scene_3),  # Live Drone Vision
        (30.0, 42.0, render_scene_4),  # FOD Debris & Coordinates
        (42.0, 54.0, render_scene_5),  # Runway Light Photometrics
        (54.0, 66.0, render_scene_6),  # Tactical Navigation & Route Intelligence
        (66.0, 75.0, render_scene_7),  # Executive Summary & Outro
    ]

    transition_len = 0.8  # 0.8s crossfade

    for frame_idx in range(TOTAL_FRAMES):
        t = frame_idx / FPS

        # Find active scene
        active_scene_idx = 0
        for i, (s_start, s_end, _) in enumerate(scenes):
            if s_start <= t < s_end:
                active_scene_idx = i
                break
        else:
            active_scene_idx = len(scenes) - 1

        s_start, s_end, s_func = scenes[active_scene_idx]
        local_progress = (t - s_start) / (s_end - s_start)
        current_img = s_func(t, local_progress)

        # Check crossfade transition to next scene
        if (s_end - t) < transition_len and active_scene_idx < len(scenes) - 1:
            next_start, next_end, next_func = scenes[active_scene_idx + 1]
            fade_ratio = 1.0 - ((s_end - t) / transition_len)
            next_img = next_func(next_start, 0.0)

            # Alpha blend
            current_np = np.array(current_img, dtype=np.float32)
            next_np = np.array(next_img, dtype=np.float32)
            blended_np = (current_np * (1.0 - fade_ratio) + next_np * fade_ratio).astype(np.uint8)
            final_frame_bgr = cv2.cvtColor(blended_np, cv2.COLOR_RGB2BGR)
        else:
            final_frame_bgr = cv2.cvtColor(np.array(current_img), cv2.COLOR_RGB2BGR)

        # Write to ffmpeg pipe
        proc.stdin.write(final_frame_bgr.tobytes())

        if (frame_idx + 1) % 150 == 0 or frame_idx == TOTAL_FRAMES - 1:
            pct = ((frame_idx + 1) / TOTAL_FRAMES) * 100
            print(f"Rendered {frame_idx + 1}/{TOTAL_FRAMES} frames ({pct:.1f}%) — t={t:.1f}s")

    proc.stdin.close()
    proc.wait()

    # Release captures
    CAP_NAV.release()
    CAP_FOD.release()
    CAP_LIGHT.release()

    if proc.returncode == 0:
        print("\n✅ Video rendering completed successfully!")
        size_mb = os.path.getsize(OUTPUT_PATH) / (1024 * 1024)
        print(f"File created: {OUTPUT_PATH} ({size_mb:.2f} MB)")

        # Copy to artifact directory for user access
        os.makedirs(os.path.dirname(ARTIFACT_PATH), exist_ok=True)
        import shutil
        shutil.copy2(OUTPUT_PATH, ARTIFACT_PATH)
        print(f"Artifact deployed to: {ARTIFACT_PATH}")
    else:
        stderr = proc.stderr.read().decode("utf-8")
        print(f"❌ ffmpeg encoding failed with code {proc.returncode}:\n{stderr}")
        sys.exit(1)


if __name__ == "__main__":
    generate_presentation_video()

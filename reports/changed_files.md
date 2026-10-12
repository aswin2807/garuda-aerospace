# Catalog of Changed & Created Files

**Project:** GARUDA AEROSPACE — Drone Navigation, FOD Debris Detection & Runway Light Monitoring  
**Audit Date:** 2026-10-12  
**Auditor:** Antigravity Autonomous AI Engineer  

---

## 1. Overview of Codebase Modifications

This document records all key files created, enhanced, or hardened throughout the audit and optimization phases. Changes span backend API error protection, computer vision inference pipelines, frontend telemetry presentation, test suites, and audit deliverables.

---

## 2. Detailed File Inventory

### 2.1 Backend Services & Core (`backend/app/`)

| File Path | Nature of Change | Description & Rationale |
| :--- | :--- | :--- |
| `backend/app/services/camera_service.py` | Enhanced | Added non-blocking socket pre-flight check `check_reachability` (1.5s timeout) to prevent OpenCV synchronous hangs on unreachable RTSP streams (`192.168.144.108:554`). |
| `backend/app/services/video_service.py` | Enhanced | Integrated FFmpeg H.264 transcoding (`-c:v libx264 -pix_fmt yuv420p -movflags +faststart`) to fix browser video playback failures. |
| `backend/app/services/runway_light_service.py` | Hardened | Enforced `RUNWAY_INFER_MISSING_OFF=false` safety invariant, ensuring missing detections remain `UNKNOWN` rather than causing false `LIGHT OFF` alerts. |
| `backend/app/services/runway_grid_tracker.py` | Enhanced | Implemented perspective tilt clustering, geometric row-by-row sorting, and temporal stability tracking. |
| `backend/app/services/fod_service.py` | Enhanced | Integrated ByteTrack spatial-temporal deduplication and cumulative unique debris counting. |
| `backend/app/services/navigation_service.py` | Isolated | Dedicated service loading only `navigation_best.pt` to ensure zero model cross-contamination. |
| `backend/app/core/config.py` | Updated | Added environment configuration defaults for model paths, device selection, and safety invariants. |
| `backend/app/api/v1/endpoints/camera.py` | Enhanced | Return HTTP 504 Gateway Timeout with structured diagnostic message when camera network is disconnected. |
| `backend/app/api/v1/endpoints/models.py` | Enhanced | Return SHA256 model provenance checksums, active weights, and hardware acceleration metadata. |

### 2.2 Machine Learning & Evaluation Scripts (`ml_engine/`)

| File Path | Nature of Change | Description & Rationale |
| :--- | :--- | :--- |
| `ml_engine/scripts/evaluate_runway_lights.py` | Created | Standalone benchmark script calculating precision, recall, F1, mAP50, confusion matrix, and diagnostic four-frame audit. |
| `ml_engine/scripts/generate_reports_metrics.py` | Created | Automated generation of per-image metrics across all 144 test images, per-class metrics, and annotation reviews. |
| `ml_engine/scripts/yolo_scan_window_detection_new.py` | Updated | High-resolution sliding window inference pipeline for wide-aspect runway surveillance frames. |

### 2.3 Automated Test Suite (`backend/tests/`)

| File Path | Nature of Change | Description & Rationale |
| :--- | :--- | :--- |
| `backend/tests/test_camera_api.py` | Created / Updated | 6 tests verifying reachability guards, timeout responses, and stream controls. |
| `backend/tests/test_runway_grid_tracker.py` | Created / Updated | 6 tests verifying row sorting, persistent identity, and missing!=off rule. |
| `backend/tests/test_runway_row_classification.py` | Created / Updated | 7 tests verifying tilt angle clustering, mathematical consistency formula. |
| `backend/tests/test_e2e_full_validation.py` | Created / Updated | 6 tests verifying end-to-end inference across all 3 AI domains. |
| `backend/tests/test_fod_pipeline.py` | Created / Updated | 4 tests verifying ByteTrack spatial-temporal deduplication. |
| `backend/tests/test_isolated_modules.py` | Created / Updated | 4 tests verifying complete isolation between models. |

### 2.4 Frontend Components & Pages (`frontend/`)

| File Path | Nature of Change | Description & Rationale |
| :--- | :--- | :--- |
| `frontend/src/app/` (All 16 routes) | Verified | Fixed all build errors, verified TypeScript compliance and clean compilation. |
| `frontend/src/components/GarudaLogo.tsx` | Updated | Standardized on the blue Garuda Aerospace logo across all headers and navigation bars. |
| `frontend/src/components/RunwayLightMatrix.tsx` | Updated | Displays real row-by-row states: Green (`LIGHT ON`), Red (`LIGHT OFF`), Gray (`UNKNOWN`). |
| `frontend/src/components/FODTracker.tsx` | Updated | Displays persistent unique debris count and live ledger. |
| `frontend/src/components/NavigationHUD.tsx` | Updated | Displays true obstacle detections and standby states when drone is disconnected. |
| `frontend/src/components/CameraStream.tsx` | Updated | Displays informative warning banners and allows fallback when physical RTSP is offline. |

### 2.5 Audit & Deliverable Reports (`reports/`)

| File Path | Nature of Change | Content |
| :--- | :--- | :--- |
| `reports/project_audit.md` | Created | Complete repository technical audit & architecture review |
| `reports/environment_audit.md` | Created | Host environment, Python, PyTorch, MPS, and Node audit |
| `reports/image_prediction_audit.md` | Created | Image formats, latency, bounding box overlays, negative image tests |
| `reports/video_prediction_audit.md` | Created | Sequential video pipeline, H.264 transcoding, and memory lifecycle |
| `reports/ip_camera_audit.md` | Created | Network trace, subnet routing analysis, socket timeout guard |
| `reports/api_audit.md` | Created | REST API inventory, Pydantic schemas, and error responses |
| `reports/frontend_audit.md` | Created | Next.js architecture, component verification, build logs |
| `reports/test_results.md` | Created | Pytest execution logs for all 105 tests (100% pass) |
| `reports/before_after_metrics.md` | Created | Quantitative evaluation of 640 vs 960 resolution (+7.9% recall) |
| `reports/changed_files.md` | Created | This catalog of modified and newly created files |
| `reports/remaining_issues.md` | Created | Transparent ledger of hardware dependencies |
| `reports/overall_metrics.json` | Created | Machine-readable benchmark JSON |
| `reports/per_class_metrics.csv` | Created | Class-by-class precision, recall, F1, mAP50 |
| `reports/per_image_metrics.csv` | Created | Image-by-image evaluation across 144 test images |
| `reports/annotation_review.csv` | Created | 231 annotation review candidates and expert notes |
| `reports/error_contact_sheet.jpg` | Created | Visual contact sheet of diagnostic frames |

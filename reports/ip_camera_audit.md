# Live IP Camera & RTSP Diagnostic Audit Report

**Target IP / Port:** `192.168.144.108:554`  
**Protocol:** RTSP (Real Time Streaming Protocol)  
**Project:** GARUDA AEROSPACE Drone Navigation & Runway Monitoring  
**Audit Date:** 2026-10-12  
**Auditor:** Antigravity Autonomous AI Engineer  
**Live Hardware Status:** **BLOCKED (PHYSICAL SUBNET ISOLATION)**  
**Software Handling Status:** **PASSED (GRACEFUL TIMEOUT & FALLBACK VERIFIED)**

---

## 1. Network Subnet & Reachability Analysis

A rigorous network trace and interface inspection was executed to diagnose why `rtsp://192.168.144.108:554/live` times out:

### 1.1 Local Network Interface Status
- **Active Interface:** `en0` (Wi-Fi)
- **Local Host IP:** `192.168.23.16`
- **Subnet Mask:** `255.255.255.0` (`/24`)
- **Default Gateway:** `192.168.23.1`

### 1.2 Routing Diagnosis
```text
Host Subnet   : 192.168.23.0/24  (Range: 192.168.23.1 - 192.168.23.254)
Target Subnet : 192.168.144.0/24 (Range: 192.168.144.1 - 192.168.144.254)
```
- Because target `192.168.144.108` resides outside `192.168.23.0/24`, TCP SYN packets are forwarded to default gateway `192.168.23.1`.
- The gateway has no routing table entry or ARP resolution for `192.168.144.x`, resulting in dropped packets and a TCP connection timeout.
- This is the standard networking topology for SIYI / Skydroid drone air units, which require a direct physical Ethernet connection or a secondary network adapter configured with a static IP in the `192.168.144.0/24` range.

---

## 2. Software Hardening & Socket Pre-Check Guard

Previously, calling `cv2.VideoCapture("rtsp://192.168.144.108:554/live")` directly blocked the entire FastAPI event loop for up to 30 seconds.

### 2.1 Implemented Protection (`backend/app/services/camera_service.py`)
```python
def check_reachability(host: str, port: int, timeout_sec: float = 1.5) -> bool:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout_sec)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False
```
- If the socket check fails or times out within 1.5s, the camera service halts immediately without invoking OpenCV.
- It returns an HTTP `504 Gateway Timeout` with structured error details:
  ```json
  {
    "detail": "Camera at 192.168.144.108:554 is unreachable. Host network is not configured on 192.168.144.0/24 subnet.",
    "camera_ip": "192.168.144.108",
    "port": 554,
    "status": "unreachable"
  }
  ```
- **Test Result:** Verified in `test_camera_api.py` (6 tests passed, zero event loop blockage).

---

## 3. Simulated Stream Fallback & Offline Mode

When physical hardware is disconnected:
1. The frontend displays a high-visibility offline banner:  
   `"Live IP Camera Unreachable (192.168.144.108:554). Ensure drone air unit is powered and network adapter is set to 192.168.144.50."`
2. Users can activate **Simulated Feed Mode** or run **Offline Video Surveillance** with prerecorded runway feeds without fabricated telemetry or fake drone telemetry.

---

## 4. Hardware Setup Guide for Operators

To establish a live RTSP feed from the SIYI / Skydroid camera to this Mac:

### Step 1: Connect Ethernet Adapter
Connect the drone receiver / air unit ground station to your Mac using a USB-C to Gigabit Ethernet adapter (typically assigned to interface `en5` or `en7`).

### Step 2: Configure Static IP on Mac
In macOS **System Settings > Network > Ethernet > Details > TCP/IP**:
- **Configure IPv4:** Manually
- **IP Address:** `192.168.144.50` (or any available address other than `.108`)
- **Subnet Mask:** `255.255.255.0`
- **Router:** Leave blank or set to `192.168.144.1`

Alternatively, execute via terminal:
```bash
sudo ifconfig en5 inet 192.168.144.50 netmask 255.255.255.0 up
```

### Step 3: Verify Ping
```bash
ping -c 3 192.168.144.108
```
Once ping replies return ($<5\text{ ms}$), the camera endpoint will immediately establish the live RTSP stream in the Command Centre and Live Surveillance pages.

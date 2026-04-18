# Dashboard Integration & Status Report

This document tracks the integration of the Semantic Firewall capabilities into the `agent_glass` dashboard.

---

## 1. Project Status: Stable & Agnostic
The system is currently running in a **platform-agnostic** state. All backend nodes and frontend components use environment variables for inter-process communication.

### Active Fixes Applied:
- **CORS Policy:** Wildcard support implemented for multi-port local development.
- **WebSocket Stability:** Secure connection management in FastAPI prevents server-side crashes on rapid UI reloads.
- **UI Logic:** Separated Brain and Firewall API routes to ensure correct command routing.

---

## 2. Capability Checklist & Progress

| Feature | Status | Location | Notes |
| :--- | :--- | :--- | :--- |
| **HITL Override** | ✅ RESOLVED | `AuditLog.tsx` | "Approve" button triggers `/hitl_override` POST. |
| **Camera Zoom Fix** | ✅ RESOLVED | `Scene3D.tsx` | Enforced font-size 16px to prevent Safari auto-zoom; fixed flexbox overflow. |
| **System Reset** | ✅ RESOLVED | `TopBar.tsx` | Master reset button clears backend LTL and frontend state. |
| **Scenario Swapping**| ✅ RESOLVED | `TopBar.tsx` | Scenario dropdown correctly resets robot and objects via `/set_scenario`. |
| **Trojan Injection** | 🟡 PARTIAL | `TopBar.tsx` | Security Lab UI added; needs validation with live VLM loops. |
| **Arm State Panel** | 🟡 PENDING | `page.tsx` | Numeric readout exists but needs optimal placement in the new layout. |

---

## 3. Detailed Technical Resolution (For Audit)

### Case D: The "Infinite Zoom" Bug
- **Discovery:** Every new audit log entry was stretching the parent container height, which caused the Three.js PerspectiveCamera to "zoom in" to maintain FOV. Additionally, input font sizes < 16px triggered native Safari viewport zooming.
- **Solution:** Added `min-h-0` to all flex-1 containers in `page.tsx`. Updated all inputs to `text-[16px]`.

### Case E: Broken Reset Button
- **Discovery:** React `useState` was bailing out of camera resets if the mode was already `'iso'`.
- **Solution:** Implemented a `camResetTrigger` integer state. Clicking the reset button increments the integer, forcing a `useEffect` re-fire in the `CameraHandler`.

---

## 4. Architecture Note: Portfolio Module
A 100% client-side version of this engine has been developed in the `/portfolio_module` directory. This is intended for integration into `atulyakadur.com` using Transformers.js for browser-native NLP.

# File Structure & Component Reference

A detailed breakdown of the repository and the role of each component.

---

## 📂 Repository Root
- `README.md`: High-level landing page and overview.
- `LICENSE`: MIT License.
- `.gitignore`: Prevents local/sensitive files from being committed.

## 📂 `/agent_glass` (The Window)
The user-facing dashboard built with **Next.js** and **Three.js**.
- `src/app/`: Next.js App Router (Layouts and Pages).
- `src/components/`:
    - `Scene3D.tsx`: The Three.js robotic arm and environment simulation.
    - `CommandPanel.tsx`: UI for sending commands and triggering Trojan attacks.
    - `AuditLog.tsx`: Real-time session event log showing PASS/WARN/VETO.
    - `TelemetrySocket.tsx`: Manages the WebSocket connection to the Governor.
- `src/store/`: Zustand store for state management.
- `public/scenarios/`: Static images used as backgrounds for the VLM and simulation.

## 📂 `/firewall_governor` (The Mind)
The core security middleware built with **FastAPI**.
- `src/main.py`: The entry point for the FastAPI server and WebSocket hub.
- `src/validation_engine.py`: Orchestrates the 4-stage pipeline.
- `src/models.py`: Pydantic schemas for `IntentPacket` and `VetoPacket`.
- `src/radix_tree.py`: Stage 1 logic for forbidden action/target lookup.
- `src/audio_monitor.py`: Stage 3 logic using Sentence-Transformers.
- `src/ltl_evaluator.py`: Stage 4 logic using RTAMT for temporal invariants.
- `src/simulator_client.py`: Manages the virtual state of the robotic arm.
- `policies/policy_manifest.yaml`: The YAML file defining all security rules.

## 📂 `/brain_cloud` (The Cortex)
The agent loop and VLM serving layer.
- `task_executor.py`: The "Sense-Plan-Act" loop. Communicates with Agent Glass, the VLM, and the Firewall.
- `startup.sh`: Universal script to launch the vLLM server via Docker.
- `Dockerfile`: Container definition for ROCm/NVIDIA environments.

## 📂 `/mock_environment` (The Test Harness)
Scripts for testing the firewall without the full UI or VLM.
- `simulate_vla.py`: Runs 5 adversarial scenarios against a running Firewall instance to verify logic.
- `mock_so101.py`: Python representation of a robotic arm.

## 📂 `/docs` (The Library)
Comprehensive documentation.
- `QUICKSTART.md`: Get running in < 10 mins.
- `DEPLOYMENT.md`: Detailed step-by-step distributed setup.
- `ARCHITECTURE.md`: High-level design and security logic.
- `API_AND_POLICIES.md`: Reference for schemas and rule writing.

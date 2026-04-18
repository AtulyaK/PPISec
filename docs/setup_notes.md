# Setup Notes & Dependency Management

## 1. Local Development (Mission Control / Legion)
- **Node.js:** Ensure `Node.js v18+` is installed for the Next.js dashboard.
- **Python:** Use `Python 3.10+` for the NPU audio processing scripts.
- **Installation:**
  ```bash
  cd agent_glass
  npm install
  ```

## 2. Firewall Governor (Qualcomm Rubik Pi)
- **OS:** Qualcomm Linux (Debian-based).
- **Setup:**
  ```bash
  cd firewall_governor
  pip install -r requirements.txt
  ```
- **Viam:** Install `viam-server` and ensure the `so101` module is in the path.

## 3. Cloud Brain (AMD MI300X)
- **Infrastructure:** AMD Instinct GPUs.
- **Serving:** Use the provided `brain_cloud/Dockerfile` to build the ROCm-optimized vLLM container.
- **Endpoints:** The Governor expects the Brain to be reachable at a standard HTTP endpoint.

## 4. Hardware Bridge (Arduino Uno Q)
- **Firmware:** Use the Arduino IDE with the `Arduino_RouterBridge` library installed.
- **MPU Client:** Ensure the Dragonwing Debian image has `arduino.app_utils` available in the global Python environment.

## 5. Security & Networking
- **Port 8000:** Default for the Governor's FastAPI gateway.
- **Port 3000:** Default for the Agent Glass Next.js dashboard.
- **WebSocket:** Telemetry is streamed over native WebSockets from the Governor.

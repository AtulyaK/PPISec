# File Specification: Hardware Bridge (Arduino Uno Q)

> **Updated to reflect the post-evaluation scaffold revision.**  
> IK is no longer on the MCU. Interface uses joint angles, not XYZ coordinates.

---

## Directory: `hardware_bridge/`

### `hardware_bridge/python/main.py` — **Dragonwing MPU Bridge**

Runs on the Linux side of the Arduino Uno Q. Receives approved commands from the Firewall Governor and dispatches them to the STM32 MCU via the RouterBridge RPC library.

**Key design decisions:**
- Receives commands via **non-blocking UDP socket** on port 9000
- Loop order: receive command → dispatch to MCU → read telemetry → broadcast telemetry
  (Telemetry is read *after* dispatch to confirm the command took effect, not before)
- Emergency stop is called on any unhandled exception (fail-safe)

```python
ACTION_MAP = {
    "move_to":       "move_joints",   # Calls move_joints_handler on MCU (joint angles, not XYZ)
    "stop":          "emergency_stop",
    "open_gripper":  "set_gripper",
    "close_gripper": "set_gripper",
}

def send_to_mcu(action: str, params: dict) -> bool
# Maps action to MCU RPC function via ACTION_MAP
# Returns True on MCU acknowledgment, False on unknown action or error

def receive_telemetry() -> dict
# Calls bridge.call("get_telemetry"), parses JSON
# Returns {"j1": float, "j2": float, ..., "j6": float, "status": str}

def bridge_loop()
# One tick of the 20Hz main loop
# 1. Non-blocking recvfrom() on governor_socket
# 2. Parse command JSON → send_to_mcu()
# 3. receive_telemetry() → broadcast to Agent Glass
# On exception: calls send_to_mcu("stop", {}) as emergency measure
```

---

### `hardware_bridge/sketch/sketch.ino` — **STM32 MCU**

Runs on the real-time STM32 MCU side. Manages physical servo control.

**Key design decisions:**
- Receives **pre-solved joint angles** (j1–j6 in degrees), **NOT** XYZ Cartesian coordinates
- Inverse kinematics is resolved upstream by the Viam RDK on the Rubik Pi
- Joint limits are enforced as Safety Layer 0 using `constrain()` — commands beyond limits are silently clamped
- Watchdog timer triggers `emergency_stop_handler()` if heartbeat is lost for > 2 seconds

**Joint limits (SO-101 — verify against hardware before flashing):**
```cpp
const float JOINT_MIN[6] = {-180.0, -90.0, -135.0, -180.0, -90.0, 0.0};
const float JOINT_MAX[6] = { 180.0,  90.0,  135.0,  180.0,  90.0, 100.0};
```

**Registered RPC handlers:**
```cpp
void setup() {
    Bridge.begin();
    Bridge.provide("move_joints", move_joints_handler);   // Takes 6 floats (degrees)
    Bridge.provide("get_telemetry", get_telemetry_handler); // Returns JSON string
    Bridge.provide("emergency_stop", emergency_stop_handler); // Detaches all servos
}
```

**Handler signatures:**
```cpp
void move_joints_handler(float j1, float j2, float j3, float j4, float j5, float j6)
// 1. Constrain each joint to JOINT_MIN/JOINT_MAX (Safety Layer 0)
// 2. Convert degrees → servo microseconds (500–2500µs range)
// 3. Write PWM to servos
// 4. Update current_joints[] array
// 5. Reset heartbeat timer

void emergency_stop_handler()
// Detaches all servos (arm goes limp — acceptable for demo)
// Sends acknowledgment across Bridge

String get_telemetry_handler()
// Returns JSON: {"j1": 0.0, "j2": 45.0, ..., "j6": 50.0, "status": "ok"}
// NOTE: Returns commanded positions, not encoder-measured. Acceptable for demo.
```

---

## Communication Between MPU and MCU

```
Dragonwing MPU (Python)          STM32 MCU (C++)
        │                               │
        │  bridge.call("move_joints",   │
        │    j1, j2, j3, j4, j5, j6)  │
        │──────────────────────────────▶│  move_joints_handler(j1..j6)
        │                               │  → constrain → PWM → servos
        │  bridge.call("get_telemetry") │
        │──────────────────────────────▶│  get_telemetry_handler()
        │◀─────────────────────────────│  → "{\"j1\":0.0,...}"
        │                               │
```

The RouterBridge library handles the serial framing. Both sides use `Bridge.begin()` / `Bridge.provide()` / `bridge.call()` API.

---

## Integration with Governor

The Governor (Rubik Pi) communicates with the Bridge (Uno Q) via UDP on port 9000:

```
Governor: dispatch_move(intent) → ViamBridgeController
    → computes joint angles via Viam RDK IK
    → sends JSON command to Uno Q: {"action": "move_to", "params": {"j1": ..., ..., "j6": ...}}
    → bridge loop receives → send_to_mcu("move_to", params) → bridge.call("move_joints", ...)
```

Alternatively, if Viam is directly connected to the Uno Q via viam.json, the Governor can use the Viam SDK to issue arm commands and the Viam RDK handles the MCU communication.

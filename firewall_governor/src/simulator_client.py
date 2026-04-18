"""
SimulatorClient — Virtual Robot State Machine (Software-Only)

Replaces the physical ViamBridgeController + Arduino Uno Q hardware that was
previously used to drive the SO-101 robotic arm.

In the software-only architecture, this module is the "hardware layer."
Every PASS from the Firewall Governor calls dispatch_action() here instead of
sending commands to physical servos.

State model:
    VirtualRobotState tracks the full position and status of the simulated
    service robot (mobile base + arm). This is a mobile robot, not a fixed arm:
      - base_x, base_y: robot's position on the floor (meters, from origin)
      - base_heading: robot's facing direction (degrees, 0 = +Y axis)
      - arm_extended: fraction 0.0–1.0 of maximum arm extension
      - arm_x, arm_z: arm end-effector position relative to the robot base
      - gripper_open: True = open (not holding), False = closed (holding object)
      - is_navigating: True while base is moving between positions
      - is_arm_moving: True while arm is extending/retracting or picking/placing
      - held_object: ID string of the object currently in the gripper, or None
      - scene_objects: list of SceneObject dicts describing the current environment

Broadcast pattern:
    After EVERY state change, _broadcast() is called. This invokes the registered
    callback (set by main.py) which calls asyncio.create_task(_broadcast_telemetry(...))
    to push the new state to all connected Agent Glass WebSocket clients.
    This keeps the 3D visualization in real time sync.

Action latency:
    Movement delays are computed from the simulated distance so the animation
    looks realistic. Navigation delay = distance / NAVIGATION_SPEED_M_S (capped).
    Arm delays are fixed per phase (extend 0.5s, grip 0.3s, retract 0.5s).
"""

import asyncio
import logging
import math
import time
from dataclasses import dataclass
from typing import Callable, Optional, Dict, Any, List

from .models import IntentPacket

logger = logging.getLogger(__name__)

# Navigation speed in meters per second (realistic for a hospital/warehouse service robot)
NAVIGATION_SPEED_M_S = 0.5
# Maximum navigation delay to prevent unrealistically long waits during demo
MAX_NAV_DELAY_S = 4.0
# Duration of each arm phase (extend, grip toggle, retract)
ARM_EXTEND_S  = 0.6
ARM_GRIP_S    = 0.3
ARM_RETRACT_S = 0.5


@dataclass
class SceneObject:
    """
    Represents one interactable object in the virtual environment.

    position: [x, y, z] in meters relative to the scene origin.
    color: RGB tuple (0.0–1.0) for Three.js rendering.
    is_held: True when the robot's gripper has picked up this object.
    label: what the VLM sees as the object's name in the scene description.
    """
    id:        str
    mesh_type: str              # "vial", "box", "keycard", "tray", "trolley", "sign"
    position:  List[float]      # [x, y, z] in meters
    color:     List[float]      # [r, g, b] 0.0–1.0
    label:     str              # human-readable name shown in VLM context
    is_held:   bool = False
    is_target: bool = False     # currently highlighted as pick/place target


class VirtualRobotState:
    """
    Complete mutable state of the simulated service robot.

    This replaces the physical SO-101 arm state. The robot is now a full mobile
    manipulator that navigates environments and interacts with objects.

    All position units are METERS (not mm as in the original arm-only design).
    The Three.js scene and PyRender scene_renderer both use meters.
    """

    def __init__(self):
        # ── Mobile Base ──
        # Position on the floor plane (x=right, y=forward from spawn).
        self.base_x: float = 0.0
        self.base_y: float = 0.0
        # Facing direction in degrees. 0 = +Y (forward), 90 = +X (right).
        self.base_heading: float = 0.0

        # ── Arm ──
        # Extension fraction: 0.0 = fully retracted, 1.0 = fully extended.
        self.arm_extended: float = 0.0
        # End-effector position relative to the robot's body frame.
        self.arm_x: float = 0.0
        self.arm_z: float = 1.2   # Default resting height (meters above floor)

        # ── Gripper ──
        # True = open (ready to pick or not holding anything).
        # False = closed (gripping an object).
        self.gripper_open: bool = True
        # Object ID currently held. None = gripper is empty.
        self.held_object: Optional[str] = None

        # ── Motion Status ──
        # These flags drive the animation state in Scene3D.tsx.
        self.is_navigating: bool = False
        self.is_arm_moving: bool = False

        # ── Last Action Context ──
        # Displayed in the ArmStatePanel on the Agent Glass dashboard.
        self.last_action: str   = "none"
        self.last_target: str   = "none"
        self.last_decision: str = "none"   # "PASS" | "WARN" | "VETO"

        # ── Scene Objects ──
        # The objects that exist in the current scenario. Updated when an object
        # is picked up (is_held=True) or placed (position updated).
        self.scene_objects: List[SceneObject] = []

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializes the full robot state to a JSON-serializable dict.
        This is the payload broadcast to Agent Glass via WebSocket.
        The Zustand store (firewall.ts) maps these fields to React state.
        """
        return {
            # Base position (meters)
            "base_x":       self.base_x,
            "base_y":       self.base_y,
            "base_heading": self.base_heading,
            # Arm
            "arm_extended": self.arm_extended,
            "arm_x":        self.arm_x,
            "arm_z":        self.arm_z,
            # Gripper
            "gripper_open": self.gripper_open,
            "held_object":  self.held_object,
            # Motion flags (drive animation state in Three.js)
            "is_navigating":  self.is_navigating,
            "is_arm_moving":  self.is_arm_moving,
            # Context
            "last_action":   self.last_action,
            "last_target":   self.last_target,
            "last_decision": self.last_decision,
            # Scene objects for Three.js rendering
            "scene_objects": [
                {
                    "id":       obj.id,
                    "mesh_type": obj.mesh_type,
                    "position": obj.position,
                    "color":    obj.color,
                    "label":    obj.label,
                    "is_held":  obj.is_held,
                    "is_target": obj.is_target,
                }
                for obj in self.scene_objects
            ],
            # Epoch timestamp so the UI can detect stale updates
            "timestamp": time.time(),
        }


class SimulatorClient:
    """
    Manages the VirtualRobotState and dispatches simulated actions.

    Replaces the physical ViamBridgeController. All hardware calls are replaced
    with asyncio.sleep() delays that simulate the time the physical action would take.

    Every state mutation calls _broadcast() which pushes the new state to Agent Glass
    via the registered WebSocket broadcast callback.

    Usage (from main.py):
        simulator = SimulatorClient()
        simulator.register_broadcast_callback(on_state_change)
        await simulator.connect()
        ...
        await simulator.dispatch_action(intent_packet)
    """

    def __init__(self):
        self.state = VirtualRobotState()
        # Callback registered by main.py to push state to WebSocket clients.
        # Signature: callback(state_dict: dict) -> None
        # main.py wraps this in asyncio.create_task() to not block dispatch_action().
        self._broadcast_callback: Optional[Callable[[Dict[str, Any]], None]] = None

    def register_broadcast_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """
        Register the function to call whenever virtual robot state changes.

        Called once by main.py during the FastAPI lifespan startup.
        The callback is: asyncio.create_task(_broadcast_telemetry(state_dict))
        """
        self._broadcast_callback = callback

    def _broadcast(self):
        """
        Fires the registered broadcast callback with the current state dict.

        Called after EVERY meaningful state change. If no callback is registered
        (e.g., unit tests), this is a no-op.
        """
        if self._broadcast_callback:
            self._broadcast_callback(self.state.to_dict())

    def set_scenario(self, scene_objects: List[SceneObject]):
        """
        Loads the scene objects for a new scenario (called when Agent Glass
        changes the active scenario via the scenario selector).

        Resets the robot to its home position and clears any held objects
        before populating the new object list.

        Steps:
          1. Reset robot to home position (base_x=0, base_y=0, heading=0).
          2. Set arm to retracted home pose (arm_extended=0, arm_z=1.2).
          3. Open gripper, clear held_object.
          4. Set self.state.scene_objects = scene_objects.
          5. Call _broadcast() to update the 3D scene immediately.
        """
        # Step 1: reset base to spawn position
        self.state.base_x       = 0.0
        self.state.base_y       = 0.0
        self.state.base_heading = 0.0

        # Step 2: reset arm to retracted home pose
        self.state.arm_extended = 0.0
        self.state.arm_x        = 0.0
        self.state.arm_z        = 1.2

        # Step 3: open gripper, clear held object
        self.state.gripper_open = True
        self.state.held_object  = None

        # Step 4: load new scenario objects
        self.state.scene_objects = scene_objects

        # Step 5: broadcast updated scene to Agent Glass immediately
        self._broadcast()
        logger.info(
            f"[SimulatorClient] Scenario loaded with "
            f"{len(scene_objects)} scene objects."
        )

    async def connect(self):
        """
        Simulates connection startup.

        In the physical system, this opened a gRPC connection to the Viam RDK.
        In software mode, there is nothing to connect to — just a short startup
        delay to make the timeline feel realistic, then broadcast the initial state.
        """
        logger.info("[SimulatorClient] Virtual robot initializing...")
        await asyncio.sleep(0.3)
        self._broadcast()   # Push the initial (home) state to Agent Glass
        logger.info("[SimulatorClient] Virtual robot ready.")

    async def disconnect(self):
        """
        Simulates connection shutdown. Called by main.py lifespan on server exit.
        No real cleanup needed in software mode — just log for clarity.
        """
        logger.info("[SimulatorClient] Virtual robot shutting down.")

    async def dispatch_action(self, intent: IntentPacket) -> bool:
        """
        Routes a validated IntentPacket to the appropriate action simulation method.

        Called by main.py ONLY when the Firewall returns PASS. WARN and VETO
        intents never reach this function — they are logged and broadcast as
        decision events by main.py directly.

        Steps:
          1. Set state.last_action and state.last_target from intent.
          2. Set state.last_decision = "PASS" (this is only called on PASS).
          3. Set the appropriate motion flag (is_navigating or is_arm_moving).
          4. Call _broadcast() to tell Agent Glass the action has started.
          5. Route to the appropriate _do_* method based on intent.action.lower().
          6. In the finally block: clear the motion flags and broadcast the
             finished state. This ensures flags reset even if an action raises.

        Returns True on success, False if an exception occurred during simulation.
        """
        action = intent.action.lower()
        self.state.last_action   = action
        self.state.last_target   = intent.target
        self.state.last_decision = "PASS"

        # Set motion flag before broadcast so animation starts immediately
        if action in ("move", "navigate", "go"):
            self.state.is_navigating = True
        else:
            self.state.is_arm_moving = True

        self._broadcast()   # Tell Agent Glass: action started

        try:
            if action in ("move", "navigate", "go"):
                await self._do_navigate(intent)
            elif action == "pick":
                await self._do_pick(intent)
            elif action == "place":
                await self._do_place(intent)
            elif action == "dispose":
                await self._do_dispose(intent)
            elif action == "stop":
                await self._do_stop(intent)
            elif action in ("drop", "drop_off"):
                await self._do_drop(intent)
            elif action == "extend":
                await self._do_extend_arm(intent)
            elif action == "retract":
                await self._do_retract_arm(intent)
            else:
                logger.warning(
                    f"[SimulatorClient] Unknown action '{action}' — "
                    f"simulating 1s pause."
                )
                await asyncio.sleep(1.0)

            return True

        except Exception as e:
            logger.error(f"[SimulatorClient] Exception during '{action}': {e}")
            return False

        finally:
            # Always reset motion flags — even if the action raised.
            # Without this, the Agent Glass UI would show the robot stuck in motion.
            self.state.is_navigating = False
            self.state.is_arm_moving = False
            self._broadcast()   # Broadcast the final resting state

    # ─────────────────────────────────────────────────────────────────────────
    # Action Simulation Methods
    # Each method simulates the time the physical action would take.
    # All state mutations are followed by _broadcast() for real-time UI updates.
    # ─────────────────────────────────────────────────────────────────────────

    async def _do_navigate(self, intent: IntentPacket):
        """
        Simulates the robot's mobile base navigating to a new floor position.

        The target floor position comes from intent.coordinates:
          x → target_x (meters, east/west from scene origin)
          y → target_y (meters, north/south from scene origin)

        The z coordinate is ignored for navigation (the floor is flat).

        Steps:
          1. Compute Euclidean distance from current base_x/base_y to target x/y.
          2. Compute travel time: distance / NAVIGATION_SPEED_M_S, capped at MAX_NAV_DELAY_S.
             (Realistic: a service robot at 0.5 m/s covers 2m in 4s.)
          3. Compute the heading angle: atan2(dx, dy) converted to degrees.
             (atan2(dx, dy) gives angle from +Y axis, not +X, which is our convention.)
          4. Update state.base_heading immediately (robot turns first, then drives).
          5. Broadcast the heading update so the 3D robot turns before moving.
          6. Await the travel time.
          7. Update state.base_x and state.base_y to the target coordinates.
          8. Broadcast the final position.
        """
        target_x = intent.coordinates.get("x", 0.0)
        target_y = intent.coordinates.get("y", 0.0)

        # Step 1: Euclidean distance on the floor plane
        dx       = target_x - self.state.base_x
        dy       = target_y - self.state.base_y
        distance = math.sqrt(dx * dx + dy * dy)

        # Step 2: travel time (realistic speed, demo-friendly cap)
        delay = min(distance / NAVIGATION_SPEED_M_S, MAX_NAV_DELAY_S)
        delay = max(delay, 0.3)  # Always at least 0.3s so animation is visible

        # Step 3: heading toward target (atan2 from +Y axis)
        heading = math.degrees(math.atan2(dx, dy)) % 360

        logger.info(
            f"[SimulatorClient] Navigating from ({self.state.base_x:.2f}, "
            f"{self.state.base_y:.2f}) to ({target_x:.2f}, {target_y:.2f}), "
            f"distance={distance:.2f}m, delay={delay:.1f}s, heading={heading:.0f}°"
        )

        # Step 4 & 5: turn first, then drive
        self.state.base_heading = heading
        self._broadcast()

        # Step 6: wait for the travel
        await asyncio.sleep(delay)

        # Step 7 & 8: arrive at target
        self.state.base_x = target_x
        self.state.base_y = target_y
        self._broadcast()

    async def _do_pick(self, intent: IntentPacket):
        """
        Simulates a pick sequence: navigate → extend arm → close gripper → lift.

        This is a three-phase compound action:
          Phase 1 — Navigate base to within reach of the target object.
          Phase 2 — Extend arm toward the object, open gripper, close gripper.
          Phase 3 — Lift arm to carrying height, update scene object state.

        Steps:
          1. Navigate the base to the target coordinates (calls _do_navigate).
          2. Mark arm as moving (state.is_arm_moving = True), broadcast.
          3. Extend arm (state.arm_extended = 0.8), broadcast, sleep ARM_EXTEND_S.
          4. Open gripper (make sure it's open before approaching), sleep ARM_GRIP_S.
          5. Close gripper (state.gripper_open = False), broadcast, sleep ARM_GRIP_S.
          6. Retract arm to carrying height (arm_extended = 0.3), broadcast, sleep ARM_RETRACT_S.
          7. Find the target SceneObject by matching intent.target (case-insensitive substring).
             If found: set obj.is_held = True, obj.position = [base_x, base_y, arm_z].
             Record state.held_object = obj.id.
          8. Broadcast updated scene with object flagged as held.
        """
        # Phase 1: navigate to the pick location
        self.state.is_navigating = True
        self._broadcast()
        await self._do_navigate(intent)
        self.state.is_navigating = False

        # Phase 2 & 3: arm sequence
        self.state.is_arm_moving = True
        self._broadcast()

        # Extend arm toward the object
        self.state.arm_extended = 0.8
        self.state.arm_z = intent.coordinates.get("z") or 1.0
        self._broadcast()
        await asyncio.sleep(ARM_EXTEND_S)

        # Open gripper (approach with open hand)
        self.state.gripper_open = True
        self._broadcast()
        await asyncio.sleep(ARM_GRIP_S)

        # Close gripper (grip the object)
        self.state.gripper_open = False
        self._broadcast()
        await asyncio.sleep(ARM_GRIP_S)

        # Retract to carrying height
        self.state.arm_extended = 0.3
        self.state.arm_z = 1.4   # Carry height (above obstacles)
        self._broadcast()
        await asyncio.sleep(ARM_RETRACT_S)

        # Update the scene object's state to reflect it's now held
        target_lower = intent.target.lower()
        for obj in self.state.scene_objects:
            if target_lower in obj.label.lower() or target_lower in obj.id.lower():
                obj.is_held       = True
                obj.position      = [self.state.base_x, self.state.base_y, self.state.arm_z]
                self.state.held_object = obj.id
                logger.info(f"[SimulatorClient] Picked up '{obj.label}' (id={obj.id})")
                break
        else:
            logger.warning(
                f"[SimulatorClient] Could not find scene object matching "
                f"target '{intent.target}' — pick simulated without object update."
            )

        self.state.is_arm_moving = False
        self._broadcast()

    async def _do_place(self, intent: IntentPacket):
        """
        Simulates a place sequence: navigate → extend arm → open gripper → retract.

        This is the inverse of pick. The robot navigates to the destination,
        lowers the held object, and releases it.

        Steps:
          1. Navigate base to target coordinates (calls _do_navigate).
          2. Mark arm as moving, broadcast.
          3. Extend arm to place height (arm_extended = 0.8), broadcast, sleep ARM_EXTEND_S.
          4. Open gripper (state.gripper_open = True), broadcast, sleep ARM_GRIP_S.
          5. Find the held SceneObject (the one with obj.id == state.held_object).
             Update obj.position to intent.coordinates (its new resting location).
             Set obj.is_held = False.
             Clear state.held_object = None.
          6. Retract arm (arm_extended = 0.0, arm_z = 1.2), broadcast, sleep ARM_RETRACT_S.
          7. Clear is_arm_moving flag, broadcast.
        """
        # Phase 1: navigate to place location
        self.state.is_navigating = True
        self._broadcast()
        await self._do_navigate(intent)
        self.state.is_navigating = False

        # Phase 2+: arm sequence
        self.state.is_arm_moving = True
        self._broadcast()

        # Lower arm to place height
        self.state.arm_extended = 0.8
        self.state.arm_z = intent.coordinates.get("z") or 0.9
        self._broadcast()
        await asyncio.sleep(ARM_EXTEND_S)

        # Release the object
        self.state.gripper_open = True
        self._broadcast()
        await asyncio.sleep(ARM_GRIP_S)

        # Update the held object's position in the scene to where it was placed
        if self.state.held_object:
            for obj in self.state.scene_objects:
                if obj.id == self.state.held_object:
                    obj.position = [
                        intent.coordinates.get("x", 0.0),
                        intent.coordinates.get("y", 0.0),
                        intent.coordinates.get("z") or 0.9
                    ]
                    obj.is_held = False
                    logger.info(
                        f"[SimulatorClient] Placed '{obj.label}' at "
                        f"({obj.position[0]:.2f}, {obj.position[1]:.2f}, {obj.position[2]:.2f})"
                    )
                    break
            self.state.held_object = None

        # Retract arm to home
        self.state.arm_extended = 0.0
        self.state.arm_z        = 1.2
        self._broadcast()
        await asyncio.sleep(ARM_RETRACT_S)

        self.state.is_arm_moving = False
        self._broadcast()

    async def _do_dispose(self, intent: IntentPacket):
        """
        Simulates a dispose sequence (which should never be reached in production
        because Stage 1 or Stage 2 should block it).

        If this is called, it means the Firewall passed a "dispose" action — which
        would only happen if the policy manifest has no dispose rule AND the modality
        is trusted AND the confidence is high. This is an extremely edge case but
        handled defensively.

        Logs a WARNING with the full intent so it is clearly visible in audit trail.

        Steps:
          1. Log a warning that dispose was passed and executed.
          2. Navigate to target coordinates (calls _do_navigate).
          3. Execute the same gripper release sequence as _do_place.
          4. If a held object exists, remove it from state.scene_objects entirely
             (disposition means the object no longer exists in the scene).
        """
        logger.warning(
            f"[SimulatorClient] DISPOSE action passed the firewall and is being "
            f"executed! target='{intent.target}' source_modality — verify policy coverage."
        )

        # Navigate to disposal location
        self.state.is_navigating = True
        self._broadcast()
        await self._do_navigate(intent)
        self.state.is_navigating = False

        # Arm sequence: extend, open, retract
        self.state.is_arm_moving = True
        self.state.arm_extended  = 0.8
        self._broadcast()
        await asyncio.sleep(ARM_EXTEND_S)

        self.state.gripper_open = True
        self._broadcast()
        await asyncio.sleep(ARM_GRIP_S)

        # Remove disposed object from scene entirely (it's been disposed of)
        if self.state.held_object:
            before    = len(self.state.scene_objects)
            self.state.scene_objects = [
                obj for obj in self.state.scene_objects
                if obj.id != self.state.held_object
            ]
            after = len(self.state.scene_objects)
            logger.warning(
                f"[SimulatorClient] Removed {before - after} object(s) from scene "
                f"(disposed)."
            )
            self.state.held_object = None

        self.state.arm_extended  = 0.0
        self.state.arm_z         = 1.2
        self.state.is_arm_moving = False
        self._broadcast()
        await asyncio.sleep(ARM_RETRACT_S)

    async def _do_stop(self, intent: IntentPacket):
        """
        Simulates an emergency or commanded stop.

        Immediately clears all motion flags and broadcasts the stopped state.
        This is the fail-safe action when the VLM outputs low confidence or
        an ambiguous command. The arm does not move at all.

        Steps:
          1. Log the stop command.
          2. Set is_navigating = False, is_arm_moving = False.
          3. Broadcast immediately (no delay — stops are instant).
          4. Sleep 0.1s so the UI acknowledges the stop before the next command.
        """
        logger.info(
            f"[SimulatorClient] STOP command received. "
            f"target='{intent.target}' — robot halted."
        )
        self.state.is_navigating = False
        self.state.is_arm_moving = False
        self._broadcast()
        await asyncio.sleep(0.1)

    async def _do_drop(self, intent: IntentPacket):
        """
        Simulates dropping the currently held object at the current position.

        Drop is different from place: the robot does not navigate to a new
        location, it releases the object wherever it currently stands.

        Steps:
          1. Open gripper immediately (no navigation), broadcast.
          2. If a held object exists: set obj.is_held=False,
             obj.position = [base_x, base_y, 0.0] (dropped on the floor).
             Clear state.held_object = None.
          3. Broadcast updated scene.
          4. Sleep 0.2s for animation.
        """
        logger.info(
            f"[SimulatorClient] DROP command — releasing held object "
            f"'{self.state.held_object}' at current position."
        )
        self.state.gripper_open = True
        self._broadcast()

        if self.state.held_object:
            for obj in self.state.scene_objects:
                if obj.id == self.state.held_object:
                    obj.is_held  = False
                    obj.position = [self.state.base_x, self.state.base_y, 0.0]
                    break
            self.state.held_object = None

        self._broadcast()
        await asyncio.sleep(0.2)

    async def _do_extend_arm(self, intent: IntentPacket):
        """
        Extends the arm to a target extension level and height.
        Used for inspection or reaching without picking.

        Steps:
          1. Set arm_extended = min(1.0, intent.coordinates.x / 0.6)
             (treats coordinates.x as desired extension distance in meters, max 0.6m).
          2. Set arm_z = intent.coordinates.z (vertical height of end-effector).
          3. Broadcast, sleep ARM_EXTEND_S.
        """
        self.state.arm_extended = min(1.0, intent.coordinates.get("x", 0.0) / 0.6)
        self.state.arm_z        = intent.coordinates.get("z") or 1.2
        self._broadcast()
        await asyncio.sleep(ARM_EXTEND_S)

    async def _do_retract_arm(self, intent: IntentPacket):
        """
        Retracts the arm back to the home resting position.

        Steps:
          1. Set arm_extended = 0.0 (fully retracted).
          2. Set arm_z = 1.2 (default resting height).
          3. Broadcast, sleep ARM_RETRACT_S.
        """
        self.state.arm_extended = 0.0
        self.state.arm_z        = 1.2
        self._broadcast()
        await asyncio.sleep(ARM_RETRACT_S)

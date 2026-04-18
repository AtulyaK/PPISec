"""
SceneRenderer — Server-Side Scene Image Generator (Software-Only)

Purpose:
    Generates composite scene images that are sent to the VLM as visual input.
    This replaces the physical camera that previously captured the real environment.

Pipeline (per render call):
    1. Load the scenario background JPEG (pre-prepared photo of the environment).
    2. If trojan_active: draw the Trojan Sign text box onto the background JPEG
       using PIL.ImageDraw (precise text, no font guessing by the VLM).
    3. Render the virtual robot (base + arm + gripper) using PyRender OSMesa
       with the current VirtualRobotState joint angles/positions.
    4. Composite the robot render (RGBA) over the background JPEG using PIL
       alpha blending (arm render overlays the real photo background).
    5. Return the composite as a base64-encoded JPEG string ready for the VLM.

Platform notes (see rendering_research.md for full analysis):
    - CPU Rendering: PYOPENGL_PLATFORM=osmesa → Works on any Linux/Mac.
    - GPU Rendering: PYOPENGL_PLATFORM=egl → Requires NVIDIA/AMD GPU drivers.
    - All render times are acceptable: /render_scene is called at most once per
      sense-plan-act step, and a step takes 3–10 seconds total anyway.

Environment variable:
    PYOPENGL_PLATFORM must be set BEFORE importing pyrender.
    The renderer reads this from os.environ at startup.
    Default: "osmesa" (works on any Linux, always safe fallback).
    Set to "egl" for GPU cluster hardware-accelerated rendering.

    Example (in your shell or systemd unit):
        export PYOPENGL_PLATFORM=osmesa
        # OR for GPU cluster:
        export PYOPENGL_PLATFORM=egl
"""

import os
import base64
import logging
import math
from io import BytesIO
from pathlib import Path
from typing import Optional, List

import numpy as np
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# PyRender backend selection.
# PYOPENGL_PLATFORM MUST be set before importing pyrender or OpenGL.
# If not set, default to "osmesa" (universally safe for headless environments).
# ─────────────────────────────────────────────────────────────────────────────
if "PYOPENGL_PLATFORM" not in os.environ:
    os.environ["PYOPENGL_PLATFORM"] = "osmesa"
    logger.info(
        "SceneRenderer: PYOPENGL_PLATFORM not set — defaulting to 'osmesa'. "
        "For GPU cluster, set PYOPENGL_PLATFORM=egl before starting the server."
    )

try:
    import pyrender
    import trimesh
    PYRENDER_AVAILABLE = True
    logger.info(
        f"SceneRenderer: PyRender loaded. "
        f"Backend: {os.environ.get('PYOPENGL_PLATFORM', 'osmesa')}"
    )
except ImportError:
    PYRENDER_AVAILABLE = False
    logger.warning(
        "SceneRenderer: PyRender not installed — robot render step disabled. "
        "Scene images will be background + sign only (no robot overlay). "
        "Run: pip install pyrender trimesh"
    )

# ─────────────────────────────────────────────────────────────────────────────
# Paths
# Scenarios directory: backgrounds are loaded from here.
# Assets directory: robot primitive meshes (OBJ/STL/GLTF) live here.
# ─────────────────────────────────────────────────────────────────────────────
SCENARIOS_DIR = Path(__file__).parent.parent / "scenarios"
ASSETS_DIR    = Path(__file__).parent.parent / "assets"

# Standard render output resolution for VLM input.
# 1024×768 gives good VLM comprehension without excessive tokens.
RENDER_WIDTH  = 1024
RENDER_HEIGHT = 768


class RobotStateSnapshot:
    """
    A lightweight snapshot of the virtual robot state passed to the renderer.
    Decoupled from VirtualRobotState to avoid circular imports.

    Populated in main.py from simulator_client.VirtualRobotState.to_dict().
    """

    def __init__(
        self,
        base_x:       float = 0.0,
        base_y:       float = 0.0,
        base_heading: float = 0.0,
        arm_extended: float = 0.0,
        arm_z:        float = 1.2,
        gripper_open: bool = True,
    ):
        self.base_x       = base_x
        self.base_y       = base_y
        self.base_heading = base_heading
        self.arm_extended = arm_extended
        self.arm_z        = arm_z
        self.gripper_open = gripper_open


class SceneRenderer:
    """
    Generates VLM-ready scene images combining:
      - A real/AI-generated environment background JPEG (from scenarios/)
      - An optional Trojan Sign drawn with PIL
      - An optional PyRender robot overlay (from the current VirtualRobotState)

    Instantiated once by main.py at server startup. The OffscreenRenderer is
    kept alive between calls (initializing it per-call is slow).
    """

    def __init__(self):
        # PyRender OffscreenRenderer — initialized lazily on first render call.
        # Kept alive between calls to avoid re-initializing the OpenGL context.
        # If None, robot overlay is skipped (background + sign only).
        self._renderer: Optional[object] = None

        # Cache of background images keyed by scenario ID.
        # Avoids re-reading the JPEG from disk on every render call.
        # Format: { scenario_id: PIL.Image (RGB, RENDER_WIDTH × RENDER_HEIGHT) }
        self._bg_cache: dict = {}

        # Font for the Trojan Sign text. Tries to load a system font.
        # Falls back to PIL's built-in default if no system font is available.
        self._font_large: Optional[ImageFont.FreeTypeFont] = None
        self._font_small: Optional[ImageFont.FreeTypeFont] = None
        self._load_fonts()

    def _load_fonts(self):
        """
        Loads TrueType fonts for Trojan Sign rendering.

        Tries common font paths on macOS and Linux in order:
          macOS: /System/Library/Fonts/Helvetica.ttc
          Linux: /usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf
          Ubuntu: /usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf

        Falls back to PIL's built-in bitmap font if none found.
        The built-in font is small and pixelated but functional.

        The sign font must be readable but not overly styled — the VLM reads it
        like a real sign, so standard sans-serif is most appropriate.
        """
        font_paths = [
            "/System/Library/Fonts/Helvetica.ttc",                             # macOS
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",            # Linux (Debian/Ubuntu)
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",    # Ubuntu
            "/System/Library/Fonts/Arial.ttf",                                 # macOS alternative
        ]

        for path in font_paths:
            if Path(path).exists():
                try:
                    self._font_large = ImageFont.truetype(path, size=26)
                    self._font_small = ImageFont.truetype(path, size=18)
                    logger.info(f"SceneRenderer: loaded font from {path}")
                    return
                except Exception as e:
                    logger.warning(f"SceneRenderer: font load failed for {path}: {e}")
                    continue

        # Fallback: PIL's built-in bitmap font (no path needed)
        logger.warning(
            "SceneRenderer: no TrueType font found — using PIL built-in bitmap font. "
            "Sign text will be low resolution. Install a system font package: "
            "apt install fonts-liberation"
        )
        self._font_large = ImageFont.load_default()
        self._font_small = ImageFont.load_default()

    def _get_background(self, scenario_id: str) -> Image.Image:
        """
        Returns the background image for the given scenario, resized to RENDER dimensions.

        Lookup order:
          1. Check self._bg_cache[scenario_id] — return cached copy (no disk I/O).
          2. Look for {SCENARIOS_DIR}/{scenario_id}.jpg (JPEG preferred for size).
             Also checks .png and .webp extensions.
          3. If file not found: generate a solid gray background with the scenario
             name written on it (graceful fallback, always produces a valid image).
          4. Resize to RENDER_WIDTH × RENDER_HEIGHT using LANCZOS resampling.
          5. Ensure the image is RGB (not RGBA — background should be opaque).
          6. Cache and return.

        The cached image is a copy of the PIL Image. Modifying it (drawing sign text)
        is safe because callers draw on their own copy via image.copy().
        """
        if scenario_id in self._bg_cache:
            return self._bg_cache[scenario_id]

        # Search for background file in multiple formats
        found_path: Optional[Path] = None
        for ext in (".jpg", ".jpeg", ".png", ".webp"):
            candidate = SCENARIOS_DIR / f"{scenario_id}{ext}"
            if candidate.exists():
                found_path = candidate
                break

        if found_path:
            try:
                img = Image.open(found_path).convert("RGB")
                img = img.resize((RENDER_WIDTH, RENDER_HEIGHT), Image.LANCZOS)
                logger.info(f"SceneRenderer: loaded background '{found_path}'")
            except Exception as e:
                logger.warning(f"SceneRenderer: failed to load background '{found_path}': {e}")
                img = self._generate_placeholder_background(scenario_id)
        else:
            logger.warning(
                f"SceneRenderer: no background found for scenario '{scenario_id}' "
                f"in {SCENARIOS_DIR}. Using placeholder."
            )
            img = self._generate_placeholder_background(scenario_id)

        self._bg_cache[scenario_id] = img
        return img

    def _generate_placeholder_background(self, scenario_id: str) -> Image.Image:
        """
        Generates a solid-color placeholder background when no photo is available.

        Different scenarios get different tints so they are visually distinguishable:
          hospital → light blue
          pharmacy → light green
          warehouse → light orange
          lab → light purple
          hotel → light gold
          default → neutral gray

        A center text label shows the scenario name so the VLM still gets context.
        """
        color_map = {
            "hospital":  (180, 210, 230),   # Blue-gray (clinical)
            "pharmacy":  (180, 230, 190),   # Green (medical supply)
            "warehouse": (230, 200, 160),   # Warm orange (industrial)
            "lab":       (200, 180, 230),   # Purple (scientific)
            "hotel":     (230, 220, 170),   # Gold (hospitality)
        }
        bg_color = color_map.get(scenario_id, (200, 200, 200))

        img  = Image.new("RGB", (RENDER_WIDTH, RENDER_HEIGHT), bg_color)
        draw = ImageDraw.Draw(img)

        # Draw a simple environmental cue (floor line + background depth)
        floor_y = int(RENDER_HEIGHT * 0.7)
        draw.rectangle(
            [(0, floor_y), (RENDER_WIDTH, RENDER_HEIGHT)],
            fill=tuple(max(0, c - 30) for c in bg_color)  # Darker floor
        )

        # Label the placeholder
        label = f"[Scenario: {scenario_id}]"
        draw.text(
            (20, 20),
            label,
            fill=(80, 80, 80),
            font=self._font_small
        )

        return img

    def _draw_trojan_sign(
        self,
        image: Image.Image,
        sign_text: str,
        position: str = "wall_center"
    ) -> Image.Image:
        """
        Draws a Trojan Sign onto the image using PIL.

        The sign is rendered as a white rectangular label with a black border,
        positioned to be clearly visible and readable by the VLM.

        Why PIL instead of rendering in PyRender:
          - PIL gives us exact control over the text content, font, and position.
          - The VLM needs to be able to read the text clearly — rasterized PIL text
            is pixel-perfect, not subject to 3D perspective distortion.
          - This mimics a real scenario more accurately: actual attack signs are
            printed labels with clear, legible text.

        Sign visual design:
          - White rectangle background (like a safety/instruction notice)
          - Black 2px border (makes it stand out from any background)
          - Bold black text on white (maximum contrast for VLM OCR)
          - Optional red "NOTICE" header bar (draws attention, common in real signs)

        position argument controls where on the background the sign is placed:
          "wall_center" → eye-level, center of the image (most visible)
          "wall_right"  → eye-level, right side
          "shelf"       → lower, near shelves
          "floor"       → on the floor (less visible, tests VLM attention)

        Steps:
          1. Split sign_text into lines at "\n" or every 40 characters.
          2. Compute the sign bounding box based on line count and font size.
          3. Determine x, y position from position argument.
          4. Draw white fill rectangle + black border rectangle.
          5. Draw a red header strip at the top: "⚠ NOTICE" in white.
          6. Draw each line of sign_text in black below the header.
          7. Return the modified image.
        """
        draw = ImageDraw.Draw(image)

        # Step 1: split text into lines (respect existing newlines + word wrap at 40 chars)
        raw_lines = sign_text.split("\n")
        lines = []
        for raw_line in raw_lines:
            # Wrap long lines at 40 characters
            if len(raw_line) > 40:
                words  = raw_line.split()
                line   = ""
                for word in words:
                    if len(line) + len(word) + 1 <= 40:
                        line = (line + " " + word).strip()
                    else:
                        if line:
                            lines.append(line)
                        line = word
                if line:
                    lines.append(line)
            else:
                lines.append(raw_line)

        # Step 2: compute sign box dimensions
        line_height   = 30   # pixels per text line
        header_height = 35   # height of the "NOTICE" header bar
        padding       = 12   # padding inside the sign border
        sign_width    = 380
        sign_height   = header_height + padding + (len(lines) * line_height) + padding

        # Step 3: determine position
        position_map = {
            "wall_center": (
                (RENDER_WIDTH  - sign_width)  // 2,
                int(RENDER_HEIGHT * 0.30),
            ),
            "wall_right": (
                RENDER_WIDTH - sign_width - 40,
                int(RENDER_HEIGHT * 0.28),
            ),
            "shelf": (
                int(RENDER_WIDTH * 0.3),
                int(RENDER_HEIGHT * 0.50),
            ),
            "floor": (
                int(RENDER_WIDTH * 0.2),
                int(RENDER_HEIGHT * 0.68),
            ),
        }
        x, y = position_map.get(position, position_map["wall_center"])

        # Step 4: draw white fill + black border
        draw.rectangle(
            [(x, y), (x + sign_width, y + sign_height)],
            fill=(255, 255, 255),
            outline=(20, 20, 20),
            width=2
        )

        # Step 5: draw red "NOTICE" header bar
        draw.rectangle(
            [(x, y), (x + sign_width, y + header_height)],
            fill=(200, 30, 30)   # Red header background
        )
        draw.text(
            (x + padding, y + 8),
            "⚠  NOTICE",
            fill=(255, 255, 255),
            font=self._font_large
        )

        # Step 6: draw each line of sign text below the header
        text_y = y + header_height + padding
        for line in lines:
            draw.text(
                (x + padding, text_y),
                line,
                fill=(20, 20, 20),
                font=self._font_small
            )
            text_y += line_height

        logger.debug(
            f"SceneRenderer: drew Trojan Sign at ({x}, {y}) "
            f"with {len(lines)} lines."
        )

        return image

    def _init_renderer(self):
        """
        Lazily initializes the PyRender OffscreenRenderer on the first render call.

        Why lazy init: the OpenGL context initialization can take 0.5–2 seconds.
        Doing it at class construction time would slow down server startup.
        On first actual render call, the delay is acceptable.

        If PyRender is unavailable (PYRENDER_AVAILABLE=False), this is a no-op.
        The renderer will remain None and robot overlay will be skipped.
        """
        if not PYRENDER_AVAILABLE or self._renderer is not None:
            return

        try:
            self._renderer = pyrender.OffscreenRenderer(
                viewport_width=RENDER_WIDTH,
                viewport_height=RENDER_HEIGHT
            )
            logger.info(
                f"SceneRenderer: PyRender OffscreenRenderer initialized "
                f"({RENDER_WIDTH}×{RENDER_HEIGHT}, "
                f"backend={os.environ.get('PYOPENGL_PLATFORM')})."
            )
        except Exception as e:
            logger.error(
                f"SceneRenderer: PyRender OffscreenRenderer initialization failed: {e}. "
                f"Robot overlay disabled. Try setting PYOPENGL_PLATFORM=osmesa."
            )
            self._renderer = None

    def _build_robot_mesh(self, robot_state: RobotStateSnapshot) -> "pyrender.Scene":
        """
        Constructs a PyRender scene containing the virtual service robot mesh.

        The robot is built from standard trimesh geometric primitives — no URDF
        file required. The primitives are parameterized by the robot state
        so the rendered pose matches the VirtualRobotState.

        Robot anatomy (all dimensions in meters):
          Mobile base:
            - Cylinder, radius=0.25m, height=0.15m, at floor level (z=0.075)
            - Gunmetal gray (0.3, 0.3, 0.35, 1.0)

          Torso:
            - Box, (0.35 × 0.25 × 0.50)m, sitting on top of the base
            - Light blue/white (0.85, 0.90, 0.95, 1.0)

          Head:
            - Sphere, radius=0.12m, on top of the torso
            - Same color as torso

          Arm column (Stretch-style, vertical telescoping):
            - Cylinder, radius=0.035m, height parameterized by arm_extended
              arm_extended=0.0 → height=0.20m (retracted)
              arm_extended=1.0 → height=0.80m (fully extended)
            - Positioned on the right side of the torso

          Arm horizontal segment:
            - Box, (0.25 × 0.05 × 0.05)m, extending right from the arm column

          Gripper:
            - Two small boxes (finger geometry):
              Left finger:  (0.06 × 0.03 × 0.12)m
              Right finger: (0.06 × 0.03 × 0.12)m
              Separation:   0.04m open, 0.01m closed (based on gripper_open)
            - Red if open, green if closed

        Scene setup:
          - Camera: PerspectiveCamera at (0.8, -2.0, 1.8) looking toward (0, 0, 1)
            (positioned in front and to the side of the robot for a 3/4 view that
            shows both the arm and the environment in the background)
          - Directional light: (10, 10, 5) intensity=3.0 (overhead + front fill)
          - Ambient light: [0.25, 0.25, 0.25] (no harsh dark shadows)

        Steps:
          1. Create trimesh primitives for each robot part at the computed poses.
          2. Convert each to pyrender.Mesh.from_trimesh() with metallic material.
          3. Create pyrender.Scene with ambient_light.
          4. Add all meshes to the scene at their computed poses.
          5. Add camera and directional light.
          6. Return the scene.
        """
        if not PYRENDER_AVAILABLE:
            return None

        scene = pyrender.Scene(
            ambient_light=[0.25, 0.25, 0.25],
            bg_color=[0.0, 0.0, 0.0, 0.0]   # Transparent background for compositing
        )

        # ── Computed layout ──────────────────────────────────────────────────
        # The robot is centered at (0, 0) in scene space. Base height offset
        # accounts for the base cylinder's half-height sitting on z=0 floor.
        base_h      = 0.15
        base_top_z  = base_h              # Top of the base cylinder
        torso_h     = 0.50
        torso_top_z = base_top_z + torso_h
        head_r      = 0.12
        head_z      = torso_top_z + head_r

        # Arm vertical extent based on arm_extended fraction
        arm_col_h   = 0.20 + robot_state.arm_extended * 0.60  # 0.20–0.80m
        arm_z_base  = base_top_z   # Arm column starts at base top

        # Gripper separation: 0.04m open, 0.01m closed
        gripper_sep = 0.04 if robot_state.gripper_open else 0.01
        gripper_color = (
            [0.9, 0.2, 0.2, 1.0] if robot_state.gripper_open    # Red = open
            else [0.2, 0.8, 0.2, 1.0]                           # Green = closed
        )

        # ── Helper: make a colored mesh from a trimesh primitive ─────────────
        def make_mesh(tm, color_rgba):
            """Converts a trimesh primitive to a pyrender.Mesh with a flat color."""
            mat = pyrender.MetallicRoughnessMaterial(
                baseColorFactor=color_rgba,
                metallicFactor=0.2,
                roughnessFactor=0.6,
            )
            return pyrender.Mesh.from_trimesh(tm, material=mat, smooth=True)

        def pose_at(x=0.0, y=0.0, z=0.0, rot_deg=0.0):
            """Returns a 4x4 pose matrix for translation + Z rotation."""
            p = np.eye(4, dtype=np.float32)
            p[0, 3] = x
            p[1, 3] = y
            p[2, 3] = z
            if rot_deg != 0.0:
                rad   = math.radians(rot_deg)
                cos_r = math.cos(rad)
                sin_r = math.sin(rad)
                p[0, 0] =  cos_r
                p[0, 1] = -sin_r
                p[1, 0] =  sin_r
                p[1, 1] =  cos_r
            return p

        # ── Mobile base (cylinder) ───────────────────────────────────────────
        base_mesh = trimesh.creation.cylinder(radius=0.25, height=base_h, sections=32)
        scene.add(
            make_mesh(base_mesh, [0.30, 0.30, 0.35, 1.0]),
            pose=pose_at(z=base_h / 2)
        )

        # ── Torso (box) ──────────────────────────────────────────────────────
        torso_mesh = trimesh.creation.box(extents=[0.35, 0.25, torso_h])
        scene.add(
            make_mesh(torso_mesh, [0.85, 0.90, 0.95, 1.0]),
            pose=pose_at(z=base_top_z + torso_h / 2)
        )

        # ── Head (sphere) ────────────────────────────────────────────────────
        head_mesh = trimesh.creation.icosphere(radius=head_r, subdivisions=3)
        scene.add(
            make_mesh(head_mesh, [0.85, 0.90, 0.95, 1.0]),
            pose=pose_at(z=head_z)
        )

        # ── Arm column (vertical cylinder, telescoping) ───────────────────────
        arm_col_mesh = trimesh.creation.cylinder(radius=0.035, height=arm_col_h, sections=16)
        scene.add(
            make_mesh(arm_col_mesh, [0.60, 0.60, 0.65, 1.0]),
            pose=pose_at(x=0.18, z=arm_z_base + arm_col_h / 2)
        )

        # ── Arm horizontal segment ────────────────────────────────────────────
        arm_horiz_x = 0.15 * robot_state.arm_extended   # Extends right as arm extends
        arm_h_mesh  = trimesh.creation.box(extents=[arm_horiz_x + 0.05, 0.04, 0.04])
        scene.add(
            make_mesh(arm_h_mesh, [0.55, 0.55, 0.60, 1.0]),
            pose=pose_at(
                x=0.18 + (arm_horiz_x + 0.05) / 2,
                z=arm_z_base + arm_col_h
            )
        )

        # ── Gripper fingers ────────────────────────────────────────────────────
        finger_extent  = [0.06, 0.03, 0.12]
        gripper_base_x = 0.18 + arm_horiz_x + 0.05
        gripper_base_z = arm_z_base + arm_col_h - 0.06

        for side, offset in [("left", -gripper_sep / 2), ("right", gripper_sep / 2)]:
            finger_mesh = trimesh.creation.box(extents=finger_extent)
            scene.add(
                make_mesh(finger_mesh, gripper_color),
                pose=pose_at(
                    x=gripper_base_x,
                    y=offset,
                    z=gripper_base_z
                )
            )

        # ── Camera ────────────────────────────────────────────────────────────
        # 3/4 perspective view: in front-right of robot, looking toward it.
        # yfov: vertical field of view in radians. pi/3 = 60° (wide enough to see full robot).
        camera      = pyrender.PerspectiveCamera(yfov=math.pi / 3.0, aspectRatio=RENDER_WIDTH / RENDER_HEIGHT)
        cam_pose    = np.array([
            [ 0.8, 0.0, -0.6,  1.8],   # Look slightly left (toward center)
            [ 0.0, 1.0,  0.0,  -1.8],  # Camera Y position (back from robot)
            [ 0.6, 0.0,  0.8,  1.6],   # Height: 1.6m (eye level for a standing person)
            [ 0.0, 0.0,  0.0,  1.0],
        ], dtype=np.float32)
        scene.add(camera, pose=cam_pose)

        # ── Lighting ──────────────────────────────────────────────────────────
        # Directional light simulates overhead office/hospital fluorescent lighting.
        light     = pyrender.DirectionalLight(color=[1.0, 1.0, 1.0], intensity=3.0)
        light_pose = pose_at(x=5.0, y=-5.0, z=10.0)
        scene.add(light, pose=light_pose)

        return scene

    def _render_robot(self, robot_state: RobotStateSnapshot) -> Optional[Image.Image]:
        """
        Renders the robot scene using PyRender and returns it as a PIL RGBA Image.

        The returned image has a transparent background (alpha=0 where no robot
        geometry is present), so it can be alpha-composited over the background JPEG.

        If PyRender is unavailable or initialization fails, returns None.
        The calling code in render_scene() handles None by skipping the composite step.

        Steps:
          1. Call self._init_renderer() (no-op if already initialized or unavailable).
          2. If self._renderer is None: return None.
          3. Build the robot scene: scene = self._build_robot_mesh(robot_state).
          4. Call color, depth = self._renderer.render(scene, flags=pyrender.RenderFlags.RGBA).
             The RGBA flag gives us a transparent background where no geometry is drawn.
          5. Convert the numpy RGBA array to PIL.Image via Image.fromarray(color).
          6. Return the PIL Image (mode "RGBA").
        """
        self._init_renderer()
        if self._renderer is None:
            return None

        scene = self._build_robot_mesh(robot_state)
        if scene is None:
            return None

        try:
            # RGBA render flag: pixels with no geometry have alpha=0 (transparent).
            # This is what allows clean compositing over the background photo.
            color, _depth = self._renderer.render(
                scene,
                flags=pyrender.RenderFlags.RGBA
            )
            return Image.fromarray(color, mode="RGBA")

        except Exception as e:
            logger.error(f"SceneRenderer: PyRender render() failed: {e}")
            return None

    def render_scene(
        self,
        scenario:     str,
        robot_state:  RobotStateSnapshot,
        trojan_active: bool = False,
        sign_text:    str   = "",
        sign_position: str  = "wall_center",
        jpeg_quality: int   = 88,
    ) -> str:
        """
        The main entry point. Generates a complete composite scene image and
        returns it as a base64-encoded JPEG string for the VLM.

        Output format: base64(JPEG) — same as what OpenAI vision APIs accept
        in "data:image/jpeg;base64,..." format.

        Steps:
          1. Load background: bg = self._get_background(scenario).copy()
             The .copy() is critical — we draw on the copy, not the cached original.

          2. If trojan_active and sign_text is not empty:
             bg = self._draw_trojan_sign(bg, sign_text, sign_position)
             This modifies the PIL Image in place (draws on bg).

          3. Render robot: robot_img = self._render_robot(robot_state)
             Returns a PIL RGBA Image or None if PyRender is unavailable.

          4. If robot_img is not None:
             Composite the robot over the background:
               bg.paste(robot_img, (0, 0), mask=robot_img.split()[3])
             robot_img.split()[3] is the alpha channel. paste() uses it as a mask:
             pixels with alpha=0 (transparent) show through to the background.
             pixels with alpha=255 (fully opaque robot geometry) cover the background.

          5. Convert to JPEG and base64 encode:
               buffer = BytesIO()
               bg.convert("RGB").save(buffer, format="JPEG", quality=jpeg_quality)
               b64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")

          6. Log the render summary (scenario, trojan status, composite result).

          7. Return b64_str.

        jpeg_quality: 88 is a good balance between file size and VLM comprehension.
        Lower values (60–75) compress more but may degrade text readability on signs.
        """
        # Step 1: load background (from cache or disk)
        bg = self._get_background(scenario).copy()

        # Step 2: inject Trojan Sign if active
        if trojan_active and sign_text:
            bg = self._draw_trojan_sign(bg, sign_text, sign_position)
            logger.debug(
                f"SceneRenderer: Trojan Sign injected: '{sign_text[:40]}...' "
                f"at position '{sign_position}'"
            )

        # Step 3: render the robot via PyRender
        robot_img = self._render_robot(robot_state)

        # Step 4: composite robot over background (if render succeeded)
        if robot_img is not None:
            # Ensure both images are the same size before compositing
            if robot_img.size != (RENDER_WIDTH, RENDER_HEIGHT):
                robot_img = robot_img.resize(
                    (RENDER_WIDTH, RENDER_HEIGHT),
                    Image.LANCZOS
                )
            # The alpha channel of robot_img masks the paste:
            # transparent (α=0) → show background photo
            # opaque (α=255) → show robot geometry
            bg.paste(robot_img, (0, 0), mask=robot_img.split()[3])
        else:
            logger.debug(
                "SceneRenderer: robot overlay skipped (PyRender unavailable). "
                "Scene image is background + sign only."
            )

        # Step 5: encode as base64 JPEG
        buffer = BytesIO()
        bg.convert("RGB").save(buffer, format="JPEG", quality=jpeg_quality)
        b64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")

        # Step 6: log summary
        logger.info(
            f"SceneRenderer: render complete — "
            f"scenario='{scenario}', trojan={trojan_active}, "
            f"robot_overlay={'yes' if robot_img else 'no'}, "
            f"output_size={len(b64_str)} chars"
        )

        # Step 7: return base64 JPEG string
        return b64_str

# Asset Management & Custom Scenarios

This guide explains how to add "real" 3D models and backgrounds to the PPISec Dashboard.

## 1. Asset Storage
All raw files must be placed in the `agent_glass/public/assets/` directory.

- **`robots/`**: Robotic arm models (`.glb` or `.gltf`).
- **`objects/`**: Scene items like pill bottles, crates, etc.
- **`environments/`**: Background images (`.jpg`) or HDRI world lighting (`.hdr`).

## 2. Dynamic Configuration (`scenarios.json`)
Instead of editing code, you can define the entire world in `agent_glass/public/assets/config/scenarios.json`.

### Example Configuration:
```json
{
  "scenarios": [
    {
      "id": "pharmacy",
      "name": "Medical Pharmacy",
      "icon": "💊",
      "environment": "hospital.hdr",
      "robot": {
        "model": "ur10_arm.glb",
        "scale": 1.0,
        "position": [0, 0, 0]
      },
      "objects": [
        {
          "id": "bottle_1",
          "model": "pill_bottle.glb",
          "position": [1.2, 0.4, 0.9],
          "rotation": [0, 0, 0],
          "scale": 0.1,
          "label": "Aspirin (Batch 4)"
        }
      ]
    }
  ]
}
```

## 3. Adding a New Scenario
1. **Upload Models:** Drop your GLB files into `public/assets/objects/`.
2. **Update JSON:** Add a new entry to the `scenarios` array in `public/assets/config/scenarios.json`.
3. **Restart:** Refresh the dashboard. The new scenario will appear in the deployment dropdown automatically.

## 4. Technical Note: GLB vs GLTF
Always prefer **`.glb`** (Binary GLTF) as it is a single self-contained file. If you use `.gltf`, you must also upload the associated `.bin` and texture files to the same folder.

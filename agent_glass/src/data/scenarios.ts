export interface SceneObjectSpec {
  id: string
  model: string
  position: [number, number, number]
  scale: number
  label: string
  is_target?: boolean
}

export interface Scenario {
  id: string
  name: string
  icon: string
  environment?: string
  background_model?: string
  robot_model: string
  robot_scale: number
  robot_y_offset: number
  human: {
    model: string
    position: [number, number, number]
    rotation: [number, number, number]
    scale: number
    label: string
  }
  objects: SceneObjectSpec[]
}

export const SCENARIOS: Scenario[] = [
  {
    id: "pharmacy",
    name: "Medical Pharmacy",
    icon: "💊",
    robot_model: "industrial_arm.glb",
    robot_scale: 1.8,
    robot_y_offset: 2,
    human: {
      model: "pharmacist.glb",
      position: [2.5, 1, 0.9],
      rotation: [0, -1.5, 0],
      scale: 1.2,
      label: "Chief Pharmacist (Trusted Actor)"
    },
    objects: [
      { id: "vial_1", model: "vial.glb", position: [1.2, 0.4, 0.9], scale: 0.1, label: "Insulin-X" },
      { id: "vial_2", model: "vial.glb", position: [1.4, 0.6, 0.9], scale: 0.1, label: "Standard_Vial" }
    ]
  },
  {
    id: "warehouse",
    name: "Industrial Logistics",
    icon: "📦",
    background_model: "warehouse.glb",
    robot_model: "heavy_manipulator.glb",
    robot_scale: 1.2,
    robot_y_offset: 1.8,
    human: {
      model: "pharmacist.glb",
      position: [3.5, 0, 1.0],
      rotation: [0, -1.2, 0],
      scale: 1.3,
      label: "Safety Supervisor"
    },
    objects: [
      { id: "crate_1", model: "crate.glb", position: [2.0, 0.5, 0.5], scale: 0.6, label: "Cargo_Crate_A", is_target: true }
    ]
  }
]

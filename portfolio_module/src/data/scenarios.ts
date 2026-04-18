export interface SceneObjectSpec {
  id: string
  mesh_type: 'box' | 'sphere' | 'cylinder'
  position: [number, number, number] // [x, y, z] in meters
  color: [number, number, number] // [r, g, b] 0-1
  label: string
  is_target?: boolean
}

export interface Scenario {
  id: string
  name: string
  description: string
  icon: string
  objects: SceneObjectSpec[]
}

export const SCENARIOS: Scenario[] = [
  {
    id: 'pharmacy',
    name: 'Medical Pharmacy',
    description: 'Autonomous medication sorting and inventory management.',
    icon: '💊',
    objects: [
      { id: 'bottle_1', mesh_type: 'cylinder', position: [1.2, 0.4, 0.9], color: [0.9, 0.2, 0.2], label: 'Pill Bottle (A-22)' },
      { id: 'bottle_2', mesh_type: 'cylinder', position: [1.4, 0.6, 0.9], color: [0.2, 0.4, 0.9], label: 'Insulin Vial' },
      { id: 'shelf_low', mesh_type: 'box', position: [1.5, 0.0, 0.4], color: [0.8, 0.8, 0.8], label: 'Storage Shelf A' },
      { id: 'counter', mesh_type: 'box', position: [1.0, 1.0, 0.8], color: [0.6, 0.6, 0.7], label: 'Dispensing Counter' },
    ]
  },
  {
    id: 'warehouse',
    name: 'Industrial Logistics',
    description: 'High-volume cargo handling and pallet organization.',
    icon: '📦',
    objects: [
      { id: 'crate_1', mesh_type: 'box', position: [2.0, 0.5, 0.5], color: [0.6, 0.4, 0.2], label: 'Cargo Crate (Heavy)', is_target: true },
      { id: 'crate_2', mesh_type: 'box', position: [2.2, -0.5, 0.5], color: [0.6, 0.4, 0.2], label: 'Cargo Crate (Standard)' },
      { id: 'palette', mesh_type: 'box', position: [2.5, 0.0, 0.1], color: [0.4, 0.4, 0.4], label: 'Loading Palette' },
      { id: 'dock_gate', mesh_type: 'box', position: [3.5, 0.0, 1.5], color: [0.2, 0.2, 0.3], label: 'Loading Dock B-4' },
    ]
  },
  {
    id: 'laboratory',
    name: 'Bio-Research Lab',
    description: 'Precision handling of hazardous biological samples.',
    icon: '🧪',
    objects: [
      { id: 'flask_1', mesh_type: 'sphere', position: [0.8, 1.2, 1.0], color: [0.2, 0.9, 0.4], label: 'Hazardous Sample 4-C' },
      { id: 'centrifuge', mesh_type: 'cylinder', position: [1.5, 1.5, 0.6], color: [0.7, 0.7, 0.7], label: 'Centrifuge Alpha' },
      { id: 'biohazard_bin', mesh_type: 'box', position: [0.0, 2.0, 0.6], color: [0.9, 0.8, 0.1], label: 'Disposal Unit' },
      { id: 'workspace', mesh_type: 'box', position: [1.0, 1.0, 0.85], color: [1.0, 1.0, 1.0], label: 'Sterile Workzone' },
    ]
  }
]

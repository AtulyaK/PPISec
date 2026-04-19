'use client'

import { useRef, useMemo, useState, useEffect, Suspense } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { OrbitControls, Grid, Environment, Float, ContactShadows, Sparkles, PerspectiveCamera, useGLTF, Html } from '@react-three/drei'
import * as THREE from 'three'
import { useFirewallStore, ArmState } from '../store/firewall'
import { motion, AnimatePresence } from 'framer-motion'
import { Target, Navigation, Box, Video, Cpu, Activity, ShieldAlert, Zap, Layers, RotateCcw } from 'lucide-react'
import scenariosData from '../../public/assets/config/scenarios.json'

declare global {
  interface Window {
    __LAST_CAM_DIST: number
  }
}

// ─── Constants ────────────────────────────────────────────────────────────────
const toScene = (m: number) => m
const CAM_PRESETS = {
  iso: [8, 8, 8] as [number, number, number],
  top: [0, 12, 0] as [number, number, number],
  front: [0, 4, 10] as [number, number, number],
}

// ─── Camera Controller ────────────────────────────────────────────────────────
function CameraHandler({ mode, resetTrigger }: { mode: 'iso' | 'top' | 'front', resetTrigger: number }) {
  const { camera } = useThree()
  const controlsRef = useRef<any>(null)

  useEffect(() => {
    const targetPos = CAM_PRESETS[mode]
    console.log('[CameraHandler] Resetting to mode:', mode, targetPos)
    camera.position.set(...targetPos)
    camera.lookAt(0, 0, 0)
    if (controlsRef.current) {
      controlsRef.current.target.set(0, 0, 0)
      controlsRef.current.update()
    }
  }, [mode, camera, resetTrigger])

  useFrame(() => {
    if (controlsRef.current) {
      const dist = camera.position.distanceTo(controlsRef.current.target)
      if (Math.abs(window.__LAST_CAM_DIST - dist) > 0.1) {
        console.log('[CameraHandler] Current Distance:', dist)
        window.__LAST_CAM_DIST = dist
      }
    }
  })

  return (
    <OrbitControls
      ref={controlsRef}
      enablePan={false}
      makeDefault
      minPolarAngle={0}
      maxPolarAngle={Math.PI / 2.1}
      minDistance={5}
      maxDistance={20}
      enableDamping={true}
      dampingFactor={0.05}
    />
  )
}

// ─── Shared Materials ─────────────────────────────────────────────────────────
const useArmMaterials = (color: string, isGhost: boolean) => {
  return useMemo(() => ({
    frame: new THREE.MeshPhysicalMaterial({
      color: color,
      metalness: 1,
      roughness: 0,
      transparent: isGhost,
      opacity: isGhost ? 0.3 : 1,
      transmission: isGhost ? 0.8 : 0,
      thickness: 1,
      emissive: color,
      emissiveIntensity: isGhost ? 1 : 0.2,
    }),
    joint: new THREE.MeshPhysicalMaterial({
      color: isGhost ? '#ef4444' : '#ffffff',
      metalness: 1,
      roughness: 0,
      transparent: isGhost,
      opacity: isGhost ? 0.4 : 1,
      emissive: isGhost ? '#ef4444' : '#ffffff',
      emissiveIntensity: 0.5,
    }),
    gripper: new THREE.MeshPhysicalMaterial({
      color: '#cbd5e1',
      metalness: 1,
      roughness: 0.1,
      transparent: isGhost,
      opacity: isGhost ? 0.3 : 1,
    }),
    base: new THREE.MeshPhysicalMaterial({
      color: '#0f172a',
      metalness: 0.8,
      roughness: 0.2,
      transparent: isGhost,
      opacity: isGhost ? 0.1 : 1,
    })
  }), [color, isGhost])
}

// ─── Arm geometry components ──────────────────────────────────────────────────
function ArmLink({ length, radius = 0.05, material }: { length: number, radius?: number, material: THREE.Material }) {
  return (
    <mesh castShadow material={material}>
      <cylinderGeometry args={[radius, radius, length, 32]} />
    </mesh>
  )
}

function Joint({ material }: { material: THREE.Material }) {
  return (
    <mesh castShadow material={material}>
      <sphereGeometry args={[0.07, 32, 32]} />
    </mesh>
  )
}

function Gripper({ open, material }: { open: boolean, material: THREE.Material }) {
  const offset = open ? 0.08 : 0.02
  return (
    <group>
      <mesh position={[-offset, -0.08, 0]} castShadow material={material}>
        <boxGeometry args={[0.02, 0.16, 0.04]} />
      </mesh>
      <mesh position={[offset, -0.08, 0]} castShadow material={material}>
        <boxGeometry args={[0.02, 0.16, 0.04]} />
      </mesh>
    </group>
  )
}

// ─── Native Object Loaders ───────────────────────────────────────────────────
function DynamicObject({ url, position, rotation, scale, label, ...props }: { url: string, position?: any, rotation?: any, scale?: any, label?: string, [key: string]: any }) {
  const { scene } = useGLTF(url) as any
  const clonedScene = useMemo(() => scene.clone(), [scene])
  return (
    <group position={position} rotation={rotation || [0, 0, 0]} scale={scale} {...props}>
      <primitive object={clonedScene} castShadow receiveShadow />
      {label && (
        <Html position={[0, 1.4, 0]} center distanceFactor={10} zIndexRange={[100, 0]}>
          <motion.div 
            initial={{ opacity: 0, y: 10, scale: 0.8 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            className="flex flex-col items-center gap-1"
          >
            <div className="px-3 py-1 bg-slate-900/40 border border-white/20 backdrop-blur-xl rounded-full text-[10px] font-black text-white whitespace-nowrap tracking-widest shadow-[0_0_20px_rgba(255,255,255,0.1)] flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-cyan-500 shadow-[0_0_8px_#22d3ee] animate-pulse" />
              {label.toUpperCase()}
            </div>
            <div className="w-[1px] h-6 bg-gradient-to-t from-transparent via-white/20 to-transparent" />
          </motion.div>
        </Html>
      )}
    </group>
  )
}

function TrojanSign({ text }: { text: string }) {
  return (
    <group position={[-1.5, 0, 0.5]} rotation={[0, 0.4, 0]}>
      {/* Physical Sign Post */}
      <mesh position={[0, 0.5, 0]}>
        <cylinderGeometry args={[0.02, 0.02, 1, 16]} />
        <meshStandardMaterial color="#334155" metalness={0.8} roughness={0.2} />
      </mesh>
      {/* Sign Plate */}
      <mesh position={[0, 1, 0]}>
        <boxGeometry args={[0.8, 0.4, 0.02]} />
        <meshStandardMaterial color="#0f172a" metalness={0.5} roughness={0.5} />
      </mesh>
      {/* Glowing Border */}
      <mesh position={[0, 1, 0.011]}>
        <planeGeometry args={[0.82, 0.42]} />
        <meshBasicMaterial color="#ef4444" transparent opacity={0.2} />
      </mesh>
      {/* Adversarial Text Label */}
      <Html position={[0, 1, 0.02]} center transform distanceFactor={1.5} rotation={[0, 0, 0]}>
        <div className="px-4 py-2 bg-red-600/10 border-2 border-red-500/50 rounded flex flex-col items-center gap-1 w-64 select-none">
          <span className="text-[10px] font-black text-red-500 uppercase tracking-tighter">PHYSICAL_SEC_OVERRIDE</span>
          <p className="text-xs font-black text-white text-center leading-tight uppercase tracking-tight italic">
            {text}
          </p>
        </div>
      </Html>
    </group>
  )
}

function ScenarioEnvironment() {
  const { activeScenario, trojanConfig } = useFirewallStore()
  const scenario = activeScenario
  return (
    <group>
      {/* Background environment if specified */}
      {scenario.background_model && (
        <DynamicObject url={`/assets/objects/${scenario.background_model}`} position={[0, 0, 0]} scale={2} />
      )}
      
      {/* Human Base Mesh */}
      <DynamicObject
        url={`/assets/objects/${scenario.human.model}`}
        position={scenario.human.position}
        rotation={scenario.human.rotation}
        scale={scenario.human.scale}
        label={scenario.human.label}
      />
      {/* Target Interaction Objects */}
      {scenario.objects.map((obj, i) => (
        <DynamicObject
          key={i}
          url={`/assets/objects/${obj.model}`}
          position={obj.position}
          scale={obj.scale}
          label={obj.label}
        />
      ))}
      
      {/* Conditionally render the Trojan Sign */}
      {trojanConfig.active && <TrojanSign text={trojanConfig.text} />}
    </group>
  )
}


// ─── Robotic Arm Visual ───────────────────────────────────────────────────────
function RobotAssembly({ state, color, isGhost = false }: { state: ArmState, color: string, isGhost?: boolean }) {
  const robotRef = useRef<THREE.Group>(null)
  const current = useRef({ x: state.base_x, y: state.base_y, h: state.base_heading })
  const { activeScenario } = useFirewallStore()
  const scenario = activeScenario

  useFrame((_, delta) => {
    const lerpSpeed = 5.0
    current.current.x = THREE.MathUtils.lerp(current.current.x, state.base_x, delta * lerpSpeed)
    current.current.y = THREE.MathUtils.lerp(current.current.y, state.base_y, delta * lerpSpeed)
    current.current.h = THREE.MathUtils.lerp(current.current.h, state.base_heading, delta * lerpSpeed)

    if (robotRef.current) {
      robotRef.current.position.set(current.current.x, 0, current.current.y)
      robotRef.current.rotation.y = THREE.MathUtils.degToRad(current.current.h)
    }
  })

  // Apply ghost styling if needed, otherwise render raw model
  return (
    <group ref={robotRef}>
      <Suspense fallback={null}>
        <DynamicObject 
          url={`/assets/robots/${scenario.robot_model}`} 
          scale={scenario.robot_scale} 
          position={[0, scenario.robot_y_offset || 0, 0]}
        />
      </Suspense>
      {/* If ghost mode is active, we render an abstract bounding volume to show intent */}
      {isGhost && (
        <mesh position={[0, (scenario.robot_y_offset || 0), 0]}>
          <cylinderGeometry args={[scenario.robot_scale * 0.4, scenario.robot_scale * 0.4, scenario.robot_scale, 16]} />
          <meshPhysicalMaterial 
            color="#ef4444" 
            transparent 
            opacity={0.3} 
            emissive="#ef4444" 
            emissiveIntensity={0.5} 
            wireframe
          />
        </mesh>
      )}
    </group>
  )
}

// ─── Status Hologram ──────────────────────────────────────────────────────────
function StatusLabel() {
  const { lastDecision } = useFirewallStore()
  if (lastDecision === 'IDLE') return null

  const config = {
    PASS: { color: '#10b981' },
    WARN: { color: '#f59e0b' },
    VETO: { color: '#ef4444' },
    PENDING: { color: '#6366f1' },
  }

  const { color } = config[lastDecision as keyof typeof config] || config.PASS

  return (
    <Float speed={2} rotationIntensity={0.1} floatIntensity={0.2}>
      <group position={[0, 2.8, 0]}>
        <mesh rotation-x={Math.PI / 2}>
          <ringGeometry args={[0.9, 0.92, 128]} />
          <meshBasicMaterial color={color} transparent opacity={0.4} />
        </mesh>
        <pointLight color={color} intensity={2} distance={3} />
      </group>
    </Float>
  )
}

// ─── Main Component ───────────────────────────────────────────────────────────
export default function Scene3D() {
  const { armState, proposedArmState, lastDecision } = useFirewallStore()
  const [camMode, setCamMode] = useState<'iso' | 'top' | 'front'>('iso')
  const [camResetTrigger, setCamResetTrigger] = useState(0)

  const mainColor =
    lastDecision === 'VETO' ? '#ef4444' :
      lastDecision === 'WARN' ? '#f59e0b' :
        '#6366f1'

  return (
    <div className="relative w-full h-full bg-[#020617] overflow-hidden group/canvas">
      {/* Cinematic Overlays */}
      <div className="vignette" />

      {/* 3D Telemetry HUD Overlay */}
      <div className="absolute inset-0 z-10 pointer-events-none flex flex-col p-8">
        <div className="flex justify-between items-start">
          {/* Top Left: Diagnostics HUD */}
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-xl bg-slate-900/80 border border-white/10 flex items-center justify-center backdrop-blur-xl shadow-2xl">
                <Cpu className="w-5 h-5 text-indigo-400" />
              </div>
              <div className="flex flex-col">
                <span className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em] mb-0.5">Telemetry_Node</span>
                <span className="text-sm font-black text-white italic tracking-tighter">SURVEILLANCE_B12</span>
              </div>
            </div>

            <div className="flex flex-col gap-1.5 ml-1">
              {[
                { label: 'Local_X', value: armState.base_x, icon: Navigation },
                { label: 'Local_Y', value: armState.base_y, icon: Activity },
                { label: 'Manip_Z', value: armState.arm_z, icon: Layers },
              ].map((item) => (
                <div key={item.label} className="flex items-center gap-3">
                  <item.icon className="w-3 h-3 text-slate-600" />
                  <div className="flex items-center gap-2">
                    <span className="text-[8px] font-mono font-bold text-slate-500 uppercase tracking-tighter w-14">{item.label}::</span>
                    <span className="text-[10px] font-mono font-bold text-indigo-400 glow-idle">{item.value.toFixed(3)}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Top Right: Camera System */}
          <div className="flex flex-col gap-3 pointer-events-auto">
            <div className="p-1 px-1.5 rounded-full bg-slate-950/80 border border-white/10 backdrop-blur-xl flex items-center gap-1 shadow-2xl">
              <button
                onClick={() => setCamMode('iso')}
                className={`p-2 rounded-full transition-all duration-300 hover:bg-slate-800 text-slate-400 hover:text-white`}
                title="Initialize Reset"
              >
                <RotateCcw className="w-3.5 h-3.5" />
              </button>
              <div className="w-px h-4 bg-white/10 mx-1" />
              {[
                { id: 'top', icon: Video, label: 'Perspective Top' },
                { id: 'iso', icon: Navigation, rotate: 45, label: 'Perspective Iso' },
                { id: 'front', icon: Box, label: 'Perspective Front' },
              ].map((p) => (
                <button
                  key={p.id}
                  onClick={() => setCamMode(p.id as any)}
                  className={`p-2 rounded-full transition-all duration-300 ${camMode === p.id ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/30' : 'text-slate-500 hover:text-white'}`}
                  title={p.label}
                >
                  <p.icon className="w-3.5 h-3.5" style={p.rotate ? { transform: `rotate(${p.rotate}deg)` } : {}} />
                </button>
              ))}
            </div>
            <div className="flex items-center justify-end gap-2 px-2">
              <span className="text-[8px] font-black text-slate-600 uppercase tracking-widest">Active_Camera_0{camMode === 'iso' ? '1' : camMode === 'top' ? '2' : '3'}</span>
              <div className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse" />
            </div>
          </div>
        </div>

        {/* Bottom HUD: Dynamic Status */}
        <div className="mt-auto flex justify-center pb-4">
          <AnimatePresence mode="wait">
            <motion.div
              key={armState.last_action}
              initial={{ opacity: 0, scale: 0.9, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9, y: 10 }}
              className="px-10 py-5 rounded-2xl bg-slate-950/60 border border-white/5 backdrop-blur-2xl shadow-2xl flex flex-col items-center gap-1 min-w-[320px] relative overflow-hidden"
            >
              <div className="absolute top-0 inset-x-0 h-[1px] bg-gradient-to-r from-transparent via-indigo-500/50 to-transparent" />
              <div className="flex items-center gap-2 mb-1">
                <Activity className="w-3 h-3 text-indigo-500" />
                <span className="text-[9px] font-black text-indigo-400 uppercase tracking-[0.4em]">Unit_Directive</span>
              </div>
              <span className="text-xl font-black text-white italic tracking-tighter uppercase mb-2">
                {armState.last_action || 'Standing_By'}
              </span>
              <div className="flex items-center gap-4 text-[9px] font-mono font-bold text-slate-500">
                <span className="flex items-center gap-1.5"><Zap className="w-3 h-3" /> PWR: 98%</span>
                <div className="w-1 h-1 rounded-full bg-slate-800" />
                <span className="flex items-center gap-1.5"><ShieldAlert className="w-3 h-3" /> GOV: PASS_AUTO</span>
              </div>
            </motion.div>
          </AnimatePresence>
        </div>
      </div>

      {/* 3D Core */}
      <Canvas shadows gl={{ antialias: true, alpha: true }}>
        <PerspectiveCamera makeDefault fov={40} position={CAM_PRESETS.iso} />
        <CameraHandler mode={camMode} resetTrigger={camResetTrigger} />

        <color attach="background" args={['#020617']} />
        <fog attach="fog" args={['#020617', 5, 30]} />

        <ambientLight intensity={0.4} />
        <spotLight position={[10, 15, 10]} angle={0.2} penumbra={1} intensity={1.5} castShadow />
        <pointLight position={[-8, 8, -8]} intensity={0.5} color="#4f46e5" />
        <Environment preset="night" />

        <group position={[0, -0.01, 0]}>
          <Grid args={[40, 40]} cellSize={1} cellThickness={0.5} cellColor="#1e293b" sectionSize={5} sectionThickness={1} sectionColor="#334155" fadeDistance={40} infiniteGrid />
          <ContactShadows opacity={0.6} scale={20} blur={2.4} far={10} resolution={512} color="#000000" />
        </group>

        <Suspense fallback={null}>
          <ScenarioEnvironment />
        </Suspense>

        <RobotAssembly state={armState} color={mainColor} />

        {proposedArmState && lastDecision !== 'PASS' && (
          <RobotAssembly state={proposedArmState} color="#ef4444" isGhost />
        )}

        <StatusLabel />
        <Sparkles count={40} scale={15} size={1} speed={0.2} opacity={0.1} color="#4f46e5" />
      </Canvas>
    </div>
  )
}

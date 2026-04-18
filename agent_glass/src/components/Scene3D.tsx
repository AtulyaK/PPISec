'use client'

import { useRef, useEffect } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { OrbitControls, Grid, Environment, Float, Text3D, Center } from '@react-three/drei'
import * as THREE from 'three'
import { useFirewallStore } from '../store/firewall'

// ─── Arm geometry constants (all in mm, scaled to Three.js units by /100) ────
const SCALE = 0.01

function toScene(mm: number) {
  return mm * SCALE
}

// ─── Individual arm link rendered as a rounded box ────────────────────────────
function ArmLink({
  length,
  radius = 0.05,
  color,
}: {
  length: number
  radius?: number
  color: string
}) {
  return (
    <mesh castShadow>
      <cylinderGeometry args={[radius, radius, length, 16]} />
      <meshStandardMaterial color={color} metalness={0.6} roughness={0.3} />
    </mesh>
  )
}

// ─── Gripper fingers ──────────────────────────────────────────────────────────
function Gripper({ open }: { open: boolean }) {
  const offset = open ? 0.08 : 0.02
  return (
    <group>
      {/* Left finger */}
      <mesh position={[-offset, -0.08, 0]} castShadow>
        <boxGeometry args={[0.03, 0.16, 0.03]} />
        <meshStandardMaterial color="#e2e8f0" metalness={0.8} roughness={0.2} />
      </mesh>
      {/* Right finger */}
      <mesh position={[offset, -0.08, 0]} castShadow>
        <boxGeometry args={[0.03, 0.16, 0.03]} />
        <meshStandardMaterial color="#e2e8f0" metalness={0.8} roughness={0.2} />
      </mesh>
    </group>
  )
}

// ─── Joint sphere ─────────────────────────────────────────────────────────────
function Joint({ color = '#64748b' }: { color?: string }) {
  return (
    <mesh castShadow>
      <sphereGeometry args={[0.07, 16, 16]} />
      <meshStandardMaterial color={color} metalness={0.7} roughness={0.2} />
    </mesh>
  )
}

// ─── The animated arm assembly ────────────────────────────────────────────────
function RoboticArm() {
  const { armState, lastDecision } = useFirewallStore()

  // Lerp current position toward target for smooth animation
  const currentPos = useRef({ x: 0, y: 2, z: 1 })
  const targetPos = useRef({ x: 0, y: 2, z: 1 })

  useEffect(() => {
    targetPos.current = {
      x: toScene(armState.x),
      y: toScene(armState.y),
      z: toScene(armState.z),
    }
  }, [armState.x, armState.y, armState.z])

  const endEffectorRef = useRef<THREE.Group>(null)
  const glowRef = useRef<THREE.PointLight>(null)

  useFrame((_, delta) => {
    const lerpSpeed = armState.is_moving ? 2.0 : 5.0
    currentPos.current.x = THREE.MathUtils.lerp(currentPos.current.x, targetPos.current.x, delta * lerpSpeed)
    currentPos.current.y = THREE.MathUtils.lerp(currentPos.current.y, targetPos.current.y, delta * lerpSpeed)
    currentPos.current.z = THREE.MathUtils.lerp(currentPos.current.z, targetPos.current.z, delta * lerpSpeed)

    if (endEffectorRef.current) {
      endEffectorRef.current.position.set(currentPos.current.x, currentPos.current.y, currentPos.current.z)
    }

    // Glow color based on decision
    if (glowRef.current) {
      const targetColor =
        lastDecision === 'VETO' ? new THREE.Color('#ef4444') :
        lastDecision === 'WARN' ? new THREE.Color('#f59e0b') :
        lastDecision === 'PASS' ? new THREE.Color('#22c55e') :
        new THREE.Color('#6366f1')
      glowRef.current.color.lerp(targetColor, delta * 3)
    }
  })

  const armColor =
    lastDecision === 'VETO' ? '#ef4444' :
    lastDecision === 'WARN' ? '#f59e0b' :
    '#6366f1'

  return (
    <>
      {/* Dynamic glow following end-effector */}
      <pointLight ref={glowRef} intensity={2} distance={3} decay={2} />

      {/* Base */}
      <mesh position={[0, 0.05, 0]} receiveShadow castShadow>
        <cylinderGeometry args={[0.2, 0.25, 0.1, 32]} />
        <meshStandardMaterial color="#1e293b" metalness={0.9} roughness={0.1} />
      </mesh>

      {/* Shoulder joint */}
      <group position={[0, 0.15, 0]}>
        <Joint color={armColor} />

        {/* Upper arm */}
        <group position={[0, 0.4, 0]}>
          <ArmLink length={0.65} color={armColor} />

          {/* Elbow joint */}
          <group position={[0, 0.35, 0]}>
            <Joint color={armColor} />

            {/* Forearm */}
            <group position={[0, 0.3, 0]}>
              <ArmLink length={0.5} color={armColor} />

              {/* Wrist joint */}
              <group position={[0, 0.28, 0]}>
                <Joint color={armColor} />

                {/* End effector group — positions tracked */}
                <group ref={endEffectorRef}>
                  {/* Wrist link */}
                  <ArmLink length={0.2} color={armColor} />
                  <group position={[0, 0.12, 0]}>
                    <Gripper open={armState.gripper_open} />
                  </group>
                </group>
              </group>
            </group>
          </group>
        </group>
      </group>
    </>
  )
}

// ─── Target position indicator ────────────────────────────────────────────────
function TargetMarker() {
  const { armState } = useFirewallStore()
  const ref = useRef<THREE.Mesh>(null)

  useFrame(({ clock }) => {
    if (ref.current) {
      ref.current.position.set(
        toScene(armState.x),
        toScene(armState.y),
        toScene(armState.z),
      )
      ref.current.rotation.y = clock.getElapsedTime() * 1.5
      const pulse = 0.7 + 0.3 * Math.sin(clock.getElapsedTime() * 4)
      ref.current.scale.setScalar(pulse)
    }
  })

  return (
    <mesh ref={ref}>
      <octahedronGeometry args={[0.06]} />
      <meshStandardMaterial color="#818cf8" wireframe emissive="#818cf8" emissiveIntensity={0.5} />
    </mesh>
  )
}

// ─── Work surface ─────────────────────────────────────────────────────────────
function WorkSurface() {
  return (
    <>
      {/* Table */}
      <mesh position={[0, -0.02, 0]} receiveShadow>
        <boxGeometry args={[6, 0.04, 6]} />
        <meshStandardMaterial color="#0f172a" metalness={0.1} roughness={0.9} />
      </mesh>
      <Grid
        position={[0, 0, 0]}
        args={[6, 6]}
        cellSize={0.5}
        cellThickness={0.3}
        cellColor="#1e293b"
        sectionSize={2}
        sectionThickness={0.8}
        sectionColor="#334155"
        fadeDistance={12}
        fadeStrength={1}
        infiniteGrid
      />
    </>
  )
}

// ─── Decision status label floating above the arm ─────────────────────────────
function StatusLabel() {
  const { lastDecision } = useFirewallStore()

  const color =
    lastDecision === 'VETO' ? '#ef4444' :
    lastDecision === 'WARN' ? '#f59e0b' :
    lastDecision === 'PASS' ? '#22c55e' :
    '#6366f1'

  if (lastDecision === 'IDLE') return null

  return (
    <Float speed={2} rotationIntensity={0.1} floatIntensity={0.3}>
      <group position={[0, 3, 0]}>
        <Center>
          <mesh>
            <planeGeometry args={[1.2, 0.3]} />
            <meshBasicMaterial color={color} opacity={0.15} transparent />
          </mesh>
        </Center>
      </group>
    </Float>
  )
}

// ─── Main Scene3D component ───────────────────────────────────────────────────
export default function Scene3D() {
  return (
    <div className="w-full h-full">
      <Canvas
        shadows
        camera={{ position: [4, 4, 4], fov: 45 }}
        gl={{ antialias: true, alpha: false }}
        style={{ background: 'transparent' }}
      >
        <color attach="background" args={['#020817']} />
        <fog attach="fog" args={['#020817', 10, 30]} />

        {/* Lighting */}
        <ambientLight intensity={0.3} />
        <directionalLight
          castShadow
          position={[5, 10, 5]}
          intensity={1.5}
          shadow-mapSize={[2048, 2048]}
        />
        <pointLight position={[-5, 5, -5]} intensity={0.5} color="#818cf8" />

        <Environment preset="city" />

        {/* Scene content */}
        <WorkSurface />
        <RoboticArm />
        <TargetMarker />
        <StatusLabel />

        <OrbitControls
          enablePan={true}
          enableZoom={true}
          makeDefault
          minPolarAngle={0}
          maxPolarAngle={Math.PI / 2.1}
        />
      </Canvas>
    </div>
  )
}

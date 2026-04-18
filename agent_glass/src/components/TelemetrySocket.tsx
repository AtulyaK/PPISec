'use client'

import { useEffect, useRef } from 'react'
import { useFirewallStore, TelemetryEvent, ArmState } from '../store/firewall'

const WS_URL = process.env.NEXT_PUBLIC_BACKEND_WS ?? 'ws://localhost:8000/ws/telemetry'

export function TelemetrySocket() {
  const {
    setArmState,
    addEvent,
    setDecision,
    setProcessing,
    setWsConnected,
  } = useFirewallStore()
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    function connect() {
      const ws = new WebSocket(WS_URL)
      wsRef.current = ws

      ws.onopen = () => {
        setWsConnected(true)
        console.log('[TelemetrySocket] Connected to', WS_URL)
      }

      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data as string)

          if (msg.type === 'arm_state' || msg.type === 'robot_state') {
            const data = msg.data || msg.robot_state
            if (data) setArmState(data)
          } else if (msg.type === 'decision') {
            // Construct proposed robot state from coordinates in the message
            let proposed: ArmState | undefined = undefined
            if (msg.coordinates && msg.robot_state) {
              const action = (msg.action || '').toLowerCase()
              const isNav = ['move', 'navigate', 'go'].includes(action)
              
              proposed = {
                ...msg.robot_state,
                // If navigation, map x/y to base. If manipulation, use current base but updated arm.
                base_x: isNav ? (msg.coordinates.x ?? msg.robot_state.base_x) : msg.robot_state.base_x,
                base_y: isNav ? (msg.coordinates.y ?? msg.robot_state.base_y) : msg.robot_state.base_y,
                arm_z: !isNav ? (msg.coordinates.z ?? msg.robot_state.arm_z) : msg.robot_state.arm_z,
                last_action: msg.action,
                last_target: msg.target,
              }
            }

            const event: TelemetryEvent = {
              id: msg.request_id ?? crypto.randomUUID(),
              timestamp: Date.now(),
              decision: msg.decision,
              action: msg.action ?? '',
              target: msg.target ?? '',
              source_modality: msg.source_modality ?? 'unknown',
              reason: msg.reason ?? null,
              latency_ms: msg.latency_ms ?? 0,
              reasoning_trace: msg.reasoning_trace ?? '',
              arm_state: msg.robot_state,
              proposed_arm_state: proposed,
              hitl_override_token: msg.hitl_override_token || null,
            }
            addEvent(event)
            setDecision(msg.decision, msg.reason, msg.latency_ms, proposed)
            setProcessing(false)
          } else if (msg.type === 'processing') {
            setProcessing(true)
          }
        } catch (e) {
          console.error('[TelemetrySocket] Failed to parse message', e)
        }
      }

      ws.onclose = () => {
        setWsConnected(false)
        console.warn('[TelemetrySocket] Disconnected — retrying in 3s')
        setTimeout(connect, 3000)
      }

      ws.onerror = (e) => {
        console.error('[TelemetrySocket] Error', e)
        ws.close()
      }
    }

    connect()
    return () => {
      wsRef.current?.close()
    }
  }, []) // eslint-disable-line

  return null // Headless component — only manages the WS connection
}

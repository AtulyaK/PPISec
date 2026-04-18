'use client'

import { useEffect, useRef } from 'react'
import { useFirewallStore, TelemetryEvent } from '../store/firewall'

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

          if (msg.type === 'arm_state') {
            setArmState(msg.data)
          } else if (msg.type === 'decision') {
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
              arm_state: msg.arm_state,
            }
            addEvent(event)
            setDecision(msg.decision, msg.reason, msg.latency_ms)
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

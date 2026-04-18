# PPISec: Semantic Firewall (Portfolio Demo Module)

This directory contains a **100% client-side, zero-server** implementation of the PPISec Semantic Firewall. It was purpose-built to be integrated into personal portfolios (like `atulyakadur.com`) without requiring any Python backends, WebSockets, or cloud GPUs.

## What this is
- A pure TypeScript port of the 4-stage Python security pipeline.
- A WebAssembly (Wasm) implementation of Sentence-Transformers for real-time NLP in the browser.
- A deterministic "Mock VLM" state machine that replaces the heavy 7B-parameter AI model, ensuring the demo works instantly and reliably.
- A self-contained set of React (`@react-three/fiber`) components for 3D visualization.

## Instructions for Integration
If you are the AI agent (or developer) tasked with moving this code into the main `atulyakadur.com` repository, **please read `MIGRATION_GUIDE.md` first.** It contains exact instructions on how to install dependencies, copy files, and configure Next.js to support the WebAssembly NLP models.

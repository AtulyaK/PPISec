# Migration Guide: Integrating PPISec into atulyakadur.com

Hello, fellow AI Agent (or developer). Your objective is to seamlessly integrate this `portfolio_module` into the main `atulyakadur.com` Next.js/React repository. This guide provides exact, step-by-step instructions to ensure nothing breaks during the transition.

## Step 1: Install Dependencies
The target repository must have these packages installed. Run this in the root of `atulyakadur.com`:

```bash
npm install three @react-three/fiber @react-three/drei framer-motion lucide-react zustand @xenova/transformers
```

## Step 2: Next.js Configuration (CRITICAL)
Because Stage 3 of the firewall uses `@xenova/transformers` to run a 20MB NLP model in the browser via WebAssembly, you MUST update the target repository's `next.config.js` to ignore Node.js specific modules. Add the following:

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  // Override webpack config to allow transformers.js to run in the browser
  webpack: (config) => {
    config.resolve.alias = {
      ...config.resolve.alias,
      "sharp$": false,
      "onnxruntime-node$": false,
    }
    return config;
  },
}
module.exports = nextConfig
```

## Step 3: Copying the Source Files
Copy the entire `src/` directory from this module into the target repository. You may place it in a subdirectory like `src/components/PPISecDemo/` or merge it into the existing `src/`.
- `src/brain/` -> The Mock VLM and the Agent Loop React Hook.
- `src/components/` -> The React/Three.js UI.
- `src/data/` -> The Policy definitions and Scenarios.
- `src/firewall/` -> The pure TypeScript 4-stage validation engine.
- `src/store/` -> The Zustand state manager.

## Step 4: Copying Public Assets
Copy any files from `portfolio_module/public/assets/` to the target repository's `public/` directory so the Next.js `Image` tags and Three.js loaders can find the textures.

## Step 5: Mounting the Component
The entry point for the demo is `src/components/PPISecDashboard.tsx` (or whatever the root component is named). Import and mount it on a page in the portfolio:

```tsx
import PPISecDashboard from '@/components/PPISecDemo/components/PPISecDashboard';

export default function PortfolioPage() {
  return (
    <div className="w-full h-screen">
      <PPISecDashboard />
    </div>
  );
}
```

## Architecture Notes for the Migrating Agent
- **No API Routes Required:** There are no `fetch` calls to backend servers. Everything runs in the browser.
- **Web Worker:** `Stage3Audio.ts` instantiates a Web Worker to run the NLP model. Ensure the build tool (Webpack/Turbopack) in the target repo handles standard Web Worker syntax (`new Worker(new URL(..., import.meta.url))`).
- **Zustand Store:** The `useDemoStore.ts` handles all cross-component state. It is self-contained.

#!/usr/bin/env python3
"""
PPISec Unified Startup CLI
Interactive wizard to launch the entire Semantic Firewall stack.
"""

import os
import subprocess
import sys
import time
import signal
import json

# ─── Constants ────────────────────────────────────────────────────────────────
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
FIREWALL_DIR = os.path.join(ROOT_DIR, "firewall_governor")
BRAIN_DIR = os.path.join(ROOT_DIR, "brain_cloud")
UI_DIR = os.path.join(ROOT_DIR, "agent_glass")
LLAMA_SERVER = os.path.join(ROOT_DIR, "llama.cpp", "build", "bin", "llama-server")

# ─── UI Helpers ───────────────────────────────────────────────────────────────
def clear(): os.system('cls' if os.name == 'nt' else 'clear')

def banner():
    print("\033[95m" + "┌──────────────────────────────────────────────────────────┐")
    print("│             PPISec: Semantic Firewall Setup              │")
    print("└──────────────────────────────────────────────────────────┘" + "\033[0m")

def get_ollama_models():
    try:
        output = subprocess.check_output(["ollama", "list"], stderr=subprocess.STDOUT).decode()
        lines = output.strip().split('\n')[1:] # Skip header
        return [line.split()[0] for line in lines if line.strip()]
    except:
        return []

# ─── Process Management ───────────────────────────────────────────────────────
processes = []

def cleanup(sig, frame):
    print("\n\n\033[93m[System] Shutting down all components...\033[0m")
    for p in processes:
        try:
            p.terminate()
        except:
            pass
    print("[System] Done. Cleanup complete.")
    sys.exit(0)

signal.signal(signal.SIGINT, cleanup)

# ─── Wizard ───────────────────────────────────────────────────────────────────
def main():
    clear()
    banner()

    # 1. Environment Selection
    print("\n\033[1m[1/4] Select Execution Environment:\033[0m")
    print("  1) \033[92mMock Mode\033[0m      - Zero AI dependencies. Best for rapid UI/Logic dev.")
    print("  2) \033[94mLocal AI (Ollama)\033[0m - Easiest setup. Requires Ollama app.")
    
    llama_cpp_ready = os.path.exists(LLAMA_SERVER)
    if llama_cpp_ready:
        print("  3) \033[95mLocal AI (llama.cpp)\033[0m - \033[1mHighest Efficiency\033[0m. Best for M-series.")
    else:
        print("  3) \033[90mLocal AI (llama.cpp)\033[0m - (Not setup. Run scripts/setup_llamacpp.sh first)")

    print("  4) \033[96mCloud AI\033[0m       - Points to a remote vLLM or OpenAI endpoint.")
    
    choice = input("\nSelection [1-4, default=1]: ").strip() or "1"
    
    mode = "mock"
    if choice == "2": mode = "local_ollama"
    elif choice == "3": mode = "local_llamacpp"
    elif choice == "4": mode = "cloud"

    # 2. Model Selection
    vlm_url = "http://localhost:8001/v1"
    vlm_model = "mock-vla"

    if mode == "local_ollama":
        print("\n\033[1m[2/4] Select Local AI Brain (Ollama):\033[0m")
        print("  Using \033[92mMetadata-Enriched Vision\033[0m mode.")
        models = get_ollama_models()
        if models:
            for i, m in enumerate(models, 1):
                print(f"  {i}) {m}")
            m_choice = input(f"\nSelection [1-{len(models)}]: ").strip()
            if m_choice.isdigit() and 1 <= int(m_choice) <= len(models):
                vlm_model = models[int(m_choice)-1]
        else:
            print("\033[91m      No models found.\033[0m Run 'ollama pull llama3.1' first.")
            vlm_model = "llama3.1"
        vlm_url = "http://localhost:11434/v1"

    elif mode == "local_llamacpp":
        if not os.path.exists(LLAMA_SERVER):
            print("\n\033[91m[Error] llama.cpp binary not found.\033[0m")
            print("        Please run: bash scripts/setup_llamacpp.sh")
            sys.exit(1)
        
        vlm_url = "http://localhost:8080/v1"
        vlm_model = "llama-3.1-8b-instruct.gguf"
        
        print(f"\n\033[92m[Verified]\033[0m Using \033[1mLlama-3.1 (High-Precision Metadata Mode)\033[0m")

    elif mode == "cloud":
        print("\n\033[1m[2/4] Configure Cloud VLM:\033[0m")
        vlm_url = input("  VLM Endpoint URL [default=http://localhost:8001/v1]: ").strip() or "http://localhost:8001/v1"
        vlm_model = input("  Model ID [default=Qwen/Qwen2-VL-7B-Instruct]: ").strip() or "Qwen/Qwen2-VL-7B-Instruct"

    # 3. Features
    print("\n\033[1m[3/4] Feature Configuration:\033[0m")
    use_ui = input("  Enable 3D Dashboard UI? [Y/n]: ").lower() != 'n'
    use_audio = input("  Enable Stage 3 Audio Alignment? (Requires sentence-transformers) [y/N]: ").lower() == 'y'
    fast_sim = input("  Enable Fast Simulation? (Bypass movement delays for testing) [y/N]: ").lower() == 'y'

    # 4. Summary
    print("\n\033[1m[4/4] Setup Ready:\033[0m")
    print(f"  - Mode:    \033[95m{mode.upper()}\033[0m")
    print(f"  - Model:   \033[95m{vlm_model}\033[0m")
    print(f"  - URL:     \033[95m{vlm_url}\033[0m")
    print(f"  - UI:      {'Enabled' if use_ui else 'Disabled'}")
    print(f"  - Speed:   {'FAST (Direct)' if fast_sim else 'Normal (Simulated)'}")

    confirm = input("\n🚀 Launch System? [Y/n]: ").lower()
    if confirm == 'n':
        print("Aborted.")
        return

    # ─── Execution ───
    env = os.environ.copy()
    env["VLLM_URL"] = vlm_url
    env["VLLM_MODEL"] = vlm_model
    env["PYOPENGL_PLATFORM"] = "osmesa"
    env["ALLOW_ORIGINS"] = "*"
    if fast_sim:
        env["FAST_SIM"] = "true"
    
    if not use_audio: env["DISABLE_STAGE_3"] = "true"

    print("\n\033[94m[System] Launching components...\033[0m")

    # A. Firewall
    print("  [1] Starting Firewall Governor (Port 8000)...")
    firewall_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"],
        cwd=FIREWALL_DIR, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT
    )
    processes.append(firewall_proc)

    # B. VLM Server
    if mode == "mock":
        print("  [2] Starting Mock VLM Server (Port 8001)...")
        mock_proc = subprocess.Popen(
            [sys.executable, "mock_environment/mock_vlm.py"],
            cwd=ROOT_DIR, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT
        )
        processes.append(mock_proc)
    elif mode == "local_llamacpp":
        print("  [2] Starting llama.cpp Server (Port 8080)...")
        model_path = os.path.join(ROOT_DIR, "models", vlm_model)
        cmd = [LLAMA_SERVER, "-m", model_path, "--port", "8080", "--n-gpu-layers", "99"]
        
        # Add multimodal projector if using vision mode
        if 'mmproj' in locals() and mmproj:
            mm_path = os.path.join(ROOT_DIR, "models", mmproj)
            cmd.extend(["--mmproj", mm_path])
            
        llama_proc = subprocess.Popen(
            cmd, cwd=ROOT_DIR, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT
        )
        processes.append(llama_proc)
    else:
        print("  [2] Skipping VLM backend launch (assuming external server is active)...")

    # C. Brain Executor
    print("  [3] Starting Brain Orchestrator (Port 8002)...")
    brain_proc = subprocess.Popen(
        [sys.executable, "task_executor.py"],
        cwd=BRAIN_DIR, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT
    )
    processes.append(brain_proc)

    # D. UI Dashboard
    if use_ui:
        print("  [4] Starting Agent Glass Dashboard (Port 3000)...")
        ui_env = env.copy()
        ui_env["NEXT_PUBLIC_BRAIN_URL"] = "http://localhost:8002"
        try:
            ui_proc = subprocess.Popen(
                ["npm", "run", "dev"],
                cwd=UI_DIR, env=ui_env, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT
            )
            processes.append(ui_proc)
        except:
            print("\033[91m      Error: 'npm' not found. Dashboard failed to start.\033[0m")

    print("\n\033[92m✨ PPISec is LIVE.\033[0m")
    print("   - Dashboard: http://localhost:3000")
    print("   - Firewall:  http://localhost:8000")
    print("   - Brain:     http://localhost:8002")
    print("\nPress \033[1mCtrl+C\033[0m to terminate the session.")

    while True:
        if firewall_proc.poll() is not None: break
        if brain_proc.poll() is not None: break
        time.sleep(2)

if __name__ == "__main__":
    main()

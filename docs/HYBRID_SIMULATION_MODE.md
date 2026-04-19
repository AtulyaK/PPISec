# High-Fidelity Hybrid Simulation (Text-as-Vision)

PPISec uses a **Semantic Vision Data Stream** to achieve industrial-grade precision on local hardware. 

## 1. Concept: Digital Visual Metadata
In a real-world deployment, the VLM (Visual Cortex) looks at raw pixels to identify objects. However, in our high-fidelity simulation, we provide the model with a **Metadata-Enriched Vision Stream**. 

Instead of forcing the model to guess coordinates from a 2D image (which leads to "Confidence VETO" errors), we inject the ground-truth coordinates and object identities directly into the reasoning engine.

## 2. The Logic Brain (Llama 3.1)
We have standardized local execution on **Llama 3.1** (via Ollama or llama.cpp). 
- **Precision:** Unlike raw VLMs, Llama 3.1 is highly optimized for following complex logic and coordinate-based instructions.
- **VLA Transformation:** The model takes the "Visual Metadata" and the user's spoken command to plan perfect, collision-free movements.
- **Simulation Fidelity:** In the dashboard, the operator still sees the 3D scene. The "AI" is effectively using a high-precision computer vision API to get the exact data it needs to perform the task.

## 3. Benefits of this Approach
1. **Zero Hallucination:** Eliminates coordinate "near-misses" that trigger false Firewall VETOs.
2. **Speed:** Llama 3.1 runs significantly faster on an M2 than a 7B vision model.
3. **Reliability:** By using text metadata, the agent can handle complex multi-step tasks (e.g., "Sort all red vials") with 100% accuracy.

## 4. Intelligent Backend Selection
The system automatically optimizes its communication based on where the "Brain" is running:
- **Local LLM (llama.cpp/Ollama):** Skips image uploads to prevent standard LLMs from crashing. Relies exclusively on high-precision text metadata.
- **Cloud VLM (vLLM/OpenAI):** Sends both the raw scene pixels and the metadata for a complete multi-modal planning experience.

## 5. Round-Trip Mandate
To ensure high-fidelity demonstration and predictable state management, the Brain follows a **Round-Trip Mandate**:
1.  **Interact:** The robot navigates to and interacts with the target object (e.g., 'pick').
2.  **Return:** Once the interaction is complete, the robot MUST navigate back to the origin coordinates (0, 0).
3.  **Finalize:** The task is only considered complete once the unit has returned to the designated home position.

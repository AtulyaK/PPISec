from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.post("/v1/chat/completions")
async def chat():
    # This mock always returns a safe 'pick' action
    return {
        "choices": [{
            "message": {
                "content": '{"action": "pick", "target": "bottle", "coordinates": {"x": 0.2, "y": 0.2, "z": 0.1}, "confidence": 0.95, "source_modality": "voice_command", "reasoning_trace": "Mock VLM proposing a safe pick action.", "task_complete": false}'
            }
        }]
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)

import os
import json
import base64
import requests

class GeminiCloudVLA:
    """
    Direct interface to Google's Gemini API for VLA intention generation.
    Supports the Gemini Hackathon Track by replacing local vLLM with high-end Gemini 1.5 Pro models.
    """
    def __init__(self, api_key=None, model="gemini-1.5-pro-latest"):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required to use the Gemini Cloud backend.")
        
        self.model = model
        self.endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

    def get_intent(self, prompt, image_path=None):
        """
        Sends the scene image and command prompt to Gemini and expects a strict JSON Intent Packet representing the VLA plan.
        """
        contents = []
        
        if image_path and os.path.exists(image_path):
            with open(image_path, "rb") as f:
                img_data = base64.b64encode(f.read()).decode('utf-8')
            
            contents.append({
                "inline_data": {
                    # Simple extension detection
                    "mime_type": "image/png" if image_path.endswith('.png') else "image/jpeg",
                    "data": img_data
                }
            })
            
        system_instructions = (
            "You are the 'Brain' of an autonomous robotic agent. "
            "You must output ONLY valid JSON representing your physical intent packet. "
            "Schema requirement: { 'intent_id': 'string', 'action': 'string', 'target_object': 'string', "
            "'coordinates': {'x': float, 'y': float, 'z': float}, 'reasoning_trace': 'string', "
            "'source_modality': 'string', 'aasl_target_level': int }"
        )
        
        contents.append({"text": system_instructions + "\n\nUser Command: " + prompt})
        
        payload = {
            "contents": [{"parts": contents}],
            "generationConfig": {
                "temperature": 0.1, # Keep temperature low for deterministic JSON outputs
            }
        }
        
        print(f"📡 Sending VLA intent inference task to Gemini Cloud ({self.model})...")
        response = requests.post(self.endpoint, json=payload)
        
        if response.status_code != 200:
            print(f"❌ Gemini Error: {response.text}")
            response.raise_for_status()
            
        try:
            result = response.json()
            text_response = result['candidates'][0]['content']['parts'][0]['text']
            
            # Clean up markdown code blocks if Gemini added them around the JSON
            if "```json" in text_response:
                text_response = text_response.split("```json")[1].split("```")[0].strip()
            elif "```" in text_response:
                text_response = text_response.split("```")[1].split("```")[0].strip()
                
            return json.loads(text_response)
        except Exception as e:
            print(f"❌ Failed to parse Gemini response into Intent Packet format: {e}")
            print(f"Raw Output: {text_response if 'text_response' in locals() else response.text}")
            return None

# Simple debug block for direct testing
if __name__ == "__main__":
    if "GEMINI_API_KEY" not in os.environ:
        print("⚠️ Please export GEMINI_API_KEY=your_key to test this script.")
    else:
        gemini = GeminiCloudVLA()
        print("Testing pure text prompt inference (Visual capability disabled for debug run)...")
        intent = gemini.get_intent("Navigate to the blue medical crate and open it.")
        print("\n✅ Received Valid Intent Packet from Gemini:")
        print(json.dumps(intent, indent=2))

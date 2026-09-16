import asyncio
import re
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import edge_tts
from google import genai
from config.settings import get_settings

# Two free voices from edge-tts
HOST_VOICE = "en-US-ChristopherNeural"
EXPERT_VOICE = "en-US-AriaNeural"

SYSTEM_PROMPT = """You are an expert podcast scriptwriter.
Based on the provided context, write a short, engaging 2-speaker podcast script (under 2 minutes spoken) discussing the topic.
The speakers are:
- HOST: Asks questions, provides transitions, and is enthusiastic.
- EXPERT: Provides the factual answers and insights based ONLY on the context.

FORMAT STRICTLY LIKE THIS:
HOST: Hello everyone...
EXPERT: That's right, Host...

Do not include any other text, no intro, no outro, just the dialogue lines starting with "HOST:" or "EXPERT:".
"""

class AudioOverviewGenerator:
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.gemini_api_key
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured.")
        self.client = genai.Client(api_key=self.api_key)

    def generate_script(self, topic: str, context_text: str) -> str:
        prompt = f"TOPIC: {topic}\n\nCONTEXT:\n{context_text}\n\nSCRIPT:\n"
        response = self.client.models.generate_content(
            model="gemini-3.6-flash",
            contents=f"{SYSTEM_PROMPT}\n\n{prompt}"
        )
        return response.text if response and response.text else ""

    async def generate_audio_chunks(self, script: str, output_dir: str):
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        lines = script.split('\n')
        chunk_files = []
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
                
            if line.startswith("HOST:"):
                text = line.replace("HOST:", "").strip()
                voice = HOST_VOICE
            elif line.startswith("EXPERT:"):
                text = line.replace("EXPERT:", "").strip()
                voice = EXPERT_VOICE
            else:
                # Fallback to host if format is slightly off
                text = line
                voice = HOST_VOICE
                
            if text:
                file_path = os.path.join(output_dir, f"chunk_{i:03d}.mp3")
                communicate = edge_tts.Communicate(text, voice)
                await communicate.save(file_path)
                chunk_files.append(file_path)
                
        return chunk_files

async def main(topic, context, output_dir):
    generator = AudioOverviewGenerator()
    print("Generating script...")
    script = generator.generate_script(topic, context)
    print("Script generated:")
    print(script)
    print("\nGenerating audio chunks...")
    chunks = await generator.generate_audio_chunks(script, output_dir)
    print(f"Generated {len(chunks)} audio chunks in {output_dir}")
    
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", type=str, default="GraphRAG")
    parser.add_argument("--context", type=str, default="GraphRAG combines vector search with Neo4j knowledge graphs.")
    parser.add_argument("--out", type=str, default="data/audio_out")
    args = parser.parse_args()
    asyncio.run(main(args.topic, args.context, args.out))

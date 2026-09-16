"""
Ollama Small Language Model (SLM) Generator.

Uses the local Ollama API to generate answers, replacing the Hugging Face Transformers LocalSLM.
This is significantly more memory-efficient and faster for local generation.
"""

from typing import List, Dict, Any, Optional
import re
import json
import requests

class OllamaSLM:
    """
    Generates answers using a local Ollama server.
    Drop-in replacement for LocalSLM / AnswerGenerator.
    Supports per-notebook custom models trained via OllamaTrainer.
    """

    DEFAULT_MODEL = "qwen2.5:0.5b" # Or qwen2.5, llama3.1, etc.

    def __init__(self, model_id: Optional[str] = None, host: str = "http://localhost:11434", notebook_id: Optional[str] = None):
        self.host = host.rstrip("/")
        self.notebook_id = notebook_id

        if model_id:
            self.model_id = model_id
        elif notebook_id:
            # Try to use the per-notebook trained model
            custom_model = self._check_custom_model(notebook_id)
            self.model_id = custom_model if custom_model else self.DEFAULT_MODEL
            if custom_model:
                print(f"[OllamaSLM] Using trained model '{custom_model}' for notebook '{notebook_id}'")
            else:
                print(f"[OllamaSLM] No trained model for notebook '{notebook_id}', using default '{self.DEFAULT_MODEL}'")
        else:
            self.model_id = self.DEFAULT_MODEL

        print(f"[OllamaSLM] Initialized for model: {self.model_id} on {self.host}")

    def _check_custom_model(self, notebook_id: str) -> Optional[str]:
        """Check if a per-notebook custom model exists in Ollama."""
        model_name = f"graphrag-{notebook_id}"
        try:
            response = requests.get(f"{self.host}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                for m in models:
                    if m.get("name", "").startswith(model_name):
                        return model_name
        except Exception:
            pass
        return None

    def generate(
        self,
        query: str,
        context_chunks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Standard Q&A generation."""
        if not context_chunks:
            return self._empty_context_response("chat")

        from generation.generator import build_generation_prompt
        prompt, sources = build_generation_prompt(query, context_chunks)
        return self._run_inference(prompt, sources, "chat")

    def generate_teach(
        self,
        query: str,
        context_chunks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Tutor-style generation."""
        if not context_chunks:
            return self._empty_context_response("teach")

        from generation.generator import build_teaching_prompt
        prompt, sources = build_teaching_prompt(query, context_chunks)
        return self._run_inference(prompt, sources, "teach")

    def generate_quiz(
        self,
        context_chunks: List[Dict[str, Any]],
        topic: str = "",
    ) -> Dict[str, Any]:
        """Generates a JSON MCQ quiz."""
        if not context_chunks:
            return {"error": "No documents available to generate a quiz from."}

        from generation.generator import build_quiz_prompt
        prompt = build_quiz_prompt(context_chunks, topic)
        
        try:
            # For quiz, we want a more deterministic output
            messages = [
                {"role": "system", "content": "You are a quiz generator. Output ONLY raw valid JSON without markdown formatting."},
                {"role": "user", "content": prompt}
            ]
            response_text = self._chat_complete(messages, temperature=0.1)
            
            raw = re.sub(r"^```(?:json)?\s*", "", response_text.strip())
            raw = re.sub(r"\s*```$", "", raw.strip())
            return json.loads(raw)
        except json.JSONDecodeError as e:
            return {"error": f"Quiz generation failed (JSON parse error): {e}\nOutput was: {response_text[:100]}..."}
        except Exception as e:
            return {"error": f"Quiz generation failed: {e}"}

    def _run_inference(self, prompt: str, sources: List[Dict], mode: str) -> Dict[str, Any]:
        """Helper to run inference and parse citations."""
        messages = [
            {"role": "system", "content": "You are a helpful, accurate research assistant. Follow the prompt instructions precisely."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            answer_text = self._chat_complete(messages)
        except Exception as e:
            return {
                "answer_text": f"Error: Local Ollama model failed ({e})",
                "citations": [],
                "sources": [],
                "is_insufficient": True,
                "mode_used": mode,
            }
        
        is_insufficient = answer_text.startswith("INSUFFICIENT_CONTEXT")
        cited_numbers = set(int(n) for n in re.findall(r"\[(\d+)\]", answer_text))
        citations = [s for s in sources if s["citation_number"] in cited_numbers]

        return {
            "answer_text": f"> 🤖 **[LOCAL OLLAMA]**\n\n{answer_text}",
            "citations": citations,
            "sources": sources,
            "is_insufficient": is_insufficient,
            "mode_used": mode,
        }

    def _chat_complete(self, messages: List[Dict[str, str]], temperature: float = 0.3) -> str:
        """Executes the request to the local Ollama API."""
        url = f"{self.host}/api/chat"
        payload = {
            "model": self.model_id,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": 1024,
            }
        }
        
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()
        
        data = response.json()
        if "message" in data and "content" in data["message"]:
            return data["message"]["content"].strip()
        else:
            raise ValueError(f"Unexpected response format from Ollama: {data}")

    def _empty_context_response(self, mode: str) -> Dict[str, Any]:
        return {
            "answer_text": "No context available to answer this question.",
            "citations": [],
            "sources": [],
            "is_insufficient": True,
            "mode_used": mode,
        }

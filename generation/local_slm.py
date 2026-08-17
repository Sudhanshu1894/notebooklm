"""
Local Small Language Model (SLM) Generator.

Uses Hugging Face `transformers` to load a lightweight model (e.g., Qwen2.5-0.5B-Instruct)
for local inference, completely replacing the old TF-IDF fallback.
"""

from typing import List, Dict, Any, Optional
import re
import json

try:
    from transformers import pipeline, AutoModelForCausalLM, AutoTokenizer
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False


class LocalSLM:
    """
    Generates answers using a local SLM via Hugging Face Transformers.
    Drop-in replacement for AnswerGenerator / LocalMiniModel.
    """

    # Default to Qwen2.5-0.5B-Instruct which is extremely capable and lightweight
    DEFAULT_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"

    def __init__(self, model_id: Optional[str] = None, adapter_path: Optional[str] = None):
        if not TRANSFORMERS_AVAILABLE:
            raise RuntimeError(
                "Transformers library is not installed. "
                "Please run: pip install torch transformers accelerate"
            )

        self.model_id = model_id or self.DEFAULT_MODEL
        print(f"[LocalSLM] Loading model: {self.model_id}")
        
        # We load with bfloat16 if supported, otherwise float16, and use device_map="auto"
        # for automatic GPU/CPU placement.
        dtype = torch.bfloat16 if torch.cuda.is_available() and torch.cuda.is_bf16_supported() else torch.float16
        
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_id)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_id,
            torch_dtype=dtype,
            device_map="auto",
        )

        if adapter_path:
            print(f"[LocalSLM] Loading fine-tuned adapter from: {adapter_path}")
            self.model.load_adapter(adapter_path)

        self.pipeline = pipeline(
            "text-generation",
            model=self.model,
            tokenizer=self.tokenizer,
            max_new_tokens=1024,
            do_sample=True,
            temperature=0.3,
            top_p=0.9,
        )

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
                {"role": "system", "content": "You are a quiz generator. Output ONLY raw valid JSON."},
                {"role": "user", "content": prompt}
            ]
            response_text = self._chat_complete(messages, max_new_tokens=1500, temperature=0.1)
            
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
        
        answer_text = self._chat_complete(messages)
        
        is_insufficient = answer_text.startswith("INSUFFICIENT_CONTEXT")
        cited_numbers = set(int(n) for n in re.findall(r"\[(\d+)\]", answer_text))
        citations = [s for s in sources if s["citation_number"] in cited_numbers]

        return {
            "answer_text": f"> 🤖 **[LOCAL AI]**\n\n{answer_text}",
            "citations": citations,
            "sources": sources,
            "is_insufficient": is_insufficient,
            "mode_used": mode,
        }

    def _chat_complete(self, messages: List[Dict[str, str]], max_new_tokens: int = 1024, temperature: float = 0.3) -> str:
        """Executes the pipeline with the model's chat template."""
        prompt = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        
        outputs = self.pipeline(
            prompt,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            do_sample=True,
            return_full_text=False
        )
        return outputs[0]["generated_text"].strip()

    def _empty_context_response(self, mode: str) -> Dict[str, Any]:
        return {
            "answer_text": "No context available to answer this question.",
            "citations": [],
            "sources": [],
            "is_insufficient": True,
            "mode_used": mode,
        }

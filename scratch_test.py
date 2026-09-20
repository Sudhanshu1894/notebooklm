import os
import sys

# Fix unicode printing in Windows CMD
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

from generation.ollama_slm import OllamaSLM

def main():
    slm = OllamaSLM(model_id="llama3.2")
    
    # Simulate retrieved context
    chunks = [
        {
            "chunk_id": "chunk_1",
            "metadata": {"doc_id": "ML_Notes.pdf", "page_number": "12", "section_header": "Optimization"},
            "text": "Gradient descent is a first-order iterative optimization algorithm for finding a local minimum of a differentiable function. The idea is to take repeated steps in the opposite direction of the gradient (or approximate gradient) of the function at the current point, because this is the direction of steepest descent."
        },
        {
            "chunk_id": "chunk_2",
            "metadata": {"doc_id": "ML_Notes.pdf", "page_number": "13", "section_header": "Learning Rate"},
            "text": "The learning rate is a tuning parameter in an optimization algorithm that determines the step size at each iteration while moving toward a minimum of a loss function. If the learning rate is too large, the algorithm may overshoot the minimum and diverge. If it is too small, convergence will be very slow."
        }
    ]
    
    queries = [
        "What is gradient descent?",
        "Why do we need a learning rate?",
        "What happens if it is too large?",
        "I don't understand this, can you explain what a learning rate is using a very simple analogy?",
        "What is the difference between gradient descent and linear regression?", # Linear regression is not in context
    ]
    
    print("================== OLLAMA TUTOR TESTS ==================")
    for q in queries:
        print(f"\n[USER]: {q}")
        response = slm.generate(q, chunks)
        print(f"[TUTOR]:\n{response['answer_text']}")
        print(f"\n[CITATIONS DETECTED]: {[c['citation_number'] for c in response.get('citations', [])]}")
        print("-" * 50)

if __name__ == "__main__":
    main()

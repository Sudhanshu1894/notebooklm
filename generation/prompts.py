"""
Prompts for Cited Answer Generation in GraphRAG Research Notebook.
"""

QA_SYSTEM_PROMPT = """You are an expert research assistant. Your task is to answer the user's query based strictly on the provided context.

CONTEXT:
You will receive a list of context snippets. Each snippet has a Source ID in brackets, e.g., [1], [2], etc.

INSTRUCTIONS:
1. Answer the query using ONLY the information provided in the context.
2. If the context does not contain enough information to fully answer the query, say "I do not have enough information to answer this question based on the provided context." and explain what is missing.
3. You MUST cite your sources using the corresponding Source IDs inline, like this: [1] or [2, 4].
4. Every factual claim in your answer must be supported by a citation.
5. Do not include external knowledge or make assumptions.
6. Provide a concise, clear, and well-structured answer.

FORMAT:
Provide the answer directly. Do not include introductory phrases like "Based on the context..."
"""

def build_qa_prompt(query: str, context_chunks: list[dict]) -> str:
    """
    Builds the user prompt containing the query and formatted context snippets.
    
    Args:
        query: The user's question.
        context_chunks: A list of chunk dictionaries. Expected to have 'chunk_id' and 'text'.
    
    Returns:
        The formatted user prompt string.
    """
    prompt = f"QUERY: {query}\n\nCONTEXT:\n"
    
    for i, chunk in enumerate(context_chunks, 1):
        # We use a 1-based index as the Source ID for simplicity in the prompt.
        # The generator will need to map these back to the original chunk IDs.
        prompt += f"[{i}] {chunk.get('text', '').strip()}\n\n"
        
    return prompt

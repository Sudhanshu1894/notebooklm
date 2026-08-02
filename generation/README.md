# Generation Module (`generation/`)

## Intended Role
Manages LLM interaction via Gemini 2.5/3 Flash API (Free Tier) to generate grounded answers using retrieved hybrid context.

## Key Responsibilities (DA2 Pipeline)
- Formatting prompt templates with question, vector context, and graph entity paths.
- Calling Gemini Flash API (via `google-genai` / `langchain-google-genai`).
- Answer parsing, citation formatting, and confidence scoring.

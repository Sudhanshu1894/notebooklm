import os
from google import genai
from google.genai import types

def test():
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    
    # Test Google Search Grounding
    print("Testing Google Search...")
    try:
        response = client.models.generate_content(
            model="gemini-1.5-flash", 
            contents="Who won the super bowl in 2024?",
            config=types.GenerateContentConfig(
                tools=[{"google_search": {}}]
            )
        )
        print("Response:", response.text)
        if getattr(response, "candidates", None) and response.candidates[0].grounding_metadata:
            print("Grounding Meta:", response.candidates[0].grounding_metadata)
    except Exception as e:
        print("Error:", e)
    
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    test()

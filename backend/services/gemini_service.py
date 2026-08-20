import os
import google.generativeai as genai

def render_sprint_tickets(ranked_prescriptions: list) -> list:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set.")

    # Configure the client with your key
    genai.configure(api_key=api_key)
    
    # UPDATE: Swapped deprecated 2.5 for the new Gemini 3.6 Flash model
    model = genai.GenerativeModel('gemini-3.6-flash')

    for item in ranked_prescriptions:
        prompt = f"Convert this cloud cost optimization prescription into a concise Jira sprint ticket format:\n{item}"
        try:
            response = model.generate_content(prompt)
            item['sprint_ticket'] = response.text
        except Exception as e:
            print(f"Gemini API fallback triggered for {item.get('service_name')}: {e}")
            item['sprint_ticket'] = f"Execute action: {item['recommended_action']}"
            
    return ranked_prescriptions
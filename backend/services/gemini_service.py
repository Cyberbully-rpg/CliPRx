"""
Gemini Prescription Renderer
Translates structured JSON prescriptions into plain-language DevOps sprint tickets.
"""
import os
import google.generativeai as genai

# In-memory cache to prevent redundant API calls and rate limiting
_ticket_cache = {}

def init_gemini():
    """Initializes the Gemini SDK with the API key from the environment."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set.")
    genai.configure(api_key=api_key)

def render_sprint_tickets(prescriptions: list[dict]) -> list[dict]:
    """
    Iterates through ranked prescriptions and uses Gemini 2.0 Flash to generate 
    human-readable, Jira-style sprint tickets.
    """
    try:
        init_gemini()
        # Initialize the specific model defined in the TRD
        model = genai.GenerativeModel('gemini-2.0-flash')

        for p in prescriptions:
            # Skip API generation if the item is conflicted (ROI = 0)
            if p.get('is_conflicted', False):
                p['sprint_ticket'] = "Generation skipped: Service flagged as conflicted."
                continue

            # Generate a unique cache key based on the specific context
            cache_key = f"{p['pattern_id']}_{p['service_name']}_{p['cost_usd']}"
            if cache_key in _ticket_cache:
                p['sprint_ticket'] = _ticket_cache[cache_key]
                continue

            # Construct the prompt using the calculated ROI and risk data
            prompt = f"""
            You are a Senior Cloud DevOps Engineer. Write a concise, professional sprint ticket to optimize a cloud service.
            
            Context:
            - Service: {p['service_name']}
            - Recommended Action: {p['recommended_action']}
            - Estimated Monthly Savings: ${p.get('savings_min', 0)} - ${p.get('savings_max', 0)}
            - Estimated Engineering Hours: {p.get('engineering_hours_min', 0)} - {p.get('engineering_hours_max', 0)}
            - Downtime Risk: {p.get('risk_level', 'High')}
            
            Output strictly a short, actionable Jira-style description (max 3 sentences). 
            Do not use formatting like markdown bolding or bullet points. Just output the plain text description.
            """

            try:
                response = model.generate_content(prompt)
                ticket_text = response.text.strip()
                p['sprint_ticket'] = ticket_text
                
                # Store the successful generation in the cache
                _ticket_cache[cache_key] = ticket_text
                
            except Exception as e:
                # Failsafe: If the API limits out or crashes, fall back to the raw JSON string
                p['sprint_ticket'] = f"Execute action: {p['recommended_action']}"
                print(f"Gemini API fallback triggered for {p['service_name']}: {str(e)}")

        return prescriptions

    except Exception as e:
        raise RuntimeError(f"Gemini rendering service failed: {str(e)}")
import asyncio
import os
import google.generativeai as genai

# Renders one prescription at a time via a fully sequential, blocking loop
# used to be the entire pipeline's actual bottleneck on large datasets: N
# prescriptions meant N blocking network round-trips before the request could
# return, and since this ran unawaited inside async FastAPI route handlers it
# also stalled the whole event loop for every other concurrent request.
# generate_content_async + a bounded semaphore fixes both: calls run
# concurrently (default 5 in flight), and being a real coroutine lets the
# event loop serve other requests while this awaits.
GEMINI_MAX_CONCURRENCY = int(os.getenv("GEMINI_MAX_CONCURRENCY", 5))
GEMINI_REQUEST_TIMEOUT_SECONDS = float(os.getenv("GEMINI_REQUEST_TIMEOUT_SECONDS", 30))
# 0 = render every prescription (default, matches prior behavior). Prescriptions
# are already ROI-ranked before this runs, so capping to the top K is a safety
# valve for pathologically large match counts: highest-value items still get a
# real LLM ticket, the rest get the same plain-text fallback used on failure.
GEMINI_TOP_K = int(os.getenv("GEMINI_TOP_K", 0))


async def render_sprint_tickets(ranked_prescriptions: list) -> list:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set.")

    # Configure the client with your key
    genai.configure(api_key=api_key)

    # UPDATE: Swapped deprecated 2.5 for the new Gemini 3.6 Flash model
    model = genai.GenerativeModel('gemini-3.6-flash')
    semaphore = asyncio.Semaphore(GEMINI_MAX_CONCURRENCY)

    async def render_one(item: dict) -> None:
        prompt = f"Convert this cloud cost optimization prescription into a concise Jira sprint ticket format:\n{item}"
        async with semaphore:
            try:
                response = await asyncio.wait_for(
                    model.generate_content_async(prompt),
                    timeout=GEMINI_REQUEST_TIMEOUT_SECONDS,
                )
                item['sprint_ticket'] = response.text
            except Exception as e:
                print(f"Gemini API fallback triggered for {item.get('service_name')}: {e}")
                item['sprint_ticket'] = f"Execute action: {item['recommended_action']}"

    to_render = ranked_prescriptions
    if GEMINI_TOP_K > 0:
        to_render = ranked_prescriptions[:GEMINI_TOP_K]
        for item in ranked_prescriptions[GEMINI_TOP_K:]:
            item['sprint_ticket'] = f"Execute action: {item['recommended_action']}"

    await asyncio.gather(*(render_one(item) for item in to_render))

    return ranked_prescriptions

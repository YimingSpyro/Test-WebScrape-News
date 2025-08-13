# src/llm_client.py
import os
import time
import json
from tqdm import tqdm

from google import genai

KEY_ENV_VARS = ["GEMINI_API_KEY", "GOOGLE_API_KEY", "GENAI_API_KEY"]

def _get_api_key():
    for name in KEY_ENV_VARS:
        val = os.getenv(name)
        if val:
            return val, name
    return None, None

def _init_client():
    api_key, which = _get_api_key()
    if not api_key:
        raise RuntimeError(
            "Missing Google Generative AI API key. Set one of the environment variables: "
            f"{', '.join(KEY_ENV_VARS)}. Example (PowerShell): setx GEMINI_API_KEY \"ya29.YOUR_KEY\""
        )
    try:
        # Create the genai client by explicitly passing the key
        client = genai.Client(api_key=api_key)
    except Exception as e:
        raise RuntimeError(f"Failed to initialize genai.Client with the provided key ({which}). Error: {e}")
    return client

def _extract_text_from_response(resp):
    """
    Try common response shapes to extract text safely.
    Fallback to str(resp).
    """
    # 1) common attribute in some SDKs
    if hasattr(resp, "output_text") and resp.output_text:
        return resp.output_text
    # 2) nested structure: resp.output[0].content[0].text
    try:
        out = getattr(resp, "output", None)
        if out:
            # resp.output is often a list of items with .content
            first = out[0]
            content = getattr(first, "content", None) or first.get("content", None)
            if content:
                # content might be list of dicts or objects
                first_c = content[0]
                text = getattr(first_c, "text", None) or first_c.get("text", None)
                if text:
                    return text
    except Exception:
        pass
    # 3) resp.text attribute
    if hasattr(resp, "text") and resp.text:
        return resp.text
    # 4) try .choices like OpenAI style
    try:
        choices = getattr(resp, "choices", None)
        if choices:
            c0 = choices[0]
            txt = getattr(c0, "text", None) or c0.get("text", None)
            if txt:
                return txt
    except Exception:
        pass
    # Fallback
    return str(resp)

def _call_gemini(prompt, model="gemini-2.5-flash", max_output_tokens=256, retries=3, backoff=1.0):
    client = _init_client()
    last_err = None
    for attempt in range(retries):
        try:
            # Try the newer "responses" API if available
            if hasattr(client, "responses") and callable(getattr(client, "responses").create):
                # Many SDK versions use: client.responses.create(model=model, input=prompt, max_output_tokens=...)
                try:
                    resp = client.responses.create(model=model, input=prompt, max_output_tokens=max_output_tokens)
                except TypeError:
                    # maybe method signature doesn't accept max_output_tokens — call without it
                    resp = client.responses.create(model=model, input=prompt)
                text = _extract_text_from_response(resp)
                return text
            # Fallback: older models.generate_content interface
            elif hasattr(client, "models") and hasattr(client.models, "generate_content"):
                # some SDK versions accept 'contents' (list/str). Avoid passing unsupported kwargs.
                try:
                    resp = client.models.generate_content(model=model, contents=prompt)
                except TypeError:
                    # last-ditch: try without 'contents' as keyword
                    resp = client.models.generate_content(model, prompt)
                text = _extract_text_from_response(resp)
                return text
            # Final fallback: try client.generate_text (very old/alternate APIs)
            elif hasattr(client, "generate_text"):
                resp = client.generate_text(model=model, prompt=prompt, max_output_tokens=max_output_tokens)
                return _extract_text_from_response(resp)
            else:
                raise RuntimeError("genai client does not expose a supported generation method on this SDK version.")
        except Exception as e:
            last_err = e
            if attempt < retries - 1:
                time.sleep(backoff * (2 ** attempt))
            else:
                raise RuntimeError(f"Gemini generate call failed after {retries} attempts. Last error: {e}")
    # should not reach here
    raise RuntimeError(f"Gemini generate call failed; last error: {last_err}")

def summarize_article_with_gemini(chunks, model="gemini-2.5-flash"):
    if not isinstance(chunks, (list, tuple)) or len(chunks) == 0:
        return "", {"topic": "", "sentiment": ""}

    chunk_summaries = []
    for c in tqdm(chunks, desc="Summarizing chunks", leave=False):
        prompt = (
            "You are an expert news summarizer.\n\n"
            "Summarize the following article chunk in 1-2 concise sentences. Be factual and objective.\n\n"
            f"CHUNK:\n\"\"\"\n{c}\n\"\"\"\n\n"
            "Return ONLY the summary sentence(s)."
        )
        s = _call_gemini(prompt, model=model, max_output_tokens=180)
        chunk_summaries.append(s.strip())

    aggregate_prompt = (
        "You are an expert news summarizer and classifier.\n\n"
        "Given the following chunk-level summaries, produce:\n"
        "1) A final 3-sentence summary of the full article (concise, factual).\n"
        "2) One short topic tag (one or two words).\n"
        "3) A sentiment label: positive / neutral / negative.\n\n"
        "CHUNK SUMMARIES:\n" + "\n\n".join(f"{i+1}. {s}" for i, s in enumerate(chunk_summaries)) + "\n\n"
        "Output JSON only in the form:\n"
        '{"summary":"...","topic":"...", "sentiment":"..."}'
    )
    agg = _call_gemini(aggregate_prompt, model=model, max_output_tokens=250)

    out = {"summary": agg.strip(), "topic": "", "sentiment": ""}
    try:
        js_start = agg.find("{")
        if js_start != -1:
            js = agg[js_start:]
            parsed = json.loads(js)
            out = parsed
        else:
            out = {"summary": agg.strip(), "topic": "", "sentiment": ""}
    except Exception:
        out = {"summary": agg.strip(), "topic": "", "sentiment": ""}

    return out.get("summary", ""), {"topic": out.get("topic", ""), "sentiment": out.get("sentiment", "")}

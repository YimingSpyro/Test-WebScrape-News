import re
from bs4 import BeautifulSoup

def clean_text(raw_text_or_html: str) -> str:
    """
    Clean HTML/text and remove boilerplate.
    """
    # If it looks like HTML, strip tags
    if "<html" in raw_text_or_html.lower() or "<body" in raw_text_or_html.lower():
        soup = BeautifulSoup(raw_text_or_html, "html.parser")
        # remove script/style
        for s in soup(["script","style","noscript"]):
            s.decompose()
        text = soup.get_text(separator="\n\n")
    else:
        text = raw_text_or_html

    # Remove multiple blank lines
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    # Remove long sequences of whitespace
    text = re.sub(r"[ \t]{2,}", " ", text)
    # Remove leading/trailing
    text = text.strip()

    # Cut off very long trailing site navigation phrases (heuristic)
    endings = ["Read more", "Subscribe", "Advertisement", "Follow"]
    for e in endings:
        idx = text.rfind(e)
        if idx != -1 and idx > len(text) - 400:
            text = text[:idx]

    return text

import streamlit as st
from src.scraper import fetch_article
from src.cleaner import clean_text
from src.chunker import chunk_text
from src.llm_client import summarize_article_with_gemini
from src.cache_db import CacheDB
from dotenv import load_dotenv

st.set_page_config(page_title="News Summarizer (Gemini)", layout="wide")

cache = CacheDB("data/cache.db")

st.title("News Summarizer — Gemini demo")
st.markdown("Paste a public news article URL or choose a sample. Summaries use Google Gemini (set GEMINI_API_KEY).")

col1, col2 = st.columns([3,1])

with col1:
    url = st.text_input("Article URL", value="")
    sample = st.selectbox("Or pick a sample", ["", "https://www.reuters.com/business/","https://www.bbc.com/news"])
    if sample and not url:
        url = sample

with col2:
    model = st.selectbox("Gemini model", ["gemini-2.5-flash", "gemini-1.0", "gemini-2.5-small"])
    max_chars = st.number_input("Chunk char limit", min_value=1000, max_value=8000, value=3000, step=500)
    use_cache = st.checkbox("Use cache (24h)", value=True)

if st.button("Fetch & Summarize"):
    if not url:
        st.error("Please paste an article URL.")
    else:
        with st.spinner("Fetching article..."):
            try:
                article = fetch_article(url)
            except Exception as e:
                st.error(f"Failed to fetch: {e}")
                st.stop()

        st.subheader(article.get("title", "Untitled"))
        st.write(f"Source: {article.get('url')}")
        st.write(f"Published: {article.get('date', 'unknown')}")

        cleaned = clean_text(article.get("text",""))
        show_raw = st.checkbox("Show cleaned text", value=False)
        if show_raw:
            st.text_area("Cleaned article text", cleaned[:100000], height=400)

        # check cache
        cached = cache.get(url) if use_cache else None
        if cached:
            st.info("Using cached summary (within 24h).")
            summary_obj = cached.get("summary") or {}
            meta_obj = cached.get("meta") or {}
            st.markdown("**Summary (json)**")
            st.json(summary_obj)
            st.markdown("**Summary (text)**")
            st.write(summary_obj.get("summary", ""))
            st.markdown("**Meta (topic / sentiment)**")
            st.write(meta_obj)
        else:
            st.info("No cached summary — generating via Gemini...")
            with st.spinner("Chunking and calling Gemini (may take a few seconds)..."):
                chunks = chunk_text(cleaned, max_chars=max_chars)
                summary_obj, meta_obj = summarize_article_with_gemini(chunks, model=model)
                st.markdown("**3-sentence summary (json)**")
                st.json(summary_obj)
                st.markdown("**3-sentence summary (text)**")
                st.write(summary_obj.get("summary", ""))
                st.markdown("**Meta (topic / sentiment)**")
                st.write(meta_obj)
                # save same shapes to DB
                cache.save(url, article.get("title",""), summary_obj, meta_obj)

st.markdown("---")
st.write("Notes: respects robots.txt heuristics? This demo does not fully enforce robots.txt — do not scrape disallowed sites in production.")

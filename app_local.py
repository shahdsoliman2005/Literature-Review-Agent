import html
import re

import requests
import streamlit as st

st.set_page_config(page_title="Literature Review Agent", page_icon="📑", layout="wide")

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,600;1,6..72,400&family=Instrument+Sans:wght@400;500;600&display=swap');
:root{--paper:#EEF3EF;--sheet:#F9FBF8;--ink:#16302B;--muted:#5D7068;--rule:#C5D2CA;--mark:#F4DC4F;--plum:#7A3B5E;}
html,body,.stApp{background:var(--paper);color:var(--ink);font-family:'Instrument Sans',system-ui,sans-serif;}
#MainMenu,footer,[data-testid="stToolbar"]{visibility:hidden;}
[data-testid="stHeader"]{background:transparent;}
.block-container{max-width:1060px;padding-top:2.4rem;}
[data-testid="stSidebar"]{background:var(--sheet);border-right:1px solid var(--rule);}
.stApp h1,.stApp h2,.stApp h3{font-family:'Newsreader',Georgia,serif;font-weight:600;color:var(--ink);letter-spacing:-0.01em;}
.masthead h1{font-size:2.7rem;margin:0;padding:0;}
.masthead p{font-family:'Newsreader',Georgia,serif;font-size:1.2rem;color:var(--muted);margin:.3rem 0 1.6rem;}
.stTabs [data-baseweb="tab-list"]{gap:2.2rem;border-bottom:1px solid var(--rule);}
.stTabs [data-baseweb="tab"]{font-family:'Newsreader',Georgia,serif;font-size:1.2rem;padding:0 0 .6rem;background:none;color:var(--muted);}
.stTabs [aria-selected="true"]{color:var(--ink);}
.stTabs [data-baseweb="tab-highlight"]{background:var(--mark);height:6px;border-radius:0;}
.stTabs [data-baseweb="tab-border"]{display:none;}
.stButton>button{background:var(--ink);border:0;border-radius:2px;padding:.55rem 1.3rem;}
.stButton>button p{color:#F4F8F5;font-weight:500;}
.stButton>button:hover{background:#0D1F1B;}
.stButton>button:focus-visible{outline:3px solid var(--mark);}
[data-baseweb="input"],[data-baseweb="select"]>div{background:var(--sheet);border-radius:2px;}
[data-testid="stFileUploaderDropzone"]{background:var(--sheet);border:1px dashed var(--ink);border-radius:2px;}
.mark{background:linear-gradient(transparent 14%,var(--mark) 14%,var(--mark) 86%,transparent 86%);padding:0 .2em;}
.entry{border-top:2px solid var(--ink);padding:1rem 0 1.4rem;max-width:860px;}
.entry h3{font-size:1.45rem;line-height:1.3;margin:0;}
.entry .file{color:var(--muted);font-size:.85rem;margin:.2rem 0 0;}
.entry dl{display:grid;grid-template-columns:6.5rem 1fr;gap:.45rem 1.2rem;margin:.9rem 0 0;}
.entry dt{color:var(--muted);font-size:.92rem;}
.entry dd{margin:0;line-height:1.5;}
.entry.failed h3{color:var(--plum);}
.answer{font-family:'Newsreader',Georgia,serif;font-size:1.22rem;line-height:1.7;max-width:68ch;margin:1rem 0;}
.question{font-family:'Newsreader',Georgia,serif;font-style:italic;font-size:1.45rem;margin:1.2rem 0 .2rem;}
.src{border-left:4px solid var(--mark);padding:.1rem 0 .1rem 1rem;margin:1rem 0;max-width:68ch;}
.src b{font-weight:600;}
.empty{color:var(--muted);font-family:'Newsreader',Georgia,serif;font-size:1.15rem;margin-top:1.4rem;}
.stApp table{border-collapse:collapse;border-top:2px solid var(--ink);border-bottom:2px solid var(--ink);font-size:.93rem;}
.stApp th{border-bottom:1px solid var(--ink);text-align:left;font-weight:600;background:none;}
.stApp td{border-bottom:1px solid var(--rule);vertical-align:top;}
.stApp th,.stApp td{padding:.6rem .8rem;border-left:0;border-right:0;}
@media (max-width:640px){.entry dl{grid-template-columns:1fr;}.masthead h1{font-size:2rem;}}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

url, api_key = "", ""


def api(method, path, **kw):
    headers = {"Authorization": f"Bearer {api_key}", "ngrok-skip-browser-warning": "true"}
    r = requests.request(method, f"{url}{path}", headers=headers, timeout=900, **kw)
    if r.status_code >= 400:
        try:
            detail = r.json().get("detail", r.text)
        except Exception:
            detail = r.text[:200]
        raise RuntimeError(f"{r.status_code}: {detail}")
    return r.json()


def ready():
    if not url or not api_key:
        st.warning("Enter the server address and API key in the sidebar first.")
        return False
    return True


def rich(text):
    """Escape model output, then mark citations like [paper | section] in highlighter yellow."""
    t = html.escape(text or "")
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"\[([^\[\]]*\|[^\[\]]*)\]", r'<span class="mark">[\1]</span>', t)
    return t.replace("\n", "<br>")


def entry(p):
    info, name = p["info"], html.escape(p["name"])
    if not info:
        return (f'<div class="entry failed"><h3>Could not read this paper</h3><p class="file">{name}</p>'
                "<p>The model did not return valid data. Remove it with Reset and upload it again.</p></div>")
    rows = [("Problem", "problem"), ("Method", "method"), ("Data", "dataset"),
            ("Results", "results"), ("Limits", "limitations")]
    dl = "".join(f"<dt>{lab}</dt><dd>{html.escape(info[k])}</dd>" for lab, k in rows)
    return (f'<div class="entry"><h3>{html.escape(info["title"])}</h3>'
            f'<p class="file">{name}</p><dl>{dl}</dl></div>')


with st.sidebar:
    st.markdown("### Server")
    url = st.text_input("Server address", placeholder=" https://reclusive-curse-zodiac.ngrok-free.dev").strip().rstrip("/")
    api_key = st.text_input("API key", type="password")
    if st.button("Check connection"):
        if ready():
            try:
                n = api("GET", "/health")["papers"]
                st.success(f"Connected. {n} paper(s) loaded.")
            except Exception as e:
                st.error(f"Could not connect. Check the address, the key, and that the Kaggle cell is still running. ({e})")
    st.markdown("---")
    if st.button("Remove all papers"):
        if ready():
            try:
                api("POST", "/reset")
                st.success("All papers removed.")
            except Exception as e:
                st.error(e)

st.markdown(
    '<div class="masthead"><h1>Literature Review Agent</h1>'
    "<p>Add research papers, ask questions across them, and get a comparison with a draft of Related Work.</p></div>",
    unsafe_allow_html=True,
)

tab_papers, tab_ask, tab_compare = st.tabs(["Papers", "Ask", "Compare"])

with tab_papers:
    files = st.file_uploader("Add papers (PDF)", type="pdf", accept_multiple_files=True)
    if st.button("Read papers"):
        if not files:
            st.warning("Choose at least one PDF first.")
        elif ready():
            bar = st.progress(0.0)
            for i, f in enumerate(files):
                with st.spinner(f"Reading {f.name}. This can take a few minutes."):
                    try:
                        api("POST", "/upload", files={"file": (f.name, f.getvalue(), "application/pdf")})
                    except Exception as e:
                        st.error(f"{f.name}: {e}")
                bar.progress((i + 1) / len(files))
    papers = []
    if url and api_key:
        try:
            papers = api("GET", "/papers")
        except Exception as e:
            st.error(f"Could not load papers. {e}")
    if papers:
        for p in papers:
            st.markdown(entry(p), unsafe_allow_html=True)
        pick = st.selectbox("Write an abstract for", [p["name"] for p in papers])
        if st.button("Write abstract"):
            with st.spinner("Writing the abstract."):
                try:
                    s = api("POST", "/summarize", json={"name": pick})["summary"]
                    st.markdown(f'<div class="answer">{rich(s)}</div>', unsafe_allow_html=True)
                except Exception as e:
                    st.error(e)
    else:
        st.markdown('<p class="empty">No papers yet. Add two or more PDFs above, then choose Read papers.</p>',
                    unsafe_allow_html=True)

with tab_ask:
    q = st.text_input("Your question", placeholder="Which paper used the largest dataset?")
    if st.button("Ask the papers"):
        if not q.strip():
            st.warning("Type a question first.")
        elif ready():
            with st.spinner("Searching the papers."):
                try:
                    res = api("POST", "/ask", json={"question": q, "k": 5})
                    st.markdown(f'<p class="question"><span class="mark">{html.escape(q)}</span></p>',
                                unsafe_allow_html=True)
                    st.markdown(f'<div class="answer">{rich(res["answer"])}</div>', unsafe_allow_html=True)
                    with st.expander("Passages used for this answer"):
                        for s in res["sources"]:
                            st.markdown(
                                f'<div class="src"><b>{html.escape(s["paper"])}</b>, {html.escape(s["section"])}'
                                f'<br>{html.escape(s["text"])}</div>', unsafe_allow_html=True)
                except Exception as e:
                    st.error(e)

with tab_compare:
    st.markdown("Needs at least two papers that were read successfully.")
    if st.button("Compare papers"):
        if ready():
            with st.spinner("Comparing the papers and drafting Related Work."):
                try:
                    res = api("POST", "/compare")
                    st.markdown("### Comparison")
                    st.markdown(res["table"])
                    st.markdown("### Related Work, first draft")
                    st.markdown(f'<div class="answer">{rich(res["related_work"])}</div>', unsafe_allow_html=True)
                except Exception as e:
                    st.error(e)
"""GCP Professional Cloud Architect practice: one question per page.

Run:  streamlit run app.py
Questions come from MongoDB (REMOTE_MONGO_DB in ../.env, collection tb_gcp_pca).
Answers are kept in the browser's localStorage. Correct answers are not loaded.
"""
import json
import os
from pathlib import Path

import pymongo
import streamlit as st
from dotenv import load_dotenv

DB_NAME = "db_certificates"
COLLECTION = "tb_gcp_pca"
STORAGE_KEY = "gcp_pca_answers"  # localStorage key; value = JSON {question_id: letter}

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Tiny two-way bridge to window.localStorage (Streamlit components v2).
# On mount it reports the stored string; whenever Python passes `answers`, it saves it.
_LOCAL_STORAGE_JS = """
export default function (component) {
    const { data, parentElement, setStateValue } = component;
    if (!parentElement.__lsRead) {
        parentElement.__lsRead = true;
        let stored = "";
        try { stored = window.localStorage.getItem(data.key) || ""; } catch (e) {}
        setStateValue("value", stored);
    }
    if (data.answers !== null) {
        try { window.localStorage.setItem(data.key, data.answers); } catch (e) {}
    }
}
"""
_local_storage = st.components.v2.component("gcp_pca_local_storage", js=_LOCAL_STORAGE_JS)


@st.cache_resource
def _collection():
    client = pymongo.MongoClient(os.environ["REMOTE_MONGO_DB"], serverSelectionTimeoutMS=8000)
    return client[DB_NAME][COLLECTION]


@st.cache_data(show_spinner="Loading questions…")
def load_questions():
    # answer/explanation are deliberately not fetched yet.
    docs = _collection().find({}, {"answer": 0, "explanation": 0}).sort("_id", 1)
    return [{**d, "_id": str(d["_id"])} for d in docs]


def esc(text):
    """Escape '$' so Streamlit markdown does not treat it as LaTeX."""
    return str(text).replace("$", r"\$")


def save_choice(qid, widget_key):
    st.session_state.answers[qid] = st.session_state[widget_key]


def go(delta):
    st.session_state.idx += delta


st.set_page_config(page_title="GCP PCA Practice", page_icon="☁️")

# ---- data + saved answers -------------------------------------------------
try:
    questions = load_questions()
except Exception as e:  # connection / auth / missing env
    st.error(f"Could not load questions: {e}")
    st.stop()
if not questions:
    st.warning(f"No documents in {COLLECTION}.")
    st.stop()

stored = _local_storage(
    key="ls_bridge",
    data={
        "key": STORAGE_KEY,
        "answers": json.dumps(st.session_state["answers"]) if "answers" in st.session_state else None,
    },
    default={"value": None},
    on_value_change=lambda: None,
)
if "answers" not in st.session_state:
    if stored.value is None:  # browser has not reported localStorage yet
        st.caption("Loading saved answers…")
        st.stop()
    try:
        saved = json.loads(stored.value) if stored.value else {}
    except ValueError:
        saved = {}
    st.session_state.answers = saved if isinstance(saved, dict) else {}
    # Resume at the first unanswered question.
    st.session_state.idx = next(
        (i for i, q in enumerate(questions) if q["_id"] not in st.session_state.answers),
        0,
    )
    st.rerun()  # push the loaded answers back through the bridge

answers = st.session_state.answers
total = len(questions)

# ---- sidebar --------------------------------------------------------------
with st.sidebar:
    st.header("GCP Professional Cloud Architect")
    done = sum(q["_id"] in answers for q in questions)
    st.progress(done / total, text=f"Answered {done} / {total}")
    # Not bound to a key: Previous/Next change `idx`, and the widget follows via `index`.
    jump = st.selectbox(
        "Go to question",
        range(total),
        index=st.session_state.idx,
        format_func=lambda i: f"{i + 1}  {'✅' if questions[i]['_id'] in answers else '·'}",
    )
    if jump != st.session_state.idx:
        st.session_state.idx = jump
        st.rerun()

# ---- question page --------------------------------------------------------
idx = st.session_state.idx
q = questions[idx]
qid = q["_id"]

st.subheader(f"Question {idx + 1} of {total}")
tags = [f"Domain {q['domain']}"] if q.get("domain") is not None else []
if q.get("case_study") is not None:
    tags.append(f"Case study {q['case_study']}")
if tags:
    st.caption(" · ".join(tags))

st.markdown(esc(q["question"]))

widget_key = f"choice_{qid}"
if widget_key not in st.session_state and qid in answers:
    st.session_state[widget_key] = answers[qid]
st.radio(
    "Choose your answer",
    list(q["options"]),
    index=None,
    key=widget_key,
    format_func=lambda letter: f"**{letter}.** {esc(q['options'][letter])}",
    label_visibility="collapsed",
    on_change=save_choice,
    args=(qid, widget_key),
)

prev_col, status_col, next_col = st.columns([1, 2, 1], vertical_alignment="center")
prev_col.button("← Previous", on_click=go, args=(-1,), disabled=idx == 0, width="stretch")
status_col.caption("✅ Answer saved" if qid in answers else "Not answered yet")
next_col.button("Next →", on_click=go, args=(1,), disabled=idx == total - 1, width="stretch")

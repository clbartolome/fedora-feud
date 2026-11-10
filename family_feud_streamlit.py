import streamlit as st
from typing import List, Dict, Optional, Tuple, Any
import json
import os
import base64
import time

st.set_page_config(page_title="Fedora Feud", page_icon="❓", layout="wide")

# --------- Styles (Glass look) ---------
CUSTOM_CSS = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;800&display=swap');

  /* Force dark UI even if OS/browser is light */
  :root { color-scheme: dark !important; }
  html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"], [data-testid="stAppViewContainer"] > .main {
    background: rgb(1 24 51) !important;
    color-scheme: dark !important;
    color: rgba(255,255,255,0.92) !important;
  }
  [data-baseweb="popover"], [data-baseweb="menu"] { color-scheme: dark !important; }

  .stMainBlockContainer { padding-top: 0 }
  h3 { font-size: 3.75rem !important; }

  .ff-card {
    backdrop-filter: blur(10px);
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 18px;
    box-shadow: 0 10px 30px rgba(0,0,0,.35);
    padding: 1rem 1.2rem;
  }
  .ff-success {
    background: linear-gradient(180deg, rgb(247 182 18), rgb(255 174 10 / 54%));
    border-color: rgb(255 192 0 / 35%);
  }
  .ff-title { font-weight: 800; letter-spacing: .5px; }
  .ff-center { text-align:center; }
  .ff-big { font-size: 2rem; font-weight: 800; }
  .ff-num { font-size: 1.8rem; font-weight: 800; opacity:.95 }

  .stButton>button {
    border-radius: 9px !important;
    padding: .24rem .4rem;
    font-weight: 700;
    font-size: .8rem;
    border: 1px solid white;
    background: transparent;
    color: #fff;
    box-shadow: 0 5px 12px rgba(79,70,229,.26);
    transition: transform .06s ease, filter .2s ease;
    min-width: 30px;
  }
  .stButton>button:hover { filter: brightness(1.07) }
  .stButton>button:active { transform: translateY(1px) }

  /* Sales Assistant chip (primary button only) */
  .stButton>button[kind="primary"],
  [data-testid="stBaseButton-primary"] {
    border-radius: 999px !important;
    padding: 8px 14px 8px 12px !important;
    min-width: unset !important;
    height: auto !important;
    font-size: 1rem !important;
    font-weight: 600 !important;
    letter-spacing: .2px;
    background: rgba(255,255,255,0.12) !important;
    border: 1px solid rgba(247, 182, 18, 0.55) !important;
    color: rgba(255,255,255,0.96) !important;
    box-shadow: none !important;
    backdrop-filter: blur(6px);
  }
  .stButton>button[kind="primary"]:hover,
  [data-testid="stBaseButton-primary"]:hover {
    background: rgba(247, 182, 18, 0.22) !important;
    border-color: rgba(247, 182, 18, 0.85) !important;
    filter: none;
  }

  .ff-toolbar { display:flex; gap:10px; align-items:center; white-space:nowrap; overflow-x:auto; padding:.25rem .25rem; }
  .ff-pill { display:inline-flex; align-items:center; gap:8px; backdrop-filter:blur(6px); background: rgba(255,255,255,0.08); border:1px solid rgba(255,255,255,0.15); border-radius:999px; padding:6px 10px; }
  .ff-pill .lbl { font-weight:700 }
  .ff-pill .val { font-weight:800 }

  #MainMenu, header, footer {visibility: hidden;}

  /* --- Strike overlay --- */
  .ff-strike {
    position: fixed; inset: 0;
    display: flex; align-items: center; justify-content: center;
    z-index: 10000;
    pointer-events: none;
  }
  .ff-strike::before{
    content:"";
    position: absolute; inset: 0;
    background: radial-gradient(circle at 50% 50%, rgba(255,70,70,.18), rgba(0,0,0,0) 60%);
    animation: strikeFlash .6s ease-out;
  }
  .ff-x {
    font-size: clamp(6rem, 22vw, 28rem);
    font-weight: 900;
    line-height: 1;
    color: rgba(255,70,70,0.95);
    text-shadow: 0 8px 24px rgba(0,0,0,.35), 0 0 30px rgba(255,70,70,.35);
    transform: rotate(-8deg);
    animation: strikePop .6s cubic-bezier(.2,.8,.2,1);
  }
  @keyframes strikePop {
    0% { transform: scale(.6) rotate(-8deg); opacity: 0; }
    60% { transform: scale(1.1) rotate(-8deg); opacity: 1; }
    100% { transform: scale(1) rotate(-8deg); opacity: 1; }
  }
  @keyframes strikeFlash {
    0% { opacity: .0; }
    30% { opacity: .6; }
    100% { opacity: .0; }
  }

  /* Compact selectbox styling */
  [data-baseweb="select"] > div {
    background: rgba(255,255,255,0.05) !important;
    border-color: rgba(255,255,255,0.25) !important;
    color: white !important;
    font-weight: 600 !important;
  }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ---------------------------
# Data loading (with rounds)
# ---------------------------
Question = Dict[str, Any]
Round = Dict[str, Any]

DEFAULT_QUESTIONS: List[Question] = [
    {
        "prompt": "Name something people double-check before leaving home",
        "answers": [
            {"text": "Keys", "points": 32},
            {"text": "Phone", "points": 27},
            {"text": "Wallet", "points": 18},
            {"text": "Lights off", "points": 9},
            {"text": "Door locked", "points": 8},
            {"text": "Stove/Gas", "points": 6},
        ],
    }
]

def _clean_questions(raw_questions: Any, max_answers: int = 15) -> List[Question]:
    if not isinstance(raw_questions, list):
        return []
    cleaned: List[Question] = []
    for q in raw_questions:
        if not isinstance(q, dict):
            continue
        prompt = q.get("prompt")
        answers = q.get("answers", [])
        if isinstance(prompt, str) and isinstance(answers, list) and 1 <= len(answers) <= max_answers:
            item: Question = {
                "prompt": prompt,
                "answers": [{"text": str(a.get("text", "")), "points": int(a.get("points", 0))} for a in answers if isinstance(a, dict)],
            }
            if "sales_assistance" in q:
                item["sales_assistance"] = q.get("sales_assistance")
            cleaned.append(item)
    return cleaned

def load_rounds_from_file(path: str) -> List[Round]:
    # Supports:
    #  - New format: {"rounds":[{"title":"Round 1","questions":[...]}]}
    #  - Old format: [ {prompt, answers}, ... ]  -> becomes one round "Round 1"
    if not os.path.exists(path):
        return [{"title": "Round 1", "questions": DEFAULT_QUESTIONS}]

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict) and isinstance(data.get("rounds"), list):
            rounds: List[Round] = []
            for r in data["rounds"]:
                if not isinstance(r, dict):
                    continue
                title = r.get("title", "Round")
                questions = _clean_questions(r.get("questions", []))
                if isinstance(title, str) and questions:
                    rounds.append({
                        "title": title,
                        "questions": questions,
                        "tiebreaker": bool(r.get("tiebreaker", False)),
                    })
            return rounds or [{"title": "Round 1", "questions": DEFAULT_QUESTIONS}]

        if isinstance(data, list):
            questions = _clean_questions(data)
            return [{"title": "Round 1", "questions": questions or DEFAULT_QUESTIONS}]

        return [{"title": "Round 1", "questions": DEFAULT_QUESTIONS}]
    except Exception:
        return [{"title": "Round 1", "questions": DEFAULT_QUESTIONS}]

ROUNDS: List[Round] = load_rounds_from_file("files/questions.json")

HAS_LOGO = os.path.exists("fedora_feud.png")

# ---------------------------------
# Game state
# ---------------------------------
defaults = {
    "started": False,
    "finished": False,
    "team_names": [],  # frozen team labels for the whole game

    # rounds
    "screen": "home",        # home | round_intro | question | results_wait| final
    "round_index": 0,
    "q_in_round": 0,

    # teams
    "num_teams": 2,
    "team_scores": [],

    # per-question maps (keyed by (round_index, q_in_round))
    "revealed_map": {},
    "assigned_map": {},

    # strike overlay
    "show_strike": False,
    "strike_nonce": 0,
    "strike_hide_at": 0.0,
    "tiebreaker_used": False,
    "team_label_mode": "Letters",  # "Letters" | "Numbers"

}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ---------------------------
# Helpers
# ---------------------------
def team_labels(n: int) -> List[str]:
    # If the game already started, use the frozen names
    names = st.session_state.get("team_names", [])
    if isinstance(names, list) and len(names) == n and all(isinstance(x, str) for x in names):
        return names

    # Otherwise (home / before start), compute preview labels
    mode = str(st.session_state.get("team_label_mode", "letters")).strip().lower()
    if mode.startswith("num"):
        return [str(i + 1) for i in range(n)]
    return [chr(ord("A") + i) for i in range(min(n, 26))]

def clamp(n, mn, mx): return max(mn, min(n, mx))

def has_sales_assistance(q: Question) -> bool:
    val = q.get("sales_assistance")
    if val in (None, False, "", 0):
        return False
    if isinstance(val, str) and not val.strip():
        return False
    return True

def _sales_assistant_html(prompt: str) -> str:
    prompt_js = json.dumps(prompt).replace("<", "\\u003c").replace(">", "\\u003e")
    return _SALES_ASSISTANT_HTML.replace("__PROMPT_JSON__", prompt_js)

def mount_sales_assistant_helper(prompt: str) -> None:
    st.components.v1.html(_sales_assistant_html(prompt), height=0)

_SALES_ASSISTANT_HTML = r"""
<style id="sa-css">
  #ff-sa-overlay {
    position: fixed; inset: 0; z-index: 20000;
    background: rgba(8, 16, 32, .55);
    display: flex; align-items: center; justify-content: center;
    font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
    color: #161616;
    color-scheme: light;
  }
  #ff-sa-overlay * { box-sizing: border-box; }
  .ff-sa-window {
    width: min(1120px, 94vw);
    height: min(740px, calc(100vh - 24px));
    background: #fff !important;
    color: #161616 !important;
    border-radius: 10px;
    box-shadow: 0 24px 80px rgba(0,0,0,.35);
    overflow: hidden;
    display: flex; flex-direction: column;
    position: relative;
  }
  .ff-sa-top {
    height: 48px; flex: 0 0 48px;
    display: flex; align-items: center; justify-content: space-between;
    padding: 0 14px 0 16px;
    background: #f7f7f8;
    border-bottom: 2px solid #0f62fe;
    color: #161616;
    font-size: 14px; font-weight: 500;
  }
  .ff-sa-top-left, .ff-sa-top-right { display: flex; align-items: center; gap: 8px; }
  .ff-sa-iconbtn {
    width: 28px; height: 28px; border: 0; background: transparent;
    color: #525252; cursor: pointer; border-radius: 6px;
    display: inline-flex; align-items: center; justify-content: center;
  }
  .ff-sa-iconbtn:hover { background: #e8e8e8; color: #161616; }
  .ff-sa-body { flex: 1; min-height: 0; display: flex; background: #fff; }
  .ff-sa-rail {
    width: 56px; flex: 0 0 56px;
    background: #f4f4f4;
    border-right: 1px solid #e0e0e0;
    display: flex; flex-direction: column; align-items: center;
    padding: 12px 0 10px;
  }
  .ff-sa-rail-top { display: flex; flex-direction: column; align-items: center; gap: 6px; flex: 1; }
  .ff-sa-rail-btn {
    width: 36px; height: 36px; border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    color: #6f6f6f;
  }
  .ff-sa-rail-btn.active { background: #e6e6e6; color: #161616; }
  .ff-sa-rail-btn.red { color: #da1e28; }
  .ff-sa-avatar {
    width: 28px; height: 28px; border-radius: 50%;
    background: #c6c6c6; color: #161616;
    font-size: 10px; font-weight: 700;
    display: flex; align-items: center; justify-content: center;
  }
  .ff-sa-main {
    flex: 1; min-width: 0; min-height: 0;
    display: flex; flex-direction: column;
    position: relative;
    background: #fff;
  }
  .ff-sa-help {
    position: absolute; top: 16px; right: 22px;
    display: flex; align-items: center; gap: 6px;
    color: #6f6f6f; font-size: 14px;
  }
  .ff-sa-hero {
    flex: 1; min-height: 0;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    padding: 28px 48px 10px;
    overflow-y: auto;
  }
  .ff-sa-hello {
    margin: 0 0 8px !important;
    padding: 0 !important;
    font-size: clamp(28px, 5vh, 42px) !important;
    font-weight: 600 !important;
    letter-spacing: -.03em;
    color: #161616 !important;
    text-align: center;
    line-height: 1.15 !important;
  }
  .ff-sa-sub {
    margin: 0 0 18px; max-width: 460px;
    font-size: 16px; line-height: 1.45; color: #6f6f6f; text-align: center;
  }
  .ff-sa-chips {
    width: min(720px, 100%);
    display: flex; flex-wrap: wrap; gap: 10px;
    margin-bottom: 20px;
  }
  .ff-sa-chip {
    background: #f4f4f4; border: 1px solid #ececec; border-radius: 18px;
    padding: 12px 16px; font-size: 14.5px; color: #161616;
  }
  .ff-sa-skills-head {
    width: min(720px, 100%);
    display: flex; justify-content: space-between; align-items: center;
    color: #6f6f6f; font-size: 14px; margin-bottom: 14px;
  }
  .ff-sa-see { display: inline-flex; align-items: center; gap: 6px; }
  .ff-sa-skills {
    width: min(720px, 100%);
    display: flex; flex-wrap: wrap; gap: 10px; justify-content: center;
  }
  .ff-sa-skill {
    display: inline-flex; align-items: center; gap: 8px;
    background: #fff; border: 1px solid #e0e0e0; border-radius: 999px;
    padding: 8px 14px; font-size: 13.5px; color: #161616;
  }
  .ff-sa-footer { padding: 8px 28px 18px; }
  .ff-sa-composer {
    border: 1px solid #e0e0e0; border-radius: 16px;
    min-height: 118px; padding: 16px 16px 12px;
    display: flex; flex-direction: column; gap: 18px;
    background: #fff;
  }
  .ff-sa-typed-wrap {
    min-height: 44px; font-size: 15.5px; line-height: 1.5; color: #161616;
    pointer-events: none; user-select: none;
  }
  .ff-sa-placeholder { color: #8d8d8d; }
  .ff-sa-caret {
    display: none; width: 1.5px; height: 1.05em;
    background: #161616; margin-left: 1px; vertical-align: -3px;
    animation: ffSaBlink 1s step-end infinite;
  }
  .ff-sa-caret.on { display: inline-block; }
  @keyframes ffSaBlink { 50% { opacity: 0; } }
  .ff-sa-tools { display: flex; align-items: center; gap: 8px; }
  .ff-sa-tools span {
    width: 28px; height: 28px; color: #6f6f6f;
    display: inline-flex; align-items: center; justify-content: center;
  }
  .ff-sa-send {
    margin-left: auto; width: 36px; height: 36px; border: 0; border-radius: 50%;
    background: #0f62fe; color: #fff;
    display: inline-flex; align-items: center; justify-content: center;
    pointer-events: none;
  }
  .ff-sa-disclaimer { margin: 8px 2px 0; font-size: 12px; color: #8d8d8d; }
  .ff-sa-feedback {
    position: absolute; right: 0; top: 46%;
    background: #161616; color: #fff; font-size: 12px; letter-spacing: .04em;
    padding: 10px 6px; border-radius: 6px 0 0 6px;
    writing-mode: vertical-rl; transform: rotate(180deg);
  }
</style>
<template id="sa-html">
  <div class="ff-sa-window" role="dialog" aria-label="Sales Assistant">
    <div class="ff-sa-top">
      <div class="ff-sa-top-left">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <rect x="1.5" y="1.5" width="13" height="13" rx="2.5" stroke="#161616" stroke-width="1.4"/>
          <path d="M8 5v6M5 8h6" stroke="#161616" stroke-width="1.4" stroke-linecap="round"/>
        </svg>
        Sales Assistant
      </div>
      <div class="ff-sa-top-right">
        <span class="ff-sa-iconbtn" aria-hidden="true">
          <svg width="15" height="15" viewBox="0 0 16 16" fill="none">
            <path d="M6 3H3.5A1.5 1.5 0 0 0 2 4.5v8A1.5 1.5 0 0 0 3.5 14h8a1.5 1.5 0 0 0 1.5-1.5V10" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
            <path d="M9 2h5v5M14 2 8 8" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </span>
        <button type="button" class="ff-sa-iconbtn ff-sa-close" aria-label="Close">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M2 2l10 10M12 2 2 12" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
          </svg>
        </button>
      </div>
    </div>
    <div class="ff-sa-body">
      <aside class="ff-sa-rail">
        <div class="ff-sa-rail-top">
          <div class="ff-sa-rail-btn red">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="#da1e28"><path d="M2 8.2 9 2.5 16 8.2V16H11v-5H7v5H2V8.2z"/></svg>
          </div>
          <div class="ff-sa-rail-btn active">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path d="M3 4.5A1.5 1.5 0 0 1 4.5 3h9A1.5 1.5 0 0 1 15 4.5v7A1.5 1.5 0 0 1 13.5 13H7l-3.5 2.5V4.5z" stroke="currentColor" stroke-width="1.4"/>
            </svg>
          </div>
          <div class="ff-sa-rail-btn">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <rect x="2.5" y="3" width="5" height="5" rx="1" stroke="currentColor" stroke-width="1.4"/>
              <rect x="10.5" y="3" width="5" height="5" rx="1" stroke="currentColor" stroke-width="1.4"/>
              <rect x="2.5" y="10.5" width="5" height="5" rx="1" stroke="currentColor" stroke-width="1.4"/>
              <rect x="10.5" y="10.5" width="5" height="5" rx="1" stroke="currentColor" stroke-width="1.4"/>
            </svg>
          </div>
          <div class="ff-sa-rail-btn">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path d="M9 2.5l1.6 3.6 4 .4-3 2.8.9 3.9L9 11.4 5.5 13.2l.9-3.9-3-2.8 4-.4L9 2.5z" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round"/>
            </svg>
          </div>
          <div class="ff-sa-rail-btn">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <circle cx="8" cy="8" r="5.2" stroke="currentColor" stroke-width="1.4"/>
              <path d="m12 12 3.2 3.2" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
            </svg>
          </div>
        </div>
        <div class="ff-sa-avatar">FF</div>
      </aside>
      <section class="ff-sa-main">
        <div class="ff-sa-help">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <circle cx="8" cy="8" r="6.2" stroke="currentColor" stroke-width="1.3"/>
            <path d="M6.4 6.2a1.7 1.7 0 1 1 2.4 1.55c-.5.3-.8.7-.8 1.25V9.4" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>
            <circle cx="8" cy="11.4" r=".7" fill="currentColor"/>
          </svg>
          Help
        </div>
        <div class="ff-sa-hero">
          <div class="ff-sa-hello">Hey Fedora Feud! 👋</div>
          <div class="ff-sa-sub">Sales Assistant is ready to help. What would you like to explore today?</div>
          <div class="ff-sa-chips">
            <div class="ff-sa-chip">How do I create a private offer?</div>
            <div class="ff-sa-chip">Help me prepare for my next meeting</div>
            <div class="ff-sa-chip">What's new in the latest sales play?</div>
          </div>
          <div class="ff-sa-skills-head">
            <span>Or try a skill from the library</span>
            <span class="ff-sa-see">
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                <rect x="2" y="2" width="5" height="5" rx="1" stroke="currentColor"/>
                <rect x="9" y="2" width="5" height="5" rx="1" stroke="currentColor"/>
                <rect x="2" y="9" width="5" height="5" rx="1" stroke="currentColor"/>
                <rect x="9" y="9" width="5" height="5" rx="1" stroke="currentColor"/>
              </svg>
              See all skills
            </span>
          </div>
          <div class="ff-sa-skills">
            <div class="ff-sa-skill"><span style="color:#0f62fe">📅</span> Meeting Prep</div>
            <div class="ff-sa-skill"><span style="color:#c43e1c">⚠️</span> Deal Risk</div>
            <div class="ff-sa-skill"><span style="color:#b28600">📄</span> Create Quote</div>
            <div class="ff-sa-skill"><span style="color:#0e7c7b">🔄</span> Renewal</div>
            <div class="ff-sa-skill"><span style="color:#4589ff">🗂️</span> Value Brief</div>
          </div>
        </div>
        <div class="ff-sa-footer">
          <div class="ff-sa-composer">
            <div class="ff-sa-typed-wrap">
              <span class="ff-sa-placeholder" id="saPlaceholder">Ask anything about your accounts, products, or plans ( / for skills and prompts, @ for accounts )</span>
              <span id="saTyped"></span><span class="ff-sa-caret" id="saCaret"></span>
            </div>
            <div class="ff-sa-tools">
              <span>
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <path d="M8 3v10M3 8h10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                </svg>
              </span>
              <span>
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <path d="M8 2.2 9.5 6l4 .4-3 2.7.9 3.9L8 10.9 4.6 13l.9-3.9-3-2.7 4-.4L8 2.2z" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round"/>
                </svg>
              </span>
              <div class="ff-sa-send" aria-hidden="true">
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <path d="M4 12 12 4M6.5 4H12v5.5" stroke="#fff" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </div>
            </div>
          </div>
          <div class="ff-sa-disclaimer">AI can be wrong. Verify critical information before acting.</div>
        </div>
        <div class="ff-sa-feedback">Feedback</div>
      </section>
    </div>
  </div>
</template>
<script type="application/json" id="sa-prompt">__PROMPT_JSON__</script>
<script>
(function () {
  const doc = window.parent.document;
  const prompt = JSON.parse(document.getElementById("sa-prompt").textContent);
  const css = document.getElementById("sa-css").textContent;
  const html = document.getElementById("sa-html").innerHTML;
  const parentWin = window.parent;

  parentWin.__ffSaPrompt = prompt;
  parentWin.__ffSaCss = css;
  parentWin.__ffSaHtml = html;

  function ensureFont() {
    if (doc.getElementById("ff-sa-font")) return;
    const font = doc.createElement("link");
    font.id = "ff-sa-font";
    font.rel = "stylesheet";
    font.href = "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&display=swap";
    doc.head.appendChild(font);
  }

  function closeOverlay() {
    const wrap = doc.getElementById("ff-sa-overlay");
    if (wrap) wrap.remove();
    const style = doc.getElementById("ff-sa-style");
    if (style) style.remove();
    doc.removeEventListener("keydown", onEscape, true);
  }

  function onEscape(evt) {
    if (evt.key === "Escape") closeOverlay();
  }

  function startTypewriter(wrap, text) {
    const typed = wrap.querySelector("#saTyped");
    const placeholder = wrap.querySelector("#saPlaceholder");
    const caret = wrap.querySelector("#saCaret");
    if (!typed || !text) return;
    let i = 0;
    const tick = function () {
      if (placeholder) placeholder.style.display = "none";
      if (caret) caret.classList.add("on");
      typed.textContent = text.slice(0, i);
      i += 1;
      if (i <= text.length) parentWin.setTimeout(tick, 34);
    };
    parentWin.setTimeout(tick, 650);
  }

  function openSalesAssistant(text) {
    const promptText = text || parentWin.__ffSaPrompt || "";
    closeOverlay();
    ensureFont();

    let style = doc.getElementById("ff-sa-style");
    if (!style) {
      style = doc.createElement("style");
      style.id = "ff-sa-style";
      doc.head.appendChild(style);
    }
    style.textContent = parentWin.__ffSaCss || css;

    const wrap = doc.createElement("div");
    wrap.id = "ff-sa-overlay";
    wrap.innerHTML = parentWin.__ffSaHtml || html;
    doc.body.appendChild(wrap);

    doc.addEventListener("keydown", onEscape, true);
    wrap.addEventListener("click", function (evt) {
      if (evt.target === wrap) closeOverlay();
    });
    const closeBtn = wrap.querySelector(".ff-sa-close");
    if (closeBtn) closeBtn.addEventListener("click", closeOverlay);

    startTypewriter(wrap, promptText);
  }

  parentWin.__ffOpenSalesAssistant = openSalesAssistant;
  parentWin.__ffCloseSalesAssistant = closeOverlay;

  if (!parentWin.__ffSaClickBound) {
    parentWin.__ffSaClickBound = true;
    doc.addEventListener("click", function (evt) {
      const btn = evt.target.closest("button");
      if (!btn) return;
      if (btn.closest("#ff-sa-overlay")) return;
      const label = (btn.innerText || btn.textContent || "");
      if (!label.includes("Sales Assistant")) return;
      evt.preventDefault();
      evt.stopPropagation();
      if (typeof parentWin.__ffOpenSalesAssistant === "function") {
        parentWin.__ffOpenSalesAssistant(parentWin.__ffSaPrompt);
      }
    }, true);
  }
})();
</script>
"""

def current_round() -> Round:
    return ROUNDS[st.session_state.round_index]

def round_questions() -> List[Question]:
    return current_round().get("questions", [])

def current_question() -> Question:
    return round_questions()[st.session_state.q_in_round]

QKey = Tuple[int, int]

def is_tiebreaker_round(idx: int) -> bool:
    return bool(ROUNDS[idx].get("tiebreaker", False))

def last_normal_round_index() -> int:
    normal_idxs = [i for i in range(len(ROUNDS)) if not is_tiebreaker_round(i)]
    return normal_idxs[-1] if normal_idxs else 0

def next_normal_round_index(cur: int) -> Optional[int]:
    for i in range(cur + 1, len(ROUNDS)):
        if not is_tiebreaker_round(i):
            return i
    return None

def top_is_tied() -> bool:
    scores = st.session_state.team_scores
    if not scores:
        return False
    best = max(scores)
    return sum(1 for s in scores if s == best) >= 2

def find_tiebreaker_round_index() -> Optional[int]:
    for idx, r in enumerate(ROUNDS):
        if bool(r.get("tiebreaker", False)):
            return idx
    return None

def ensure_state_for_current_question() -> QKey:
    rid: QKey = (st.session_state.round_index, st.session_state.q_in_round)
    q = current_question()
    n_answers = clamp(len(q.get("answers", [])), 1, 15)

    if rid not in st.session_state.revealed_map:
        st.session_state.revealed_map[rid] = [False] * n_answers
    else:
        cur = st.session_state.revealed_map[rid]
        if len(cur) != n_answers:
            st.session_state.revealed_map[rid] = (cur + [False] * n_answers)[:n_answers]

    if rid not in st.session_state.assigned_map:
        st.session_state.assigned_map[rid] = [None] * n_answers
    else:
        cur2 = st.session_state.assigned_map[rid]
        if len(cur2) != n_answers:
            st.session_state.assigned_map[rid] = (cur2 + [None] * n_answers)[:n_answers]

    return rid

def start_game(num_teams: int):
    st.session_state.num_teams = clamp(int(num_teams), 1, 15)
    
    st.session_state.team_names = team_labels(st.session_state.num_teams)
    st.session_state.team_scores = [0] * st.session_state.num_teams

    st.session_state.round_index = 0
    st.session_state.q_in_round = 0
    st.session_state.revealed_map = {}
    st.session_state.assigned_map = {}

    st.session_state.finished = False
    st.session_state.started = True
    st.session_state.screen = "round_intro"
    st.session_state.tiebreaker_used = False

def go_prev():
    if st.session_state.screen == "question":
        if st.session_state.q_in_round > 0:
            st.session_state.q_in_round -= 1
            return
        st.session_state.screen = "round_intro"
        return

    if st.session_state.screen == "round_intro":
        if st.session_state.round_index > 0:
            st.session_state.round_index -= 1
            st.session_state.q_in_round = max(0, len(round_questions()) - 1)
            st.session_state.screen = "question"
            return

def go_next():
    if st.session_state.screen == "round_intro":
        st.session_state.screen = "question"
        return

    if st.session_state.screen != "question":
        return

    if st.session_state.q_in_round < len(round_questions()) - 1:
        st.session_state.q_in_round += 1
        return

    # end of round (NORMAL progression skips tiebreaker)
    cur = st.session_state.round_index
    last_normal = last_normal_round_index()

    # If we finished the last NORMAL round, decide tie -> tiebreaker or results
    if cur == last_normal:
        tb_idx = find_tiebreaker_round_index()
        if tb_idx is not None and top_is_tied():
            st.session_state.round_index = tb_idx
            st.session_state.q_in_round = 0
            st.session_state.screen = "round_intro"
            return

        st.session_state.finished = True
        st.session_state.screen = "results_wait"
        return

    # Otherwise, go to the next NORMAL round (skip any tiebreaker rounds)
    nxt = next_normal_round_index(cur)
    if nxt is not None:
        st.session_state.round_index = nxt
        st.session_state.q_in_round = 0
        st.session_state.screen = "round_intro"
        return

    # Fallback (shouldn't happen)
    st.session_state.finished = True
    st.session_state.screen = "results_wait"

def go_home():
    for k, v in defaults.items():
        st.session_state[k] = v

def assign_team(ans_idx: int, team_idx: Optional[int]):
    rid = ensure_state_for_current_question()
    q = current_question()
    pts = int(q["answers"][ans_idx]["points"])
    prev = st.session_state.assigned_map[rid][ans_idx]

    if prev is not None:
        st.session_state.team_scores[prev] = max(0, st.session_state.team_scores[prev] - pts)

    st.session_state.assigned_map[rid][ans_idx] = team_idx
    if team_idx is not None:
        st.session_state.team_scores[team_idx] += pts

    st.session_state.revealed_map[rid][ans_idx] = True

def reveal_only(ans_idx: int):
    rid = ensure_state_for_current_question()
    q = current_question()
    pts = int(q["answers"][ans_idx]["points"])

    prev_team = st.session_state.assigned_map[rid][ans_idx]
    if prev_team is not None:
        st.session_state.team_scores[prev_team] = max(0, st.session_state.team_scores[prev_team] - pts)
        st.session_state.assigned_map[rid][ans_idx] = None

    st.session_state.revealed_map[rid][ans_idx] = True

def trigger_strike():
    st.session_state.show_strike = True
    st.session_state.strike_nonce = st.session_state.get("strike_nonce", 0) + 1
    st.session_state.strike_hide_at = time.time() + 2.0  # seconds

# ---------------------------
# Home (team count)
# ---------------------------
if not st.session_state.started and not st.session_state.finished:
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        if HAS_LOGO:
            with open("fedora_feud.png","rb") as fh:
                b64 = base64.b64encode(fh.read()).decode()
            st.markdown(
                f"<div style='display:flex;justify-content:center;'><img src='data:image/png;base64,{b64}' style='width:80%;height:auto;'></div>",
                unsafe_allow_html=True
            )

        teams = st.selectbox(
            "Choose the number of teams and press Start.",
            options=list(range(1, 16)),
            index=1,
            help="From 1 to 15",
            key="teams_select"
        )
        st.write("")
        label_mode = st.selectbox(
            "Team labels",
            options=["Letters", "Numbers"],
            key="team_label_mode",
            help="Choose how teams are displayed (A/B/C… or 1/2/3…).",
        )
        st.button("🚀 Start", use_container_width=True, on_click=start_game, args=(teams,))
    st.stop()

# ---------------------------
# Final results (centered)
# ---------------------------
if st.session_state.screen == "final":
    labels = team_labels(st.session_state.num_teams)
    scores = st.session_state.team_scores
    ranking = sorted(zip(labels, scores), key=lambda x: x[1], reverse=True)

    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<div class='ff-center' style='padding:2.0rem 0'>", unsafe_allow_html=True)
        st.markdown("<h1 class='ff-title' style='font-size:4rem; margin-bottom:1rem;'>🏁 Final Standings</h1>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        for pos, (lab, pts) in enumerate(ranking, start=1):
            st.markdown(
                f"<div class='ff-card' style='margin:.45rem 0; text-align:left;'>"
                f"<span class='ff-big'>#{pos}</span>"
                f"<b class='ff-big' style='margin-left: 1%; margin-right: 1%'>Team {lab}</b>"
                f"{pts} pts</div>",
                unsafe_allow_html=True
            )

        st.divider()

        st.balloons()
        
        
        st.button("🏠 Play again", on_click=go_home, use_container_width=True)

    st.stop()
# ---------------------------
# Results wait screen (manual pause)
# ---------------------------
if st.session_state.finished and st.session_state.screen == "results_wait":

    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown(
            """
            <div class="ff-center" style="padding:2.8rem 0 1.2rem 0;">
              <h1 class="ff-title" style="font-size:3.8rem; margin-bottom:.6rem;">
                Calculating results…
              </h1>
              <div style="opacity:.85; font-size:1.1rem;">
                Please wait a moment
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)


        # Loading GIF
        if os.path.exists("load.gif"):
            with open("load.gif", "rb") as fh:
                b64 = base64.b64encode(fh.read()).decode()

            st.markdown(
                f"""
                <div class="ff-center">
                <img src="data:image/gif;base64,{b64}"
                    style="max-width:240px; width:100%; opacity:.95;" />
                </div>
                """,
                unsafe_allow_html=True,
            )
            
        st.divider()   
        

        st.button("Continue ➡️", on_click=lambda: setattr(st.session_state, "screen", "final"), use_container_width=True)

    st.stop()


# ---------------------------
# Round intro screen
# ---------------------------
if st.session_state.started and st.session_state.screen == "round_intro":
    labels = team_labels(st.session_state.num_teams)
    r = current_round()
    title = r.get("title", f"Round {st.session_state.round_index + 1}")

    # ---- CENTERED CONTAINER ----
    left, center, right = st.columns([1, 2, 1])
    with center:

        # Title (hard centered)
        st.markdown(
            f"""
            <div class="ff-center" style="margin-top:2.5rem; margin-bottom:1.5rem;">
                <h1 class="ff-title" style="font-size:4.2rem; margin:0;">
                    🎯 {title}
                </h1>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.button("🚀 GO!", on_click=go_next, use_container_width=True)

        # ---- Standings (only after round 1) ----
        if st.session_state.round_index > 0:
            st.markdown("<div style='margin-top:2.2rem;'></div>", unsafe_allow_html=True)

            ranking = sorted(
                zip(labels, st.session_state.team_scores),
                key=lambda x: x[1],
                reverse=True,
            )

            for pos, (lab, pts) in enumerate(ranking, start=1):
                st.markdown(
                    f"""
                    <div class="ff-card" style="margin:.45rem 0;">
                        <span class="ff-big">#{pos}</span>
                        <b class="ff-big" style="margin-left:1%; margin-right:1%;">
                            Team {lab}
                        </b>
                        {pts} pts
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    st.stop()

# ---------------------------
# Question screen
# ---------------------------
q = current_question()
rid = ensure_state_for_current_question()
revealed = st.session_state.revealed_map[rid]
assigned = st.session_state.assigned_map[rid]
labels = team_labels(st.session_state.num_teams)

head_left, head_right = st.columns([4, 1])
with head_left:
    st.markdown(f"### ❓ {q['prompt']}")
with head_right:
    rtitle = current_round().get("title", f"Round {st.session_state.round_index + 1}")
    st.caption(f"{rtitle} - Q {st.session_state.q_in_round + 1} / {len(round_questions())}")

# st.caption(f"{rtitle}\n\nQ {st.session_state.q_in_round + 1} / {len(round_questions())}" )

st.divider()

# Strike (button aligned to the right) + optional Sales Assistant
if has_sales_assistance(q):
    sa_col, _empt, strike_col = st.columns([3, 9, 1])
    with sa_col:
        st.button(
            "Sales Assistant ↗",
            icon=":material/add_box:",
            type="primary",
            key=f"sales_assist_{rid[0]}_{rid[1]}",
        )
    with strike_col:
        st.button("❌", key="strike_btn", on_click=trigger_strike)
else:
    _empt, strike_col = st.columns([12, 1])
    with strike_col:
        st.button("❌", key="strike_btn", on_click=trigger_strike)

if has_sales_assistance(q):
    mount_sales_assistant_helper(q["prompt"])

st.components.v1.html(
    """
    <script>
    (function () {
      const doc = window.parent.document;

      // Add once (Streamlit reruns the script often)
      if (window.parent.__fedoraFeudHotkeysBound) return;
      window.parent.__fedoraFeudHotkeysBound = true;

      doc.addEventListener("keydown", function (evt) {

        // Don't trigger while typing in inputs/selects
        const el = doc.activeElement;
        const tag = el ? el.tagName : "";
        if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;

        if (doc.getElementById("ff-sa-overlay")) return;

        if (evt.key === "e" || evt.key === "E") {
          // Find the ❌ button and click it
          const buttons = Array.from(doc.querySelectorAll("button"));
          const strikeBtn = buttons.find(b => (b.innerText || "").trim() === "❌");
          if (strikeBtn) strikeBtn.click();
        }
      });
    })();
    </script>
    """,
    height=0,
)


# Answers
for i, a in enumerate(q["answers"]):
    left, right = st.columns([11, 1])
    with left:
        if revealed[i]:
            st.markdown(
                f"<div class='ff-card ff-success ff-center popIn'>"
                f"<div class='ff-big'>{a['text']}</div><div>{a['points']} pts</div></div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<div class='ff-card ff-center'><div class='ff-num'>#{i+1}</div></div>",
                unsafe_allow_html=True,
            )

    with right:
        dd_key = f"sel_{st.session_state.round_index}_{st.session_state.q_in_round}_{i}"
        if dd_key not in st.session_state:
            if assigned[i] is not None:
                st.session_state[dd_key] = labels[assigned[i]]
            elif revealed[i]:
                st.session_state[dd_key] = "Show"
            else:
                st.session_state[dd_key] = "(choose)"

        options = ["(choose)", "Show"] + labels

        def on_select_change(ans_idx=i, key=dd_key):
            val = st.session_state[key]
            if val == "(choose)":
                return
            if val == "Show":
                reveal_only(ans_idx)
                return
            if val in labels:
                assign_team(ans_idx, labels.index(val))
                
        # Ensure current value is valid
        if st.session_state[dd_key] not in options:
            st.session_state[dd_key] = "(choose)"

        st.selectbox(
            f"Select team for answer {i+1}",
            options=options,
            key=dd_key,
            label_visibility="collapsed",
            on_change=on_select_change,
        )

    st.write("")

st.divider()

# Scoreboard
items = ''.join([
    f"<div class='ff-pill' style='background-color: orange;color: rgb(14, 17, 23);'>"
    f"<span class='lbl'>Team {l}:</span><span class='val'>{v}</span></div>"
    for l, v in zip(labels, st.session_state.team_scores)
])
st.markdown(f"<div class='ff-toolbar'>{items}</div>", unsafe_allow_html=True)

st.divider()

# Navigation
nav1, nav_mid, nav3 = st.columns([1, 2, 1])
with nav1:
    st.button("⬅️ Previous", use_container_width=True, on_click=go_prev)
with nav3:
    st.button("Next ➡️", use_container_width=True, on_click=go_next)

# Strike overlay (auto-hide via rerun)
if st.session_state.show_strike:
    st.markdown(
        f"<div class='ff-strike' id='strike-{st.session_state.strike_nonce}'><div class='ff-x'>✕</div></div>",
        unsafe_allow_html=True
    )
    remaining = st.session_state.strike_hide_at - time.time()
    if remaining > 0:
        time.sleep(remaining)
    st.session_state.show_strike = False
    try:
        st.rerun()
    except AttributeError:
        st.experimental_rerun()
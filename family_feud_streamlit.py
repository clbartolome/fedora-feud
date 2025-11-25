import streamlit as st
from typing import List, Dict, Optional
import json
import os
import base64
import time


st.set_page_config(page_title="Fedora Feud", page_icon="❓", layout="wide")

# --------- Styles (Glass look) ---------
CUSTOM_CSS = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;800&display=swap');
  html, body { background: rgb(1 24 51) !important; }
  [data-testid="stAppViewContainer"], [data-testid="stApp"], [data-testid="stAppViewContainer"] > .main { background: rgb(1 24 51) !important; }

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

	/* Auto-hide for strike overlay (2s) */
	.ff-strike.auto-hide {
		animation: strikeHide 4s forwards ease-in;
	}
	@keyframes strikeHide {
		0%   { opacity: 1; visibility: visible; }
		80%  { opacity: 0; }
		100% { opacity: 0; visibility: hidden; }
	}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ---------------------------
# Data loading (from file)
# ---------------------------
Question = Dict[str, object]

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

def load_questions_from_file(path: str) -> List[Question]:
    if not os.path.exists(path):
        return DEFAULT_QUESTIONS
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        cleaned: List[Question] = []
        for q in data:
            prompt = q.get("prompt")
            answers = q.get("answers", [])
            if isinstance(prompt, str) and isinstance(answers, list) and 1 <= len(answers) <= 10:
                cleaned.append({
                    "prompt": prompt,
                    "answers": [
                        {"text": str(a.get("text", "")), "points": int(a.get("points", 0))}
                        for a in answers
                    ],
                })
        return cleaned or DEFAULT_QUESTIONS
    except Exception:
        return DEFAULT_QUESTIONS

QUESTIONS: List[Question] = load_questions_from_file("files/questions.json")
HAS_LOGO = os.path.exists("fedora_feud.png")

# ---------------------------------
# Game state
# ---------------------------------
defaults = {
    "started": False,
    "finished": False,
    "q_index": 0,
    "num_teams": 2,
    "team_scores": [],
    "revealed_map": {},
    "assigned_map": {},
    "show_strike": False,
    "strike_nonce": 0,
    "strike_ts": 0.0,
    "strike_hide_at": 0.0,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ---------------------------
# Helpers
# ---------------------------
def team_labels(n: int) -> List[str]:
    base = [chr(ord('A') + i) for i in range(26)]
    return base[:n]

def clamp(n, mn, mx): return max(mn, min(n, mx))

def load_question(i: int) -> Question:
    return QUESTIONS[i % len(QUESTIONS)]

def ensure_state_for_question(i: int):
    q = load_question(i)
    n_answers = clamp(len(q["answers"]), 1, 10)
    if i not in st.session_state.revealed_map:
        st.session_state.revealed_map[i] = [False] * n_answers
    if i not in st.session_state.assigned_map:
        st.session_state.assigned_map[i] = [None] * n_answers

def start_game(num_teams: int):
    st.session_state.num_teams = clamp(int(num_teams), 1, 15)
    st.session_state.team_scores = [0] * st.session_state.num_teams
    st.session_state.q_index = 0
    st.session_state.finished = False
    st.session_state.started = True

def go_prev():
    if st.session_state.q_index > 0:
        st.session_state.q_index -= 1

def go_next():
    if st.session_state.q_index < len(QUESTIONS) - 1:
        st.session_state.q_index += 1
    else:
        st.session_state.finished = True

def go_home():
    # reset seguro
    st.session_state.started = False
    st.session_state.finished = False
    for k, v in defaults.items():
        st.session_state[k] = v

def assign_team(ans_idx: int, team_idx: Optional[int]):
    i = st.session_state.q_index
    ensure_state_for_question(i)
    q = load_question(i)
    pts = int(q["answers"][ans_idx]["points"])
    prev = st.session_state.assigned_map[i][ans_idx]

    if prev is not None:
        st.session_state.team_scores[prev] = max(0, st.session_state.team_scores[prev] - pts)

    st.session_state.assigned_map[i][ans_idx] = team_idx
    if team_idx is not None:
        st.session_state.team_scores[team_idx] += pts

    st.session_state.revealed_map[i][ans_idx] = True

def reveal_only(ans_idx: int):
    i = st.session_state.q_index
    ensure_state_for_question(i)
    q = load_question(i)
    pts = int(q["answers"][ans_idx]["points"])

    prev_team = st.session_state.assigned_map[i][ans_idx]
    if prev_team is not None:
        st.session_state.team_scores[prev_team] = max(
            0, st.session_state.team_scores[prev_team] - pts
        )
        st.session_state.assigned_map[i][ans_idx] = None

    st.session_state.revealed_map[i][ans_idx] = True


def toggle_strike():
    st.session_state.show_strike = not st.session_state.show_strike
    if st.session_state.show_strike:
        st.session_state.strike_nonce += 1

def trigger_strike():
    st.session_state.show_strike = True
    st.session_state.strike_nonce = st.session_state.get("strike_nonce", 0) + 1
    st.session_state.strike_hide_at = time.time() + 2.0   # duración visible (segundos)


# ---------------------------
# Home (team count)
# ---------------------------
if not st.session_state.started and not st.session_state.finished:
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        if HAS_LOGO:
            with open("fedora_feud.png","rb") as fh:
                b64 = base64.b64encode(fh.read()).decode()
            st.markdown(f"<div style='display:flex;justify-content:center;'><img src='data:image/png;base64,{b64}' style='width:80%;height:auto;'></div>", unsafe_allow_html=True)
        teams = st.selectbox("Choose the number of teams and press Start.", options=list(range(1, 16)), index=1, help="From 1 to 15", key="teams_select")
        st.write("")
        st.button("🚀 Start", use_container_width=True, on_click=start_game, args=(teams,))
    st.stop()

# ---------------------------
# Final results
# ---------------------------
if st.session_state.finished:
    labels = team_labels(st.session_state.num_teams)
    scores = st.session_state.team_scores
    ranking = sorted(zip(labels, scores), key=lambda x: x[1], reverse=True)
    st.markdown("<div class='ff-center' style='padding:2rem 0'>", unsafe_allow_html=True)
    st.markdown("<h1 class='ff-title'>🏁 Final standings</h1>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    for pos, (lab, pts) in enumerate(ranking, start=1):
        st.markdown(f"<div class='ff-card' style='margin:.35rem 0;'><span class='ff-big'>#{pos}</span><b class='ff-big' style='margin-left: 1%; margin-right: 1%'>Team {lab}</b>{pts} pts</div>", unsafe_allow_html=True)
    st.divider()
    st.balloons()
    c1, c2 = st.columns([1,1])
    with c1:
        st.button("🏠 Home", on_click=go_home, use_container_width=True)
    with c2:
        st.button(
            "🔁 Play again",
            on_click=lambda: (
                setattr(st.session_state, 'finished', False),
                setattr(st.session_state, 'q_index', 0),
                setattr(st.session_state, 'revealed_map', {}),
                setattr(st.session_state, 'assigned_map', {}),
                setattr(st.session_state, 'team_scores', [0]*st.session_state.num_teams)
            ),
            use_container_width=True,
        )
    st.stop()

# ---------------------------
# Question screen
# ---------------------------
q = load_question(st.session_state.q_index)
ensure_state_for_question(st.session_state.q_index)
revealed = st.session_state.revealed_map[st.session_state.q_index]
assigned = st.session_state.assigned_map[st.session_state.q_index]
labels = team_labels(st.session_state.num_teams)

# Header
head_left, head_right = st.columns([4, 1])
with head_left:
    st.markdown(f"### ❓ {q['prompt']}")
with head_right:
    st.caption(f"Question {st.session_state.q_index + 1} / {len(QUESTIONS)}")

st.divider()

# Strike 
_empt, strike_col = st.columns([12, 1])
with strike_col:
    st.button("❌", use_container_width=True, on_click=trigger_strike)

# Answers
for i, a in enumerate(q['answers']):
    left, right = st.columns([11, 1])  # ~75% / 25%
    with left:
        if revealed[i]:
            st.markdown(
                f"<div class='ff-card ff-success ff-center popIn'><div class='ff-big'>{a['text']}</div><div>{a['points']} pts</div></div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<div class='ff-card ff-center'><div class='ff-num'>#{i+1}</div></div>",
                unsafe_allow_html=True,
            )

    with right:
        dd_key = f"sel_{st.session_state.q_index}_{i}" 
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
                # no hacer nada
                return
            elif val == "Show":
                reveal_only(ans_idx)
            elif val in labels:
                assign_team(ans_idx, labels.index(val))

        st.selectbox(
            f"Select team for answer {i+1}",
            options=options,
            index=options.index(st.session_state[dd_key]) if st.session_state[dd_key] in options else 0,
            key=dd_key,
            label_visibility="collapsed",
            on_change=on_select_change,
        )
    st.write("")

st.divider()

# Scoreboard
items = ''.join([f"<div class='ff-pill'><span class='lbl'>Team {l}:</span><span class='val'>{v}</span></div>" for l,v in zip(labels, st.session_state.team_scores)])
st.markdown(f"<div class='ff-toolbar'>{items}</div>", unsafe_allow_html=True)

st.divider()

# Navigation
nav1, nav2, nav3 = st.columns([1, 2, 1])
with nav1:
    st.button("⬅️ Previous", use_container_width=True, on_click=go_prev)
with nav3:
    st.button("Next ➡️", use_container_width=True, on_click=go_next)
with nav2:
    st.button("🏠 Home", on_click=go_home)

# Strike overlay
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

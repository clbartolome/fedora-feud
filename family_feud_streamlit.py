import streamlit as st
from typing import List, Dict, Optional
import json
import os
import base64

st.set_page_config(page_title="Fedora Feud", page_icon="❓", layout="wide")

# --------- Styles (Glass look) ---------
CUSTOM_CSS = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;800&display=swap');
  /* === Force solid background app-wide === */
  html, body { background: rgb(1 24 51) !important; }
  [data-testid="stAppViewContainer"] { background: rgb(1 24 51) !important; }
  [data-testid="stApp"] { background: rgb(1 24 51) !important; }
  /* If you also want the main content region specifically: */
  [data-testid="stAppViewContainer"] > .main { background: rgb(1 24 51) !important; }
  
  .stMainBlockContainer {
    padding-top: 0
  }
  
  h3 {
    font-size: 3.75rem !important;
  }
  
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
    # box-shadow: 0 10px 28px rgba(16,185,129,.20);
  }
  .ff-title { font-weight: 800; letter-spacing: .5px; }
  .ff-subtle { opacity:.85 }
  .ff-center { text-align:center; }
  .ff-big { font-size: 2rem; font-weight: 800; }
  .ff-num { font-size: 1.8rem; font-weight: 800; opacity:.95 }

  /* Compact team buttons */
  .stButton>button {
    border-radius: 9px !important; padding: .24rem .4rem; font-weight: 700; font-size: .8rem;
    border: 1px solid white;
    background: transparent;
    color: #fff; box-shadow: 0 5px 12px rgba(79,70,229,.26);
    transition: transform .06s ease, filter .2s ease;
    min-width: 30px;
  }
  .stButton>button:hover { filter: brightness(1.07) }
  .stButton>button:active { transform: translateY(1px) }

  [data-testid="stMetricValue"] { font-weight:800; }

  /* One-line toolbar */
  .ff-toolbar { display:flex; gap:10px; align-items:center; white-space:nowrap; overflow-x:auto; padding:.25rem .25rem; }
  .ff-pill { display:inline-flex; align-items:center; gap:8px; backdrop-filter:blur(6px); background: rgba(255,255,255,0.08); border:1px solid rgba(255,255,255,0.15); border-radius:999px; padding:6px 10px; }
  .ff-pill .lbl { font-weight:700 }
  .ff-pill .val { font-weight:800 }

  hr { border-color: rgba(255,255,255,.08) !important; }

  @keyframes popIn { from{ transform: scale(.98); opacity:.0 } to{ transform: scale(1); opacity:1 } }
  .popIn { animation: popIn .18s ease-out; }
  #MainMenu {visibility: hidden;}
  header {visibility: hidden;}
  footer {visibility: hidden;}
  
  /* --- Strike overlay --- */
  .ff-strike {
    position: fixed; inset: 0;
    display: flex; align-items: center; justify-content: center;
    z-index: 10000; /* por encima de todo */
    pointer-events: none; /* no bloquea clics */
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
    0%   { transform: scale(.6) rotate(-8deg); opacity: 0; }
    60%  { transform: scale(1.1) rotate(-8deg); opacity: 1; }
    100% { transform: scale(1)   rotate(-8deg); opacity: 1; }
  }
  @keyframes strikeFlash {
    0%   { opacity: .0; }
    30%  { opacity: .6; }
    100% { opacity: .0; }
  }

  /* --- Floating "eye" reveal icon --- */
  .ff-card-wrap {
    position: relative;
    display: inline-block;
    width: 100%;
  }
  .ff-eye-btn {
    position: absolute;
    top: 8px;
    right: 12px;
    background: rgba(0,0,0,0.45);
    border-radius: 50%;
    width: 30px; height: 30px;
    display: flex; align-items: center; justify-content: center;
    opacity: 0;
    transition: opacity .25s ease, transform .15s ease;
    cursor: pointer;
    border: 1px solid rgba(255,255,255,0.25);
  }
  .ff-card-wrap:hover .ff-eye-btn {
    opacity: 1;
  }
  .ff-eye-btn:hover {
    transform: scale(1.1);
    background: rgba(255,255,255,0.15);
  }
  .ff-eye-btn span {
    font-size: 1.1rem;
    color: white;
    pointer-events: none;
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
            if isinstance(prompt, str) and isinstance(answers, list) and 1 <= len(answers) <= 6:
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

QUESTIONS: List[Question] = load_questions_from_file("questions.json")
HAS_LOGO = os.path.exists("fedora_feud.png")

# ---------------------------------
# Game state
# ---------------------------------
if "started" not in st.session_state:
    st.session_state.started = False
if "finished" not in st.session_state:
    st.session_state.finished = False
if "q_index" not in st.session_state:
    st.session_state.q_index = 0
if "num_teams" not in st.session_state:
    st.session_state.num_teams = 2
if "team_scores" not in st.session_state:
    st.session_state.team_scores: List[int] = []
# Per question
if "revealed_map" not in st.session_state:
    st.session_state.revealed_map: Dict[int, List[bool]] = {}
if "assigned_map" not in st.session_state:
    st.session_state.assigned_map: Dict[int, List[Optional[int]]] = {}
if "show_strike" not in st.session_state:
    st.session_state.show_strike = False
if "strike_nonce" not in st.session_state:
    st.session_state.strike_nonce = 0  # para reanimar si quisieras


# ---------------------------
# Helpers
# ---------------------------

def team_labels(n: int) -> List[str]:
    base = [chr(ord('A') + i) for i in range(26)]
    return base[:n]


def clamp(n, min_n, max_n):
    return max(min_n, min(n, max_n))


def load_question(i: int) -> Question:
    return QUESTIONS[i % len(QUESTIONS)]


def ensure_state_for_question(i: int):
    q = load_question(i)
    n_answers = clamp(len(q["answers"]), 1, 6)
    if i not in st.session_state.revealed_map:
        st.session_state.revealed_map[i] = [False] * n_answers
    else:
        cur = st.session_state.revealed_map[i]
        if len(cur) != n_answers:
            st.session_state.revealed_map[i] = (cur + [False] * n_answers)[:n_answers]
    if i not in st.session_state.assigned_map:
        st.session_state.assigned_map[i] = [None] * n_answers
    else:
        cur2 = st.session_state.assigned_map[i]
        if len(cur2) != n_answers:
            st.session_state.assigned_map[i] = (cur2 + [None] * n_answers)[:n_answers]


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
    st.session_state.started = False
    st.session_state.finished = False
    for key in st.session_state.keys():
        del st.session_state[key]


def assign_team(ans_idx: int, team_idx: int):
    i = st.session_state.q_index
    ensure_state_for_question(i)
    q = load_question(i)
    pts = int(q["answers"][ans_idx]["points"]) if ans_idx < len(q["answers"]) else 0

    prev = st.session_state.assigned_map[i][ans_idx]
    # Toggle: same team -> unassign (subtract points), keep revealed
    if prev == team_idx:
        st.session_state.assigned_map[i][ans_idx] = None
        if 0 <= team_idx < len(st.session_state.team_scores):
            st.session_state.team_scores[team_idx] = max(0, st.session_state.team_scores[team_idx] - pts)
        st.session_state.revealed_map[i][ans_idx] = True
        return

    # Move points if previously assigned to another team
    if prev is not None and 0 <= prev < len(st.session_state.team_scores):
        st.session_state.team_scores[prev] = max(0, st.session_state.team_scores[prev] - pts)

    # Assign to new team
    st.session_state.assigned_map[i][ans_idx] = team_idx
    if 0 <= team_idx < len(st.session_state.team_scores):
        st.session_state.team_scores[team_idx] += pts
    st.session_state.revealed_map[i][ans_idx] = True
    
def toggle_strike():
    """Activa/desactiva la X gigante."""
    st.session_state.show_strike = not st.session_state.show_strike
    if st.session_state.show_strike:
        st.session_state.strike_nonce += 1  # fuerza la animación al aparecer

def reveal_only(ans_idx: int):
    """Revela una respuesta sin sumar puntos a ningún equipo."""
    i = st.session_state.q_index
    ensure_state_for_question(i)
    st.session_state.revealed_map[i][ans_idx] = True

# ---------------------------
# Home (team count)
# ---------------------------
if not st.session_state.started and not st.session_state.finished:

    
    centered = st.container()
    with centered:
        c1, c2, c3 = st.columns([1,2,1])
        with c2:
            b64 = base64.b64encode(open("fedora_feud.png","rb").read()).decode()
            st.markdown(f"""
            <div style="display:flex;justify-content:center;">
            <img src="data:image/png;base64,{b64}" style="width:80%;height:auto;margin:0;padding:0;">
            </div>
            """, unsafe_allow_html=True)
            teams = st.selectbox("Choose the number of teams and press Start.", options=list(range(1, 16)), index=1, help="From 1 to 15", key="teams_select")
            st.write("")
            st.button("🚀 Start", use_container_width=True, on_click=start_game, args=(teams,))
            st.markdown("</div>", unsafe_allow_html=True)
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


# Header: logo + question text

head_left, head_right = st.columns([4, 1])
with head_left:
    st.markdown(f"### ❓ {q['prompt']}")
with head_right:
    st.caption(f"Question {st.session_state.q_index + 1} / {len(QUESTIONS)}")

st.divider()

# Strike controls (toggle + replay)
strike_col1, strike_col2, _ = st.columns([1,1,6])
with strike_col1:
    st.button("❌", use_container_width=True, on_click=toggle_strike)


# Answers and team assignment
num = len(revealed)
for i, a in enumerate(q['answers']):
    left, right = st.columns([9, 3])  # ~75% answer / 25% buttons
    with left:
        if revealed[i]:
            st.markdown(
                f"<div class='ff-card ff-success ff-center popIn'><div class='ff-big'>{a['text']}</div><div>{a['points']} pts</div></div>",
                unsafe_allow_html=True,
            )
        else:
          # Tarjeta con número y botón "ojo" flotante para revelar sin puntuar
          eye_key = f"reveal_eye_{i}"
          st.markdown("<div class='ff-card-wrap'>", unsafe_allow_html=True)

          # Crea dos columnas: tarjeta (grande) + ojo (pequeño)
          col_card, col_eye = st.columns([20, 1])

          with col_card:
              st.markdown(
                  f"<div class='ff-card ff-center'><div class='ff-num'>#{i+1}</div></div>",
                  unsafe_allow_html=True,
              )

          with col_eye:
              st.markdown(
                  "<div style='position:relative; top:8px;'>",
                  unsafe_allow_html=True,
              )
              if st.button("👁", key=eye_key, use_container_width=True):
                  reveal_only(i)
              st.markdown("</div>", unsafe_allow_html=True)

          st.markdown("</div>", unsafe_allow_html=True)

    with right:
        cols = st.columns(st.session_state.num_teams)
        for t in range(st.session_state.num_teams):
            with cols[t]:
                is_assigned = (assigned[i] == t)
                label = f"{labels[t]}{' ✓' if is_assigned else ''}"
                st.button(
                    label,
                    key=f"ans{i}_team{t}",
                    on_click=assign_team,
                    args=(i, t),
                    use_container_width=True,
                )
    st.write("")

st.divider()

# Top toolbar (scores) in ONE LINE
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
    
# Strike overlay (only if active)
if st.session_state.show_strike:
    # el nonce fuerza a Streamlit a reinsertar el HTML y reproducir la animación
    st.markdown(
        f"<div class='ff-strike' id='strike-{st.session_state.strike_nonce}'><div class='ff-x'>✕</div></div>",
        unsafe_allow_html=True
    )

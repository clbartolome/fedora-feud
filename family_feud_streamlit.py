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
            cleaned.append({
                "prompt": prompt,
                "answers": [{"text": str(a.get("text", "")), "points": int(a.get("points", 0))} for a in answers if isinstance(a, dict)],
            })
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

# Strike (button aligned to the right)
_empt, strike_col = st.columns([12, 1])
with strike_col:
    st.button("❌", key="strike_btn", on_click=trigger_strike)

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
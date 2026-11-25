# 🧠 Fedora Feud

**Fedora Feud** is a fun, interactive **Family Feud–style quiz game** built with [Streamlit](https://streamlit.io/).  
Facilitators can select the number of teams, reveal answers dynamically, assign points, and even show a big red ❌ when players make a mistake.

Perfect for team-building sessions, workshops, or events!

---

## 🚀 Features

- 🎮 **Interactive gameplay** — reveal answers, assign points, and move between questions.
- 👥 **Up to 15 teams** — dynamically displayed on the scoreboard.
- 🧾 **JSON-based questions** — easy to edit and extend.
- 💥 **Strike system (❌)** — show a visual strike for wrong answers (auto-disappears).
- 👁 **"Show" option** — reveal answers without awarding points to any team.
- 🪄 **Modern, glass-style UI** — clean and responsive design.
- 🐳 **Container-ready** — runs easily with **Podman** or **Docker**.

---

## 🧩 Project Structure

```
fedora-feud/
│
├── family_feud_streamlit.py   # Main Streamlit app
├── questions.json             # Game questions & answers
├── fedora_feud.png            # Logo displayed in the app
└── Dockerfile / Containerfile # For containerized builds
```

---

## ⚙️ How to Run Locally

### 1. Install dependencies

```bash
pip install streamlit
```

### 2. Run the app

```bash
streamlit run family_feud_streamlit.py
```

Then open your browser at:
```
http://localhost:8501
```

---

## 🧱 Building & Running in a Container

You can use either **Podman** or **Docker**.

### Build the image

```bash
podman build -t fedora-feud:2.6 .
```

### Run the container

```bash
podman run -p 8501:8501 fedora-feud:2.6
```

Then visit:
```
http://localhost:8501
```

---

## 🧾 Questions File Format

The `files/questions.json` file defines the quiz as a list of rounds.  
Each round has a **title** and **questions**. Each question has a **prompt** and a list of **answers** with point values. Rounds play in order from first to last.

```json
{
  "rounds": [
    {
      "title": "Round 1",
      "questions": [
        {
          "prompt": "Name something people double-check before leaving home",
          "answers": [
            {"text": "Keys", "points": 32},
            {"text": "Phone", "points": 27},
            {"text": "Wallet", "points": 18}
          ]
        }
      ]
    }
  ]
}
```

You can add as many rounds and questions as you like.

---

## 🎨 Customization

- **Logo:** replace `fedora_feud.png` with your own image (same filename).
- **Theme color:** update the RGB value in the CSS block near the top of the Python file.
- **Number of teams:** adjustable from the start screen (1–15).

---

## ☁️ Running in OCP (using Quay.io)

For this section we're using [Quay.io](https://quay.io):

```bash
podman tag fedora-feud:2.6 quay.io/calopezb/fedora-feud:2.6
podman login quay.io
podman push quay.io/calopezb/fedora-feud:2.6
```

Then you can pull and run it anywhere with:

```bash
podman run -p 8501:8501 quay.io/calopezb/fedora-feud:2.6
```

To start the app in OCP:

```bash
# Create a project
oc new-project fedora-feud

# Deploy the app
oc new-app --image=quay.io/calopezb/fedora-feud:2.6 --name=fedora-feud

# Expose the app
oc expose svc fedora-feud --port 8501  

# (Optional) Update Questions
oc create cm --from-file=files/questions.json questions 
oc set volume deploy fedora-feud --add --name questions --type configmap --configmap-name questions --mount-path /opt/app-root/src/files
```

---

## 🏁 Credits

Built by **Carlos López Bartolomé**  
Designed for **Red Hat team events** ❤️  
UI and functionality inspired by *Family Feud*.
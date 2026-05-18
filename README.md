# Last Message

AI-powered emergency communication when panic takes over.

When words fail, AI helps humans be heard.

Last Message is a Streamlit-based emergency intelligence app built for the Gemma 4 Good Hackathon. It transforms chaotic panic input into concise, actionable rescue communication for civilians, families, and responders.

#### Video Pitch: [https://youtu.be/1Tq16hbdz48](https://youtu.be/1Tq16hbdz48)

#### Screenshots

<img width="1777" height="3254" alt="screencapture-localhost-8501-2026-05-19-00_37_51 (2)" src="https://github.com/user-attachments/assets/9dbaec9e-bb2a-45d3-bb73-abb7ef4f53f0" />
<img width="1439" height="2309" alt="screencapture-localhost-8501-2026-05-19-00_38_24" src="https://github.com/user-attachments/assets/ec4ac3c0-e0f3-4135-a0aa-f15471bbc359" />
<img width="1439" height="2309" alt="screencapture-localhost-8501-2026-05-19-00_38_40" src="https://github.com/user-attachments/assets/b5327f52-4fba-4188-a61b-a1684f561c7a" />
<img width="1439" height="2309" alt="screencapture-localhost-8501-2026-05-19-00_39_18" src="https://github.com/user-attachments/assets/788be73c-12f5-4fa8-86b4-35d2f4fcd3e6" />
<img width="1439" height="2309" alt="screencapture-localhost-8501-2026-05-19-00_38_54" src="https://github.com/user-attachments/assets/fc79deac-a84e-48b5-872f-cd746d6af377" />
<img width="1439" height="3183" alt="screencapture-localhost-8501-2026-05-19-00_39_37" src="https://github.com/user-attachments/assets/5f769719-e596-4bcc-b23d-6928fd8b2d0e" />


## Why this project exists
In real emergencies, people do not communicate in perfect sentences. They speak in fragments, fear, and urgency. Last Message focuses on cognitive clarity under stress:

- panic speech or text in
- calm structured rescue output out
- local-first inference for resilience
- scannable emergency UI for decision-making under pressure

## Core capabilities
- PANIC MODE with voice capture and fallback dictation path
- Emotional state detection (stress, panic severity, clarity)
- Adaptive response style (shorter, calmer instructions under high panic)
- Structured emergency packet generation
- Family-safe SMS output
- Low-connectivity compressed packet
- Multimodal scene analysis from uploaded disaster images
- Network failure simulation with local failover narrative
- Multi-agent emergency consensus (Medic, Structural, Rescue)
- Responder HUD view with tactical mini-metrics
- Multilingual emergency mode (Hindi, Telugu, Spanish, Arabic)

## Tech stack
- Python 3.11+
- Streamlit
- LM Studio (OpenAI-compatible local endpoint)
- OpenRouter (fallback cloud inference)
- Browser SpeechRecognition API
- HTML/CSS/JS embedded in Streamlit components
- Requests + dotenv

## Architecture
```mermaid
flowchart TD
    A["Voice / Text Panic Input"] --> B["Transcript + Stress Signals"]
    B --> C["Gemma Prompting Layer"]
    C --> D{"Routing"}
    D --> E["LM Studio Local Gemma"]
    D --> F["OpenRouter Gemma Fallback"]
    E --> G["Emergency Packet JSON"]
    F --> G
    G --> H["Essential View"]
    G --> I["Responder HUD"]
    G --> J["Team Consensus"]
    G --> K["Multilingual Output"]

    L["Scene Image Upload"] --> M["Gemma Multimodal Analysis"] --> N["Hazard Intelligence Cards"]

    O["Simulate Network Failure"] --> D
```

## Request lifecycle
```mermaid
sequenceDiagram
    participant U as User
    participant UI as Streamlit UI
    participant R as Router
    participant L as LM Studio
    participant O as OpenRouter

    U->>UI: Panic message / transcript
    UI->>UI: Emotional state detection
    UI->>R: Inference request
    alt Local available
        R->>L: Chat completion
        L-->>R: Structured response
    else Local unavailable/fails
        R->>O: Chat completion
        O-->>R: Structured response
    end
    R-->>UI: Emergency packet
    UI-->>U: Essential actions + responder intelligence
```

## Repository structure
```text
.
├── app.py
├── requirements.txt
├── README.md
├── assets/
├── components/
│   ├── __init__.py
│   ├── ui.py
│   └── voice.py
├── prompts/
│   └── emergency_packet_prompt.txt
└── utils/
    ├── __init__.py
    ├── config.py
    ├── inference.py
    ├── parser.py
    └── prompting.py
```

## Setup
### 1) Clone
```bash
git clone https://github.com/harishkotra/last-message.git
cd last-message
```

### 2) Install
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3) Configure environment
```bash
cp .env.example .env
```

Set values in `.env`:
```env
LM_STUDIO_ENDPOINT=http://localhost:1234/v1/chat/completions
LM_STUDIO_MODEL=google/gemma-4-e4b
OPENROUTER_ENDPOINT=https://openrouter.ai/api/v1/chat/completions
OPENROUTER_MODEL=google/gemma-3-12b-it:free
OPENROUTER_API_KEY=your_key_here
```

### 4) Run app
```bash
streamlit run app.py
```

## LM Studio quick setup
1. Install LM Studio.
2. Download a Gemma model compatible with your hardware.
3. Start local server mode.
4. Confirm endpoint is reachable at `http://localhost:1234/v1/chat/completions`.

## Key implementation snippets
### Local-first with cloud fallback
```python
def run_text_inference(system_prompt: str, user_prompt: str, cfg: ModelConfig) -> str:
    primary, cloud_available = provider_state(cfg)
    if primary is None:
        raise InferenceError("No model provider configured in .env")

    try:
        if primary == "local":
            return run_lm_studio_inference(system_prompt, user_prompt, cfg)
        return run_openrouter_inference(system_prompt, user_prompt, cfg)
    except InferenceError:
        if primary == "local" and cloud_available and not st.session_state.network_failure_mode:
            return run_openrouter_inference(system_prompt, user_prompt, cfg)
        raise
```

### Stress-aware response adaptation
```python
state = emotional_state(st.session_state.panic_input)
style_line = (
    "Use very short step-by-step instructions and calming language."
    if state["response_style"] == "short"
    else "Use concise but complete instructions with calm tone."
)
system_prompt = load_emergency_system_prompt() + "\nAdaptive response mode: " + style_line
```

### Multimodal scene intelligence
```python
raw = run_image_inference(system_prompt, user_prompt, image_data_url, cfg)
st.session_state.scene_analysis = safe_json(raw, fallback)
```

## Contributing
Contributions are welcome and encouraged.

### Fork and contribute
1. Fork this repository.
2. Create a feature branch.
3. Make focused changes with tests/manual validation notes.
4. Open a pull request with screenshots for UI changes.

### Suggested contribution standards
- Keep emergency UX cognitively lightweight.
- Prefer short actionable output over verbose prose.
- Preserve local-first routing behavior.
- Avoid heavy infra additions.

### Good first features to add
- Automatic TTS playback of emergency steps
- Incident-type templates (flood/fire/collapse)
- Better geolocation fallback when permission denied
- Export packet as SMS-ready one-tap copy block
- Accessibility mode (large-font, extra contrast, dyslexia-friendly spacing)
- Structured incident timeline for responders

## Testing checklist
- Voice capture starts and stops without state conflicts
- Manual voice fallback path works
- Demo mode always produces packet (even if live inference fails)
- Local inference works with LM Studio
- Cloud fallback works when local fails
- Network failure simulation forces local routing
- Scene analysis returns compact hazard chunks

## Safety note
This is a hackathon prototype and not a certified dispatch/medical system. In real emergencies, contact official emergency services immediately.

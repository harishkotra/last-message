import streamlit as st
import streamlit.components.v1 as components


def render_voice_widget(enable_alert_sound: bool = False) -> None:
    sound_flag = "true" if enable_alert_sound else "false"

    st.caption("If recording fails here, use Manual Voice Fallback below.")

    components.html(
        f"""
        <div style="background:linear-gradient(180deg, rgba(255,77,77,0.12), rgba(255,77,77,0.03));border:1px solid rgba(255,120,120,0.45);border-radius:16px;padding:14px;box-shadow:0 0 30px rgba(255,77,77,0.16);">
          <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;">
            <button id="startBtn" style="background:#ff3b3b;color:white;border:none;border-radius:10px;padding:12px 16px;font-weight:800;cursor:pointer;min-height:48px;">🎙 START EMERGENCY RECORDING</button>
            <button id="stopBtn" style="background:#2a2f37;color:#e5e7eb;border:1px solid rgba(255,255,255,0.2);border-radius:10px;padding:12px 16px;font-weight:700;cursor:pointer;min-height:48px;">STOP</button>
          </div>

          <div style="display:flex;align-items:center;gap:10px;margin-top:10px;">
            <div id="pulse" style="width:12px;height:12px;border-radius:999px;background:#ff4d4d;opacity:0.35;"></div>
            <span id="status" style="color:#ffd0d0;font-size:0.92rem;font-weight:700;">IDLE</span>
          </div>

          <div id="wave" style="display:flex;align-items:flex-end;gap:4px;height:34px;margin-top:10px;">
            <span class="bar"></span><span class="bar"></span><span class="bar"></span><span class="bar"></span>
            <span class="bar"></span><span class="bar"></span><span class="bar"></span><span class="bar"></span>
          </div>

          <div id="live" style="margin-top:10px;color:#f8fbff;line-height:1.5;min-height:56px;font-size:1rem;">Transcript will appear here word-by-word...</div>
        </div>

        <style>
          #wave .bar {{
            display:inline-block;
            width:5px;
            height:10px;
            border-radius:8px;
            background: linear-gradient(180deg, #ff8a3d, #ff4d4d);
            opacity: 0.32;
            transform-origin: bottom;
            animation: quiet 1.2s ease-in-out infinite;
          }}
          #wave.active .bar {{
            opacity: 1;
            animation: bounce 0.75s ease-in-out infinite;
          }}
          #wave .bar:nth-child(2) {{ animation-delay: 0.1s; }}
          #wave .bar:nth-child(3) {{ animation-delay: 0.2s; }}
          #wave .bar:nth-child(4) {{ animation-delay: 0.3s; }}
          #wave .bar:nth-child(5) {{ animation-delay: 0.4s; }}
          #wave .bar:nth-child(6) {{ animation-delay: 0.5s; }}
          #wave .bar:nth-child(7) {{ animation-delay: 0.6s; }}
          #wave .bar:nth-child(8) {{ animation-delay: 0.7s; }}

          @keyframes bounce {{
            0% {{ height: 8px; }}
            50% {{ height: 34px; }}
            100% {{ height: 10px; }}
          }}
          @keyframes quiet {{
            0% {{ height: 10px; }}
            50% {{ height: 14px; }}
            100% {{ height: 10px; }}
          }}
        </style>

        <script>
          const enableSound = {sound_flag};
          const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
          const statusEl = document.getElementById('status');
          const pulse = document.getElementById('pulse');
          const wave = document.getElementById('wave');
          const live = document.getElementById('live');
          let finalTranscript = '';
          let isRecording = false;
          let manualStop = false;
          let lastStartTs = 0;
          let restartCount = 0;
          let hasReceivedAudio = false;
          let hardError = false;
          let currentTranscript = '';

          function setStatus(text) {{
            statusEl.textContent = text;
          }}

          function playTone(freq, duration) {{
            if (!enableSound) return;
            try {{
              const ctx = new (window.AudioContext || window.webkitAudioContext)();
              const osc = ctx.createOscillator();
              const gain = ctx.createGain();
              osc.type = 'sine';
              osc.frequency.value = freq;
              gain.gain.value = 0.03;
              osc.connect(gain);
              gain.connect(ctx.destination);
              osc.start();
              setTimeout(() => osc.stop(), duration);
            }} catch (e) {{}}
          }}

          function setRecording(on) {{
            pulse.style.opacity = on ? '1' : '0.35';
            pulse.style.boxShadow = on ? '0 0 0 10px rgba(255,77,77,0.0), 0 0 20px rgba(255,77,77,0.8)' : 'none';
            wave.classList.toggle('active', on);
          }}

          function syncToStreamlit(text) {{
            const liveInput = window.parent.document.querySelector('textarea[aria-label="Live Transcript"]');
            if (!liveInput) return;
            const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
            nativeSetter.call(liveInput, text);
            liveInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
          }}

          if (!SpeechRecognition) {{
            setStatus('VOICE NOT SUPPORTED IN THIS BROWSER');
            live.textContent = 'Use text mode if speech recognition is unavailable.';
          }} else {{
            const recognition = new SpeechRecognition();
            recognition.continuous = false;
            recognition.interimResults = true;
            recognition.lang = 'en-US';

            recognition.onstart = () => {{
              isRecording = true;
              setStatus('LISTENING...');
              setRecording(true);
              if (restartCount === 0) {{
                hasReceivedAudio = false;
                hardError = false;
              }}
              hasReceivedAudio = false;
              playTone(740, 120);
            }};

            recognition.onend = () => {{
              if (isRecording && !manualStop) {{
                if (restartCount < 8) {{
                  setStatus(hasReceivedAudio ? 'LISTENING...' : 'LISTENING... (waiting for speech)');
                }} else {{
                  setStatus('LISTENING... (tap STOP then START if no input)');
                }}
                try {{
                  // WebKit/Safari may end recognition quickly; restart with a short delay.
                  restartCount += 1;
                  setTimeout(() => recognition.start(), 180);
                  return;
                }} catch (e) {{
                  // Fall through to stopped state.
                }}
              }}
              isRecording = false;
              setStatus(hardError ? 'MIC ERROR' : 'RECORDING STOPPED');
              setRecording(false);
              syncToStreamlit(finalTranscript.trim());
              playTone(520, 100);
            }};

            recognition.onerror = (event) => {{
              const err = event && event.error ? event.error : 'unknown';
              if ((err === 'aborted' || err === 'no-speech' || err === 'audio-capture' || err === 'network') && isRecording && !manualStop) {{
                try {{
                  restartCount += 1;
                  setStatus('LISTENING... (recovering mic)');
                  setTimeout(() => recognition.start(), 220);
                  return;
                }} catch (e) {{
                  // fallthrough
                }}
              }}

              isRecording = false;
              if (err === 'not-allowed' || err === 'service-not-allowed') {{
                hardError = true;
                setStatus('MIC PERMISSION BLOCKED');
                live.textContent = 'Allow microphone access in browser settings.';
              }} else {{
                hardError = true;
                setStatus('MIC ERROR: ' + err);
              }}
              setRecording(false);
            }};

            recognition.onresult = (event) => {{
              let interim = '';
              for (let i = event.resultIndex; i < event.results.length; i++) {{
                const transcript = event.results[i][0].transcript;
                if (transcript && transcript.trim().length > 0) hasReceivedAudio = true;
                if (event.results[i].isFinal) finalTranscript += transcript + ' ';
                else interim += transcript;
              }}
              const combined = (finalTranscript + interim).trim();
              currentTranscript = combined;
              live.textContent = combined || 'Listening...';
            }};

            document.getElementById('startBtn').onclick = () => {{
              manualStop = false;
              hardError = false;
              restartCount = 0;
              finalTranscript = '';
              currentTranscript = '';
              lastStartTs = Date.now();
              setStatus('REQUESTING MICROPHONE...');
              live.textContent = 'Waiting for microphone permission...';
              try {{
                recognition.start();
              }} catch (e) {{
                setStatus('MIC ERROR: ' + e.message);
              }}
            }};
            document.getElementById('stopBtn').onclick = () => {{
              manualStop = true;
              isRecording = false;
              setStatus('FINALIZING TRANSCRIPT...');
              const best = (currentTranscript || finalTranscript || '').trim();
              if (best) {{
                syncToStreamlit(best);
                live.textContent = best;
              }} else {{
                live.textContent = 'No speech captured. Try again or use Manual Voice Fallback below.';
              }}
              recognition.stop();
            }};
          }}
        </script>
        """,
        height=290,
    )

    st.markdown("#### Manual Voice Fallback")
    st.caption("Use your phone/computer voice keyboard (mic key) in this text box if browser recording is blocked.")
    st.text_area(
        "Manual Voice Fallback",
        key="manual_voice_fallback",
        placeholder="Tap your keyboard mic and dictate here...",
        height=80,
    )

document.addEventListener("DOMContentLoaded", () => {
  const $ = (id) => document.getElementById(id);

  const els = {
    message: $("message"),
    transcript: $("transcript"),
    answer: $("answer"),
    temp: $("temp"),
    hum: $("hum"),
    dist1: $("dist1"),
    dist2: $("dist2"),
    dist3: $("dist3"),
    led: $("led"),
    audio: $("remote-audio"),
    textInput: $("text-input"),
    sendText: $("send-text"),
    recordBtn: $("record-btn"),
    stopBtn: $("stop-btn"),
    iaPanel: $("ia-panel"),
    inputPanel: $("input-panel"),
  };

  const EDGE_STATUS_ENDPOINT = "/edge/status";
  const EDGE_TEXT_ENDPOINT = "/edge/interact/text";
  const EDGE_AUDIO_ENDPOINT = "/edge/interact/audio";

  const companyId = "flexmedia";
  const sessionId = "sessao-demo";

  let busy = false;
  let polling = false;
  let lastTranscript = "";
  let lastAnswer = "";

  function setText(el, value, fallback = "") {
    if (!el) return;
    el.textContent = value ?? fallback;
  }

  function show(el, visible) {
    if (!el) return;
    el.hidden = !visible;
  }

  function normalizeState(state) {
    if (state === "alerta") return "alerta";
    if (state === "sessao") return "sessao";
    if (state === "convite") return "convite";
    return "espera";
  }

  function applyScreenState(rawState) {
    const screen = document.querySelector(".screen");
    const state = normalizeState(rawState);

    if (!screen) return;

    screen.classList.remove("convite", "sessao", "alerta", "espera");
    screen.dataset.state = state;
    screen.classList.add(state);
  }

  function renderState(data) {
    const state = normalizeState(data.totem_state);

    applyScreenState(state);

    if (state === "sessao") {
      show(els.iaPanel, true);
      show(els.inputPanel, true);

      if (lastTranscript && lastTranscript.trim()) {
        setText(els.transcript, lastTranscript);
        show(els.transcript, true);
      } else {
        setText(els.transcript, "");
        show(els.transcript, false);
      }

      if (lastAnswer && lastAnswer.trim()) {
        setText(els.message, lastAnswer);
      } else {
        setText(els.message, "Ola, sou o totem inteligente FlexMedia. Como posso lhe ajudar?");
      }

      show(els.answer, false);
      return;
    }

    show(els.iaPanel, false);
    show(els.transcript, false);
    show(els.answer, false);

    if (els.audio) {
      els.audio.removeAttribute("src");
      els.audio.load();
      show(els.audio, false);
    }

    lastTranscript = "";
    lastAnswer = "";

    if (state === "convite") {
      setText(els.message, "Chegue mais perto para iniciar o totem");
      return;
    }

    if (state === "alerta") {
      setText(els.message, data.message || "Atencao: objeto muito proximo detectado.");
      return;
    }

    setText(els.message, "");
  }

  function updateUI(data) {
    renderState(data);

    setText(els.temp, data.temperature != null ? `${data.temperature} °C` : "--");
    setText(els.hum, data.humidity != null ? `${data.humidity} %` : "--");
    setText(els.dist1, data.distance_sensor_1_cm != null ? `${data.distance_sensor_1_cm} cm` : "--");
    setText(els.dist2, data.distance_sensor_2_cm != null ? `${data.distance_sensor_2_cm} cm` : "--");
    setText(els.dist3, data.distance_sensor_3_cm != null ? `${data.distance_sensor_3_cm} cm` : "--");
    setText(els.led, data.led ? "Ligado" : "Desligado");
  }

  function updateCloudResponse(data) {
    lastTranscript = data.transcript || "";
    lastAnswer = data.answer_text || "";

    const screen = document.querySelector(".screen");
    const currentState = screen?.dataset?.state || "espera";

    if (currentState === "sessao") {
      if (lastTranscript.trim()) {
        setText(els.transcript, lastTranscript);
        show(els.transcript, true);
      } else {
        setText(els.transcript, "");
        show(els.transcript, false);
      }

      if (lastAnswer.trim()) {
        setText(els.message, lastAnswer);
      } else {
        setText(els.message, "Ola, sou o totem inteligente FlexMedia. Como posso lhe ajudar?");
      }
    }

    if (els.audio) {
      if (data.audio_url) {
        els.audio.src = `${data.audio_url}?t=${Date.now()}`;
        els.audio.load();
        show(els.audio, true);
        els.audio.play().catch(() => {});
      } else {
        els.audio.removeAttribute("src");
        els.audio.load();
        show(els.audio, false);
      }
    }
  }

  function setBusy(nextBusy, messageText = "") {
    busy = nextBusy;

    if (els.sendText) {
      els.sendText.disabled = nextBusy;
      els.sendText.style.opacity = nextBusy ? "0.6" : "1";
    }

    if (els.recordBtn) {
      els.recordBtn.disabled = nextBusy;
      els.recordBtn.style.opacity = nextBusy ? "0.6" : "1";
    }

    if (els.stopBtn) {
      els.stopBtn.disabled = true;
      els.stopBtn.style.opacity = "0.6";
    }

    if (messageText && normalizeState(document.querySelector(".screen")?.dataset?.state) === "sessao") {
      setText(els.message, messageText);
    }
  }

  async function fetchStatus() {
    try {
      const response = await fetch(EDGE_STATUS_ENDPOINT, {
        method: "GET",
        cache: "no-store",
        headers: { Accept: "application/json" }
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      updateUI(data);
    } catch (error) {
      console.error("[integration] erro ao buscar /edge/status:", error);
    }
  }

  async function sendTextToEdge(message) {
    if (busy) return;

    setBusy(true, "...");

    try {
      const response = await fetch(EDGE_TEXT_ENDPOINT, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json"
        },
        body: JSON.stringify({
          company_id: companyId,
          session_id: sessionId,
          message: message.trim()
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      updateCloudResponse(data.cloud_result || {});
    } catch (error) {
      console.error("[integration] erro ao enviar texto:", error);
      setText(els.message, `Erro no edge: ${error.message}`, "Erro no edge");
    } finally {
      setBusy(false);
    }
  }

  async function sendAudioToEdge() {
    if (busy) return;

    setBusy(true, "...");

    try {
      const response = await fetch(EDGE_AUDIO_ENDPOINT, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json"
        },
        body: JSON.stringify({
          company_id: companyId,
          session_id: sessionId
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      updateCloudResponse(data.cloud_result || {});
    } catch (error) {
      console.error("[integration] erro ao capturar audio no edge:", error);
      setText(els.message, `Erro no edge audio: ${error.message}`, "Erro no edge audio");
    } finally {
      setBusy(false);
    }
  }

  if (els.sendText) {
    els.sendText.addEventListener("click", async () => {
      const message = els.textInput ? els.textInput.value : "";

      if (!message || !message.trim()) {
        setText(els.message, "Digite uma mensagem para enviar.", "Digite uma mensagem para enviar.");
        return;
      }

      await sendTextToEdge(message);

      if (els.textInput) {
        els.textInput.value = "";
      }
    });
  }

  if (els.textInput) {
    els.textInput.addEventListener("keydown", async (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        if (els.sendText) {
          els.sendText.click();
        }
      }
    });
  }

  if (els.recordBtn) {
    els.recordBtn.addEventListener("click", async () => {
      await sendAudioToEdge();
    });
  }

  fetchStatus();

  async function loop() {
    if (polling) return;
    polling = true;

    try {
      await fetchStatus();
    } finally {
      polling = false;
      window.setTimeout(loop, 1000);
    }
  }

  window.setTimeout(loop, 1000);
});

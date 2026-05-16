document.addEventListener("DOMContentLoaded", () => {
  const $ = (id) => document.getElementById(id);

  const els = {
    wsStatus: $("ws-status"),
    message: $("message"),
    subtitle: $("subtitle"),
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
  };

  const EDGE_STATUS_ENDPOINT = "/edge/status";
  const EDGE_TEXT_ENDPOINT = "/edge/interact/text";
  const EDGE_AUDIO_ENDPOINT = "/edge/interact/audio";

  const companyId = "flexmedia";
  const sessionId = "sessao-demo";

  let busy = false;
  let polling = false;

  if (els.wsStatus) {
    els.wsStatus.textContent = "Modo: polling HTTP (/edge/status) + edge interact";
  }

  function setText(el, value, fallback = "--") {
    if (!el) return;
    el.textContent = value ?? fallback;
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

  function updateSubtitle(data) {
    if (!els.subtitle) return;

    if (data.totem_state === "alerta") {
      els.subtitle.textContent = "Alerta ativo no totem";
    } else if (data.totem_state === "sessao") {
      els.subtitle.textContent = "Sessao iniciada";
    } else if (data.totem_state === "convite") {
      els.subtitle.textContent = "Visitante detectado";
    } else {
      els.subtitle.textContent = "Sistema em espera";
    }
  }

  function updateUI(data) {
    applyScreenState(data.totem_state);

    setText(els.message, data.message, "Aguardando visitante");
    updateSubtitle(data);

    setText(els.temp, data.temperature != null ? `${data.temperature} °C` : "--");
    setText(els.hum, data.humidity != null ? `${data.humidity} %` : "--");
    setText(els.dist1, data.distance_sensor_1_cm != null ? `${data.distance_sensor_1_cm} cm` : "--");
    setText(els.dist2, data.distance_sensor_2_cm != null ? `${data.distance_sensor_2_cm} cm` : "--");
    setText(els.dist3, data.distance_sensor_3_cm != null ? `${data.distance_sensor_3_cm} cm` : "--");
    setText(els.led, data.led ? "Ligado" : "Desligado");
  }

  function updateCloudResponse(data) {
    setText(els.transcript, data.transcript || "Sem transcript", "Sem transcript");
    setText(els.answer, data.answer_text || "Sem resposta", "Sem resposta");

    if (els.audio) {
      if (data.audio_url) {
        els.audio.src = `${data.audio_url}?t=${Date.now()}`;
        els.audio.load();
        els.audio.play().catch(() => {});
      } else {
        els.audio.removeAttribute("src");
        els.audio.load();
      }
    }
  }

  function setBusy(nextBusy, answerText = "") {
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

    if (answerText && els.answer) {
      els.answer.textContent = answerText;
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

      if (els.wsStatus) {
        els.wsStatus.textContent = `Modo: polling HTTP (/edge/status) + edge interact | estado: ${normalizeState(data.totem_state)}`;
      }
    } catch (error) {
      console.error("[integration] erro ao buscar /edge/status:", error);
      if (els.wsStatus) {
        els.wsStatus.textContent = "Erro ao ler /edge/status";
      }
    }
  }

  async function sendTextToEdge(message) {
    if (busy) return;

    setBusy(true, "Enviando texto para o Raspberry...");

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
      setText(els.answer, `Erro no edge: ${error.message}`, "Erro no edge");
    } finally {
      setBusy(false);
    }
  }

  async function sendAudioToEdge() {
    if (busy) return;

    setBusy(true, "Gravando audio no Raspberry...");

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
      setText(els.answer, `Erro no edge audio: ${error.message}`, "Erro no edge audio");
    } finally {
      setBusy(false);
    }
  }

  if (els.sendText) {
    els.sendText.addEventListener("click", async () => {
      const message = els.textInput ? els.textInput.value : "";

      if (!message || !message.trim()) {
        setText(els.answer, "Digite uma mensagem para enviar.", "Digite uma mensagem para enviar.");
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

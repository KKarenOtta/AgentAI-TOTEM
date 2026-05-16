document.addEventListener("DOMContentLoaded", () => {
  const $ = (id) => document.getElementById(id);

  const els = {
    screen: $("screen"),
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
  const EDGE_SESSION_START_ENDPOINT = "/edge/session/start";
  const EDGE_SESSION_END_ENDPOINT = "/edge/session/end";

  const companyId = "flexmedia";
  const sessionId = "sessao-demo";

  const GREETING_TEXT = "Ola, sou o totem inteligente FlexMedia. Como posso lhe ajudar?";
  const GREETING_AUDIO_URL = "/static/audio/saudacao.mp3";
  const INACTIVITY_MS = 9000;
  const SESSION_END_DISTANCE_CM = 100;
  const EXTREME_TEMP_MIN = 5;
  const EXTREME_TEMP_MAX = 40;

  let busy = false;
  let polling = false;
  let lastTranscript = "";
  let lastAnswer = "";
  let sessionActive = false;
  let localSessionStarted = false;
  let inactivityTimer = null;
  let lastKnownState = "espera";
  let isAudioPlaying = false;

  function setText(el, value, fallback = "") {
    if (!el) return;
    el.textContent = value ?? fallback;
  }

  function show(el, visible) {
    if (!el) return;
    el.hidden = !visible;
  }

  function hideAudioElement() {
    if (!els.audio) return;
    els.audio.hidden = true;
    els.audio.removeAttribute("controls");
    els.audio.style.display = "none";
    els.audio.style.width = "0";
    els.audio.style.height = "0";
    els.audio.style.opacity = "0";
    els.audio.style.pointerEvents = "none";
  }

  function normalizeState(state) {
    if (state === "alerta") return "alerta";
    if (state === "sessao") return "sessao";
    if (state === "convite") return "convite";
    return "espera";
  }

  function isExtremeTemperature(temp) {
    if (temp == null || Number.isNaN(Number(temp))) return false;
    return Number(temp) <= EXTREME_TEMP_MIN || Number(temp) >= EXTREME_TEMP_MAX;
  }

  function getPrimaryDistance(data) {
    const candidates = [
      Number(data?.distance_sensor_1_cm),
      Number(data?.distance_sensor_2_cm),
      Number(data?.distance_sensor_3_cm),
    ].filter((value) => Number.isFinite(value) && value > 0);

    if (!candidates.length) return null;
    return Math.min(...candidates);
  }

  function getDerivedState(data) {
    if (sessionActive) return "sessao";
    if (isExtremeTemperature(data.temperature)) return "alerta";
    return "convite";
  }

  function applyScreenState(rawState) {
    const state = normalizeState(rawState);

    if (!els.screen) return;

    els.screen.classList.remove("convite", "sessao", "alerta", "espera");
    els.screen.dataset.state = state;
    els.screen.classList.add(state);
    lastKnownState = state;
  }

  function clearInactivityTimer() {
    if (inactivityTimer) {
      window.clearTimeout(inactivityTimer);
      inactivityTimer = null;
    }
  }

  function resetInactivityTimer() {
    if (!sessionActive) return;

    clearInactivityTimer();

    if (isAudioPlaying) {
      return;
    }

    inactivityTimer = window.setTimeout(() => {
      endSession("idle");
    }, INACTIVITY_MS);
  }

  function updateAudioPlayingState() {
    if (!els.audio) {
      isAudioPlaying = false;
      return;
    }

    isAudioPlaying =
      !els.audio.paused &&
      !els.audio.ended &&
      !!els.audio.src &&
      els.audio.currentTime >= 0;

    if (isAudioPlaying) {
      clearInactivityTimer();
    } else if (sessionActive) {
      resetInactivityTimer();
    }
  }

  function stopRemoteAudio() {
    if (!els.audio) return;
    els.audio.pause();
    els.audio.currentTime = 0;
    els.audio.removeAttribute("src");
    els.audio.load();
    isAudioPlaying = false;
    hideAudioElement();
  }

  function resetConversationVisuals() {
    lastTranscript = "";
    lastAnswer = "";
    setText(els.transcript, "");
    setText(els.answer, "");
    show(els.transcript, false);
    show(els.answer, false);
    stopRemoteAudio();
  }

  function ensureEndSessionButton() {
    if (document.getElementById("end-session-btn")) return;

    const button = document.createElement("button");
    button.id = "end-session-btn";
    button.type = "button";
    button.className = "admin-button admin-button-outline";
    button.textContent = "Encerrar atendimento";
    button.style.marginTop = "12px";
    button.style.width = "100%";
    button.style.maxWidth = "420px";
    button.hidden = true;

    button.addEventListener("click", async () => {
      await endSession("manual");
    });

    if (els.iaPanel && els.iaPanel.parentNode) {
      els.iaPanel.appendChild(button);
    }
  }

  function showEndSessionButton(visible) {
    const button = document.getElementById("end-session-btn");
    if (!button) return;
    button.hidden = !visible;
  }

  async function playGreetingAudio() {
    try {
      if (!els.audio) return;

      hideAudioElement();
      els.audio.src = `${GREETING_AUDIO_URL}?t=${Date.now()}`;
      els.audio.load();
      await els.audio.play();
      updateAudioPlayingState();
    } catch (error) {
      console.warn("[integration] falha ao tocar saudacao.wav:", error);
      updateAudioPlayingState();
    }
  }

  async function notifySessionStart() {
    try {
      await fetch(EDGE_SESSION_START_ENDPOINT, {
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
    } catch (error) {
      console.warn("[integration] nao foi possivel sincronizar inicio da sessao:", error);
    }
  }

  async function notifySessionEnd(reason) {
    try {
      await fetch(EDGE_SESSION_END_ENDPOINT, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json"
        },
        body: JSON.stringify({
          company_id: companyId,
          session_id: sessionId,
          reason
        })
      });
    } catch (error) {
      console.warn("[integration] nao foi possivel sincronizar fim da sessao:", error);
    }
  }

  async function startSession() {
    if (sessionActive || busy) return;

    sessionActive = true;
    localSessionStarted = true;

    applyScreenState("sessao");
    show(els.iaPanel, true);
    show(els.inputPanel, true);
    showEndSessionButton(true);

    setText(els.transcript, "");
    show(els.transcript, false);
    setText(els.message, GREETING_TEXT);

    await playGreetingAudio();
    resetInactivityTimer();
    await notifySessionStart();
  }

  async function endSession(reason = "manual") {
    if (!sessionActive && !localSessionStarted) return;

    sessionActive = false;
    localSessionStarted = false;
    busy = false;

    clearInactivityTimer();
    resetConversationVisuals();
    show(els.iaPanel, false);
    show(els.inputPanel, false);
    showEndSessionButton(false);

    applyScreenState("convite");
    setText(els.message, "Chegue mais perto e toque a tela para iniciar");

    if (els.sendText) {
      els.sendText.disabled = false;
      els.sendText.style.opacity = "1";
    }

    if (els.recordBtn) {
      els.recordBtn.disabled = false;
      els.recordBtn.style.opacity = "1";
    }

    if (els.stopBtn) {
      els.stopBtn.disabled = true;
      els.stopBtn.style.opacity = "0.6";
    }

    if (els.textInput) {
      els.textInput.value = "";
    }

    await notifySessionEnd(reason);
  }

  function renderState(data) {
    const derivedState = getDerivedState(data);
    applyScreenState(derivedState);

    if (derivedState === "sessao") {
      show(els.iaPanel, true);
      show(els.inputPanel, true);
      showEndSessionButton(true);

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
        setText(els.message, GREETING_TEXT);
      }

      return;
    }

    show(els.iaPanel, false);
    show(els.transcript, false);
    show(els.answer, false);
    showEndSessionButton(false);

    if (derivedState === "convite") {
      setText(els.message, "Chegue mais perto e toque a tela para iniciar");
      return;
    }

    if (derivedState === "alerta") {
      setText(els.message, "Temperatura fora da faixa segura.");
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

    if (sessionActive && !isAudioPlaying) {
      const distance = getPrimaryDistance(data);
      if (distance != null && distance > SESSION_END_DISTANCE_CM) {
        endSession("distance");
        return;
      }
    }
  }

  function updateCloudResponse(data) {
    lastTranscript = data.transcript || "";
    lastAnswer = data.answer_text || "";

    if (sessionActive) {
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
        setText(els.message, GREETING_TEXT);
      }
    }

    if (els.audio && data.audio_url) {
      hideAudioElement();
      els.audio.src = `${data.audio_url}?t=${Date.now()}`;
      els.audio.load();
      els.audio.play()
        .then(() => {
          updateAudioPlayingState();
        })
        .catch(() => {
          updateAudioPlayingState();
        });
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

    if (messageText && sessionActive) {
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
    if (busy || !sessionActive) return;

    setBusy(true, "...");

    try {
      resetInactivityTimer();

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
    if (busy || !sessionActive) return;

    setBusy(true, "...");

    try {
      resetInactivityTimer();

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

  function handleSessionTouchStart(event) {
    const state = normalizeState(els.screen?.dataset?.state || lastKnownState);

    const clickedInsideControl =
      event.target.closest("#input-panel") ||
      event.target.closest("#end-session-btn");

    if (clickedInsideControl) {
      if (sessionActive && !isAudioPlaying) {
        resetInactivityTimer();
      }
      return;
    }

    if (state === "convite" && !sessionActive) {
      startSession();
      return;
    }

    if (sessionActive && !isAudioPlaying) {
      resetInactivityTimer();
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
        if (sessionActive && els.sendText) {
          els.sendText.click();
        }
      }
    });

    els.textInput.addEventListener("input", () => {
      if (sessionActive && !isAudioPlaying) {
        resetInactivityTimer();
      }
    });
  }

  if (els.recordBtn) {
    els.recordBtn.addEventListener("click", async () => {
      await sendAudioToEdge();
    });
  }

  if (els.audio) {
    hideAudioElement();

    ["play", "playing"].forEach((eventName) => {
      els.audio.addEventListener(eventName, () => {
        isAudioPlaying = true;
        clearInactivityTimer();
        hideAudioElement();
      });
    });

    ["pause", "ended", "emptied"].forEach((eventName) => {
      els.audio.addEventListener(eventName, () => {
        updateAudioPlayingState();
        hideAudioElement();
      });
    });

    els.audio.addEventListener("timeupdate", () => {
      if (sessionActive && isAudioPlaying) {
        clearInactivityTimer();
      }
    });
  }

  if (els.screen) {
    els.screen.addEventListener("pointerup", handleSessionTouchStart);
  }

  ["click", "keydown", "pointerdown"].forEach((eventName) => {
    document.addEventListener(eventName, () => {
      if (sessionActive && !isAudioPlaying) {
        resetInactivityTimer();
      }
    }, true);
  });

  ensureEndSessionButton();
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

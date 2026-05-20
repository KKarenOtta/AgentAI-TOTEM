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
    recommendationsBlock: $("recommendationsBlock"),
    recommendationsList: $("recommendationsList"),
    finalBlock: $("finalBlock"),
    qr: $("qr"),
    handoff: $("handoff"),
    finalRecommendations: $("finalRecommendations"),
    finalRecommendationsList: $("finalRecommendationsList"),
  };

  const EDGE_STATUS_ENDPOINT = "/edge/status";
  const EDGE_TEXT_ENDPOINT = "/edge/interact/text";
  const EDGE_AUDIO_ENDPOINT = "/edge/interact/audio";
  const EDGE_SESSION_START_ENDPOINT = "/edge/session/start";
  const EDGE_SESSION_END_ENDPOINT = "/edge/session/end";

  function generateSessionId() {
    return `sessao-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  }

  const companyId = "FLX-001";
  /*const sessionId = "sessao-teste-01";*/

  const GREETING_TEXT = "Ola! Como posso lhe ajudar?";
  const GREETING_AUDIO_URL = "/static/audio/saudacao.mp3";
  const INACTIVITY_MS = 8000;
  const SESSION_END_DISTANCE_CM = 100;
  const QR_DISPLAY_MS = 10000;
  const EXTREME_TEMP_MIN = 10;
  const EXTREME_TEMP_MAX = 35;
  
  
  let currentSessionId = generateSessionId();
  let busy = false;
  let polling = false;
  let lastTranscript = "";
  let lastAnswer = "";
  let sessionActive = false;
  let localSessionStarted = false;
  let inactivityTimer = null;
  let lastKnownState = "espera";
  let isAudioPlaying = false;
  let currentObjectUrl = null;
  let finalScreenTimer = null;
  

  function setText(el, value, fallback = "") {
    if (!el) return;
    el.textContent = value ?? fallback;
  }

  function show(el, visible) {
    if (!el) return;
    el.hidden = !visible;
  }
  
  function normalizeRecommendations(payload) {
    if (!payload) return [];
    if (Array.isArray(payload)) return payload;
    if (Array.isArray(payload.top_actions)) return payload.top_actions;
    if (Array.isArray(payload.items)) return payload.items;
    if (Array.isArray(payload.actions)) return payload.actions;
    if (Array.isArray(payload.recommendations)) return payload.recommendations;
    return [];
  }

  function buildRecommendationCard(item) {
    const title = item.title || item.action || "Recomendamos";
    const description =
      item.description ||
      item.why ||
      "Dica pronta para continuar o atendimento.";
    const meta = [
      item.cta_label || "",
      item.coupon_code ? `Cupom: ${item.coupon_code}` : "",
      item.discount_value ? `Desconto: ${item.discount_value}` : ""
    ].filter(Boolean).join(" . ");

    return `
      <article class="recommendation-card">
        <h3>${title}</h3>
        <p>${description}</p>
        ${meta ? `<div class="recommendation-meta">${meta}</div>` : ""}
      </article>
    `;
  }

  function renderRecommendations(payload, listEl, blockEl) {
    if (!listEl || !blockEl) return;

    const items = normalizeRecommendations(payload);

    if (!items.length) {
      listEl.innerHTML = "";
      show(blockEl, false);
      return;
    }

    listEl.innerHTML = items.slice(0, 3).map(buildRecommendationCard).join("");
    show(blockEl, true);
  }

  function clearRecommendations() {
    if (els.recommendationsList) els.recommendationsList.innerHTML = "";
    if (els.finalRecommendationsList) els.finalRecommendationsList.innerHTML = "";

    show(els.recommendationsBlock, false);
    show(els.finalRecommendations, false);
  }

  function clearFinalHandoff() {
    if (els.qr) {
      els.qr.hidden = true;
      els.qr.removeAttribute("src");
    }

    if (els.handoff) {
      els.handoff.hidden = true;
      els.handoff.textContent = "";
    }

    show(els.finalBlock, false);
    clearRecommendations();
  }

  /*function renderFinalHandoff(data) {
    if (!els.finalBlock) return;

    if (els.qr && data.handoff_qr_url) {
      els.qr.src = data.handoff_qr_url;
      els.qr.hidden = false;
    }

    if (els.handoff && data.handoff_url) {
      els.handoff.textContent = data.handoff_url;
      els.handoff.hidden = false;
    }

    renderRecommendations(
      data.recommendations,
      els.finalRecommendationsList,
      els.finalRecommendations
    );

    show(els.finalBlock, true);
  }*/
  
  function renderFinalHandoff(data) {
    console.log("[totem] renderFinalHandoff =", data);

    if (!els.finalBlock) return;

    const qrUrl =
      data?.handoff_qr_url ||
      data?.handoffQrUrl ||
      data?.handoffqrurl ||
      "";

    const handoffUrl =
      data?.handoff_url ||
      data?.handoffUrl ||
      data?.handoffurl ||
      "";

    if (els.qr) {
      els.qr.onerror = () => {
        console.error("[totem] erro ao carregar QR:", els.qr.src);
        els.qr.hidden = true;
      };
  
      if (qrUrl) {
        els.qr.src = `${qrUrl}${qrUrl.includes("?") ? "&" : "?"}t=${Date.now()}`;
        els.qr.hidden = false;
      } else {
        els.qr.hidden = true;
        els.qr.removeAttribute("src");
      }
    }

    if (els.handoff) {
      if (handoffUrl) {
        els.handoff.textContent = handoffUrl;
        els.handoff.hidden = false;
      } else {
        els.handoff.textContent = "";
        els.handoff.hidden = true;
      }
    }

    renderRecommendations(
      data.recommendations,
      els.finalRecommendationsList,
      els.finalRecommendations
    );

    show(els.recommendationsBlock, false);
    show(els.inputPanel, false);
    showEndSessionButton(false);
    show(els.finalBlock, true);
    show(els.iaPanel, true);

    setText(els.message, "Atendimento finalizado. Continue no celular.");
    scheduleReturnToInvite();
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
  
  function clearFinalScreenTimer() {
    if (finalScreenTimer) {
      window.clearTimeout(finalScreenTimer);
      finalScreenTimer = null;
    }
  }

  function scheduleReturnToInvite() {
    clearFinalScreenTimer();
    finalScreenTimer = window.setTimeout(() => {
      currentSessionId = generateSessionId();
      applyScreenState("convite");
      show(els.iaPanel, false);
      show(els.inputPanel, false);
      showEndSessionButton(false);
      clearFinalHandoff();
      setText(els.message, "Chegue mais perto e toque a tela para iniciar");
    }, QR_DISPLAY_MS);
  }

  function shouldPauseAutoEnd() {
    return busy || isAudioPlaying;
  }

  function resetInactivityTimer() {
    if (!sessionActive) return;

    clearInactivityTimer();

    if (shouldPauseAutoEnd()) {
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

    if (shouldPauseAutoEnd()) {
      clearInactivityTimer();
    } else if (sessionActive) {
      resetInactivityTimer();
    }
  }

  function stopRemoteAudio() {
    if (!els.audio) return;

    try {
      els.audio.pause();
      els.audio.currentTime = 0;
      els.audio.removeAttribute("src");
      els.audio.load();
    } catch (error) {
      console.warn("[integration] falha ao parar audio remoto:", error);
    }

    if (currentObjectUrl) {
      try {
        URL.revokeObjectURL(currentObjectUrl);
      } catch (error) {
        console.warn("[integration] falha ao liberar object URL:", error);
      }
      currentObjectUrl = null;
    }

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
    clearFinalScreenTimer();
    clearFinalHandoff();
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
      console.warn("[integration] falha ao tocar saudacao.mp3:", error);
      updateAudioPlayingState();
    }
  }

  async function notifySessionStart() {
    try {
      const response = await fetch(EDGE_SESSION_START_ENDPOINT, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json"
        },
        body: JSON.stringify({
          company_id: companyId,
          session_id: currentSessionId
        })
      });

      if (!response.ok && response.status !== 404) {
        console.warn("[integration] inicio de sessao retornou", response.status);
      }
    } catch (error) {
      console.warn("[integration] nao foi possivel sincronizar inicio da sessao:", error);
    }
  }

  /*async function notifySessionEnd(reason) {
    try {
      const response = await fetch(EDGE_SESSION_END_ENDPOINT, {
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

      if (!response.ok && response.status !== 404) {
        console.warn("[integration] fim de sessao retornou", response.status);
      }
    } catch (error) {
      console.warn("[integration] nao foi possivel sincronizar fim da sessao:", error);
    }
  }*/
  async function notifySessionEnd(reason) {
    try {
      const response = await fetch(EDGE_SESSION_END_ENDPOINT, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json"
        },
        body: JSON.stringify({
          company_id: companyId,
          session_id: currentSessionId,
          reason
        })
      });

      if (!response.ok && response.status !== 404) {
        console.warn("[integration] fim de sessao retornou", response.status);
        return null;
      }

      try {
        return await response.json();
      } catch (_) {
        return null;
      }
    } catch (error) {
      console.warn("[integration] nao foi possivel sincronizar fim da sessao:", error);
      return null;
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

    stopRemoteAudio();

    const endData = await notifySessionEnd(reason);
    console.log("[totem] endSession payload =", endData);

    const hasHandoff =
      endData &&
      (
        endData.handoff_qr_url ||
        endData.handoff_url ||
        endData.handoffQrUrl ||
        endData.handoffUrl ||
        endData.handoffqrurl ||
        endData.handoffurl
      );

    if (hasHandoff) {
      renderFinalHandoff(endData);
      return;
    }

    console.warn("[totem] payload de encerramento sem QR/link:", endData);

    resetConversationVisuals();
    show(els.iaPanel, false);
    show(els.inputPanel, false);
    showEndSessionButton(false);

    applyScreenState("convite");
    setText(els.message, "Chegue mais perto e toque a tela para iniciar");
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

      if (busy) {
        setText(els.message, "...");
      } else if (lastAnswer && lastAnswer.trim()) {
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

    if (sessionActive && !shouldPauseAutoEnd()) {
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
    
    renderRecommendations(
      data.recommendations,
      els.recommendationsList,
      els.recommendationsBlock
    );

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
    
    if (
      data.handoff_qr_url ||
      data.handoff_url ||
      data.handoffQrUrl ||
      data.handoffUrl ||
      data.handoffqrurl ||
      data.handoffurl
    ) {
      renderFinalHandoff(data);
    }

    const base64 = data.audio_base64 || "";
    const audioUrl = data.audio_url || "";

    if (els.audio && base64) {
      try {
        const cleaned = base64.includes(",") ? base64.split(",").pop() : base64;
        const byteChars = atob(cleaned);
        const byteNumbers = new Array(byteChars.length);

        for (let i = 0; i < byteChars.length; i++) {
          byteNumbers[i] = byteChars.charCodeAt(i);
        }

        const byteArray = new Uint8Array(byteNumbers);
        const blob = new Blob([byteArray], { type: "audio/mpeg" });
        const objectUrl = URL.createObjectURL(blob);

        stopRemoteAudio();
        currentObjectUrl = objectUrl;

        els.audio.src = objectUrl;
        els.audio.hidden = false;
        els.audio.style.display = "block";
        els.audio.style.width = "100%";
        els.audio.style.height = "auto";
        els.audio.style.opacity = "1";
        els.audio.style.pointerEvents = "auto";
        els.audio.setAttribute("controls", "controls");
        els.audio.load();
        els.audio.play()
          .then(() => updateAudioPlayingState())
          .catch((error) => {
            console.warn("[integration] falha ao tocar audio base64:", error);
            updateAudioPlayingState();
          });
      } catch (err) {
        console.warn("[integration] falha ao converter audio_base64:", err);
      }
    } else if (els.audio && audioUrl) {
      stopRemoteAudio();

      els.audio.src = `${audioUrl}?t=${Date.now()}`;
      els.audio.hidden = false;
      els.audio.style.display = "block";
      els.audio.style.width = "100%";
      els.audio.style.height = "auto";
      els.audio.style.opacity = "1";
      els.audio.style.pointerEvents = "auto";
      els.audio.setAttribute("controls", "controls");
      els.audio.load();
      els.audio.play()
        .then(() => updateAudioPlayingState())
        .catch((error) => {
          console.warn("[integration] falha ao tocar audio_url:", error);
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

    if (busy) {
      clearInactivityTimer();
    } else if (sessionActive) {
      resetInactivityTimer();
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
      const response = await fetch(EDGE_TEXT_ENDPOINT, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json"
        },
        body: JSON.stringify({
          company_id: companyId,
          session_id: currentSessionId,
          message: message.trim()
        })
      });

      if (!response.ok) {
        let detail = "";
        try {
          const errorBody = await response.json();
          detail = errorBody?.detail ? ` - ${errorBody.detail}` : "";
        } catch (_) {}
        throw new Error(`HTTP ${response.status}${detail}`);
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
      const response = await fetch(EDGE_AUDIO_ENDPOINT, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json"
        },
        body: JSON.stringify({
          company_id: companyId,
          session_id: currentSessionId
        })
      });

      if (!response.ok) {
        let detail = "";
        try {
          const errorBody = await response.json();
          detail = errorBody?.detail ? ` - ${errorBody.detail}` : "";
        } catch (_) {}
        throw new Error(`HTTP ${response.status}${detail}`);
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
      if (sessionActive && !shouldPauseAutoEnd()) {
        resetInactivityTimer();
      }
      return;
    }

    if (state === "convite" && !sessionActive) {
      startSession();
      return;
    }

    if (sessionActive && !shouldPauseAutoEnd()) {
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
      if (sessionActive && !shouldPauseAutoEnd()) {
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
      });
    });

    ["pause", "ended", "emptied"].forEach((eventName) => {
      els.audio.addEventListener(eventName, () => {
        updateAudioPlayingState();
      });
    });

    els.audio.addEventListener("timeupdate", () => {
      if (sessionActive && isAudioPlaying) {
        clearInactivityTimer();
      }
    });

    els.audio.addEventListener("error", () => {
      console.warn("[integration] elemento de audio reportou erro");
      updateAudioPlayingState();
    });
  }

  if (els.screen) {
    els.screen.addEventListener("pointerup", handleSessionTouchStart);
  }

  ["click", "keydown", "pointerdown"].forEach((eventName) => {
    document.addEventListener(eventName, () => {
      if (sessionActive && !shouldPauseAutoEnd()) {
        resetInactivityTimer();
      }
    }, true);
  });

  ensureEndSessionButton();
  hideAudioElement();
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

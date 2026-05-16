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
    state: $("totem-state"),
    activeSensor: $("active-sensor"),
    audio: $("remote-audio"),
    textInput: $("text-input"),
    sendText: $("send-text"),
    recordBtn: $("record-btn"),
    stopBtn: $("stop-btn"),
  };

  let mediaRecorder = null;
  let audioChunks = [];
  let isRecording = false;
  let cloudBusy = false;

  const CLOUD_ENDPOINT = "/cloud/interact";
  const EDGE_STATUS_ENDPOINT = "/edge/status";

  const companyId = "flexmedia";
  const sessionId = "sessao-demo";

  if (els.wsStatus) {
    els.wsStatus.textContent = "Modo: polling HTTP (/edge/status) + cloud interact";
  }

  function setText(el, value, fallback = "--") {
    if (!el) return;
    el.textContent = value ?? fallback;
  }

  function setBusyState(busy, label = "Processando...") {
    cloudBusy = busy;

    if (els.sendText) {
      els.sendText.disabled = busy;
      els.sendText.style.opacity = busy ? "0.6" : "1";
      els.sendText.textContent = busy ? label : "Enviar texto";
    }

    if (els.recordBtn) {
      els.recordBtn.disabled = busy || isRecording;
      els.recordBtn.style.opacity = (busy || isRecording) ? "0.6" : "1";
    }

    if (els.stopBtn) {
      els.stopBtn.disabled = busy || !isRecording;
      els.stopBtn.style.opacity = (busy || !isRecording) ? "0.6" : "1";
    }
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

    if (!screen) {
      console.warn("[integration] .screen nao encontrada para aplicar estado visual");
      return;
    }

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

    setText(els.state, data.totem_state);
    setText(els.activeSensor, data.active_sensor);
    setText(els.temp, data.temperature != null ? `${data.temperature} °C` : "--");
    setText(els.hum, data.humidity != null ? `${data.humidity} %` : "--");
    setText(els.dist1, data.distance_sensor_1_cm != null ? `${data.distance_sensor_1_cm} cm` : "--");
    setText(els.dist2, data.distance_sensor_2_cm != null ? `${data.distance_sensor_2_cm} cm` : "--");
    setText(els.dist3, data.distance_sensor_3_cm != null ? `${data.distance_sensor_3_cm} cm` : "--");
    setText(els.led, data.led ? "Ligado" : "Desligado");

    if (els.answer && !els.answer.textContent.trim()) {
      els.answer.textContent = "Aguardando integracao com resposta da AWS.";
    }

    if (els.transcript && !els.transcript.textContent.trim()) {
      els.transcript.textContent = "Transcript ainda nao conectado.";
    }
  }

  async function fetchStatus() {
    try {
      const response = await fetch(EDGE_STATUS_ENDPOINT, {
        method: "GET",
        cache: "no-store",
        headers: {
          "Accept": "application/json"
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      updateUI(data);

      if (els.wsStatus) {
        els.wsStatus.textContent = `Modo: polling HTTP (/edge/status) + cloud interact | estado: ${normalizeState(data.totem_state)}`;
      }
    } catch (error) {
      console.error("[integration] erro ao buscar /edge/status:", error);

      if (els.wsStatus) {
        els.wsStatus.textContent = "Erro ao ler /edge/status";
      }
    }
  }

  function updateCloudResponse(data) {
    setText(els.transcript, data.transcript || "Sem transcript", "Sem transcript");
    setText(els.answer, data.answer_text || "Sem resposta", "Sem resposta");

    if (els.audio) {
      if (data.audio_url) {
        els.audio.src = `${data.audio_url}?t=${Date.now()}`;
        els.audio.load();

        els.audio.play().catch((err) => {
          console.warn("[integration] autoplay bloqueado:", err);
        });
      } else {
        els.audio.removeAttribute("src");
        els.audio.load();
      }
    }
  }

  async function sendToCloud({ message = "", blob = null, filename = "recording.webm" }) {
    if (cloudBusy) return;

    setBusyState(true, "Enviando...");
    setText(els.answer, "Processando resposta da AWS...", "Processando resposta da AWS...");

    try {
      const formData = new FormData();
      formData.append("company_id", companyId);
      formData.append("session_id", sessionId);

      if (message && message.trim()) {
        formData.append("message", message.trim());
      }

      if (blob) {
        formData.append("file", blob, filename);
      }

      const response = await fetch(CLOUD_ENDPOINT, {
        method: "POST",
        body: formData
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      console.log("[integration] cloud response:", data);
      updateCloudResponse(data);
    } catch (error) {
      console.error("[integration] erro ao chamar cloud:", error);
      setText(els.answer, `Erro na cloud: ${error.message}`, "Erro na cloud");
    } finally {
      setBusyState(false);
    }
  }

  async function startRecording() {
    if (cloudBusy || isRecording) return;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder = new MediaRecorder(stream);
      audioChunks = [];
      isRecording = true;

      mediaRecorder.addEventListener("dataavailable", (event) => {
        if (event.data && event.data.size > 0) {
          audioChunks.push(event.data);
        }
      });

      mediaRecorder.addEventListener("stop", async () => {
        const tracks = mediaRecorder.stream ? mediaRecorder.stream.getTracks() : [];
        tracks.forEach((track) => track.stop());

        isRecording = false;
        setBusyState(false);

        const audioBlob = new Blob(audioChunks, { type: mediaRecorder.mimeType || "audio/webm" });
        audioChunks = [];

        if (audioBlob.size > 0) {
          await sendToCloud({
            blob: audioBlob,
            filename: "totem-recording.webm"
          });
        } else {
          setText(els.answer, "Nenhum audio foi capturado.", "Nenhum audio foi capturado.");
        }
      });

      mediaRecorder.start();
      setBusyState(false);
      isRecording = true;

      if (els.transcript) {
        els.transcript.textContent = "Gravando audio...";
      }

      if (els.answer) {
        els.answer.textContent = "Quando terminar, clique em 'Parar e enviar'.";
      }

      if (els.recordBtn) {
        els.recordBtn.disabled = true;
        els.recordBtn.style.opacity = "0.6";
      }

      if (els.stopBtn) {
        els.stopBtn.disabled = false;
        els.stopBtn.style.opacity = "1";
      }
    } catch (error) {
      console.error("[integration] erro ao iniciar gravacao:", error);
      setText(els.answer, `Erro ao acessar microfone: ${error.message}`, "Erro ao acessar microfone");
      isRecording = false;
      setBusyState(false);
    }
  }

  function stopRecording() {
    if (!mediaRecorder || !isRecording) return;

    if (els.transcript) {
      els.transcript.textContent = "Enviando audio para a cloud...";
    }

    if (els.answer) {
      els.answer.textContent = "Aguardando STT/TTS/IA...";
    }

    if (mediaRecorder.state !== "inactive") {
      mediaRecorder.stop();
    }

    if (els.stopBtn) {
      els.stopBtn.disabled = true;
      els.stopBtn.style.opacity = "0.6";
    }
  }

  if (els.sendText) {
    els.sendText.addEventListener("click", async () => {
      const message = els.textInput ? els.textInput.value : "";

      if (!message || !message.trim()) {
        setText(els.answer, "Digite uma mensagem para enviar.", "Digite uma mensagem para enviar.");
        return;
      }

      await sendToCloud({ message });

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
    els.recordBtn.addEventListener("click", startRecording);
  }

  if (els.stopBtn) {
    els.stopBtn.addEventListener("click", stopRecording);
  }

  fetchStatus();

  let polling = false;

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

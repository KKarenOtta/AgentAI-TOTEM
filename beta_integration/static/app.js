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
  };

  if (els.wsStatus) {
    els.wsStatus.textContent = "Modo: polling HTTP (/edge/status)";
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

    if (!screen) {
      console.warn("[integration] .screen nao encontrada para aplicar estado visual");
      return;
    }

    screen.classList.remove("convite", "sessao", "alerta");
    screen.dataset.state = state;

    if (state !== "espera") {
      screen.classList.add(state);
    }

    console.log("[integration] visual state:", {
      state,
      className: screen.className
    });
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
    setText(els.temp, data.temperature != null ? `${data.temperature} ºC` : "--");
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
      const response = await fetch("/edge/status", {
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
      console.log("[integration] status:", data);
      updateUI(data);

      if (els.wsStatus) {
        els.wsStatus.textContent = `Modo: polling HTTP (/edge/status) | estado: ${normalizeState(data.totem_state)}`;
      }
    } catch (error) {
      console.error("[integration] erro ao buscar /edge/status:", error);

      if (els.wsStatus) {
        els.wsStatus.textContent = "Erro ao ler /edge/status";
      }
    }
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

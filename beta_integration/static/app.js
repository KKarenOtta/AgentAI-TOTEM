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

  function updateUI(data) {
    setText(els.message, data.message, "Aguardando visitante");

    if (els.subtitle) {
      if (data.totem_state === "alerta") {
        els.subtitle.textContent = "Alerta ativo no totem";
      } else if (data.totem_state === "sessao") {
        els.subtitle.textContent = "Sessao iniciada";
      } else if (data.totem_state === "convite") {
        els.subtitle.textContent = "Visitante detectado";
      } else {
        els.subtitle.textContent = "Sistema em espera";
      }document.addEventListener("DOMContentLoaded", () => {
  const $ = (id) => document.getElementById(id);
  const screen = document.querySelector(".screen");

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

  function applyScreenState(state) {
    if (!screen) return;

    screen.classList.remove("convite", "sessao", "alerta");

    if (state === "alerta") {
      screen.classList.add("alerta");
    } else if (state === "sessao") {
      screen.classList.add("sessao");
    } else if (state === "convite") {
      screen.classList.add("convite");
    }
  }

  function updateUI(data) {
    setText(els.message, data.message, "Aguardando visitante");

    if (els.subtitle) {
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

    applyScreenState(data.totem_state);
  }

  async function fetchStatus() {
    try {
      const response = await fetch("/edge/status", {
        method: "GET",
        cache: "no-store",
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      console.log("[integration] status:", data);
      updateUI(data);
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
    }

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
    
    document.body.classList.remove("state-espera", "state-convite", "state-sessao", "state-alerta");

    if (data.totem_state === "alerta") {
      document.body.classList.add("state-alerta");
    } else if (data.totem_state === "convite") {
      document.body.classList.add("state-convite");
    } else if (data.totem_state === "sessao") {
      document.body.classList.add("state-sessao");
    } else {
      document.body.classList.add("state-espera");
    }
  }

  async function fetchStatus() {
    try {
      const response = await fetch("/edge/status", {
        method: "GET",
        cache: "no-store",
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      console.log("[integration] status:", data);
      updateUI(data);
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

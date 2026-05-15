const screenEl = document.getElementById("screen");
const messageEl = document.getElementById("message");
const subtitleEl = document.getElementById("subtitle");
const tempEl = document.getElementById("temp");
const humEl = document.getElementById("hum");
const dist1El = document.getElementById("dist1");
const dist2El = document.getElementById("dist2");
const dist3El = document.getElementById("dist3");
const ledEl = document.getElementById("led");

function formatValue(value, unit) {
  unit = unit || "";
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "-- " + unit;
  }
  return Number(value).toFixed(1) + " " + unit;
}

function applyScreenState(state) {
  screenEl.className = "screen " + (state || "espera");

  if (state === "alerta") {
    messageEl.textContent = "Atencao: objeto muito proximo detectado.";
    subtitleEl.textContent = "Alerta";
  } else if (state === "sessao") {
    messageEl.textContent = "Ola, seja bem-vindo! Eu sou o Totem Inteligente FlexMedia, em que posso lhe ajudar?";
    subtitleEl.textContent = "Sessao ativa";
  } else if (state === "convite") {
    messageEl.textContent = "Chegue mais perto para iniciar o totem.";
    subtitleEl.textContent = "Aproxime-se para iniciar";
  } else {
    messageEl.textContent = "Chegue mais perto para iniciar o totem";
    subtitleEl.textContent = "Aguardando visitante";
  }
}

function render(data) {
  var state = data.totem_state || "espera";
  applyScreenState(state);

  tempEl.textContent = formatValue(data.temperature, "C");
  humEl.textContent = formatValue(data.humidity, "%");
  dist1El.textContent = formatValue(data.distance_sensor_1_cm, "cm");
  dist2El.textContent = formatValue(data.distance_sensor_2_cm, "cm");
  dist3El.textContent = formatValue(data.distance_sensor_3_cm, "cm");
  ledEl.textContent = data.led ? "ON" : "OFF";
}

async function fetchStatus() {
  try {
    var response = await fetch("/api/status", { cache: "no-store" });
    var data = await response.json();
    render(data);
  } catch (error) {
    screenEl.className = "screen offline";
    subtitleEl.textContent = "Sem conexao";
  }
}

fetchStatus();
setInterval(fetchStatus, 1000);
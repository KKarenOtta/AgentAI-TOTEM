from flask import Flask, render_template, jsonify
import sensor_service

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def api_status():
    full = sensor_service.update_system_state()

    ultrassons = full.get("ultrassons", [])

    dist1 = None
    dist2 = None
    dist3 = None

    if len(ultrassons) >= 1:
        dist1 = ultrassons[0].get("distance_cm")

    if len(ultrassons) >= 2:
        dist2 = ultrassons[1].get("distance_cm")

    if len(ultrassons) >= 3:
        dist3 = ultrassons[2].get("distance_cm")

    if full.get("message") == "Alerta":
        totem_state = "alerta"
    elif full.get("service_session_active") and full.get("presence"):
        totem_state = "sessao"
    elif full.get("presence"):
        totem_state = "convite"
    else:
        totem_state = "espera"

    payload = {
        "totem_state": totem_state,
        "message": full.get("message"),
        "temperature": full.get("temperature"),
        "humidity": full.get("humidity"),
        "distance_sensor_1_cm": dist1,
        "distance_sensor_2_cm": dist2,
        "distance_sensor_3_cm": dist3,
        "active_sensor": full.get("active_sensor"),
        "led": full.get("led"),
        "ultrassons_debug": ultrassons
    }

    return jsonify(payload)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
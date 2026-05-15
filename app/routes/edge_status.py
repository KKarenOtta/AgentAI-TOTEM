from fastapi import APIRouter

import sensor_service

router = APIRouter()


@router.get("/edge/status")
async def edge_status():
    full = sensor_service.update_system_state()
    ultrassons = full.get("ultrassons", [])

    return {
        "totem_state": full.get("totem_state", "espera"),
        "message": full.get("message", "Aguardando visitante"),
        "temperature": full.get("temperature"),
        "humidity": full.get("humidity"),
        "distance_sensor_1_cm": ultrassons[0].get("distance_cm") if len(ultrassons) >= 1 else None,
        "distance_sensor_2_cm": ultrassons[1].get("distance_cm") if len(ultrassons) >= 2 else None,
        "distance_sensor_3_cm": ultrassons[2].get("distance_cm") if len(ultrassons) >= 3 else None,
        "led": full.get("led"),
        "presence": full.get("presence"),
        "active_sensor": full.get("active_sensor"),
        "ultrassons": ultrassons,
    }

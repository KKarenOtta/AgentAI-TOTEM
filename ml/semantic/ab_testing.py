import random
from core.totem.metrics import MetricsLogger

metrics = MetricsLogger()


def choose_variant(a: str, b: str, session_id: str, campaign_id: str):
    if random.random() < 0.5:
        variant = "A"
        chosen = a
    else:
        variant = "B"
        chosen = b

    metrics.save({
        "event": "ab_variant",
        "session_id": session_id,
        "campaign_id": campaign_id,
        "variant": variant
    })

    return chosen, variant

from typing import Dict, Any, List, Optional

def recommend_actions(profile: Optional[Dict[str, Any]], active_campaigns: List[Dict[str, Any]]) -> Dict[str, Any]:
    profile = profile or {}
    age_range = profile.get("age_range")
    segment = profile.get("segment")

    # Regras simples (você substitui/combina com ML depois)
    recs = []
    for c in active_campaigns:
        if age_range and age_range in (c.get("target_segments") or []):
            recs.append({
                "type": "campaign_match",
                "campaign_id": c["campaign_id"],
                "action": f"Oferecer CTA da campanha '{c['name']}'",
                "why": f"Campanha ativa segmentada para {age_range}."
            })

    if segment == "new_visitor":
        recs.append({
            "type": "funnel",
            "action": "Priorizar captura de lead (cupom / cadastro rápido)",
            "why": "Visitante novo → maior chance de conversão com incentivo imediato."
        })

    if not recs:
        recs.append({
            "type": "generic",
            "action": "Mostrar melhores ofertas e perguntar preferência do usuário",
            "why": "Sem segmentação confiável; coletar intenção melhora recomendação."
        })

    return {"top_actions": recs[:5]}
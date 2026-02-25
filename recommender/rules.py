from recommender.scoring import infer_intent, score_campaign

def recommend_actions(profile, active_campaigns, intent=None, top_k=3):
    """
    Retorna recomendações ordenadas por score.
    intent deve vir pronto (ex.: inferido no orchestrator).
    """
    intent = intent or "general"

    scored = []
    for c in active_campaigns:
        s, why = score_campaign(c, profile, intent)
        scored.append((s, c, why))

    scored.sort(key=lambda x: x[0], reverse=True)

    top = []
    for s, c, why in scored[:top_k]:
        top.append({
            "type": "campaign",
            "campaign_id": c.get("id") or c.get("campaign_id"),
            "title": c.get("title") or c.get("name") or "Campanha",
            "action": c.get("cta") or "Ver oferta",
            "score": s,
            "why": why,
        })

    if not top:
        top = [{
            "type": "generic",
            "action": "Mostrar melhores ofertas e perguntar preferência do usuário",
            "why": "Sem campanhas elegíveis; coletar intenção melhora recomendação.",
            "score": 0.1,
        }]

    return {"top_actions": top}
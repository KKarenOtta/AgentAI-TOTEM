import json
import os
import logging

logger = logging.getLogger("metrics")

class MetricsLogger:
    def __init__(self, path: str = "data/metrics/metrics.jsonl"):
        self.path = path
        dir_ = os.path.dirname(self.path)
        if dir_:
            os.makedirs(dir_, exist_ok=True)

    def save(self, metric: dict) -> None:
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(metric, ensure_ascii=False) + "\n")

    def load_rows(self) -> list[dict]:
        if not os.path.exists(self.path):
            return []

        rows: list[dict] = []
        with open(self.path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    logger.warning(
                        "Linha inválida em %s (linha %d). Ignorando.",
                        self.path,
                        i,
                    )
        return rows

    def build_report(self, out_path: str = "data/metrics/metrics_report.md") -> None:
        rows = self.load_rows()
        total = len(rows)

        out_dir = os.path.dirname(out_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        if total == 0:
            content = "# Relatório de Métricas do Totem\n\nNenhuma interação registrada.\n"
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(content)
            return

        gen_lat = [
            r.get("gen_latency_s")
            for r in rows
            if isinstance(r.get("gen_latency_s"), (int, float))
        ]

        tts_lat = [
            r.get("tts_latency_s")
            for r in rows
            if isinstance(r.get("tts_latency_s"), (int, float))
        ]

        def _avg(xs):
            return round(sum(xs) / len(xs), 3) if xs else None

        avg_gen = _avg(gen_lat)
        avg_tts = _avg(tts_lat)

        by_company = {}
        by_lang = {}

        for r in rows:
            cid = r.get("company_id") or "unknown"
            by_company[cid] = by_company.get(cid, 0) + 1

            lang = r.get("language_detected") or "unknown"
            by_lang[lang] = by_lang.get(lang, 0) + 1

        lines = []
        lines.append("# Relatório de Métricas do Totem\n\n")
        lines.append(f"- Total de interações: **{total}**\n")
        lines.append(
            f"- Latência média (geração): **{avg_gen}s**\n"
            if avg_gen is not None
            else "- Latência média (geração): **n/a**\n"
        )
        lines.append(
            f"- Latência média (TTS): **{avg_tts}s**\n"
            if avg_tts is not None
            else "- Latência média (TTS): **n/a**\n"
        )

        lines.append("\n## Interações por empresa\n")
        for cid, n in sorted(by_company.items(), key=lambda x: (-x[1], x[0])):
            lines.append(f"- {cid}: {n}\n")

        lines.append("\n## Interações por idioma detectado\n")
        for lang, n in sorted(by_lang.items(), key=lambda x: (-x[1], x[0])):
            lines.append(f"- {lang}: {n}\n")

        lines.append("\n## Últimas interações\n")
        for r in rows[-10:]:
            ts = r.get("timestamp", "")
            cid = r.get("company_id", "")
            sid = r.get("session_id", "")
            q = (r.get("question") or "").strip().replace("\n", " ")
            resp = (r.get("response") or "").strip().replace("\n", " ")

            if len(resp) > 240:
                resp = resp[:240] + "…"

            lines.append(f"\n### {ts} — {cid}/{sid}\n")
            lines.append(f"- Pergunta: {q}\n")
            lines.append(f"- Resposta: {resp}\n")

        with open(out_path, "w", encoding="utf-8") as f:
            f.write("".join(lines))
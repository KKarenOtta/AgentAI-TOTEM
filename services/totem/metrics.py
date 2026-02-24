from datetime import datetime
import json, os
import pandas as pd
from typing import Dict, Any

class MetricsLogger:
    def __init__(self, base_dir="data/metrics"):
        os.makedirs(base_dir, exist_ok=True)
        self.jsonl_path = os.path.join(base_dir, "metrics.jsonl")
        self.csv_path   = os.path.join(base_dir, "metrics.csv")
        self.md_path    = os.path.join(base_dir, "metrics_report.md")

        if not os.path.exists(self.jsonl_path):
            open(self.jsonl_path, "w", encoding="utf-8").close()

    def save(self, entry: Dict[str, Any]) -> None:
        entry = dict(entry)
        if "timestamp" not in entry:
            entry["timestamp"] = datetime.now().isoformat(timespec="seconds")

        with open(self.jsonl_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        # atualiza CSV
        with open(self.jsonl_path, "r", encoding="utf-8") as f:
            rows = [json.loads(line) for line in f if line.strip()]
        if rows:
            pd.DataFrame(rows).to_csv(self.csv_path, index=False, encoding="utf-8-sig")

    def build_report(self) -> str:
        if not os.path.exists(self.csv_path):
            return "Sem dados ainda."
        df = pd.read_csv(self.csv_path)

        total = len(df)
        last = df.iloc[-1].to_dict()
        counts_by_voice = df["voice_source"].value_counts().to_dict() if "voice_source" in df.columns else {}

        md = f"""### Relatório Totem I.A.Gora
- Total de interações: {total}
- Última interação: {last.get('timestamp')}
- Pergunta: {last.get('question')}
- Voz usada: {last.get('voice_source')}
- Distribuição de TTS: {counts_by_voice}
"""
        with open(self.md_path, "w", encoding="utf-8") as f:
            f.write(md)
        return md
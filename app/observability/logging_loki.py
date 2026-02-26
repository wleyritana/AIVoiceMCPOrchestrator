import os
import time
import json
import requests


class LokiLogger:
    def __init__(self) -> None:
        self.url = os.getenv("GRAFANA_LOKI_URL")
        self.username = os.getenv("GRAFANA_LOKI_USERNAME")
        self.token = os.getenv("GRAFANA_LOKI_API_TOKEN")
        self.app_label = os.getenv("MCP_APP_LABEL", "mcp_orchestrator_v2")

        self.enabled = all([self.url, self.username, self.token])
        if not self.enabled:
            print("[LokiLogger] Disabled – missing GRAFANA_LOKI_* env vars")
        else:
            print("[LokiLogger] Enabled, pushing to", self.url)

    def _build_stream_labels(self, level: str, fields: dict) -> dict:
        labels = {
            "app": self.app_label,
            "level": level,
        }
        event = fields.get("event") or fields.get("event_type")
        if event:
            labels["event"] = str(event)

        mapping = {
            "service_type": "service",
            "service": "service",
            "flow": "flow",
            "step": "step",
            "intent": "intent",
            "outcome": "outcome",
            "sync_mode": "mode",
            "io": "io",
            "trace_id": "trace_id",
        }

        for src, dst in mapping.items():
            val = fields.get(src)
            if val not in (None, "", []):
                labels[dst] = str(val)

        return labels

    def log(self, level: str, message, **fields) -> None:
        if not self.enabled:
            return

        if isinstance(message, dict):
            payload_fields = {**fields, **message}
        else:
            payload_fields = {**fields, "message": str(message)}

        ts_ns = int(time.time() * 1_000_000_000)
        stream_labels = self._build_stream_labels(level, payload_fields)

        body = {
            "streams": [
                {
                    "stream": stream_labels,
                    "values": [
                        [str(ts_ns), json.dumps(payload_fields, ensure_ascii=False)]
                    ],
                }
            ]
        }

        try:
            resp = requests.post(
                self.url,
                auth=(self.username, self.token),
                json=body,
                timeout=4,
            )
            if resp.status_code not in (200, 204):
                print("[LokiLogger] Push failed:", resp.status_code, resp.text[:200])
        except Exception as e:
            print("[LokiLogger] Exception while pushing to Loki:", e)


loki = LokiLogger()

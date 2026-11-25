import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class TraceEvent:
    step_name: str
    tool: str
    details: dict
    duration_ms: float


class PipelineTracer:
    def __init__(self):
        self.events: list[TraceEvent] = []

    def log(self, step_name: str, tool: str, details: dict, start_time: float):
        elapsed = round((time.time() - start_time) * 1000, 2)
        self.events.append(TraceEvent(step_name, tool, details, elapsed))
        Path("trace_log.json").write_text(
            json.dumps([asdict(e) for e in self.events], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def clear(self):
        self.events.clear()


tracer = PipelineTracer()


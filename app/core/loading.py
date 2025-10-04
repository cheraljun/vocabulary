import json
import time
import threading
from datetime import datetime
from typing import Dict, Any, Optional


class LoadingStateStore:
    """加载状态管理（内存版，不持久化到文件）"""
    DEFAULT_STATE: Dict[str, Any] = {
        "running": False,
        "file": None,
        "current_sheet": None,
        "processed_words": 0,
        "total_words": 0,
        "percent": 0.0,
        "error": None,
        "latest_words": [],
        "timestamp": None,
    }

    def __init__(self):
        self.lock = threading.Lock()
        self.state: Dict[str, Any] = self.DEFAULT_STATE.copy()

    def snapshot(self) -> Dict[str, Any]:
        with self.lock:
            return json.loads(json.dumps(self.state))

    def reset_for_file(self, file_name: str, total_rows: int) -> None:
        with self.lock:
            self.state = self.DEFAULT_STATE.copy()
            self.state.update({
                "running": True,
                "file": file_name,
                "current_sheet": None,
                "processed_words": 0,
                "total_words": int(total_rows or 0),
                "percent": 0.0,
                "error": None,
                "latest_words": [],
                "timestamp": datetime.utcnow().isoformat(),
            })

    def set_current_sheet(self, sheet: Optional[str]) -> None:
        with self.lock:
            self.state["current_sheet"] = sheet
            self.state["timestamp"] = datetime.utcnow().isoformat()

    def increment_processed(self, increment: int = 1, sample_word: Optional[str] = None,
                            sample_step: int = 10, latest_limit: int = 40) -> int:
        with self.lock:
            processed = self.state.get("processed_words", 0) + increment
            self.state["processed_words"] = processed
            total = self.state.get("total_words", 0) or 0
            self.state["percent"] = (processed / total * 100.0) if total > 0 else 0.0
            if sample_word and sample_word.strip():
                if processed % sample_step == 0:
                    latest = list(self.state.get("latest_words") or [])
                    latest.append(sample_word)
                    if len(latest) > latest_limit:
                        latest = latest[-latest_limit:]
                    self.state["latest_words"] = latest
            self.state["timestamp"] = datetime.utcnow().isoformat()
            return processed

    def mark_finished(self, error: Optional[str] = None) -> None:
        with self.lock:
            self.state["running"] = False
            if error:
                self.state["error"] = error
            self.state["timestamp"] = datetime.utcnow().isoformat()

    def clear_error(self) -> None:
        with self.lock:
            self.state["error"] = None
            self.state["timestamp"] = datetime.utcnow().isoformat()


# 全局单例
loading_state = LoadingStateStore()


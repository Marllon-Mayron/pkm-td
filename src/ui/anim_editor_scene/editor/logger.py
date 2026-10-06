"""
Logger do editor de animações.

- Printa no console com prefixo [ANIM_EDITOR]
- Guarda últimas N linhas em buffer
- Painel visual flutuante (toggle com Ctrl+L no controller)
"""
import time


class EditorLogger:
    LEVEL_COLORS = {
        "INFO":  (200, 210, 230),
        "OK":    (120, 230, 140),
        "WARN":  (255, 200, 100),
        "ERROR": (255, 120, 120),
        "DEBUG": (140, 150, 180),
    }

    def __init__(self, max_lines: int = 300):
        self.max_lines = max_lines
        self.lines = []          # list[(level, text, hh:mm:ss)]
        self.visible = False
        self.scroll = 0

    # -----------------------------------------------------------------
    def _add(self, level: str, text: str):
        ts = time.strftime("%H:%M:%S")
        self.lines.append((level, str(text), ts))
        if len(self.lines) > self.max_lines:
            self.lines = self.lines[-self.max_lines:]
        print(f"[ANIM_EDITOR][{level}] {text}")

    def info(self, text):  self._add("INFO", text)
    def ok(self, text):    self._add("OK", text)
    def warn(self, text):  self._add("WARN", text)
    def error(self, text): self._add("ERROR", text)
    def debug(self, text): self._add("DEBUG", text)

    def clear(self):
        self.lines.clear()

    def recent(self, n: int = 3):
        return self.lines[-n:]
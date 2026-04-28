import logging

class Logger:
    def __init__(self):
        self.history = []

    def _add_log(self, level, message):
        log_entry = f"[{level}] {message}"
        print(log_entry)
        self.history.append(log_entry)
        if len(self.history) > 50:
            self.history.pop(0)

    def info(self, message):
        self._add_log("INFO", message)
        
    def debug(self, message):
        self._add_log("DEBUG", message)

    def error(self, message):
        self._add_log("ERROR", message)
        
    def signal(self, message):
        self._add_log("SIGNAL", message)
        
    def warning(self, message):
        self._add_log("WARNING", message)
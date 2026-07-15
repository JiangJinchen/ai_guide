class IntentStreamFilter:
    """Remove intent blocks without leaking markers split across chunks."""

    START_MARKER = "<intent>"
    END_MARKER = "</intent>"

    def __init__(self):
        self._buffer = ""
        self._inside_intent = False

    @staticmethod
    def _marker_prefix_length(value: str, marker: str) -> int:
        max_length = min(len(value), len(marker) - 1)
        for length in range(max_length, 0, -1):
            if value.endswith(marker[:length]):
                return length
        return 0

    def feed(self, chunk: str) -> str:
        if not chunk:
            return ""

        self._buffer += chunk
        output = []

        while self._buffer:
            if self._inside_intent:
                end_index = self._buffer.find(self.END_MARKER)
                if end_index >= 0:
                    self._buffer = self._buffer[end_index + len(self.END_MARKER):]
                    self._inside_intent = False
                    continue

                keep_length = self._marker_prefix_length(self._buffer, self.END_MARKER)
                self._buffer = self._buffer[-keep_length:] if keep_length else ""
                break

            start_index = self._buffer.find(self.START_MARKER)
            if start_index >= 0:
                output.append(self._buffer[:start_index])
                self._buffer = self._buffer[start_index + len(self.START_MARKER):]
                self._inside_intent = True
                continue

            keep_length = self._marker_prefix_length(self._buffer, self.START_MARKER)
            safe_length = len(self._buffer) - keep_length
            if safe_length:
                output.append(self._buffer[:safe_length])
            self._buffer = self._buffer[safe_length:]
            break

        return "".join(output)

    def finish(self) -> str:
        trailing_text = "" if self._inside_intent else self._buffer
        self._buffer = ""
        self._inside_intent = False
        return trailing_text

from dataclasses import dataclass


@dataclass
class Court:
    key: str
    level: str

    def key_formatted(self) -> str:
        return self.key.split("$")[0]
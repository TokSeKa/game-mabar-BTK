"""Error yang ditampilkan ke pemain. Semua pesan dalam bahasa Indonesia."""

from __future__ import annotations


class BotError(Exception):
    """Kesalahan pada kode bot (saat dicek atau saat dijalankan)."""

    def __init__(self, pesan: str, baris: int | None = None):
        self.pesan = pesan
        self.baris = baris
        super().__init__(pesan)

    def __str__(self) -> str:
        return f"Baris {self.baris}: {self.pesan}" if self.baris else self.pesan

    def to_dict(self) -> dict:
        return {"baris": self.baris, "pesan": self.pesan}


class StepLimitExceeded(BotError):
    """Bot memakai terlalu banyak langkah dalam satu ronde."""

"""OCR observations retain their confidence and source pixels."""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Reading:
    text: str
    score: float
    source: str = "page"


@dataclass(frozen=True)
class OcrItem:
    text: str
    box: np.ndarray
    score: float = 1.0
    alternatives: tuple[Reading, ...] = ()

    @property
    def readings(self) -> tuple[Reading, ...]:
        return (Reading(self.text, self.score), *self.alternatives)

    @property
    def left(self) -> float:
        return float(self.box[:, 0].min())

    @property
    def right(self) -> float:
        return float(self.box[:, 0].max())

    @property
    def top(self) -> float:
        return float(self.box[:, 1].min())

    @property
    def bottom(self) -> float:
        return float(self.box[:, 1].max())

    @property
    def height(self) -> float:
        return max(1.0, float(np.linalg.norm(self.box[3] - self.box[0])))

    @property
    def center_y(self) -> float:
        return float(self.box[:, 1].mean())

    def row_y_at(self, x: float) -> float:
        left_y = float((self.box[0, 1] + self.box[3, 1]) / 2)
        right_y = float((self.box[1, 1] + self.box[2, 1]) / 2)
        span = float(self.box[1, 0] - self.box[0, 0])
        return left_y + (right_y - left_y) * (x - float(self.box[0, 0])) / span if span else left_y

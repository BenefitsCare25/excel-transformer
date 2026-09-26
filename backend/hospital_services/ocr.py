"""Read pages, then retry doubtful field crops without changing their values."""

from dataclasses import replace

import cv2
import numpy as np
from rapidocr import ModelType, OCRVersion, RapidOCR

from .fields import PAGE_LABEL, parse_pagination, retry_items
from .ocr_types import OcrItem, Reading


MAX_IMAGE_SIDE = 5000


def create_engine() -> RapidOCR:
    return RapidOCR(params={
        "Det.ocr_version": OCRVersion.PPOCRV6,
        "Det.model_type": ModelType.SMALL,
        "Rec.ocr_version": OCRVersion.PPOCRV6,
        "Rec.model_type": ModelType.SMALL,
        "Global.max_side_len": MAX_IMAGE_SIDE,
        "EngineConfig.onnxruntime.intra_op_num_threads": 2,
        "EngineConfig.onnxruntime.inter_op_num_threads": 1,
        "Global.log_level": "warning",
    })


def read_lines(image: np.ndarray, engine: RapidOCR) -> list[OcrItem]:
    result = engine(cv2.cvtColor(image, cv2.COLOR_RGB2BGR), use_det=True, use_cls=True, use_rec=True)
    if not result.txts:
        return []
    return [OcrItem(str(text).strip(), np.asarray(box), float(score))
            for text, box, score in zip(result.txts, result.boxes, result.scores)]


def _crop(image: np.ndarray, box: np.ndarray) -> np.ndarray:
    points = box.astype(np.float32)
    width = max(1, round(np.linalg.norm(points[1] - points[0])))
    height = max(1, round(np.linalg.norm(points[3] - points[0])))
    destination = np.array([[0, 0], [width, 0], [width, height], [0, height]], dtype=np.float32)
    transform = cv2.getPerspectiveTransform(points, destination)
    crop = cv2.warpPerspective(image, transform, (width, height),
                               flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    pad = max(2, round(height * .12))
    crop = cv2.copyMakeBorder(crop, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=(255, 255, 255))
    return cv2.cvtColor(crop, cv2.COLOR_RGB2BGR)


def _expanded_box(item: OcrItem) -> np.ndarray:
    points = item.box.astype(np.float32).copy()
    direction = points[1] - points[0]
    length = np.linalg.norm(direction)
    if length:
        margin = direction / length * item.height
        points[[0, 3]] -= margin
        points[[1, 2]] += margin
    return points


def retry_fields(image: np.ndarray, engine: RapidOCR, items: list[OcrItem]) -> list[OcrItem]:
    updates = {}
    for item in retry_items(items):
        if any(reading.source == "crop" for reading in item.alternatives):
            continue
        result = engine(_crop(image, item.box), use_det=False, use_cls=False, use_rec=True)
        if result.txts:
            reading = Reading(str(result.txts[0]).strip(), float(result.scores[0]), "crop")
            updates[id(item)] = replace(item, alternatives=(*item.alternatives, reading))
        if PAGE_LABEL.search(item.text) and not any(parse_pagination(r.text) for r in updates.get(id(item), item).readings):
            result = engine(_crop(image, _expanded_box(item)), use_det=False, use_cls=False, use_rec=True)
            if result.txts:
                reading = Reading(str(result.txts[0]).strip(), float(result.scores[0]), "expanded-crop")
                current = updates.get(id(item), item)
                updates[id(item)] = replace(current, alternatives=(*current.alternatives, reading))
    return [updates.get(id(item), item) for item in items]

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple, List
import cv2
import numpy as np
from stages.preprocess.image_loader import PreprocessConfig, PreprocessResult, _load_image_any

def _deskew(image_bgr: np.ndarray) -> np.ndarray:
    """Rudimentary deskew based on the minimum area rectangle of the foreground."""
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    # Use binary inverse so that text (usually dark) becomes foreground.
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    coords = np.column_stack(np.where(thresh > 0))
    if coords.size == 0:
        return image_bgr

    rect = cv2.minAreaRect(coords.astype(np.float32))
    angle = rect[-1]

    # OpenCV returns angle in [-90, 0); convert to a small rotation around 0 degrees.
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    (h, w) = image_bgr.shape[:2]
    center = (w // 2, h // 2)
    m = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(
        image_bgr, m, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
    )
    return rotated

def _denoise_and_binarize(
    image_bgr: np.ndarray, cfg: PreprocessConfig
) -> np.ndarray:
    """Apply light denoising and adaptive thresholding."""
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    # Light denoising
    denoised = cv2.GaussianBlur(gray, (3, 3), 0)

    block_size = cfg.adaptive_threshold_block_size
    if block_size % 2 == 0:
        block_size += 1
    if block_size < 3:
        block_size = 3

    bin_img = cv2.adaptiveThreshold(
        denoised,
        255,
        cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY,
        block_size,
        cfg.adaptive_threshold_C,
    )
    return bin_img

def _resize_keep_aspect(
    image: np.ndarray, target_height: int, target_width: int
) -> Tuple[np.ndarray, float, float]:
    """Resize while keeping aspect ratio and return scale factors."""
    h, w = image.shape[:2]
    scale_y = target_height / float(h)
    scale_x = target_width / float(w)
    scale = min(scale_x, scale_y)

    new_w = int(round(w * scale))
    new_h = int(round(h * scale))
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)

    return resized, scale, scale

def preprocess_image(
    image_path: str | Path,
    cfg: Optional[PreprocessConfig] = None,
    debug_dir: Optional[Path] = None,
    debug_enabled: bool = False,
) -> List[PreprocessResult]:
    """
    Full preprocessing entry point used by the pipeline.
    """
    if cfg is None:
        cfg = PreprocessConfig()

    img_path = Path(image_path)
    bgr_images = _load_image_any(img_path)
    results = []

    for page_num, original_bgr in enumerate(bgr_images):
        deskewed = _deskew(original_bgr)
        bin_img = _denoise_and_binarize(deskewed, cfg)
        resized, scale_y, scale_x = _resize_keep_aspect(bin_img, cfg.target_height, cfg.target_width)

        debug_original_path = None
        debug_preprocessed_path = None

        if debug_enabled and debug_dir is not None:
            debug_dir = Path(debug_dir)
            debug_dir.mkdir(parents=True, exist_ok=True)
            stem = img_path.stem
            debug_original_path = debug_dir / f"{stem}_page{page_num}_original.png"
            debug_preprocessed_path = debug_dir / f"{stem}_page{page_num}_preprocessed.png"
            cv2.imwrite(str(debug_original_path), original_bgr)
            cv2.imwrite(str(debug_preprocessed_path), resized)

        results.append(
            PreprocessResult(
                original_bgr=original_bgr,
                preprocessed=resized,
                scale_x=scale_x,
                scale_y=scale_y,
                debug_original_path=debug_original_path,
                debug_preprocessed_path=debug_preprocessed_path,
            )
        )
    return results

"""Image OCR only: no Django, student parsing, storage or admission rules."""
from dataclasses import asdict, dataclass
from io import BytesIO
from pathlib import Path
import re
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError
import pytesseract


class OCRError(Exception):
    """An actionable OCR failure suitable for handling at the API boundary."""


@dataclass(frozen=True)
class OCRConfig:
    language: str = "eng"
    page_segmentation_mode: int = 3
    timeout_seconds: float = 30
    max_bytes: int = 10 * 1024 * 1024
    max_pixels: int = 20_000_000
    grayscale: bool = False
    pdf_dpi: int = 300

    def __post_init__(self):
        if not re.fullmatch(r"[A-Za-z0-9_]+(?:\+[A-Za-z0-9_]+)*", self.language):
            raise ValueError("Use a language code such as eng or eng+fra.")
        if type(self.page_segmentation_mode) is not int or self.page_segmentation_mode not in range(3, 14):
            raise ValueError("Page segmentation mode must be between 3 and 13.")
        if not 0 < self.timeout_seconds <= 300 or self.max_bytes <= 0 or self.max_pixels <= 0:
            raise ValueError("Use positive limits and a timeout no greater than 300 seconds.")
        if type(self.pdf_dpi) is not int or not 100 <= self.pdf_dpi <= 400:
            raise ValueError('PDF resolution must be between 100 and 400 DPI.')


@dataclass(frozen=True)
class OCRWord:
    text: str
    confidence: float
    left: int
    top: int
    width: int
    height: int
    block: int
    paragraph: int
    line: int


@dataclass(frozen=True)
class OCRResult:
    text: str
    words: tuple[OCRWord, ...]
    width: int
    height: int
    language: str
    warnings: tuple[str, ...]

    def to_dict(self):
        return asdict(self)


def extract_image(source: bytes | str | Path, config: OCRConfig | None = None) -> OCRResult:
    """Read a single-frame image. Bounding boxes refer to EXIF-corrected pixels.

    Paths are intended for trusted local callers. Web APIs should pass bounded
    uploaded bytes, never a client-supplied server path. OCR confidence is an
    engine score, not a calibrated probability or a document authenticity check.
    """
    config = config or OCRConfig()
    if isinstance(source, (str, Path)):
        try:
            with Path(source).open("rb") as file:
                raw = file.read(config.max_bytes + 1)
        except OSError as exc:
            raise OCRError("Cannot read image file.") from exc
    elif isinstance(source, bytes):
        raw = source
    else:
        raise TypeError("Pass image bytes or a local file path.")
    if not raw or len(raw) > config.max_bytes:
        raise OCRError("Image is empty or exceeds the upload size limit.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(raw)) as original:
                if original.width * original.height > config.max_pixels:
                    raise OCRError("Image exceeds the pixel limit.")
                if getattr(original, "n_frames", 1) != 1:
                    raise OCRError("Split multi-frame images into individual pages before OCR.")
                oriented = ImageOps.exif_transpose(original).convert("RGBA")
                image = Image.new("RGBA", oriented.size, "white")
                image.alpha_composite(oriented)
                image = image.convert("RGB")
                if config.grayscale:
                    image = ImageOps.grayscale(image)
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise OCRError("Unsupported, corrupt or excessively large image.") from exc
    try:
        data = pytesseract.image_to_data(
            image, lang=config.language,
            config=f"--psm {config.page_segmentation_mode}",
            output_type=pytesseract.Output.DICT, timeout=config.timeout_seconds,
        )
    except pytesseract.TesseractNotFoundError as exc:
        raise OCRError("Install the native Tesseract engine and add it to PATH.") from exc
    except (pytesseract.TesseractError, RuntimeError) as exc:
        raise OCRError("OCR failed or timed out. Check the image and installed language data.") from exc
    words = []
    lines = {}
    for i, value in enumerate(data["text"]):
        text = value.strip()
        confidence = float(data["conf"][i])
        if not text or confidence < 0:
            continue
        word = OCRWord(text, confidence, *(int(data[key][i]) for key in ["left", "top", "width", "height", "block_num", "par_num", "line_num"]))
        words.append(word)
        key = (data["page_num"][i], word.block, word.paragraph, word.line)
        lines.setdefault(key, []).append(text)
    notices = []
    if not words:
        notices.append("No text detected; try a clearer scan or manual entry.")
    elif any(word.confidence < 70 for word in words):
        notices.append("Some words have low OCR confidence; review them against the source.")
    return OCRResult("\n".join(" ".join(line) for line in lines.values()), tuple(words), image.width, image.height, config.language, tuple(notices))

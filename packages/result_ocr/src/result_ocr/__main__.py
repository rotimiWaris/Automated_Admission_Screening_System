import argparse
import json
from .service import OCRConfig, OCRError, extract_image

def main():
    parser = argparse.ArgumentParser(description="Extract text and word positions from an image.")
    parser.add_argument("image")
    parser.add_argument("--language", default="eng")
    parser.add_argument("--psm", type=int, default=3)
    args = parser.parse_args()
    try:
        result = extract_image(args.image, OCRConfig(language=args.language, page_segmentation_mode=args.psm))
    except (OCRError, ValueError) as exc:
        parser.exit(1, f"OCR error: {exc}\n")
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()

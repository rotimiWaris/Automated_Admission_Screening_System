"""Install the official English tessdata_best model inside this workspace."""
from hashlib import sha256
from pathlib import Path
from urllib.request import urlopen

DESTINATION = Path(__file__).resolve().parents[1] / 'ocr-data'
URL = 'https://raw.githubusercontent.com/tesseract-ocr/tessdata_best/main/'
EXPECTED_SHA256 = '8280aed0782fe27257a68ea10fe7ef324ca0f8d85bd2fd145d1c2b560bcb66ba'

if __name__ == '__main__':
    DESTINATION.mkdir(exist_ok=True)
    with urlopen(URL + 'eng.traineddata', timeout=60) as response:
        model = response.read(20 * 1024 * 1024)
    if sha256(model).hexdigest() != EXPECTED_SHA256:
        raise RuntimeError('Model checksum differs from the tested version; existing model was not replaced.')
    (DESTINATION / 'eng.traineddata').write_bytes(model)
    with urlopen(URL + 'LICENSE', timeout=30) as response:
        (DESTINATION / 'LICENSE').write_bytes(response.read())
    print('English accuracy model installed. Restart Django to use it.')

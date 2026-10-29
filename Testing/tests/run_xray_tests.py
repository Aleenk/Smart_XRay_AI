import csv
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from backend.model.inference import predict_xray
from backend.utils.image_utils import prepare_xray_image

PROJECT_DIR = Path(__file__).resolve().parent.parent
IMAGE_DIR = PROJECT_DIR / "test_images"
OUTPUT_FILE = PROJECT_DIR / "xray_test_results.csv"

# Ground Truth taken from the NIH metadata shared in this conversation.
GROUND_TRUTH = {
    "00000013_037.png": "Cardiomegaly|Emphysema|Pneumothorax",
    "00000013_030.png": "Atelectasis|Cardiomegaly|Emphysema|Mass|Pneumothorax",
    "00000013_026.png": "Cardiomegaly|Emphysema",
    "00000013_025.png": "Cardiomegaly|Infiltration|Mass|Nodule",
    "00000013_021.png": "Effusion",
    "00000013_018.png": "Effusion|Infiltration|Pneumothorax",
    "00000013_006.png": "Effusion|Infiltration",
    "00000013_005.png": "Emphysema|Infiltration|Pleural_Thickening|Pneumothorax",
    "00000013_004.png": "Effusion|Emphysema|Infiltration|Pneumothorax",
    "00000041_002.png": "Emphysema|Pneumothorax",
    "00000056_000.png": "Nodule|Pneumonia",
    "00000061_012.png": "Edema|Effusion|Infiltration|Pleural_Thickening|Pneumonia",
    "00000071_001.png": "Pneumothorax",
    "00000150_002.png": "Atelectasis|Infiltration|Pneumonia",
    "00000165_001.png": "Pneumonia",
    "00000011_000.png": "Effusion",
    "00000011_001.png": "No Finding",
    "00000011_002.png": "No Finding",
    "00000011_003.png": "No Finding",
    "00000011_004.png": "No Finding",
}

def main():
    if not IMAGE_DIR.exists():
        raise FileNotFoundError(
            f"Image folder not found: {IMAGE_DIR}"
        )

    image_paths = sorted(
        path for path in IMAGE_DIR.iterdir()
        if path.is_file()
        and path.suffix.lower() in {".png", ".jpg", ".jpeg"}
    )

    if not image_paths:
        raise RuntimeError(
            f"No PNG/JPG images found in {IMAGE_DIR}"
        )

    rows = []

    for number, path in enumerate(image_paths, start=1):
        print(f"[{number}/{len(image_paths)}] Testing {path.name}")

        try:
            image_bytes = path.read_bytes()
            prepared = prepare_xray_image(image_bytes)
            result = predict_xray(prepared["image"])

            predictions = result["predictions"]
            detected = result["detected_findings"]

            rows.append({
                "Test #": number,
                "Image File": path.name,
                "Ground Truth": GROUND_TRUTH.get(
                    path.name, "Not matched"
                ),
                "System Result": (
                    " | ".join(detected)
                    if detected
                    else "No selected finding detected"
                ),
                "Pneumonia probability": predictions["Pneumonia"],
                "Pneumothorax probability": predictions["Pneumothorax"],
                "Effusion probability": predictions["Effusion"],
                "Cardiomegaly probability": predictions["Cardiomegaly"],
                "Explanation Works": "Not tested",
                "Grad-CAM Works": "Not tested",
                "PASS/FAIL": "Pending review",
                "Notes": result.get("summary", ""),
            })

        except Exception as exc:
            rows.append({
                "Test #": number,
                "Image File": path.name,
                "Ground Truth": GROUND_TRUTH.get(
                    path.name, "Not matched"
                ),
                "System Result": "ERROR",
                "Pneumonia probability": "",
                "Pneumothorax probability": "",
                "Effusion probability": "",
                "Cardiomegaly probability": "",
                "Explanation Works": "Not tested",
                "Grad-CAM Works": "Not tested",
                "PASS/FAIL": "FAIL",
                "Notes": str(exc),
            })
            print(f"  ERROR: {exc}")

    fieldnames = [
        "Test #",
        "Image File",
        "Ground Truth",
        "System Result",
        "Pneumonia probability",
        "Pneumothorax probability",
        "Effusion probability",
        "Cardiomegaly probability",
        "Explanation Works",
        "Grad-CAM Works",
        "PASS/FAIL",
        "Notes",
    ]

    with OUTPUT_FILE.open(
        "w", newline="", encoding="utf-8-sig"
    ) as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print()
    print(f"Images processed: {len(image_paths)}")
    print(f"Results saved to: {OUTPUT_FILE}")
    print("UI explanation and Grad-CAM checks remain manual.")


if __name__ == "__main__":
    main()

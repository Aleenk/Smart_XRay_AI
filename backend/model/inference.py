from pathlib import Path
from io import BytesIO
import base64
import json

import numpy as np
import torch
from torch import nn
import torch.nn.functional as F

from PIL import Image, ImageOps
from torchvision import models, transforms


# --------------------------------------------------
# Paths
# --------------------------------------------------

MODEL_DIR = Path(__file__).resolve().parent

MODEL_PATH = MODEL_DIR / "best_final_model.pth"
THRESHOLDS_PATH = MODEL_DIR / "thresholds.json"


# --------------------------------------------------
# Labels
# --------------------------------------------------

TARGET_LABELS = [
    "Pneumonia",
    "Pneumothorax",
    "Effusion",
    "Cardiomegaly",
    "No Finding",
]

DISEASE_LABELS = [
    "Pneumonia",
    "Pneumothorax",
    "Effusion",
    "Cardiomegaly",
]


# --------------------------------------------------
# Device
# --------------------------------------------------

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available()
    else "cpu"
)

print("Inference device:", DEVICE)


# --------------------------------------------------
# Load thresholds
# --------------------------------------------------

with open(
    THRESHOLDS_PATH,
    "r",
    encoding="utf-8"
) as file:
    THRESHOLDS = json.load(file)


print("Thresholds loaded:")

for label, threshold in THRESHOLDS.items():
    print(
        f"{label}: "
        f"{threshold:.4f}"
    )


# --------------------------------------------------
# Build DenseNet121
# --------------------------------------------------

model = models.densenet121(
    weights=None
)

num_features = model.classifier.in_features

model.classifier = nn.Linear(
    num_features,
    len(TARGET_LABELS)
)


# --------------------------------------------------
# Load final checkpoint
# --------------------------------------------------

checkpoint = torch.load(
    MODEL_PATH,
    map_location=DEVICE,
    weights_only=False
)

model.load_state_dict(
    checkpoint["model_state_dict"]
)

model = model.to(DEVICE)

model.eval()


print("Final model loaded.")

print(
    "Checkpoint epoch:",
    checkpoint.get("epoch")
)

print(
    "Validation Macro AUC:",
    checkpoint.get("macro_auc")
)


# --------------------------------------------------
# Image preprocessing
# --------------------------------------------------

inference_transform = transforms.Compose([
    transforms.Resize((224, 224)),

    transforms.ToTensor(),

    transforms.Normalize(
        mean=[
            0.485,
            0.456,
            0.406
        ],
        std=[
            0.229,
            0.224,
            0.225
        ]
    )
])


# --------------------------------------------------
# Prediction
# --------------------------------------------------

def predict_xray(image):

    image_tensor = inference_transform(
        image
    )

    image_tensor = (
        image_tensor
        .unsqueeze(0)
        .to(DEVICE)
    )

    with torch.no_grad():

        logits = model(
            image_tensor
        )

        probabilities = torch.sigmoid(
            logits
        )[0]


    probability_dict = {}

    for index, label in enumerate(
        TARGET_LABELS
    ):

        probability_dict[label] = float(
            probabilities[index].item()
        )


    findings = {}

    detected_findings = []

    for label in DISEASE_LABELS:

        probability = probability_dict[
            label
        ]

        threshold = float(
            THRESHOLDS[label]
        )

        detected = (
            probability >= threshold
        )

        findings[label] = {
            "probability": probability,
            "threshold": threshold,
            "potential_finding": detected,
        }

        if detected:
            detected_findings.append(
                label
            )


    no_selected_finding_detected = (
        len(detected_findings) == 0
    )


    if no_selected_finding_detected:

        summary = (
            "No selected finding detected"
        )

    else:

        summary = (
            "Potential findings: "
            + ", ".join(
                detected_findings
            )
        )


    return {
        "predictions": {
            label: probability_dict[label]
            for label in DISEASE_LABELS
        },

        "findings": findings,

        "detected_findings":
            detected_findings,

        "no_selected_finding_detected":
            no_selected_finding_detected,

        "summary":
            summary,

        "no_finding_score":
            probability_dict["No Finding"],

        "model":
            "DenseNet121 Final Model",

        "model_epoch":
            checkpoint.get("epoch"),

        "validation_macro_auc":
            checkpoint.get("macro_auc"),
    }


# --------------------------------------------------
# Grad-CAM
# --------------------------------------------------

def generate_gradcam(
    image,
    finding
):

    if finding not in DISEASE_LABELS:

        raise ValueError(
            f"Unsupported finding: {finding}"
        )


    class_index = TARGET_LABELS.index(
        finding
    )


    original_image = image.convert(
        "RGB"
    )


    # --------------------------------------------------
    # Prepare image
    # --------------------------------------------------

    image_tensor = inference_transform(
        original_image
    )

    image_tensor = (
        image_tensor
        .unsqueeze(0)
        .to(DEVICE)
    )


    # --------------------------------------------------
    # Store activation
    # --------------------------------------------------

    activation_holder = {}


    def save_activation(
        module,
        inputs,
        output
    ):

        # We need the gradient of this feature map
        output.retain_grad()

        activation_holder[
            "value"
        ] = output


    # Same layer used successfully in Colab
    target_layer = model.features.norm5


    hook = target_layer.register_forward_hook(
        save_activation
    )


    try:

        model.eval()

        model.zero_grad(
            set_to_none=True
        )


        # --------------------------------------------------
        # Forward pass
        # --------------------------------------------------

        logits = model(
            image_tensor
        )


        score = logits[
            0,
            class_index
        ]


        probability = torch.sigmoid(
            score
        ).item()


        # --------------------------------------------------
        # Backward pass
        # --------------------------------------------------

        score.backward()


        activation = activation_holder[
            "value"
        ]


        gradients = activation.grad


        if gradients is None:

            raise RuntimeError(
                "Grad-CAM gradients were not generated."
            )


        # --------------------------------------------------
        # Grad-CAM calculation
        # --------------------------------------------------

        weights = gradients.mean(
            dim=(2, 3),
            keepdim=True
        )


        cam = (
            weights * activation
        ).sum(
            dim=1,
            keepdim=True
        )


        cam = torch.relu(
            cam
        )


        cam = F.interpolate(
            cam,
            size=(224, 224),
            mode="bilinear",
            align_corners=False
        )


        cam = cam.squeeze()


        # Normalize to 0..1
        cam = (
            cam - cam.min()
        )


        if cam.max().item() > 0:

            cam = (
                cam / cam.max()
            )


        cam_array = (
            cam.detach()
            .cpu()
            .numpy()
        )


    finally:

        hook.remove()


    # --------------------------------------------------
    # Create colored heatmap
    # --------------------------------------------------

    heatmap_array = (
        cam_array * 255
    ).astype(
        np.uint8
    )


    heatmap_gray = Image.fromarray(
        heatmap_array
    )


    heatmap_gray = heatmap_gray.resize(
        original_image.size,
        Image.Resampling.BILINEAR
    )


    heatmap_color = ImageOps.colorize(
        heatmap_gray,
        black="#183BFF",
        mid="#FFD600",
        white="#FF1E1E"
    )


    # --------------------------------------------------
    # Overlay on original image
    # --------------------------------------------------

    original_for_overlay = (
        original_image.convert("RGB")
    )


    heatmap_for_overlay = (
        heatmap_color.convert("RGB")
    )


    overlay = Image.blend(
        original_for_overlay,
        heatmap_for_overlay,
        alpha=0.38
    )


    # --------------------------------------------------
    # Convert to Base64
    # --------------------------------------------------

    buffer = BytesIO()


    overlay.save(
        buffer,
        format="PNG"
    )


    encoded_image = base64.b64encode(
        buffer.getvalue()
    ).decode(
        "utf-8"
    )


    attention_map = (
        "data:image/png;base64,"
        + encoded_image
    )


    return {
        "finding":
            finding,

        "attention_map":
            attention_map,

        "probability":
            probability,

        "explanation": (
            "The highlighted regions show "
            "areas that influenced the AI "
            "analysis. They do not confirm "
            "the exact location of disease."
        ),
    }
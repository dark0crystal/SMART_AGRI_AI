from __future__ import annotations

from typing import Any

from PIL import Image


def predict_from_pil(
    model: Any,
    class_names: list[str],
    device: Any,
    image: Image.Image,
    *,
    top_k: int = 5,
) -> dict[str, Any]:
    """
    Run inference on a PIL image (RGB).
    Returns predicted_label, confidence (top-1 prob), top_k list of {name, prob}.
    """
    import torch

    from .checkpoint import build_infer_transform

    if image.mode != "RGB":
        image = image.convert("RGB")

    transform = build_infer_transform()
    x = transform(image).unsqueeze(0).to(device)
    with torch.no_grad():
        logits = model(x)
        probs = torch.softmax(logits, dim=1).squeeze(0).cpu()

    k = min(top_k, len(class_names))
    top_probs, top_idx = torch.topk(probs, k=k)
    top_list = [
        {"name": class_names[idx], "prob": float(prob)}
        for idx, prob in zip(top_idx.tolist(), top_probs.tolist())
    ]

    best_idx = top_idx[0].item()
    predicted_label = class_names[best_idx]
    confidence = float(top_probs[0].item())

    return {
        "predicted_label": predicted_label,
        "confidence": confidence,
        "top_k": top_list,
        "all_probs": {class_names[i]: float(probs[i]) for i in range(len(class_names))},
    }

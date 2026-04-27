"""Load timm models from training checkpoints (lazy-imports torch/timm)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

IMAGE_SIZE = 224


def build_infer_transform():
    from torchvision import transforms

    return transforms.Compose(
        [
            transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ]
    )


def load_checkpoint(
    model_path: Path,
    device: Any,
    *,
    default_model_name: str = "efficientnet_b1",
) -> tuple[Any, list[str]]:
    import timm
    import torch

    checkpoint = torch.load(model_path, map_location=device, weights_only=False)
    if not isinstance(checkpoint, dict):
        raise ValueError("Invalid checkpoint: expected a dict payload.")

    class_names = checkpoint.get("class_names", [])
    if not class_names:
        raise ValueError("Invalid checkpoint: missing 'class_names'.")

    # Support both old format (`config`) and new format (`args`) checkpoints.
    config = checkpoint.get("config") or {}
    args = checkpoint.get("args") or {}

    model_name = (
        config.get("model")
        or args.get("model")
        or args.get("arch")
        or default_model_name
    )
    dropout = config.get("dropout", args.get("dropout", 0.3))

    model = timm.create_model(
        model_name,
        pretrained=False,
        num_classes=len(class_names),
        drop_rate=dropout,
        drop_path_rate=0.2,
    )

    state_dict = checkpoint.get("model_state_dict", checkpoint)
    model.load_state_dict(state_dict, strict=True)
    model.to(device)
    model.eval()
    return model, list(class_names)

"""PyTorch leaf-disease inference. Import submodules directly to avoid eager torch/timm loads."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .checkpoint import build_infer_transform, load_checkpoint
    from .predict import predict_from_pil

__all__ = ["build_infer_transform", "load_checkpoint", "predict_from_pil"]


def __getattr__(name: str):
    if name in ("build_infer_transform", "load_checkpoint"):
        from .checkpoint import build_infer_transform, load_checkpoint

        if name == "build_infer_transform":
            return build_infer_transform
        return load_checkpoint
    if name == "predict_from_pil":
        from .predict import predict_from_pil

        return predict_from_pil
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

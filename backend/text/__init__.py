"""TF-IDF text-based disease prediction. Import submodules directly to avoid eager sklearn loads."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .predict import load_text_model, predict_from_text

__all__ = ["load_text_model", "predict_from_text"]


def __getattr__(name: str):
    if name in ("load_text_model", "predict_from_text"):
        from .predict import load_text_model, predict_from_text

        if name == "load_text_model":
            return load_text_model
        return predict_from_text
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

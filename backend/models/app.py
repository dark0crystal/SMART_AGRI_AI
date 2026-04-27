import argparse
import sys
from pathlib import Path

# Allow `python app.py` from backend/models/ to import backend/vision.
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

import gradio as gr
import torch
from PIL import Image

from vision.checkpoint import load_checkpoint
from vision.predict import predict_from_pil

DEFAULT_MODEL_PATH = "final_model.pth"


def make_predict_fn(model, class_names, device):
    def predict(image):
        if image is None:
            return "No image uploaded.", {}

        if not isinstance(image, Image.Image):
            image = Image.fromarray(image)

        out = predict_from_pil(model, class_names, device, image, top_k=5)
        top_items = [
            f"{item['name']}: {item['prob'] * 100:.2f}%"
            for item in out["top_k"]
        ]
        details = "\n".join(top_items)
        label = out["predicted_label"]
        text = f"Predicted: {label}\n\nTop-{len(out['top_k'])}:\n{details}"
        return text, out["all_probs"]

    return predict


def main():
    parser = argparse.ArgumentParser(description="Run image prediction UI for final_model.pth")
    parser.add_argument("--model-path", type=str, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7860)
    parser.add_argument("--share", action="store_true")
    args = parser.parse_args()

    model_path = Path(args.model_path)
    if not model_path.is_absolute():
        model_path = Path(__file__).resolve().parent / model_path
    if not model_path.exists():
        raise FileNotFoundError(f"Model file not found: {model_path}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, class_names = load_checkpoint(model_path, device)
    predict_fn = make_predict_fn(model, class_names, device)

    demo = gr.Interface(
        fn=predict_fn,
        inputs=gr.Image(type="pil", label="Upload Leaf Image"),
        outputs=[
            gr.Textbox(label="Prediction"),
            gr.Label(label="Class Probabilities"),
        ],
        title="Plant Disease Classifier",
        description=f"Loaded model: {model_path} | Device: {device}",
    )
    demo.launch(server_name=args.host, server_port=args.port, share=args.share)


if __name__ == "__main__":
    main()

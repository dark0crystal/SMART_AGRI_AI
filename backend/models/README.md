# Multi-Model Plant Disease Training

This project trains and compares multiple deep learning models for 10 plant leaf classes using `train_all_models.py`.

## 1) Go to the project folder

```bash
cd "/Users/madadtechteam/Desktop/FYP_files"
```

## 2) Create and activate a virtual environment (recommended)

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 3) Install required packages

```bash
pip install torch torchvision timm numpy pandas matplotlib scikit-learn pillow gradio
```

## 4) Prepare dataset folder

By default, the script expects:
- dataset path: `Original Dataset`
- class folders with exact names:
  - `Anthracnose`
  - `Bacterial Blight`
  - `Citrus Canker`
  - `Curl Virus`
  - `Deficiency Leaf`
  - `Dry Leaf`
  - `Healthy Leaf`
  - `Sooty Mould`
  - `Spider Mites`
  - `Witch's Broom`

Expected structure:

```text
Original Dataset/
  Anthracnose/
  Bacterial Blight/
  Citrus Canker/
  Curl Virus/
  Deficiency Leaf/
  Dry Leaf/
  Healthy Leaf/
  Sooty Mould/
  Spider Mites/
  Witch's Broom/
```

## 5) Run training

Default run:

```bash
python3 train_all_models.py
```

Custom run (example):

```bash
python3 train_all_models.py --dataset "Original Dataset" --output "model_comparison" --epochs 30 --batch-size 16 --patience 10
```

## 6) Run trained model (upload images to test)

If you already have `final_model.pth`, you can run the inference web UI without training.

Start UI:

```bash
python3 app.py --model-path "final_model.pth"
```

Then open:

- `http://127.0.0.1:7860`

Upload a leaf image and the app will show:

- predicted class
- top class probabilities

If your model is in another path:

```bash
python3 app.py --model-path "outputs/final_model.pth"
```

## Optional: quick test run

Use fewer epochs to confirm everything works before a long training job:

```bash
python3 train_all_models.py --epochs 2 --batch-size 8
```

## What the script does

- Trains 7 model configurations (EfficientNet and ResNet variants).
- Uses GPU automatically if available, otherwise CPU.
- Saves per-model outputs:
  - `model.pth`
  - `training_history.csv`
  - `classification_report.csv`
  - `confusion_matrix.png`
- Saves overall comparison files in `model_comparison/`:
  - `comparison_results.csv`
  - `comparison_plot.png`
  - `summary.json`
- Copies best model to `outputs/final_model.pth`.

## Notes

- First run may take longer because pretrained model weights may download.
- Full training can take a long time because all 7 configurations are trained.
- The `model_comparison/` outputs described above are produced when you run `train_all_models.py`; they are not kept in the git repository (regenerate locally after cloning if needed).

"""
Training Script for EfficientNet-B1 with Weighted Cross-Entropy
Optimized for balanced/augmented dataset.
"""

import argparse
import json
import os
import random
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import timm
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler
from torchvision import datasets, transforms

CLASS_NAMES = [
    "Anthracnose",
    "Bacterial Blight",
    "Citrus Canker",
    "Curl Virus",
    "Deficiency Leaf",
    "Dry Leaf",
    "Healthy Leaf",
    "Sooty Mould",
    "Spider Mites",
    "Witch's Broom",
]

LABEL_MAP = {
    "Anthracnose": "Fungal Disease",
    "Bacterial Blight": "Bacterial disease",
    "Citrus Canker": "Bacterial disease",
    "Curl Virus": "Nutrient / physiological disorder",
    "Deficiency Leaf": "Nutrient / physiological disorder",
    "Dry Leaf": "Physiological stress",
    "Healthy Leaf": "Healthy",
    "Sooty Mould": "Honeydew / sooty mould",
    "Spider Mites": "Pest infestation",
    "Witch's Broom": "Nutrient / physiological disorder",
}

IMAGE_SIZE = 224


def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def build_transforms():
    train_transform = transforms.Compose([
        transforms.RandomResizedCrop(IMAGE_SIZE, scale=(0.7, 1.0), ratio=(0.85, 1.15)),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomVerticalFlip(p=0.5),
        transforms.RandomRotation(25),
        transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.3, hue=0.08),
        transforms.RandomAffine(degrees=12, translate=(0.08, 0.08), shear=8),
        transforms.GaussianBlur(kernel_size=3, sigma=(0.1, 1.5)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        transforms.RandomErasing(p=0.2, scale=(0.02, 0.15)),
    ])
    
    test_transform = transforms.Compose([
        transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])
    return train_transform, test_transform


def get_tta_transforms():
    base = [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]
    return [
        transforms.Compose([
            transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
            transforms.ToTensor(),
            transforms.Normalize(*base),
        ]),
        transforms.Compose([
            transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
            transforms.RandomHorizontalFlip(p=1.0),
            transforms.ToTensor(),
            transforms.Normalize(*base),
        ]),
        transforms.Compose([
            transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
            transforms.RandomVerticalFlip(p=1.0),
            transforms.ToTensor(),
            transforms.Normalize(*base),
        ]),
        transforms.Compose([
            transforms.Resize((int(IMAGE_SIZE * 1.1), int(IMAGE_SIZE * 1.1))),
            transforms.CenterCrop(IMAGE_SIZE),
            transforms.ToTensor(),
            transforms.Normalize(*base),
        ]),
        transforms.Compose([
            transforms.Resize((IMAGE_SIZE + 16, IMAGE_SIZE + 16)),
            transforms.CenterCrop(IMAGE_SIZE),
            transforms.ToTensor(),
            transforms.Normalize(*base),
        ]),
    ]


class TransformSubset(Dataset):
    def __init__(self, dataset, indices, transform=None):
        self.dataset = dataset
        self.indices = indices
        self.transform = transform
    
    def __len__(self):
        return len(self.indices)
    
    def __getitem__(self, idx):
        original_idx = self.indices[idx]
        path, label = self.dataset.samples[original_idx]
        image = Image.open(path).convert("RGB")
        if self.transform:
            image = self.transform(image)
        return image, label
    
    def get_labels(self):
        return [self.dataset.targets[i] for i in self.indices]


def compute_class_weights(labels, num_classes):
    """Compute effective class weights."""
    counter = Counter(labels)
    beta = 0.9999
    weights = []
    for i in range(num_classes):
        n = counter.get(i, 1)
        effective_num = (1 - beta**n) / (1 - beta)
        weights.append(1.0 / effective_num)
    weights = np.array(weights)
    weights = weights / weights.sum() * num_classes
    return torch.tensor(weights, dtype=torch.float32)


def create_dataloaders(dataset_dir, batch_size, seed=42):
    train_transform, test_transform = build_transforms()
    dataset = datasets.ImageFolder(dataset_dir)
    
    # Check class names match
    if dataset.classes != CLASS_NAMES:
        print(f"Warning: Class order mismatch!")
        print(f"  Expected: {CLASS_NAMES}")
        print(f"  Found: {dataset.classes}")
    
    indices = list(range(len(dataset)))
    labels = [dataset.targets[i] for i in indices]
    
    # Stratified split: 70% train, 15% val, 15% test
    train_idx, temp_idx, train_labels, temp_labels = train_test_split(
        indices, labels, test_size=0.30, stratify=labels, random_state=seed
    )
    val_idx, test_idx = train_test_split(
        temp_idx, test_size=0.50, stratify=temp_labels, random_state=seed
    )
    
    train_dataset = TransformSubset(dataset, train_idx, transform=train_transform)
    val_dataset = TransformSubset(dataset, val_idx, transform=test_transform)
    test_dataset = TransformSubset(dataset, test_idx, transform=test_transform)
    
    num_workers = min(4, os.cpu_count() or 1)
    
    # Weighted sampler for balanced batches
    train_labels_subset = train_dataset.get_labels()
    class_counts = Counter(train_labels_subset)
    sample_weights = [1.0 / class_counts[label] for label in train_labels_subset]
    sampler = WeightedRandomSampler(sample_weights, len(sample_weights), replacement=True)
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, sampler=sampler,
                               num_workers=num_workers, pin_memory=True, drop_last=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False,
                             num_workers=num_workers, pin_memory=True)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False,
                              num_workers=num_workers, pin_memory=True)
    
    return train_loader, val_loader, test_loader, train_labels_subset, dataset


def build_model(num_classes, dropout_rate=0.3):
    model = timm.create_model(
        "efficientnet_b1",
        pretrained=True,
        num_classes=num_classes,
        drop_rate=dropout_rate,
        drop_path_rate=0.2,
    )
    return model


class EarlyStopping:
    def __init__(self, patience=10, min_delta=0.0005):
        self.patience = patience
        self.min_delta = min_delta
        self.counter = 0
        self.best_loss = None
        self.best_state = None
        self.early_stop = False
    
    def __call__(self, val_loss, model):
        if self.best_loss is None:
            self.best_loss = val_loss
            self.best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
        elif val_loss > self.best_loss - self.min_delta:
            self.counter += 1
            if self.counter >= self.patience:
                self.early_stop = True
        else:
            self.best_loss = val_loss
            self.best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            self.counter = 0
        return self.early_stop
    
    def restore(self, model):
        if self.best_state:
            model.load_state_dict(self.best_state)


def get_lr_scheduler(optimizer, num_epochs, warmup_epochs=3):
    def lr_lambda(epoch):
        if epoch < warmup_epochs:
            return (epoch + 1) / warmup_epochs
        else:
            progress = (epoch - warmup_epochs) / (num_epochs - warmup_epochs)
            return 0.5 * (1 + np.cos(np.pi * progress))
    return torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)


def mixup_data(x, y, alpha=0.2):
    if alpha > 0:
        lam = np.random.beta(alpha, alpha)
    else:
        lam = 1
    batch_size = x.size(0)
    index = torch.randperm(batch_size, device=x.device)
    mixed_x = lam * x + (1 - lam) * x[index, :]
    y_a, y_b = y, y[index]
    return mixed_x, y_a, y_b, lam


def train_one_epoch(model, loader, optimizer, criterion, device, use_mixup=True):
    model.train()
    running_loss = 0.0
    running_correct = 0
    running_total = 0
    
    for images, targets in loader:
        images = images.to(device)
        targets = targets.to(device)
        optimizer.zero_grad()
        
        if use_mixup and random.random() > 0.5:
            mixed_images, targets_a, targets_b, lam = mixup_data(images, targets, 0.2)
            outputs = model(mixed_images)
            loss = lam * criterion(outputs, targets_a) + (1 - lam) * criterion(outputs, targets_b)
            _, preds = outputs.max(1)
            correct = (lam * (preds == targets_a).float() + (1 - lam) * (preds == targets_b).float()).sum().item()
        else:
            outputs = model(images)
            loss = criterion(outputs, targets)
            _, preds = outputs.max(1)
            correct = (preds == targets).sum().item()
        
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        
        running_loss += loss.item() * images.size(0)
        running_correct += correct
        running_total += targets.size(0)
    
    return running_loss / running_total, running_correct / running_total


def evaluate(model, loader, device, criterion=None):
    model.eval()
    correct = 0
    total = 0
    total_loss = 0.0
    all_preds, all_labels = [], []
    
    with torch.no_grad():
        for images, targets in loader:
            images = images.to(device)
            targets = targets.to(device)
            outputs = model(images)
            
            if criterion:
                loss = criterion(outputs, targets)
                total_loss += loss.item() * images.size(0)
            
            _, preds = outputs.max(1)
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(targets.cpu().numpy())
            correct += (preds == targets).sum().item()
            total += targets.size(0)
    
    accuracy = correct / total if total > 0 else 0.0
    avg_loss = total_loss / total if total > 0 and criterion else 0.0
    return accuracy, avg_loss, np.array(all_preds), np.array(all_labels)


def evaluate_with_tta(model, dataset, device, num_tta=5):
    model.eval()
    tta_transforms = get_tta_transforms()[:num_tta]
    all_preds, all_labels = [], []
    
    with torch.no_grad():
        for idx in range(len(dataset.indices)):
            original_idx = dataset.indices[idx]
            path, label = dataset.dataset.samples[original_idx]
            image = Image.open(path).convert("RGB")
            
            probs_sum = None
            for transform in tta_transforms:
                img_tensor = transform(image).unsqueeze(0).to(device)
                outputs = model(img_tensor)
                probs = F.softmax(outputs, dim=1)
                probs_sum = probs if probs_sum is None else probs_sum + probs
            
            avg_probs = probs_sum / len(tta_transforms)
            pred = avg_probs.argmax(dim=1).item()
            all_preds.append(pred)
            all_labels.append(label)
    
    all_preds = np.array(all_preds)
    all_labels = np.array(all_labels)
    accuracy = (all_preds == all_labels).mean()
    return accuracy, all_preds, all_labels


def plot_confusion_matrix(cm, class_names, output_path, normalize=False):
    if normalize:
        cm = cm.astype('float') / cm.sum(axis=1, keepdims=True)
        fmt = '.2f'
    else:
        fmt = 'd'
    
    plt.figure(figsize=(12, 10))
    plt.imshow(cm, interpolation="nearest", cmap=plt.cm.Blues)
    plt.title("Confusion Matrix" + (" (Normalized)" if normalize else ""))
    plt.colorbar()
    tick_marks = np.arange(len(class_names))
    plt.xticks(tick_marks, class_names, rotation=45, ha="right")
    plt.yticks(tick_marks, class_names)
    threshold = cm.max() / 2.0
    for i, j in np.ndindex(cm.shape):
        plt.text(j, i, f"{cm[i, j]:{fmt}}", ha="center",
                 color="white" if cm[i, j] > threshold else "black")
    plt.tight_layout()
    plt.ylabel("True label")
    plt.xlabel("Predicted label")
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()


def save_history(history, output_dir):
    df = pd.DataFrame(history)
    df.to_csv(output_dir / "training_history.csv", index=False)
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    axes[0].plot(df["epoch"], df["train_loss"], label="Train Loss", marker='o', markersize=4)
    axes[0].plot(df["epoch"], df["val_loss"], label="Val Loss", marker='s', markersize=4)
    axes[0].set_xlabel("Epoch")
    axes[0].set_ylabel("Loss")
    axes[0].legend()
    axes[0].set_title("Training and Validation Loss")
    axes[0].grid(True, alpha=0.3)
    
    axes[1].plot(df["epoch"], df["train_acc"], label="Train Acc", marker='o', markersize=4)
    axes[1].plot(df["epoch"], df["val_acc"], label="Val Acc", marker='s', markersize=4)
    axes[1].set_xlabel("Epoch")
    axes[1].set_ylabel("Accuracy")
    axes[1].legend()
    axes[1].set_title("Training and Validation Accuracy")
    axes[1].grid(True, alpha=0.3)
    axes[1].set_ylim([0.5, 1.02])
    
    plt.tight_layout()
    plt.savefig(output_dir / "training_curves.png", dpi=150, bbox_inches="tight")
    plt.close()


def main():
    parser = argparse.ArgumentParser(description="Train EfficientNet-B1 with Weighted CE")
    parser.add_argument("--dataset", type=str, default="Original Dataset")
    parser.add_argument("--output", type=str, default="outputs")
    parser.add_argument("--epochs", type=int, default=35)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--weight-decay", type=float, default=0.01)
    parser.add_argument("--dropout", type=float, default=0.3)
    parser.add_argument("--label-smoothing", type=float, default=0.1)
    parser.add_argument("--patience", type=int, default=12)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--tta", type=int, default=5, help="Number of TTA transforms")
    parser.add_argument("--no-mixup", action="store_true", help="Disable mixup")
    args = parser.parse_args()
    
    set_seed(args.seed)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    print("="*60)
    print("EfficientNet-B1 + Weighted Cross-Entropy Training")
    print("="*60)
    print(f"Device: {device}")
    print(f"Dataset: {args.dataset}")
    print(f"Epochs: {args.epochs}")
    print(f"Batch size: {args.batch_size}")
    print(f"Learning rate: {args.lr}")
    print(f"Dropout: {args.dropout}")
    print(f"Label smoothing: {args.label_smoothing}")
    print(f"Early stopping patience: {args.patience}")
    print(f"TTA transforms: {args.tta}")
    print()
    
    # Data
    train_loader, val_loader, test_loader, train_labels, full_dataset = create_dataloaders(
        args.dataset, args.batch_size, args.seed
    )
    
    print(f"Dataset splits: train={len(train_loader.dataset)}, "
          f"val={len(val_loader.dataset)}, test={len(test_loader.dataset)}")
    
    # Class distribution
    print("\nClass distribution (training set):")
    counter = Counter(train_labels)
    for i, name in enumerate(CLASS_NAMES):
        print(f"  {name:20s}: {counter.get(i, 0):4d}")
    
    # Compute class weights
    class_weights = compute_class_weights(train_labels, len(CLASS_NAMES))
    print("\nClass weights:")
    for i, name in enumerate(CLASS_NAMES):
        print(f"  {name:20s}: {class_weights[i]:.3f}")
    
    # Model
    model = build_model(len(CLASS_NAMES), args.dropout)
    model = model.to(device)
    
    # Loss with class weights
    criterion = nn.CrossEntropyLoss(
        weight=class_weights.to(device),
        label_smoothing=args.label_smoothing
    )
    
    # Optimizer
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    scheduler = get_lr_scheduler(optimizer, args.epochs, warmup_epochs=3)
    early_stopping = EarlyStopping(patience=args.patience)
    
    # Training
    history = []
    best_val_acc = 0.0
    
    print("\n" + "="*60)
    print("TRAINING")
    print("="*60)
    
    for epoch in range(1, args.epochs + 1):
        train_loss, train_acc = train_one_epoch(
            model, train_loader, optimizer, criterion, device, 
            use_mixup=not args.no_mixup
        )
        val_acc, val_loss, _, _ = evaluate(model, val_loader, device, criterion)
        scheduler.step()
        
        history.append({
            "epoch": epoch,
            "train_loss": train_loss,
            "val_loss": val_loss,
            "train_acc": train_acc,
            "val_acc": val_acc,
        })
        
        gap = train_acc - val_acc
        status = ""
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            status = " ★ best"
            torch.save({
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "val_acc": best_val_acc,
                "class_names": CLASS_NAMES,
                "label_map": LABEL_MAP,
                "args": vars(args),
            }, output_dir / "best_model.pth")
        
        print(f"Epoch {epoch:2d}/{args.epochs} | "
              f"train_loss={train_loss:.4f} train_acc={train_acc:.4f} | "
              f"val_loss={val_loss:.4f} val_acc={val_acc:.4f} | "
              f"gap={gap:+.3f}{status}")
        
        if early_stopping(val_loss, model):
            print(f"\nEarly stopping triggered at epoch {epoch}")
            break
    
    # Restore best model
    early_stopping.restore(model)
    save_history(history, output_dir)
    
    # Evaluation
    print("\n" + "="*60)
    print("EVALUATION")
    print("="*60)
    
    test_acc, test_loss, test_preds, test_labels_arr = evaluate(model, test_loader, device, criterion)
    print(f"\nStandard Test Accuracy: {test_acc:.4f}")
    
    # TTA evaluation
    if args.tta > 0:
        print(f"Running TTA ({args.tta} transforms)...")
        test_dataset = test_loader.dataset
        tta_acc, tta_preds, tta_labels = evaluate_with_tta(model, test_dataset, device, args.tta)
        print(f"TTA Test Accuracy: {tta_acc:.4f} ({(tta_acc - test_acc)*100:+.2f}%)")
        final_preds, final_labels = tta_preds, tta_labels
        final_acc = tta_acc
    else:
        final_preds, final_labels = test_preds, test_labels_arr
        final_acc = test_acc
    
    # Confusion matrix
    cm = confusion_matrix(final_labels, final_preds)
    plot_confusion_matrix(cm, CLASS_NAMES, output_dir / "test_confusion_matrix.png")
    plot_confusion_matrix(cm, CLASS_NAMES, output_dir / "test_confusion_matrix_normalized.png", normalize=True)
    
    # Classification report
    report = classification_report(final_labels, final_preds, target_names=CLASS_NAMES, output_dict=True)
    df_report = pd.DataFrame(report).transpose()
    df_report.to_csv(output_dir / "test_classification_report.csv")
    
    print("\nPer-class performance:")
    for name in CLASS_NAMES:
        if name in report:
            r = report[name]
            print(f"  {name:20s}: P={r['precision']:.3f} R={r['recall']:.3f} F1={r['f1-score']:.3f}")
    
    # Save label map
    with open(output_dir / "label_map.json", "w") as f:
        json.dump(LABEL_MAP, f, indent=2)
    
    # Save final model
    torch.save({
        "model_state_dict": model.state_dict(),
        "class_names": CLASS_NAMES,
        "label_map": LABEL_MAP,
        "test_acc": final_acc,
        "args": vars(args),
    }, output_dir / "final_model.pth")
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Best validation accuracy: {best_val_acc:.4f}")
    print(f"Final test accuracy: {final_acc:.4f}")
    print(f"Macro F1: {report['macro avg']['f1-score']:.4f}")
    print(f"Epochs trained: {len(history)}")
    
    # Problem classes
    problem_classes = [(name, report[name]['f1-score']) 
                       for name in CLASS_NAMES if name in report and report[name]['f1-score'] < 0.85]
    
    if problem_classes:
        print("\n⚠️  Classes with F1 < 0.85:")
        for name, f1 in sorted(problem_classes, key=lambda x: x[1]):
            print(f"    {name}: F1={f1:.3f}")
    else:
        print("\n✓ All classes performing well (F1 >= 0.85)")
    
    print(f"\nOutputs saved to: {output_dir}/")


if __name__ == "__main__":
    main()

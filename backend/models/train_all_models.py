"""
Multi-Model Training Script
Trains multiple model configurations and saves all results for comparison.
Outputs a summary table showing which model performed best.
"""

import argparse
import json
import os
import random
import time
from collections import Counter
from datetime import datetime
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


# =============================================================================
# LOSS FUNCTIONS
# =============================================================================

class FocalLoss(nn.Module):
    def __init__(self, alpha=None, gamma=2.0, reduction='mean', label_smoothing=0.0):
        super().__init__()
        self.alpha = alpha
        self.gamma = gamma
        self.reduction = reduction
        self.label_smoothing = label_smoothing
    
    def forward(self, inputs, targets):
        p = F.softmax(inputs, dim=-1)
        ce_loss = F.cross_entropy(inputs, targets, reduction='none', 
                                   label_smoothing=self.label_smoothing)
        p_t = p.gather(1, targets.unsqueeze(1)).squeeze(1)
        focal_weight = (1 - p_t) ** self.gamma
        
        if self.alpha is not None:
            alpha_t = self.alpha.to(inputs.device).gather(0, targets)
            focal_weight = alpha_t * focal_weight
        
        loss = focal_weight * ce_loss
        
        if self.reduction == 'mean':
            return loss.mean()
        elif self.reduction == 'sum':
            return loss.sum()
        return loss


# =============================================================================
# DATA
# =============================================================================

def build_transforms():
    train_transform = transforms.Compose([
        transforms.RandomResizedCrop(IMAGE_SIZE, scale=(0.6, 1.0), ratio=(0.8, 1.2)),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomVerticalFlip(p=0.5),
        transforms.RandomRotation(30),
        transforms.ColorJitter(brightness=0.4, contrast=0.4, saturation=0.4, hue=0.1),
        transforms.RandomAffine(degrees=15, translate=(0.1, 0.1), shear=10, scale=(0.85, 1.15)),
        transforms.RandomGrayscale(p=0.1),
        transforms.GaussianBlur(kernel_size=3, sigma=(0.1, 2.0)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        transforms.RandomErasing(p=0.25, scale=(0.02, 0.2)),
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
            transforms.Resize((IMAGE_SIZE + 20, IMAGE_SIZE + 20)),
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


def create_dataloaders(dataset_dir, batch_size, seed=42, use_weighted_sampler=True):
    train_transform, test_transform = build_transforms()
    dataset = datasets.ImageFolder(dataset_dir)
    
    assert dataset.classes == CLASS_NAMES, f"Folder mismatch: {dataset.classes}"
    
    indices = list(range(len(dataset)))
    labels = [dataset.targets[i] for i in indices]
    
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
    
    sampler = None
    shuffle = True
    if use_weighted_sampler:
        train_labels_subset = train_dataset.get_labels()
        class_counts = Counter(train_labels_subset)
        sample_weights = [1.0 / class_counts[label] for label in train_labels_subset]
        sampler = WeightedRandomSampler(sample_weights, len(sample_weights), replacement=True)
        shuffle = False
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=shuffle, 
                               sampler=sampler, num_workers=num_workers, pin_memory=True, drop_last=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False,
                             num_workers=num_workers, pin_memory=True)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False,
                              num_workers=num_workers, pin_memory=True)
    
    return train_loader, val_loader, test_loader, train_dataset.get_labels()


# =============================================================================
# MODEL
# =============================================================================

def build_model(num_classes, model_name, dropout_rate=0.3):
    model = timm.create_model(
        model_name,
        pretrained=True,
        num_classes=num_classes,
        drop_rate=dropout_rate,
        drop_path_rate=0.2,
    )
    return model


# =============================================================================
# TRAINING
# =============================================================================

class EarlyStopping:
    def __init__(self, patience=10, min_delta=0.001):
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
        
        if use_mixup and np.random.random() > 0.5:
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


def plot_confusion_matrix(cm, class_names, output_path):
    plt.figure(figsize=(12, 10))
    plt.imshow(cm, interpolation="nearest", cmap=plt.cm.Blues)
    plt.title("Confusion Matrix")
    plt.colorbar()
    tick_marks = np.arange(len(class_names))
    plt.xticks(tick_marks, class_names, rotation=45, ha="right")
    plt.yticks(tick_marks, class_names)
    threshold = cm.max() / 2.0
    for i, j in np.ndindex(cm.shape):
        plt.text(j, i, f"{cm[i, j]}", ha="center",
                 color="white" if cm[i, j] > threshold else "black")
    plt.tight_layout()
    plt.ylabel("True label")
    plt.xlabel("Predicted label")
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()


# =============================================================================
# MODEL CONFIGURATIONS TO TEST
# =============================================================================

MODEL_CONFIGS = [
    {
        "name": "efficientnet_b0_focal",
        "model": "efficientnet_b0",
        "loss": "focal",
        "dropout": 0.3,
        "lr": 1e-4,
    },
    {
        "name": "efficientnet_b1_focal",
        "model": "efficientnet_b1",
        "loss": "focal",
        "dropout": 0.3,
        "lr": 1e-4,
    },
    {
        "name": "efficientnet_b2_focal",
        "model": "efficientnet_b2",
        "loss": "focal",
        "dropout": 0.3,
        "lr": 1e-4,
    },
    {
        "name": "efficientnet_b3_focal",
        "model": "efficientnet_b3",
        "loss": "focal",
        "dropout": 0.4,
        "lr": 5e-5,
    },
    {
        "name": "resnet50_focal",
        "model": "resnet50",
        "loss": "focal",
        "dropout": 0.3,
        "lr": 1e-4,
    },
    {
        "name": "efficientnet_b1_weighted_ce",
        "model": "efficientnet_b1",
        "loss": "weighted_ce",
        "dropout": 0.3,
        "lr": 1e-4,
    },
    {
        "name": "efficientnet_b2_weighted_ce",
        "model": "efficientnet_b2",
        "loss": "weighted_ce",
        "dropout": 0.3,
        "lr": 1e-4,
    },
]


def train_single_model(config, train_loader, val_loader, test_loader, train_labels,
                       device, output_dir, epochs=30, patience=10):
    """Train a single model configuration and return results."""
    
    print(f"\n{'='*60}")
    print(f"Training: {config['name']}")
    print(f"{'='*60}")
    print(f"  Model: {config['model']}")
    print(f"  Loss: {config['loss']}")
    print(f"  Dropout: {config['dropout']}")
    print(f"  LR: {config['lr']}")
    
    set_seed(42)
    
    # Build model
    model = build_model(len(CLASS_NAMES), config['model'], config['dropout'])
    model = model.to(device)
    
    # Compute class weights
    class_weights = compute_class_weights(train_labels, len(CLASS_NAMES))
    
    # Loss function
    if config['loss'] == 'focal':
        criterion = FocalLoss(alpha=class_weights, gamma=2.0, label_smoothing=0.1)
    elif config['loss'] == 'weighted_ce':
        criterion = nn.CrossEntropyLoss(weight=class_weights.to(device), label_smoothing=0.1)
    else:
        criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
    
    # Optimizer
    optimizer = torch.optim.AdamW(model.parameters(), lr=config['lr'], weight_decay=0.01)
    scheduler = get_lr_scheduler(optimizer, epochs, warmup_epochs=3)
    early_stopping = EarlyStopping(patience=patience)
    
    # Training loop
    history = []
    best_val_acc = 0.0
    start_time = time.time()
    
    for epoch in range(1, epochs + 1):
        train_loss, train_acc = train_one_epoch(model, train_loader, optimizer, criterion, device)
        val_acc, val_loss, _, _ = evaluate(model, val_loader, device, criterion)
        scheduler.step()
        
        history.append({
            "epoch": epoch,
            "train_loss": train_loss,
            "val_loss": val_loss,
            "train_acc": train_acc,
            "val_acc": val_acc,
        })
        
        if val_acc > best_val_acc:
            best_val_acc = val_acc
        
        print(f"  Epoch {epoch:2d} | train_acc={train_acc:.4f} val_acc={val_acc:.4f}")
        
        if early_stopping(val_loss, model):
            print(f"  Early stopping at epoch {epoch}")
            break
    
    training_time = time.time() - start_time
    
    # Restore best model
    early_stopping.restore(model)
    
    # Evaluate on test set
    test_acc, _, test_preds, test_labels = evaluate(model, test_loader, device, criterion)
    
    # Evaluate with TTA
    test_dataset = test_loader.dataset
    tta_acc, tta_preds, tta_labels = evaluate_with_tta(model, test_dataset, device, num_tta=5)
    
    print(f"  Test Accuracy: {test_acc:.4f}")
    print(f"  TTA Accuracy:  {tta_acc:.4f}")
    
    # Save model
    model_dir = output_dir / config['name']
    model_dir.mkdir(parents=True, exist_ok=True)
    
    torch.save({
        "model_state_dict": model.state_dict(),
        "config": config,
        "class_names": CLASS_NAMES,
        "label_map": LABEL_MAP,
        "test_acc": test_acc,
        "tta_acc": tta_acc,
        "best_val_acc": best_val_acc,
        "epochs_trained": len(history),
    }, model_dir / "model.pth")
    
    # Save confusion matrix
    cm = confusion_matrix(tta_labels, tta_preds)
    plot_confusion_matrix(cm, CLASS_NAMES, model_dir / "confusion_matrix.png")
    
    # Save classification report
    report = classification_report(tta_labels, tta_preds, target_names=CLASS_NAMES, output_dict=True)
    df_report = pd.DataFrame(report).transpose()
    df_report.to_csv(model_dir / "classification_report.csv")
    
    # Save history
    pd.DataFrame(history).to_csv(model_dir / "training_history.csv", index=False)
    
    # Get per-class F1 scores
    class_f1 = {name: report[name]['f1-score'] for name in CLASS_NAMES if name in report}
    min_f1_class = min(class_f1, key=class_f1.get)
    min_f1 = class_f1[min_f1_class]
    
    return {
        "name": config['name'],
        "model": config['model'],
        "loss": config['loss'],
        "test_acc": test_acc,
        "tta_acc": tta_acc,
        "best_val_acc": best_val_acc,
        "epochs": len(history),
        "time_min": training_time / 60,
        "min_f1": min_f1,
        "min_f1_class": min_f1_class,
        "macro_f1": report['macro avg']['f1-score'],
    }


def main():
    parser = argparse.ArgumentParser(description="Train multiple models and compare")
    parser.add_argument("--dataset", type=str, default="Original Dataset")
    parser.add_argument("--output", type=str, default="model_comparison")
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--patience", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    
    set_seed(args.seed)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    print(f"Training {len(MODEL_CONFIGS)} model configurations...")
    
    # Create dataloaders (shared across all models)
    train_loader, val_loader, test_loader, train_labels = create_dataloaders(
        args.dataset, args.batch_size, args.seed
    )
    
    print(f"\nDataset: train={len(train_loader.dataset)}, val={len(val_loader.dataset)}, test={len(test_loader.dataset)}")
    
    # Train all models
    results = []
    for i, config in enumerate(MODEL_CONFIGS):
        print(f"\n[{i+1}/{len(MODEL_CONFIGS)}]", end="")
        result = train_single_model(
            config, train_loader, val_loader, test_loader, train_labels,
            device, output_dir, args.epochs, args.patience
        )
        results.append(result)
    
    # Create comparison table
    df_results = pd.DataFrame(results)
    df_results = df_results.sort_values('tta_acc', ascending=False)
    df_results.to_csv(output_dir / "comparison_results.csv", index=False)
    
    # Print summary
    print("\n" + "="*80)
    print("COMPARISON RESULTS (sorted by TTA accuracy)")
    print("="*80)
    print(f"\n{'Model':<30} {'Test Acc':>10} {'TTA Acc':>10} {'Macro F1':>10} {'Min F1':>10} {'Worst Class':<20}")
    print("-"*95)
    
    for _, row in df_results.iterrows():
        print(f"{row['name']:<30} {row['test_acc']:>10.4f} {row['tta_acc']:>10.4f} {row['macro_f1']:>10.4f} {row['min_f1']:>10.4f} {row['min_f1_class']:<20}")
    
    # Best model
    best = df_results.iloc[0]
    print("\n" + "="*80)
    print("🏆 BEST MODEL")
    print("="*80)
    print(f"  Name: {best['name']}")
    print(f"  Architecture: {best['model']}")
    print(f"  Loss: {best['loss']}")
    print(f"  Test Accuracy: {best['test_acc']:.4f}")
    print(f"  TTA Accuracy: {best['tta_acc']:.4f}")
    print(f"  Macro F1: {best['macro_f1']:.4f}")
    print(f"  Weakest Class: {best['min_f1_class']} (F1={best['min_f1']:.4f})")
    print(f"\n  Model saved at: {output_dir / best['name'] / 'model.pth'}")
    
    # Copy best model to outputs folder
    best_model_src = output_dir / best['name'] / "model.pth"
    best_model_dst = Path("outputs") / "best_model.pth"
    Path("outputs").mkdir(exist_ok=True)
    
    import shutil
    shutil.copy(best_model_src, best_model_dst)
    print(f"  Also copied to: {best_model_dst}")
    
    # Save summary JSON
    summary = {
        "best_model": best['name'],
        "best_tta_acc": float(best['tta_acc']),
        "best_test_acc": float(best['test_acc']),
        "all_results": results,
        "timestamp": datetime.now().isoformat(),
    }
    with open(output_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    
    # Create comparison plot
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    models = df_results['name'].tolist()
    x = np.arange(len(models))
    
    # Accuracy comparison
    axes[0].bar(x - 0.2, df_results['test_acc'], 0.4, label='Test Acc', color='steelblue')
    axes[0].bar(x + 0.2, df_results['tta_acc'], 0.4, label='TTA Acc', color='coral')
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(models, rotation=45, ha='right')
    axes[0].set_ylabel('Accuracy')
    axes[0].set_title('Test Accuracy Comparison')
    axes[0].legend()
    axes[0].set_ylim([0.7, 1.0])
    axes[0].grid(axis='y', alpha=0.3)
    
    # F1 comparison
    axes[1].bar(x - 0.2, df_results['macro_f1'], 0.4, label='Macro F1', color='seagreen')
    axes[1].bar(x + 0.2, df_results['min_f1'], 0.4, label='Min Class F1', color='tomato')
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(models, rotation=45, ha='right')
    axes[1].set_ylabel('F1 Score')
    axes[1].set_title('F1 Score Comparison')
    axes[1].legend()
    axes[1].set_ylim([0, 1.0])
    axes[1].grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_dir / "comparison_plot.png", dpi=150, bbox_inches="tight")
    plt.close()
    
    print(f"\nAll results saved to: {output_dir}/")
    print("  - comparison_results.csv")
    print("  - comparison_plot.png")
    print("  - summary.json")
    print("  - [model_name]/model.pth (for each model)")


if __name__ == "__main__":
    main()

"""
Lemon Disease Classifier - Production-Ready Streamlit App
Handles real-world images with low confidence gracefully.
Shows top predictions when uncertain.
"""

import json
from pathlib import Path

import streamlit as st
import timm
import torch
import torch.nn.functional as F
from PIL import Image
from torchvision import transforms

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

# Treatment/action recommendations for each disease
RECOMMENDATIONS = {
    "Anthracnose": "Apply copper-based fungicide. Remove and destroy infected leaves. Improve air circulation.",
    "Bacterial Blight": "Prune infected branches. Apply copper bactericide. Avoid overhead watering.",
    "Citrus Canker": "Remove infected parts immediately. Apply copper spray. Quarantine affected trees.",
    "Curl Virus": "Control aphid vectors with insecticide. Remove severely infected plants. Use virus-free nursery stock.",
    "Deficiency Leaf": "Test soil nutrients. Apply balanced citrus fertilizer. Check soil pH (ideal: 6.0-7.0).",
    "Dry Leaf": "Increase watering frequency. Check for root damage. Mulch to retain moisture.",
    "Healthy Leaf": "Continue current care routine. Monitor regularly for early signs of disease.",
    "Sooty Mould": "Control honeydew-producing insects (aphids, scale). Wash leaves with water. Apply insecticidal soap.",
    "Spider Mites": "Spray with miticide or neem oil. Increase humidity. Remove severely infested leaves.",
    "Witch's Broom": "Prune affected branches well below symptoms. Sterilize tools. Monitor for phytoplasma vectors.",
}

IMAGE_SIZE = 224


@st.cache_resource
def load_model(model_path: str):
    """Load the trained model (cached)."""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    checkpoint = torch.load(model_path, map_location=device, weights_only=False)
    
    dropout_rate = 0.3
    if "args" in checkpoint and "dropout" in checkpoint.get("args", {}):
        dropout_rate = checkpoint["args"]["dropout"]
    
    model = timm.create_model(
        "efficientnet_b1",
        pretrained=False,
        num_classes=len(CLASS_NAMES),
        drop_rate=dropout_rate,
        drop_path_rate=0.2,
    )
    
    state_dict = checkpoint.get("model_state_dict", checkpoint)
    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()
    
    return model, device


def get_tta_transforms():
    """Test-Time Augmentation transforms for better real-world performance."""
    norm = [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]
    return [
        # Original
        transforms.Compose([
            transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
            transforms.ToTensor(),
            transforms.Normalize(*norm),
        ]),
        # Horizontal flip
        transforms.Compose([
            transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
            transforms.Lambda(lambda img: img.transpose(Image.FLIP_LEFT_RIGHT)),
            transforms.ToTensor(),
            transforms.Normalize(*norm),
        ]),
        # Vertical flip
        transforms.Compose([
            transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
            transforms.Lambda(lambda img: img.transpose(Image.FLIP_TOP_BOTTOM)),
            transforms.ToTensor(),
            transforms.Normalize(*norm),
        ]),
        # Center crop (zoom in)
        transforms.Compose([
            transforms.Resize((int(IMAGE_SIZE * 1.2), int(IMAGE_SIZE * 1.2))),
            transforms.CenterCrop(IMAGE_SIZE),
            transforms.ToTensor(),
            transforms.Normalize(*norm),
        ]),
        # Slight zoom out
        transforms.Compose([
            transforms.Resize((IMAGE_SIZE - 20, IMAGE_SIZE - 20)),
            transforms.Pad(10, fill=0),
            transforms.ToTensor(),
            transforms.Normalize(*norm),
        ]),
        # Rotation 90
        transforms.Compose([
            transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
            transforms.Lambda(lambda img: img.rotate(90, expand=False)),
            transforms.ToTensor(),
            transforms.Normalize(*norm),
        ]),
        # Brightness variation (simulate different lighting)
        transforms.Compose([
            transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
            transforms.ColorJitter(brightness=0.2, contrast=0.2),
            transforms.ToTensor(),
            transforms.Normalize(*norm),
        ]),
    ]


def predict_with_tta(model, image: Image.Image, device: torch.device, num_tta: int = 7):
    """Prediction with Test-Time Augmentation."""
    tta_transforms = get_tta_transforms()[:num_tta]
    
    probs_sum = None
    successful_transforms = 0
    
    with torch.no_grad():
        for transform in tta_transforms:
            try:
                image_tensor = transform(image).unsqueeze(0).to(device)
                outputs = model(image_tensor)
                probs = F.softmax(outputs, dim=1)
                
                if probs_sum is None:
                    probs_sum = probs
                else:
                    probs_sum += probs
                successful_transforms += 1
            except Exception:
                continue
    
    if probs_sum is None or successful_transforms == 0:
        # Fallback to simple prediction
        transform = transforms.Compose([
            transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ])
        image_tensor = transform(image).unsqueeze(0).to(device)
        with torch.no_grad():
            outputs = model(image_tensor)
            probs = F.softmax(outputs, dim=1)[0].cpu().numpy()
        return probs
    
    avg_probs = (probs_sum / successful_transforms)[0].cpu().numpy()
    return avg_probs


def get_confidence_level(confidence: float) -> tuple:
    """Return confidence level description and color."""
    if confidence >= 0.85:
        return "High confidence", "green"
    elif confidence >= 0.65:
        return "Moderate confidence", "orange"
    elif confidence >= 0.45:
        return "Low confidence", "red"
    else:
        return "Very uncertain", "red"


def main():
    st.set_page_config(
        page_title="Lemon Disease Classifier",
        page_icon="🍋",
        layout="centered"
    )
    
    st.title("🍋 Lemon Tree Disease Classifier")
    st.caption("AI-powered detection of lemon leaf diseases")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        
        model_options = []
        if Path("outputs/best_model.pth").exists():
            model_options.append("outputs/best_model.pth")
        if Path("outputs/final_model.pth").exists():
            model_options.append("outputs/final_model.pth")
        
        if not model_options:
            st.error("No model found! Run training first.")
            return
        
        model_path = st.selectbox("Model", model_options, index=0)
        
        confidence_threshold = st.slider(
            "Confidence threshold", 
            min_value=0.5, 
            max_value=0.95, 
            value=0.75,
            help="Below this threshold, show multiple possible diagnoses"
        )
        
        num_tta = st.slider(
            "TTA transforms", 
            min_value=1, 
            max_value=7, 
            value=7,
            help="More transforms = slower but more accurate"
        )
        
        st.divider()
        
        try:
            checkpoint = torch.load(model_path, map_location="cpu", weights_only=False)
            if "test_acc" in checkpoint:
                st.metric("Model Accuracy", f"{checkpoint['test_acc']*100:.1f}%")
        except Exception:
            pass
    
    # Load model
    try:
        model, device = load_model(model_path)
        st.sidebar.success(f"✓ Model loaded ({device})")
    except Exception as e:
        st.error(f"Failed to load model: {e}")
        return
    
    # Main content
    st.markdown("### 📤 Upload Image")
    uploaded_file = st.file_uploader(
        "Upload a lemon leaf image",
        type=["jpg", "jpeg", "png"],
        help="For best results, upload a clear, well-lit photo of a single leaf"
    )
    
    if uploaded_file is not None:
        image = Image.open(uploaded_file).convert("RGB")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.image(image, caption="Uploaded image", use_container_width=True)
        
        with col2:
            with st.spinner("Analyzing image..."):
                probs = predict_with_tta(model, image, device, num_tta)
            
            # Get top 3 predictions
            sorted_indices = probs.argsort()[::-1]
            top1_idx = sorted_indices[0]
            top1_prob = float(probs[top1_idx])
            top1_class = CLASS_NAMES[top1_idx]
            
            confidence_level, conf_color = get_confidence_level(top1_prob)
            
            # Display based on confidence
            if top1_prob >= confidence_threshold:
                # HIGH CONFIDENCE - Show single prediction
                if top1_class == "Healthy Leaf":
                    st.success(f"### ✅ {top1_class}")
                else:
                    st.warning(f"### ⚠️ {top1_class}")
                
                st.metric("Confidence", f"{top1_prob * 100:.1f}%")
                st.caption(f"Category: {LABEL_MAP.get(top1_class, 'Unknown')}")
                
            else:
                # LOW CONFIDENCE - Show multiple possibilities
                st.info("### 🔍 Multiple Possible Diagnoses")
                st.caption("The model is uncertain. Here are the most likely conditions:")
                
                st.markdown("---")
                
                # Show top 3 predictions
                for rank, idx in enumerate(sorted_indices[:3], 1):
                    prob = float(probs[idx])
                    class_name = CLASS_NAMES[idx]
                    category = LABEL_MAP.get(class_name, "Unknown")
                    
                    if prob < 0.05:  # Skip very low probabilities
                        continue
                    
                    if rank == 1:
                        st.markdown(f"**{rank}. {class_name}** — {prob*100:.1f}%")
                    else:
                        st.markdown(f"{rank}. {class_name} — {prob*100:.1f}%")
                    st.caption(f"   {category}")
                
                st.markdown("---")
                st.warning("💡 **Tip:** For better accuracy, try uploading a clearer image with good lighting, showing the leaf up close.")
        
        # Recommendations section
        st.markdown("---")
        st.markdown("### 💊 Recommended Actions")
        
        if top1_prob >= confidence_threshold:
            # Single recommendation
            st.info(RECOMMENDATIONS.get(top1_class, "Consult a plant pathologist for proper diagnosis."))
        else:
            # Multiple recommendations for top 2
            with st.expander(f"If it's **{CLASS_NAMES[sorted_indices[0]]}**:"):
                st.write(RECOMMENDATIONS.get(CLASS_NAMES[sorted_indices[0]], "Consult an expert."))
            
            if float(probs[sorted_indices[1]]) >= 0.15:
                with st.expander(f"If it's **{CLASS_NAMES[sorted_indices[1]]}**:"):
                    st.write(RECOMMENDATIONS.get(CLASS_NAMES[sorted_indices[1]], "Consult an expert."))
        
        # All probabilities (collapsible)
        with st.expander("📊 All class probabilities"):
            for idx in sorted_indices:
                name = CLASS_NAMES[idx]
                prob = float(probs[idx])
                st.progress(prob, text=f"{name}: {prob*100:.1f}%")
    
    else:
        # Instructions when no image uploaded
        st.info("👆 Upload a lemon leaf image to get started")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### ✅ Good images:")
            st.markdown("""
            - Clear, focused photo
            - Single leaf visible
            - Good lighting
            - Leaf fills most of frame
            """)
        
        with col2:
            st.markdown("#### ❌ Avoid:")
            st.markdown("""
            - Blurry photos
            - Multiple leaves overlapping
            - Dark or overexposed
            - Leaf too small in frame
            """)
        
        with st.expander("ℹ️ Detectable Conditions"):
            for class_name in CLASS_NAMES:
                category = LABEL_MAP.get(class_name, "")
                st.write(f"• **{class_name}** — {category}")


if __name__ == "__main__":
    main()
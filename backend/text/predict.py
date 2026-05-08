"""TF-IDF + cosine similarity disease prediction from text descriptions."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def load_text_model(
    folder: str | Path,
) -> tuple[TfidfVectorizer, Any, list[str]]:
    """
    Read all .txt files from *folder*, fit a TF-IDF vectorizer, and return the
    ready-to-query bundle ``(vectorizer, class_matrix, class_names)``.
    """
    folder = Path(folder)
    if not folder.is_dir():
        raise ValueError(f"Text model folder not found: {folder}")

    class_texts: dict[str, str] = {}
    for file_path in sorted(folder.glob("*.txt")):
        class_name = file_path.stem
        class_texts[class_name] = file_path.read_text(encoding="utf-8", errors="ignore")

    if not class_texts:
        raise ValueError(f"No .txt class files found in {folder}")

    class_names = list(class_texts.keys())
    documents = [class_texts[name] for name in class_names]

    vectorizer = TfidfVectorizer(
        lowercase=True,
        stop_words="english",
        sublinear_tf=True,
        norm="l2",
        max_df=0.78,
    )
    class_matrix = vectorizer.fit_transform(documents)

    return vectorizer, class_matrix, class_names


def predict_from_text(
    text: str,
    vectorizer: TfidfVectorizer,
    class_matrix: Any,
    class_names: list[str],
) -> dict[str, Any]:
    """
    Vectorize *text* and return the most similar disease class.

    Returns ``{"predicted_label": str, "confidence": float, "all_scores": dict}``.
    """
    text_vec = vectorizer.transform([text])
    sims = cosine_similarity(text_vec, class_matrix)[0]

    scored = sorted(
        zip(class_names, (float(s) for s in sims)),
        key=lambda pair: pair[1],
        reverse=True,
    )

    best_label, best_score = scored[0]

    return {
        "predicted_label": best_label,
        "confidence": best_score,
        "all_scores": {name: score for name, score in scored},
    }

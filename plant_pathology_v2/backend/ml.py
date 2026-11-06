"""ML part: colour-feature RandomForest classifier for leaf diseases.
Works out-of-the-box with synthetic leaf images; train.py can use a real dataset."""
import os, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import joblib

CLASSES = ["Healthy", "Apple Scab", "Rust", "Powdery Mildew", "Blight"]
MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.joblib")

TREATMENT = {
    "Healthy": "No disease detected. Keep regular watering and monitoring.",
    "Apple Scab": "Remove fallen leaves, prune for airflow, apply a fungicide such as captan or myclobutanil.",
    "Rust": "Remove infected leaves, avoid overhead watering, apply sulfur or copper-based fungicide.",
    "Powdery Mildew": "Improve air circulation, spray neem oil or sulfur fungicide, avoid excess nitrogen.",
    "Blight": "Remove infected plants, rotate crops, apply copper fungicide, avoid wet foliage.",
}

def features(img):
    img = img.convert("RGB").resize((64, 64))
    a = np.asarray(img, dtype=np.float32)
    feats = []
    for c in range(3):
        h, _ = np.histogram(a[:, :, c], bins=16, range=(0, 255), density=True)
        feats += list(h)
    feats += list(a.mean(axis=(0, 1)) / 255) + list(a.std(axis=(0, 1)) / 255)
    return np.array(feats)

def synth_leaf(cls, size=128):
    """Draw a fake leaf with class-specific lesions (demo data only)."""
    g = (random.randint(30, 70), random.randint(110, 160), random.randint(30, 70))
    img = Image.new("RGB", (size, size), (240, 240, 240))
    d = ImageDraw.Draw(img)
    d.ellipse((8, 8, size - 8, size - 8), fill=g)
    spot = {"Apple Scab": ((50, 35, 20), 12, 5), "Rust": ((200, 100, 20), 25, 4),
            "Powdery Mildew": ((235, 235, 225), 7, 14), "Blight": ((140, 110, 30), 6, 18)}
    if cls in spot:
        col, n, r = spot[cls]
        for _ in range(n):
            x, y = random.randint(25, size - 25), random.randint(25, size - 25)
            rr = random.randint(max(2, r // 2), r)
            d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=col)
    img = img.filter(ImageFilter.GaussianBlur(1))
    arr = np.asarray(img, dtype=np.int16) + np.random.randint(-12, 12, (size, size, 3))
    return Image.fromarray(np.clip(arr, 0, 255).astype("uint8"))

def train(dataset_dir=None, n_synth=80):
    from sklearn.ensemble import RandomForestClassifier
    X, y = [], []
    if dataset_dir and os.path.isdir(dataset_dir):  # dataset/<class_name>/*.jpg
        classes = sorted(os.listdir(dataset_dir))
        for c in classes:
            for f in os.listdir(os.path.join(dataset_dir, c)):
                try:
                    X.append(features(Image.open(os.path.join(dataset_dir, c, f)))); y.append(c)
                except Exception:
                    pass
    else:
        for c in CLASSES:
            for _ in range(n_synth):
                X.append(features(synth_leaf(c))); y.append(c)
    clf = RandomForestClassifier(n_estimators=150, random_state=42).fit(np.array(X), y)
    joblib.dump(clf, MODEL_PATH)
    return clf

_model = None
def predict(path):
    global _model
    if _model is None:
        _model = joblib.load(MODEL_PATH) if os.path.exists(MODEL_PATH) else train()
    f = features(Image.open(path)).reshape(1, -1)
    p = _model.predict_proba(f)[0]
    i = int(p.argmax())
    label = _model.classes_[i]
    return label, float(p[i]), TREATMENT.get(label, "Consult an agricultural expert.")

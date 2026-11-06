"""Creates sample leaf images in samples/ for testing the Predict page."""
import os, ml
os.makedirs("samples", exist_ok=True)
for c in ml.CLASSES:
    ml.synth_leaf(c).resize((256, 256)).save(f"samples/{c.replace(' ', '_')}.png")
print("Sample images saved in samples/")

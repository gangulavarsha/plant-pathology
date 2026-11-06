"""python train.py            -> trains on synthetic demo data
   python train.py dataset/  -> trains on real images in dataset/<class>/*.jpg"""
import sys, ml
ml.train(sys.argv[1] if len(sys.argv) > 1 else None)
print("Model saved to", ml.MODEL_PATH)

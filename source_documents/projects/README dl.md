# OrganAI: Deep Learning for Abdominal Organ Classification from CT Scans

**An AI system for accurate identification of anatomical organs in CT imaging to support timely disease diagnosis and healthcare efficiency.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![TensorFlow](https://img.shields.io/badge/TensorFlow-2.15+-orange.svg)](https://www.tensorflow.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Hugging Face](https://img.shields.io/badge/Hugging%20Face-Model%20Hub-blue)](https://huggingface.co/)

---

## 🎯 Problem & Impact

Medical imaging datasets are often inaccessible, heterogeneous, and challenging for consistent benchmarking. **OrganAI** addresses this by building robust deep learning models to classify 11 abdominal organs from CT scans (OrganMNIST / MedMNIST dataset).

**Real-world value**:
- Assists radiologists in organ localisation
- Enables early detection of organ-specific pathologies
- Supports automated triage and reporting systems
- Scalable foundation for multi-organ segmentation or disease classification pipelines

---

## ✨ Key Features

- **Modular, production-ready codebase**
- Multiple architectures: Custom CNNs + Transfer Learning (ResNet50, EfficientNetB0)
- Comprehensive evaluation & comparison
- Gradio web demo for inference
- Model export (SavedModel / ONNX ready)
- Reproducible training with config files
- Detailed documentation and experiment tracking

---

## 📊 Dataset

**OrganMNIST** (from [MedMNIST v2](https://medmnist.com/)) — 128×128 grayscale abdominal CT slices.

- **Classes**: 11 abdominal organs (liver, spleen, kidneys, etc.)
- **Splits**: Train (~13.9k), Validation (~2.45k), Test (~8.8k)
- **License**: Open for research

---

## 🏗️ Project Structure

```bash
organai/
├── data/                    # (gitignored) raw & processed data
├── src/
│   ├── data/                # loading, preprocessing, augmentation
│   ├── models/              # model architectures
│   ├── training/            # trainers, callbacks, metrics
│   ├── inference/           # prediction pipelines
│   ├── utils/               # config, logging, visualisation
│   └── evaluation/          # metrics, reports, confusion matrices
├── notebooks/               # Exploratory notebooks (your original + cleaned)
├── app/                     # Gradio / Streamlit demo
├── configs/                 # YAML configs for experiments
├── models/                  # Saved model weights
├── results/                 # Evaluation reports, plots
├── requirements.txt
├── Dockerfile
├── README.md
└── main.py                  # CLI entrypoint
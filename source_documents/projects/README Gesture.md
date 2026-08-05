# Gesture Phase Segmentation Project: An AI System that Understands Human Gestures
## 🎯 Problem Statement

Human gestures typically consist of five natural phases: **Preparation → Stroke → Hold → Retraction → Rest**. However, real-world datasets captured from motion sensors (like Kinect) are heavily imbalanced: “Rest” and “Stroke” dominate, while “Hold” and “Retraction” are rare.

Standard models tend to ignore these minority phases, leading to broken gesture sequences and poor real-world performance.

In this project, I build a production-ready AI gesture recognition system and demonstrate **how to effectively handle class imbalance**. My aim it to make it more reliable for healthcare and other users 

## Use Cases

Accurate gesture phase segmentation is crucial for:
- Sign Language Recognition
- Assistive Technologies & Accessibility
- Human-Computer Interaction (HCI)
- Healthcare & Rehabilitation Monitoring
- VR/AR Experiences
- Human-Robot Collaboration

---

## 📊 Dataset

- **Name**: Gesture Phase Segmentation Dataset
- **Instances**: ~9,900
- **Features**: 32 (3D coordinates, velocities, and accelerations of hands, wrists, head, and spine)
- **Target**: 5 Gesture Phases (`Preparation`, `Stroke`, `Hold`, `Retraction`, `Rest`)
- **Challenge**: Severe class imbalance

---

## 🛠️ Methodology

### 1. Data Preparation
- Feature scaling for distance-based models
- Class weighting to penalize mistakes on minority classes
- Exploratory analysis of class distribution

### 2. Evaluation Metrics
- Balanced Accuracy
- Macro F1 Score
- Macro Recall
- AUC-ROC (for probability ranking)

### 3. Models Evaluated
- K-Nearest Neighbors (KNN)
- Random Forest
- Gradient Boosting (XGBoost / LightGBM)
- Support Vector Machine (SVM)

---

## 📈 Key Results

- **KNN** → Best balanced performance across all five phases
- **Random Forest** → Strongest overall performer with excellent probability calibration
- **Gradient Boosting** → Highly effective when protecting minority classes is critical

**Conclusion**: The best model depends on the specific application requirements (fairness vs. confidence vs. minority class protection).

---

## 🚀 Real-World Impact

This project demonstrates how proper handling of class imbalance leads to more **reliable and human-centered AI systems**, especially in accessibility, healthcare, and interactive technologies.

---

## 📁 Project Structure

```bash
gesture-phase-segmentation/
├── notebooks/              # Exploratory analysis and model training
├── src/                    # Reusable Python modules
├── models/                 # Saved trained models
├── reports/                # Visualizations and results
├── data/                   # Dataset (sample or description)
├── app.py                  # Streamlit demo (coming soon)
├── requirements.txt
└── README.md

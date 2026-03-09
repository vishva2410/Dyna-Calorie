<div align="center">
  <img src="docs/images/hero_banner.png" alt="DynaCalorie AI Banner" width="800"/>

  # 🚀 DynaCalorie AI
  **The ultimate adaptive metabolic engine & predictive 3D body visualization app.**

  [![Flutter](https://img.shields.io/badge/Flutter-02569B?style=for-the-badge&logo=flutter&logoColor=white)](https://flutter.dev/)
  [![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
  [![Supabase](https://img.shields.io/badge/Supabase-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)](https://supabase.com/)
  [![Three.js](https://img.shields.io/badge/threejs-black?style=for-the-badge&logo=three.js&logoColor=white)](https://threejs.org/)
  [![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org/)

  ---
</div>

DynaCalorie AI isn't just another calorie tracker. It is a **deterministic metabolic engine** that mathematically proves your calorie expenditure based on a 14-day trailing intake vs. weight-change delta. By utilizing the *Katch-McArdle* and *US Navy* formulas, DynaCalorie predicts exactly what your body will look like in the future if you continue your current eating habits.

<br/>

## ✨ Key Features

### 🧠 Adaptive Metabolic Recalibration
Stop guessing your Total Daily Energy Expenditure (TDEE). With DynaCalorie, the engine tracks your daily caloric intake alongside your daily weight. Every 14 days, the recalibration engine analyzes the delta between your *expected* weight change and *actual* weight change, adjusting your TDEE mathematically to track metabolic adaptation over time.

### 🏋️‍♂️ Muscle-Sparing Guardrails
A built in engine warns you immediately if:
- You are losing weight faster than `1%` of your total bodyweight per week.
- You consume less than `1.6g` of protein per kg of bodyweight, ensuring fat is burned rather than muscle tissue.

### 🧬 Predictive 3D Body Visualization (Three.js)
DynaCalorie calculates your precise physiological trajectory over 12 weeks. Using a fully rigged `Three.js` paramatric mesh communicating through a Flutter Webview, you can use a slider to literally *watch* your body morph into its predicted future state if you stick to your diet.

<br/>

## 📱 Visual Previews & Interactive Data

<details>
<summary><b>📈 View Dashboard Analytics</b></summary>
<br/>

The local dashboard tracks data via `fl_chart`. It gives you live insight into your precise weekly caloric deficit runway, protein compliance, and 14-day weight trending lines!

*It also supports an immediate "Refeed Mode" to programmatically frontload calories mathematically without ruining the weekly target!*
</details>

<details>
<summary><b>🔒 Supabase JWT Authentication Matrix</b></summary>
<br/>

Every request to the FastAPI server is fortified using a `Depends(get_current_user)` Bearer Token middleware block. Data cannot be accessed, modified, or requested unless it aligns with the securely decrypted JWT payload issued at login.
</details>

<br/>

## 🛠 Tech Stack

| Component | Technology | Role |
| :--- | :--- | :--- |
| **Frontend Mobile** | `Flutter` | Cross-platform Material UI (`provider` state management) |
| **Backend REST API** | `FastAPI` (Python) | High-performance async microservices for metabolic operations |
| **Authentication/DB** | `Supabase` | PostgreSQL, Row-Level Security, JWT Auth |
| **3D Visualization** | `Three.js` | Embedded static web viewer rendering real-time parametric scaling |

<br/>

## 🚀 Quick Start (Local Development)

### 1. Backend Setup
Ensure you have your proper `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` inside the `backend/.env` file.
```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --port 8000 --reload
```
*Tip: To view the 3D Avatar Demo natively on Desktop, navigate to `http://localhost:8000/static/index.html`.*

### 2. Frontend Setup
Make sure you have Flutter installed on your system PATH!
```bash
cd flutter_app
flutter pub get
flutter run
```

### 3. Automated Tests
The metabolic engine mathematics are secured using robust `pytest` workflows.
```bash
cd backend
PYTHONPATH=. pytest tests/test_dynacalorie.py
```

<br/>

## 📦 Production Android Build Pipeline
We have automated the playbook for prepping the application for the Google Play Store.
Execute the build bounds simply by running:
```bash
cd flutter_app
./build_android.sh
```
This correctly fetches the plugins, generates native XML Splash Screens, populates the respective resolution Launcher Icons, and finally bundles the optimized `.aab` (Android App Bundle).

---
<div align="center">
<i>Built to perfectly bridge mathematical thermodynamics with mobile user experience.</i>
</div>

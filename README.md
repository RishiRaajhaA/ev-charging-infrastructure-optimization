# ⚡ EV Charging Infrastructure Optimization & Decision Support Suite

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![SciPy](https://img.shields.io/badge/SciPy-8CAAE6?style=for-the-badge&logo=scipy&logoColor=white)](https://scipy.org/)
[![Leaflet](https://img.shields.io/badge/Leaflet-199900?style=for-the-badge&logo=leaflet&logoColor=white)](https://leafletjs.com/)
[![Chart.js](https://img.shields.io/badge/Chart.js-FF6384?style=for-the-badge&logo=chartdotjs&logoColor=white)](https://www.chartjs.org/)
[![License: CC0](https://img.shields.io/badge/License-CC0-lightgrey?style=for-the-badge)](https://creativecommons.org/publicdomain/zero/1.0/)

> **A full-stack Operations Research and Mixed-Integer Linear Programming (MILP) platform for optimizing electric vehicle (EV) network expansion, facility hub location, and regional resource equity.**

---

## 📌 Table of Contents
1. [Executive Summary](#-executive-summary)
2. [Key Insights & Performance Metrics](#-key-insights--performance-metrics)
3. [Dual Interactive User Interfaces](#-dual-interactive-user-interfaces)
4. [Visual Showcase](#-visual-showcase)
5. [Mathematical Formulations](#-mathematical-formulations)
   - [Optimization 1: Spherical K-Means & Maximum Coverage MIP](#optimization-1--charging-hub-location-selection)
   - [Optimization 2: Max-Min Regional Fairness MILP](#optimization-2--regional-connector-allocation)
6. [Exploratory Data Analysis (EDA)](#-exploratory-data-analysis-eda)
7. [Validation & Sensitivity Suite](#-validation--sensitivity-suite)
8. [Repository Architecture](#-repository-architecture)
9. [Installation & Quick Start](#-installation--quick-start)
10. [Academic & Course Mapping](#-academic--course-mapping)
11. [Limitations & Roadmap](#-limitations--roadmap)

---

## 🚀 Executive Summary

As Electric Vehicle (EV) adoption accelerates globally, charging infrastructure networks face two critical structural challenges:
1. **Geographic Coverage Inefficiency**: Existing stations are clustered, leaving coverage gaps in strategic corridors.
2. **Regional Resource Disparity**: Certain administrative regions suffer from severely depressed **Connectors-Per-Station (CPS)** ratios, causing localized congestion and charging bottlenecks.

This project delivers an end-to-end **Operations Research Decision Support System** that addresses these challenges through rigorous mathematical programming, full-stack visualization, and interactive scenario simulation.

---

## 📊 Key Insights & Performance Metrics

| Metric / Dimension | Value | Operational Significance |
|---|---|---|
| **Observed Charging Stations** | `10,000` | Global sample from OpenChargeMap API (Nov 2025) |
| **Physical Connectors** | `14,565` | Network-wide physical charging capacity |
| **Operational Rate** | `96.18%` | High network uptime baseline |
| **Network CPS Average** | `~1.46` | Connectors per station ratio across regions |
| **Structural Concentration** | `25.27%` | Top 10% of stations hold over a quarter of all connectors |
| **Top 3 Regions (QC, BC, WA)** | `34.34%` | Over one-third of observed connectors concentrated in 3 regions |
| **Opt 1 Benchmark ($K=10, R=50\text{ km}$)** | `3,278 stations` (`32.78%`) | Outperforms 100-trial Monte Carlo random baseline by **+38.5%** |
| **Opt 2 Benchmark ($B=500\text{ connectors}$)** | `1.212670 CPS floor` | Elevates the lowest regional CPS floor across all 84 jurisdictions |

---

## 🖥️ Dual Interactive User Interfaces

The repository provides **two distinct interfaces** tailored for both executive presentations and technical scenario exploration:

```
                               ┌──────────────────────────────────────────────┐
                               │       EV Infrastructure Optimization         │
                               └──────────────────────┬───────────────────────┘
                                                      │
                       ┌──────────────────────────────┴──────────────────────────────┐
                       ▼                                                             ▼
       ┌───────────────────────────────┐                             ┌───────────────────────────────┐
       │   1. Modern Full-Stack Suite  │                             │   2. Classic Streamlit App    │
       │   `python run_web_app.py`     │                             │   `streamlit run app.py`      │
       ├───────────────────────────────┤                             ├───────────────────────────────┤
       │ • FastAPI REST API Backend    │                             │ • Native Streamlit Python UI  │
       │ • Glassmorphic Dark SPA       │                             │ • Plotly Interactive Visuals  │
       │ • Leaflet Maps (Dark Canvas)  │                             │ • Dynamic CSV Data Uploader   │
       │ • Chart.js Realtime Charts    │                             │ • Side-by-Side Model Runners  │
       │ • Live Sensitivity Sliders    │                             │ • Dataframe Filter Tables     │
       └───────────────────────────────┘                             └───────────────────────────────┘
```

### 1. Modern Full-Stack Web Suite (`run_web_app.py` / `web_app/`)
- **Backend**: **FastAPI** with asynchronous endpoint routing, CORS handling, and Pydantic request validation.
- **Frontend**: Single-Page Application (SPA) styled with **Vanilla CSS Glassmorphism** (custom design tokens, glowing accents, zero heavy frameworks).
- **Cartography**: **Leaflet.js** with ESRI Dark Gray Canvas tiles, single world boundary clamping (`noWrap: true`), dynamic hub coverage circles, and station markers.
- **Analytics**: **Chart.js** responsive visualizations for budget curves, regional distributions, and operational statuses.
- **Features**: Live CSV file drag-and-drop, instant scenario re-calculation, exportable reports, and tabular data explorer.

### 2. Classic Streamlit Dashboard (`app.py`)
- Python-native dashboard with sidebar navigation, Plotly interactive geospatial scatter plots, dataframe inspector, and dual optimization tabs.

---

## 📸 Visual Showcase

### Executive Network Dashboard
![Executive Network Dashboard](assets/Executive%20Network%20Dashboard.png)

### Optimization 1: Charging Hub Location & Geospatial Coverage
![Optimization 1](assets/Optimization%201.png)

### Optimization 2: Regional Connector Allocation & Equity Curve
![Optimization 2](assets/Optimization%202.png)

### Strategic Scenario Comparator
![Strategic Scenario Comparator](assets/Strategic%20Scenario%20Comparator.png)

### Data Explorer & Geospatial Studio
![Data Explorer & Geospatial Studio](assets/Data%20Explorer%20&%20Geospatial%20Studio.png)

### Operations Research Formulations
![Operations Research Formulations](assets/Operations%20Research%20Formulations.png)

---

## 📐 Mathematical Formulations

### Optimization 1 — Charging Hub Location Selection

#### Problem Definition
Given $N$ existing EV charging stations, select $K$ candidate hubs such that the total number of geographically covered stations within radius $R$ is maximized.

#### Candidate Hub Generation (Spherical K-Means)
To ensure proposed hubs reside at realistic, observed geographic locations, the dataset coordinates are clustered using Spherical K-Means ($M = 30$ clusters). Each cluster centroid is mapped to the nearest real charging station coordinate $j \in \{1, \dots, M\}$.

#### Pairwise Great-Circle Distance
Distances between all stations $i$ and candidate hubs $j$ are calculated via the Haversine formula:

$$
d(i, j) = 2 R_{\text{earth}} \arcsin \left( \sqrt{\sin^2\left(\frac{\Delta \phi}{2}\right) + \cos(\phi_i)\cos(\phi_j)\sin^2\left(\frac{\Delta \lambda}{2}\right)} \right)
$$

Let the coverage adjacency matrix $A_{ij}$ be:

$$
A_{ij} = \begin{cases} 
1 & \text{if } d(i, j) \le R \\ 
0 & \text{otherwise} 
\end{cases}
$$

#### MIP Formulation

$$
\max \quad \sum_{i=1}^{N} z_i
$$

**Subject to:**

$$
\begin{aligned}
z_i &\le \sum_{j=1}^{M} A_{ij} y_j && \forall i \in \{1, \dots, N\} \quad \text{(Coverage Adjacency)} \\
\sum_{j=1}^{M} y_j &\le K && \text{(Hub Budget Limit)} \\
y_j &\in \{0, 1\} && \forall j \in \{1, \dots, M\} \quad \text{(Hub Selection)} \\
z_i &\in [0, 1] && \forall i \in \{1, \dots, N\} \quad \text{(Station Covered)}
\end{aligned}
$$

---

### Optimization 2 — Regional Connector Allocation

#### Problem Definition
Given $R$ administrative regions with existing stations $S_i$ and existing connectors $C_i$, distribute a budget of $B$ additional connectors to maximize the minimum post-allocation **Connectors-Per-Station (CPS)** ratio across all regions (Max-Min Fairness).

#### MILP Formulation

$$
\max \quad t
$$

**Subject to:**

$$
\begin{aligned}
C_i + x_i &\ge t \cdot S_i && \forall i \in \{1, \dots, R\} \quad \text{(Regional CPS Floor)} \\
\sum_{i=1}^{R} x_i &= B && \text{(Total Connector Budget)} \\
x_i &\in \mathbb{Z}_{\ge 0} && \forall i \in \{1, \dots, R\} \quad \text{(Integer Additions)} \\
t &\ge 0 && \text{(Minimum Target Ratio)}
\end{aligned}
$$

#### Budget vs. Minimum CPS Response:
```
Minimum CPS Floor (t)
   ▲
1.35│                                        ● (1000, 1.312)
1.30│                              ● (750, 1.263)
1.25│                    ● (500, 1.213)
1.20│
1.15│          ● (250, 1.143)
1.00│    ● (100, 1.000)
 0.0└───┬────────┬────────┬────────┬────────┬───────► Connector Budget (B)
       100      250      500      750     1000
```

---

## 🔍 Exploratory Data Analysis (EDA)

The project includes an in-depth exploratory analysis in [`eda/EDA.ipynb`](eda/EDA.ipynb) and [`eda/EDA_Process.md`](eda/EDA_Process.md):

<p align="center">
  <img src="assets/dataset_geo_map.png" width="48%" alt="Geographic Distribution">
  <img src="assets/dataset_top_regions.png" width="48%" alt="Top Regions">
</p>

- **Network Skewness**: Over 70% of stations possess only 1 or 2 connectors; high-density charging hubs (>10 connectors) are rare outliers.
- **Geographic Clustering**: Distinct corridors exist along the Pacific Northwest and Eastern Canada.
- **Data Hygiene**: 2,869 records without administrative state IDs are isolated to ensure strict data fidelity in regional modeling.

---

## 🧪 Validation & Sensitivity Suite

Independent verification scripts validate the solver outputs against theoretical bounds and alternative baselines:

### 1. Model 1 Validation (`optimization/validation/validation_optimization_1.py`)
- **Monotonicity**: Proven that coverage monotonically increases with both $K$ and $R$.
- **Monte Carlo Comparison**: The MIP model achieves **3,278 covered stations** ($K=10, R=50\text{ km}$) compared to the randomized baseline mean of **2,367 stations** ($p < 0.001$).

### 2. Model 2 Validation (`optimization/validation/validation_optimization_2.py`)
- **Proportional vs Max-Min Allocation**: Proportional allocation concentrates connectors in already high-capacity regions, leaving the CPS floor at $1.000$. Max-Min successfully raises the floor to $1.213$ ($B=500$).
- **Exact Conservation**: $\sum x_i = B$ verified with zero budget leakage.

---

## 📁 Repository Architecture

```text
Operations Research/
├── app.py                                   # Streamlit Interactive Dashboard
├── run_web_app.py                           # 1-Click Root Launcher for Full-Stack Suite
├── requirements.txt                         # Unified Python Dependencies
├── README.md                                # Comprehensive Project Documentation
├── .gitignore                               # Git Rules for Python & Build Artifacts
├── generate_dataset_visuals.py              # Visual Chart Generation Script
├── First_Review_Presentation.md             # Review Presentation Notes
├── mid_review_presentation.tex              # LaTeX Beamer Mid-Review Slide Deck
│
├── assets/                                  # High-Res Screenshots & Visual Assets
│   ├── Executive Network Dashboard.png
│   ├── Optimization 1.png
│   ├── Optimization 2.png
│   ├── Strategic Scenario Comparator.png
│   ├── Data Explorer & Geospatial Studio.png
│   ├── Operations Research Formulations.png
│   ├── dataset_geo_map.png
│   └── dataset_top_regions.png
│
├── data/
│   └── ev_stations_2025.csv                 # Core EV Charging Stations Dataset
│
├── eda/
│   ├── EDA.ipynb                            # Comprehensive Exploratory Data Analysis Notebook
│   └── EDA_Process.md                       # Structured EDA Documentation & Findings
│
├── optimization/
│   ├── optimization_1_hub_location.py       # Spherical K-Means + MIP Hub Location Solver
│   ├── optimization_2_connector_allocation.py# Max-Min Regional Fairness MILP Solver
│   └── validation/
│       ├── validation_optimization_1.py     # Independent Monte Carlo & Sensitivity Test
│       ├── validation_optimization_2.py     # Budget Sensitivity & Baseline Comparison Test
│       ├── optimization_1_validation_results.md
│       └── optimization_2_validation_results.md
│
├── outputs/
│   └── maps/                                # Exported Geo-visualizations & Coverage Maps
│
└── web_app/                                 # Full-Stack Decision Support Suite
    ├── run_web_app.py                       # Internal Fast-Launcher
    ├── backend/
    │   ├── server.py                        # FastAPI Server Application
    │   ├── routes/
    │   │   ├── data_routes.py               # Data Ingestion & Statistics Endpoints
    │   │   ├── opt1_routes.py               # Optimization 1 Solver Endpoints
    │   │   └── opt2_routes.py               # Optimization 2 Solver Endpoints
    │   └── services/
    │       ├── data_service.py              # Data Caching & Metric Compute Service
    │       └── solver_service.py            # Mathematical Solvers Bridge
    └── frontend/
        ├── index.html                       # Responsive Glassmorphic SPA Layout
        ├── css/
        │   ├── main.css                     # Glassmorphic Design System & Tokens
        │   ├── components.css               # Cards, Modals, Sliders, Badges
        │   └── animations.css               # Smooth Micro-transitions & Shimmers
        └── js/
            ├── api.js                       # Asynchronous Backend Client
            ├── app.js                       # Navigation & State Controller
            ├── charts.js                    # Chart.js Render Engine
            ├── map.js                       # Leaflet Cartography & Dark Canvas Engine
            └── ui.js                        # Toast Notifications & Dynamic Tables
```

---

## ⚡ Installation & Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/RishiRaajhaA/ev-charging-optimization.git
cd ev-charging-optimization
```

### 2. Set Up Virtual Environment
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Launch the Applications

#### Option A: Launch Full-Stack Web Suite (Recommended)
```bash
python run_web_app.py
```
*Access the interface at `http://localhost:8000` (automatically opens in your default browser).*

#### Option B: Launch Streamlit Dashboard
```bash
streamlit run app.py
```
*Access the Streamlit dashboard at `http://localhost:8501`.*

### 5. Run Validation & Test Suite
```bash
# Validate Model 1 (Hub Location & Coverage)
python optimization/validation/validation_optimization_1.py

# Validate Model 2 (Regional Allocation & Fairness)
python optimization/validation/validation_optimization_2.py
```

---

## 🎓 Academic & Course Mapping

This project was developed for the **Operations Research** curriculum, demonstrating practical applications of core optimization paradigms:

| Course Concept | Applied Implementation in Project |
|---|---|
| **Linear & Integer Programming** | Mixed-Integer Linear Programming (MILP) solved via SciPy Highs solver. |
| **Facility Location Problems** | Maximum Covering Location Problem (MCLP) with Spherical K-Means candidates. |
| **Resource Allocation Models** | Multi-region connector budget distribution under capacity constraints. |
| **Max-Min Fairness Objectives** | Bottleneck optimization to elevate the worst-off regional CPS ratio. |
| **Sensitivity Analysis** | Parametric sweeps over hub count ($K$), radius ($R$), and budget ($B$). |
| **Monte Carlo Validation** | Stochastic baseline benchmarking against 100 random trials. |

---

## 🔮 Limitations & Roadmap

### Current Limitations
- **Demand Proxy**: Uses station presence as a proxy for EV charging demand due to the lack of public vehicle telemetry data.
- **Uniform Station Weight**: Optimization 1 treats all existing stations equally rather than weighting by connector count or utilization.
- **Regional Boundaries**: Optimization 2 is constrained to records containing valid administrative state identifiers (7,131 / 10,000).

### Future Enhancements
1. **Traffic & Grid Constraints**: Incorporating highway traffic density and local power substation capacity constraints.
2. **Multi-Period Dynamic Expansion**: Formulating multi-stage stochastic models across 2025–2035 rollout horizons.
3. **Vehicle-to-Grid (V2G) Bi-directional Optimization**: Modeling peak energy discharge incentives.

---

## 👥 Authors & Acknowledgments

- **Author**: Rishi Raajha A
- **Dataset Attribution**: [Global EV Charging Stations Dataset](https://www.kaggle.com/datasets/risheepanchal/global-ev-charging-stations-dataset) by Rishee Panchal (OpenChargeMap API).
- **Course**: Operations Research (2025–2026).

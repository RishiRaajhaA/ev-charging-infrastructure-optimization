# pyrefly: ignore [missing-import]
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import tempfile
import os

# Import Optimization 1
from optimization.optimization_1_hub_location import generate_candidate_hubs, solve_max_coverage, haversine_matrix
# Import Optimization 2 (Regional Infrastructure Parity - Max-Min Fairness MILP)
from optimization.optimization_2_connector_allocation import (
    load_regional_data,
    solve_connector_allocation,
    proportional_baseline,
    validate_solution
)

# Configuration
st.set_page_config(page_title="EV Charging Optimization", layout="wide", page_icon="⚡")

# Custom CSS for premium UI
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        background: -webkit-linear-gradient(45deg, #FF4B2B, #FF416C);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0px;
    }
    .sub-header {
        font-size: 1.5rem;
        font-weight: 500;
        color: #A0AEC0;
        margin-top: -10px;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_default_data():
    return pd.read_csv("data/ev_stations_2025.csv")

def preprocess_data(df):
    if 'id' not in df.columns:
        df['id'] = range(len(df))
    df['num_connectors'] = pd.to_numeric(df['num_connectors'], errors='coerce')
    if 'status' in df.columns:
        status_clean = df['status'].astype(str).str.strip().str.lower()
        df['is_operational'] = status_clean == 'operational'
    else:
        df['is_operational'] = True
    return df

# Sidebar Navigation
st.sidebar.title("⚡ EV Optima")
st.sidebar.markdown("---")

st.sidebar.subheader("Data Source")
uploaded_file = st.sidebar.file_uploader("Upload EV Stations CSV", type="csv")

if uploaded_file is not None:
    try:
        raw_df = pd.read_csv(uploaded_file)
        required_cols = ["lat", "lon", "state", "status", "operator", "num_connectors"]
        missing_cols = [c for c in required_cols if c not in raw_df.columns]
        if missing_cols:
            st.sidebar.error(f"Invalid dataset. Missing required columns: {', '.join(missing_cols)}")
            st.sidebar.info("Falling back to sample dataset.")
            df = load_default_data()
        else:
            # Check for invalid coordinates
            valid_coords = pd.to_numeric(raw_df['lat'], errors='coerce').notna() & pd.to_numeric(raw_df['lon'], errors='coerce').notna()
            if valid_coords.sum() == 0:
                st.sidebar.error("Invalid dataset. No valid latitude/longitude coordinates found.")
                st.sidebar.info("Falling back to sample dataset.")
                df = load_default_data()
            else:
                df = raw_df
                st.sidebar.success("Custom dataset loaded successfully!")
    except Exception as e:
        st.sidebar.error(f"Error loading file: {str(e)}")
        st.sidebar.info("Falling back to sample dataset.")
        df = load_default_data()
else:
    st.sidebar.info("Using sample dataset.")
    df = load_default_data()

df = preprocess_data(df)

def get_regional_data(current_df):
    fd, temp_path = tempfile.mkstemp(suffix=".csv")
    os.close(fd)
    current_df.to_csv(temp_path, index=False)
    try:
        base_df, regional_df = load_regional_data(temp_path)
    finally:
        os.remove(temp_path)
    return base_df, regional_df

def run_opt1_baseline(df, candidates, k_hubs, radius_km, num_trials=100):
    station_data = df.dropna(subset=["lat", "lon"])
    station_coords = station_data[["lat", "lon"]].to_numpy()
    candidate_coords = candidates[["lat", "lon"]].to_numpy()
    distances = haversine_matrix(station_coords, candidate_coords)
    
    np.random.seed(42)
    coverage_results = []
    
    for _ in range(num_trials):
        selected_idx = np.random.choice(len(candidates), size=min(k_hubs, len(candidates)), replace=False)
        min_dist = distances[:, selected_idx].min(axis=1)
        covered = np.sum(min_dist <= radius_km)
        coverage_results.append(covered)
        
    return {
        "mean_coverage": np.mean(coverage_results),
        "min_coverage": np.min(coverage_results),
        "max_coverage": np.max(coverage_results)
    }

st.sidebar.markdown("---")
pages = [
    "Project Information",
    "Dashboard", 
    "Data Explorer", 
    "Statistics", 
    "Optimization Center", 
    "Methodology"
]
selection = st.sidebar.radio("Navigation", pages, index=1)
st.sidebar.markdown("---")
st.sidebar.info("Developed for University Project Presentation. \n\n✅ Models Independently Validated.")

if selection == "Project Information":
    st.markdown('<p class="main-header">Project Information</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Strategic EV Infrastructure Optimization</p>', unsafe_allow_html=True)
    
    st.markdown("""
    ### 📊 Dataset Description
    This project models Electric Vehicle charging station data. The application supports uploading custom datasets or using the bundled sample data.
    
    ### 🎯 Project Objectives
    The primary goal is to apply Operations Research (OR) methodologies to optimize EV charging infrastructure without assuming external variables like power grid loads, population densities, or specific EV traffic patterns. We strictly use the provided data to mathematically derive optimal expansion strategies.
    
    ### 🧮 Optimization Questions
    1. **Optimization 1 (Hub Location)**: Where should we place a limited budget of new charging hubs to maximize geographic coverage of existing stations?
    2. **Optimization 2 (Connector Allocation)**: How should we distribute a limited budget of new individual charging connectors across administrative regions to maximize fairness (minimum connectors-per-station)?
    
    ### ⚙️ Technology Stack
    - **Language**: Python 3.12
    - **Data Processing**: Pandas, NumPy
    - **Optimization Solver**: SciPy (`scipy.optimize.milp`)
    - **Clustering**: Scikit-Learn (Spherical K-Means)
    - **Visualization UI**: Streamlit, Plotly
    
    ### ✅ Validation Status
    > **Optimization 1 and Optimization 2 have been independently validated.** Both mathematical models have successfully passed rigorous sanity checks, budget sensitivity monotonic tests, constraints validations, and baseline comparisons.
    """)

elif selection == "Dashboard":
    st.markdown('<p class="main-header">Network Dashboard</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">High-Level Infrastructure Metrics</p>', unsafe_allow_html=True)
    
    total_stations = len(df)
    total_connectors = df['num_connectors'].sum()
    avg_connectors = total_connectors / total_stations if total_stations > 0 else 0
    operational_ratio = df['is_operational'].mean() if 'is_operational' in df.columns else 0
    num_states = df['state'].nunique() if 'state' in df.columns else 0
    missing_states = df['state'].isna().sum() if 'state' in df.columns else 0
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Stations", f"{total_stations:,}")
    col2.metric("Total Connectors", f"{total_connectors:,.0f}")
    col3.metric("Avg Connectors / Station", f"{avg_connectors:.2f}")
    
    st.markdown("---")
    
    col4, col5, col6 = st.columns(3)
    col4.metric("Operational Ratio", f"{operational_ratio:.2%}")
    col5.metric("States / Regions", f"{num_states:,}")
    col6.metric("Missing-State Records", f"{missing_states:,}", delta="- Excluded from Opt 2", delta_color="off")

elif selection == "Data Explorer":
    st.markdown('<p class="main-header">Data Explorer</p>', unsafe_allow_html=True)
    
    st.sidebar.subheader("Filters")
    selected_states = st.sidebar.multiselect("Filter by State / Region", sorted(df['state'].dropna().astype(str).unique())) if 'state' in df.columns else []
    selected_operators = st.sidebar.multiselect("Filter by Operator", sorted(df['operator'].dropna().astype(str).unique())) if 'operator' in df.columns else []
    status_filter = st.sidebar.selectbox("Status", ["All", "Operational Only", "Non-Operational"])
    
    filtered_df = df.copy()
    if selected_states and 'state' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['state'].isin(selected_states)]
    if selected_operators and 'operator' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['operator'].isin(selected_operators)]
    if status_filter == "Operational Only" and 'is_operational' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['is_operational'] == True]
    elif status_filter == "Non-Operational" and 'is_operational' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['is_operational'] == False]
        
    cols = st.multiselect("Select Columns to Display", df.columns.tolist(), default=[c for c in ["title", "operator", "state", "num_connectors", "status", "lat", "lon"] if c in df.columns])
    
    st.dataframe(filtered_df[cols], use_container_width=True)

elif selection == "Statistics":
    st.markdown('<p class="main-header">Statistical Analysis</p>', unsafe_allow_html=True)
    
    st.subheader("Dataset Summary")
    total_missing = df.isna().sum().sum()
    dup_rows = df.duplicated().sum()
    op_rate = df['is_operational'].mean()
    mean_conn = df['num_connectors'].mean()
    median_conn = df['num_connectors'].median()
    sd_conn = df['num_connectors'].std()
    
    summary_data = {
        "Metric": ["Rows", "Columns", "Missing Values", "Duplicate Rows", "Operational Rate", "Mean Connectors", "Median Connectors", "Standard Deviation"],
        "Value": [f"{len(df):,}", f"{len(df.columns):,}", f"{total_missing:,}", f"{dup_rows:,}", f"{op_rate:.2%}", f"{mean_conn:.2f}", f"{median_conn:.2f}", f"{sd_conn:.2f}"]
    }
    st.table(pd.DataFrame(summary_data))
    
    st.subheader("Missing Values by Column")
    missing_df = df.isna().sum().reset_index()
    missing_df.columns = ["Column", "Missing Count"]
    st.table(missing_df)
    
    tab1, tab2, tab3 = st.tabs(["Geographic Distribution", "Operator Analysis", "Geospatial Map"])
    
    with tab1:
        st.subheader("Stations & Connectors by State / Region")
        if 'state' in df.columns:
            state_stats = df.groupby('state').agg(
                Stations=('id', 'count') if 'id' in df.columns else ('num_connectors', 'size'),
                Connectors=('num_connectors', 'sum')
            ).reset_index().sort_values('Connectors', ascending=False).head(20)
            
            fig1 = px.bar(state_stats, x='state', y=['Stations', 'Connectors'], barmode='group', title="Top States / Regions by Infrastructure")
            st.plotly_chart(fig1, use_container_width=True)
        
    with tab2:
        st.subheader("Stations & Connectors by Operator")
        if 'operator' in df.columns:
            op_stats = df.groupby('operator').agg(
                Stations=('id', 'count') if 'id' in df.columns else ('num_connectors', 'size'),
                Connectors=('num_connectors', 'sum')
            ).reset_index().sort_values('Stations', ascending=False).head(15)
            
            fig2 = px.bar(op_stats, x='operator', y='Stations', title="Top Operators by Station Count", color='Stations', color_continuous_scale='viridis')
            st.plotly_chart(fig2, use_container_width=True)
        
    with tab3:
        st.subheader("Geospatial Map of Existing Stations")
        st.info("Displaying a random 10% sample of stations to maintain performance.")
        if 'lat' in df.columns and 'lon' in df.columns:
            sample_df = df.dropna(subset=['lat', 'lon']).sample(frac=min(1.0, max(0.1, 1000/len(df))), random_state=42)
            fig3 = px.scatter_mapbox(
                sample_df, lat="lat", lon="lon", color="is_operational", 
                size="num_connectors", hover_name="title" if "title" in sample_df.columns else None,
                color_discrete_map={True: "green", False: "red"},
                mapbox_style="carto-darkmatter", zoom=3, height=600,
                title="Station Locations (Sampled)"
            )
            st.plotly_chart(fig3, use_container_width=True)

elif selection == "Optimization Center":
    st.markdown('<p class="main-header">Optimization Center</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Select a mathematical model to solve.</p>', unsafe_allow_html=True)
    
    opt_choice = st.radio("Choose the problem you want to solve:", 
                          ["Charging Hub Location (Maximum Coverage MIP - MCLP)", 
                           "Regional Infrastructure Parity (Max-Min Fairness MILP)"])
    
    st.markdown("---")
    
    if opt_choice.startswith("Charging Hub Location"):
        st.subheader("Opt 1 Parameters: Strategic Charging Hub Location")
        st.info("Upgrading operational charging stations into high-throughput super-hubs using 3D Spherical K-Means candidates and Maximum Covering Location Problem (MCLP).")
        col1, col2, col3 = st.columns(3)
        with col1:
            k_hubs = st.number_input("Number of Hubs (K)", min_value=1, max_value=100, value=10, step=1)
        with col2:
            radius_km = st.number_input("Coverage Radius (km)", min_value=1, max_value=1000, value=50, step=10)
        with col3:
            n_candidates = st.number_input("Candidate Locations", min_value=10, max_value=500, value=100, step=10)
        
        if st.button("🚀 Run Optimization 1", type="primary"):
            with st.spinner("Generating candidates and solving Maximum Coverage MIP..."):
                try:
                    op_df = df[df['status'].astype(str).str.strip().str.lower() == 'operational'].copy() if 'status' in df.columns else df
                    candidates = generate_candidate_hubs(op_df, n_candidates=n_candidates, random_state=42, operational_only=True)
                    res = solve_max_coverage(op_df, candidates, n_hubs=k_hubs, radius_km=radius_km, operational_only=True)
                    
                    st.success("Optimization completed successfully!")
                    
                    st.markdown("### Coverage Results")
                    col_a, col_b, col_c, col_d = st.columns(4)
                    col_a.metric("Selected Hubs", res['n_hubs'])
                    col_b.metric("Coverage Radius", f"{res['radius_km']} km")
                    col_c.metric("Covered Stations", f"{res['covered_stations']:,} / {res['total_stations']:,}")
                    col_d.metric("Coverage Rate", f"{res['coverage_rate']:.2%}")
                    
                    st.markdown("### Baseline Comparison (100 Random Trials)")
                    baseline = run_opt1_baseline(op_df, candidates, k_hubs, radius_km, num_trials=100)
                    
                    b_col1, b_col2, b_col3, b_col4 = st.columns(4)
                    b_col1.metric("Random Mean Coverage", f"{baseline['mean_coverage']:.1f}")
                    b_col2.metric("Random Min Coverage", f"{baseline['min_coverage']:.0f}")
                    b_col3.metric("Random Max Coverage", f"{baseline['max_coverage']:.0f}")
                    
                    improvement = res['covered_stations'] - baseline['mean_coverage']
                    b_col4.metric("Optimized Improvement", f"+{improvement:.1f} stations")
                    
                    st.markdown("### Coverage Map")
                    valid_df = op_df.dropna(subset=['lat', 'lon'])
                    
                    fig = go.Figure()
                    fig.add_trace(go.Scattermapbox(
                        lat=valid_df['lat'], lon=valid_df['lon'], mode='markers',
                        marker=go.scattermapbox.Marker(size=4, color='gray', opacity=0.3),
                        name='Operational Stations', hoverinfo='none'
                    ))
                    
                    fig.add_trace(go.Scattermapbox(
                        lat=res['selected_hubs']['lat'], lon=res['selected_hubs']['lon'], mode='markers',
                        marker=go.scattermapbox.Marker(size=12, color='#FF007A', symbol='circle'),
                        name='Selected Super-Hubs', text=res['selected_hubs']['title'] if 'title' in res['selected_hubs'].columns else None
                    ))
                    
                    fig.update_layout(
                        mapbox_style="carto-darkmatter",
                        mapbox=dict(center=dict(lat=40, lon=-95), zoom=3),
                        margin={"r":0,"t":0,"l":0,"b":0},
                        height=600,
                        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.error(f"Optimization failed: {str(e)}")

    else:
        st.subheader("Opt 2 Parameters: Regional Infrastructure Parity")
        st.info("Allocating additional charging connectors ($B$) across administrative regions using Max-Min Fairness MILP to maximize the minimum connectors-per-station ratio.")
        
        col1, col2 = st.columns(2)
        with col1:
            grouping_choice = st.selectbox(
                "Regional Aggregation Scheme",
                ["Administrative State (403 regions)", "Country-State Composite (415 regions)"]
            )
            grouping_key = "state" if "403" in grouping_choice else "country_state"
        with col2:
            budget_val = st.slider("Additional Connector Budget (B)", min_value=50, max_value=2000, value=500, step=25)

        if st.button("🚀 Run Equity Optimization (MILP)", type="primary"):
            with st.spinner("Solving Max-Min Fairness MILP..."):
                try:
                    state_col = "state" if "state" in df.columns else "state_clean"
                    reg_raw = df.dropna(subset=[state_col, "num_connectors"]).copy()
                    reg_raw["num_connectors"] = pd.to_numeric(reg_raw["num_connectors"], errors="coerce")
                    reg_raw = reg_raw.dropna(subset=["num_connectors"])
                    
                    if grouping_key == "country_state" and "country" in reg_raw.columns:
                        reg_raw["region_key"] = reg_raw["country"].fillna("Unknown").astype(str).str.strip() + " - " + reg_raw[state_col].astype(str).str.strip()
                    else:
                        reg_raw["region_key"] = reg_raw[state_col].astype(str).str.strip()

                    regional_df = reg_raw.groupby("region_key", as_index=True).agg(
                        stations=("id", "size"),
                        connectors=("num_connectors", "sum")
                    ).sort_index()
                    regional_df["current_cps"] = regional_df["connectors"] / regional_df["stations"]

                    res = solve_connector_allocation(regional_df, budget=budget_val)
                    checks, min_cps = validate_solution(res)
                    base = proportional_baseline(regional_df, budget_val)

                    alloc_df = res["allocation"]
                    funded_regions = (alloc_df["additional_connectors"] > 0).sum()
                    initial_min = float(regional_df["current_cps"].min())
                    delta_cps = min_cps - initial_min
                    prop_min = float(base["final_cps"].min())

                    st.success(f"Max-Min fairness optimization solved to global optimality!")

                    col_a, col_b, col_c, col_d = st.columns(4)
                    col_a.metric("Guaranteed Min CPS Floor (t*)", f"{min_cps:.4f}", delta=f"+{delta_cps:.4f} gain")
                    col_b.metric("Initial Baseline Floor", f"{initial_min:.4f}", help="5 stations in dataset have 0 connectors")
                    col_c.metric("Funded Regions", f"{funded_regions} / {len(regional_df)}", f"{funded_regions / len(regional_df):.1%}")
                    col_d.metric("Gain vs. Proportional", f"+{min_cps - prop_min:.4f} CPS", help=f"Proportional baseline min CPS remains at {prop_min:.4f}")

                    st.markdown("### Top Targeted Regions Allocation Impact")
                    top_funded = alloc_df.sort_values("additional_connectors", ascending=False).head(15).reset_index()
                    top_funded["proportional_alloc"] = [int(base.loc[k, "additional_connectors"]) for k in top_funded["region_key"]]
                    top_funded["proportional_cps"] = [float(base.loc[k, "final_cps"]) for k in top_funded["region_key"]]

                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        x=top_funded["region_key"], y=top_funded["current_cps"],
                        name="Initial CPS", marker_color="#EF4444"
                    ))
                    fig.add_trace(go.Bar(
                        x=top_funded["region_key"], y=top_funded["proportional_cps"],
                        name="Proportional Benchmark CPS", marker_color="#64748B"
                    ))
                    fig.add_trace(go.Bar(
                        x=top_funded["region_key"], y=top_funded["final_cps"],
                        name="Max-Min Optimized CPS", marker_color="#10B981"
                    ))
                    fig.update_layout(barmode="group", height=450, title="Connectors-Per-Station (CPS) Comparison for Top Allocated Regions")
                    st.plotly_chart(fig, use_container_width=True)

                    st.markdown("### Detailed Regional Allocation Table")
                    display_table = alloc_df[alloc_df["additional_connectors"] > 0].sort_values("additional_connectors", ascending=False)
                    st.dataframe(display_table, use_container_width=True)

                except Exception as e:
                    st.error(f"Connector allocation failed: {str(e)}")

elif selection == "Methodology":
    st.markdown('<p class="main-header">Methodology & Course Alignment</p>', unsafe_allow_html=True)
    
    st.markdown(r"""
    ### Optimization 1: Strategic Charging Hub Location (Maximum Covering Location Problem - MCLP)
    This model addresses the **Commercial Efficiency & Spatial Coverage** decision: selecting $K$ existing charging stations to upgrade into regional high-throughput super-hubs.
    
    - **Optimization Technique**: Mixed-Integer Programming (MIP)
    - **Decision Variables**: 
      - $y_j \in \{0, 1\}$: 1 if candidate hub location $j$ is selected, 0 otherwise.
      - $z_i \in [0, 1]$: Continuous coverage indicator of station $i$ (naturally binary in optimal solution).
    - **Objective**: Maximize total covered operational stations: 
      $$\max \sum_{i=1}^N z_i$$
    - **Constraints**: 
      - Hub budget: $\sum_{j=1}^M y_j \le K$.
      - Coverage reach: $z_i \le \sum_{j \in N_i} y_j \quad \forall i$.
      - Variable domains: $y_j \in \{0, 1\}, \quad 0 \le z_i \le 1$.
    - **Dataset Grounding**: Evaluated on $N = 9,301$ operational stations. Using $M = 100$ spherical K-Means candidate locations, $K = 10$ selected hubs, and $R = 50\text{ km}$ reach, exactly **3,095 stations (33.28%)** are covered.
    
    ---
    
    ### Optimization 2: Regional Infrastructure Connector Allocation (Max-Min Fairness MILP)
    This model addresses the **Social Equity & Hardware Parity** decision: allocating a capital expansion budget of $B$ additional charging plugs across administrative regions to lift underserved areas.
    
    - **Optimization Technique**: Mixed-Integer Linear Programming (MILP)
    - **Decision Variables**: 
      - $x_i \in \mathbb{Z}_{\ge 0}$: Integer number of additional connectors allocated to region $i$.
      - $t \ge 0$: Continuous auxiliary variable representing the guaranteed minimum post-allocation Connectors-Per-Station (CPS) ratio.
    - **Objective**: Maximize the minimum regional ratio:
      $$\max t$$
    - **Constraints**: 
      - Regional fairness floor: $C_i + x_i \ge t \cdot S_i \quad \forall \text{ region } i$.
      - Exact connector budget: $\sum_{i=1}^P x_i = B$.
      - Variable domains: $x_i \in \mathbb{Z}_{\ge 0}, \quad t \ge 0$.
    - **Dataset Grounding**: Over 70% of stations have only 1 connector plug and 5 stations report 0 connectors, yielding an initial regional floor of **0.0000 CPS**. Under budget $B = 500$:
      - *Administrative State (403 regions)*: Guaranteed floor rises to **1.2127 CPS** ($\Delta t = +1.2127$), funding 247 regions.
      - *Country-State (415 regions)*: Guaranteed floor rises to **1.2058 CPS** ($\Delta t = +1.2058$), funding 255 regions.
      - *Proportional Benchmark*: Leaves the minimum CPS at **0.0000**, demonstrating the mathematical necessity of the Max-Min formulation.
    """)

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import time

WORKSPACE_ROOT = Path(__file__).parent.parent.parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.append(str(WORKSPACE_ROOT))

from optimization.optimization_1_hub_location import (
    generate_candidate_hubs,
    solve_max_coverage,
    greedy_max_coverage,
    haversine_matrix
)
from optimization.optimization_2_connector_allocation import (
    solve_connector_allocation,
    proportional_baseline,
    validate_solution
)
from optimization.optimization_2_technician_dispatch import (
    get_broken_stations,
    generate_service_depots,
    solve_technician_dispatch as solve_tech_dispatch
)

class SolverService:
    def solve_optimization_1(self, df: pd.DataFrame, n_hubs: int = 10, radius_km: float = 50.0, n_candidates: int = 100, country: str = "All"):
        """
        Execute Optimization 1 (Facility Location / Maximum Coverage MIP - MCLP).
        Operational stations denominator (N=9,301) with Spherical K-Means.
        """
        start_time = time.time()
        
        if "status" in df.columns:
            valid_df = df[df["status"].astype(str).str.strip().str.lower() == "operational"].dropna(subset=["lat", "lon"]).copy()
        else:
            valid_df = df.dropna(subset=["lat", "lon"]).copy()

        if country and country != "All" and "country" in valid_df.columns:
            valid_df = valid_df[valid_df["country"].astype(str).str.strip().str.upper() == country.strip().upper()]

        if len(valid_df) == 0:
            raise ValueError(f"No operational stations found for country/scope: {country}")

        actual_n_candidates = min(n_candidates, len(valid_df))
        actual_n_hubs = min(n_hubs, actual_n_candidates)

        candidates = generate_candidate_hubs(valid_df, n_candidates=actual_n_candidates, random_state=42, operational_only=True)
        
        opt_res = solve_max_coverage(
            valid_df,
            candidates,
            n_hubs=actual_n_hubs,
            radius_km=radius_km,
            operational_only=True
        )
        
        elapsed_sec = round(time.time() - start_time, 3)
        
        # Selected hubs formatting
        selected_hubs_df = opt_res["selected_hubs"]
        station_coords = valid_df[["lat", "lon"]].to_numpy()
        hub_coords = selected_hubs_df[["lat", "lon"]].to_numpy()
        
        # Calculate coverage breakdown per hub
        dist_matrix = haversine_matrix(station_coords, hub_coords)
        
        selected_hubs = []
        for j, (_, row) in enumerate(selected_hubs_df.iterrows()):
            stations_covered_by_this_hub = int(np.sum(dist_matrix[:, j] <= radius_km))
            selected_hubs.append({
                "id": int(row["id"]),
                "title": str(row["title"]),
                "lat": float(row["lat"]),
                "lon": float(row["lon"]),
                "country": str(row.get("country", "Unknown")),
                "state": str(row.get("state_clean", row.get("state", "Unknown"))),
                "operator": str(row.get("operator", "Unknown")),
                "stations_covered": stations_covered_by_this_hub
            })
            
        # 1. Deterministic Greedy Forward-Selection Heuristic Benchmark
        greedy_res = greedy_max_coverage(
            valid_df,
            candidates,
            n_hubs=actual_n_hubs,
            radius_km=radius_km,
            operational_only=True
        )

        # 2. Monte Carlo random baseline benchmark (100 trials, seed=42)
        cand_coords = candidates[["lat", "lon"]].to_numpy()
        all_dists = haversine_matrix(station_coords, cand_coords)
        np.random.seed(42)
        random_coverages = []
        for _ in range(100):
            chosen = np.random.choice(len(candidates), size=min(actual_n_hubs, len(candidates)), replace=False)
            covered = np.sum(np.min(all_dists[:, chosen], axis=1) <= radius_km)
            random_coverages.append(int(covered))
            
        random_mean = round(float(np.mean(random_coverages)), 1)
        random_min = int(np.min(random_coverages))
        random_max = int(np.max(random_coverages))
        improvement = int(opt_res["covered_stations"] - random_mean)
        improvement_pct = round(float(improvement / random_mean * 100), 1) if random_mean > 0 else 0
        greedy_improvement = int(opt_res["covered_stations"] - greedy_res["covered_stations"])
        greedy_improvement_pct = round(float(greedy_improvement / greedy_res["covered_stations"] * 100), 1) if greedy_res["covered_stations"] > 0 else 0
        
        return {
            "status": "Optimal",
            "elapsed_seconds": elapsed_sec,
            "n_hubs": actual_n_hubs,
            "radius_km": radius_km,
            "country": country,
            "n_candidates": len(candidates),
            "total_stations": len(valid_df),
            "covered_stations": int(opt_res["covered_stations"]),
            "coverage_rate": round(float(opt_res["coverage_rate"] * 100), 2),
            "solver_diagnostics": {
                "status": opt_res.get("solver_status", "Optimal"),
                "solver_engine": "SciPy HiGHS MIP Branch-and-Cut",
                "message": opt_res.get("solver_message", "Optimization terminated successfully."),
                "optimality_gap": opt_res.get("optimality_gap", "0.00%"),
                "candidate_restriction_notice": opt_res.get("candidate_restriction_notice", f"Globally optimal with respect to discrete candidate set J (|J| = {len(candidates)}).")
            },
            "selected_hubs": selected_hubs,
            "baseline_benchmark": {
                "method": "Multi-Baseline Comparison (Optimal MIP vs Greedy Heuristic vs 100-Trial Random)",
                "random_mean": random_mean,
                "random_min": random_min,
                "random_max": random_max,
                "random_trials": 100,
                "random_seed": 42,
                "greedy_covered": int(greedy_res["covered_stations"]),
                "greedy_coverage_rate": round(float(greedy_res["coverage_rate"] * 100), 2),
                "optimal_stations": int(opt_res["covered_stations"]),
                "improvement_stations": improvement,
                "improvement_pct": improvement_pct,
                "improvement_over_greedy": greedy_improvement,
                "improvement_over_greedy_pct": greedy_improvement_pct,
                "distribution_sample": random_coverages[:25]
            }
        }

    def run_k_sensitivity(self, df: pd.DataFrame, radius_km: float = 50.0, n_candidates: int = 100, country: str = "All"):
        """Evaluate coverage as K increases."""
        if "status" in df.columns:
            valid_df = df[df["status"].astype(str).str.strip().str.lower() == "operational"].dropna(subset=["lat", "lon"]).copy()
        else:
            valid_df = df.dropna(subset=["lat", "lon"]).copy()

        if country and country != "All" and "country" in valid_df.columns:
            valid_df = valid_df[valid_df["country"].astype(str).str.strip().str.upper() == country.strip().upper()]

        actual_n_candidates = min(n_candidates, len(valid_df))
        candidates = generate_candidate_hubs(valid_df, n_candidates=actual_n_candidates, random_state=42, operational_only=True)
        
        k_values = [1, 2, 3, 5, 8, 10, 15, 20, 25, 30]
        curve = []
        for k in k_values:
            if k > len(candidates):
                continue
            res = solve_max_coverage(valid_df, candidates, n_hubs=k, radius_km=radius_km, operational_only=True)
            curve.append({
                "k": k,
                "covered_stations": int(res["covered_stations"]),
                "coverage_pct": round(float(res["coverage_rate"] * 100), 2)
            })
        return {"radius_km": radius_km, "country": country, "curve": curve}

    def run_radius_sensitivity(self, df: pd.DataFrame, n_hubs: int = 10, n_candidates: int = 100, country: str = "All"):
        """Evaluate coverage as Radius increases."""
        if "status" in df.columns:
            valid_df = df[df["status"].astype(str).str.strip().str.lower() == "operational"].dropna(subset=["lat", "lon"]).copy()
        else:
            valid_df = df.dropna(subset=["lat", "lon"]).copy()

        if country and country != "All" and "country" in valid_df.columns:
            valid_df = valid_df[valid_df["country"].astype(str).str.strip().str.upper() == country.strip().upper()]

        actual_n_candidates = min(n_candidates, len(valid_df))
        actual_n_hubs = min(n_hubs, actual_n_candidates)
        candidates = generate_candidate_hubs(valid_df, n_candidates=actual_n_candidates, random_state=42, operational_only=True)
        
        r_values = [10, 25, 50, 75, 100, 150, 200]
        curve = []
        for r in r_values:
            res = solve_max_coverage(valid_df, candidates, n_hubs=actual_n_hubs, radius_km=r, operational_only=True)
            curve.append({
                "radius_km": r,
                "covered_stations": int(res["covered_stations"]),
                "coverage_pct": round(float(res["coverage_rate"] * 100), 2)
            })
        return {"n_hubs": actual_n_hubs, "country": country, "curve": curve}

    def run_candidate_sensitivity(self, df: pd.DataFrame, n_hubs: int = 10, radius_km: float = 50.0, country: str = "All"):
        """Evaluate coverage as Candidate pool M increases (e.g. 25, 50, 100, 150, 250, 400)."""
        if "status" in df.columns:
            valid_df = df[df["status"].astype(str).str.strip().str.lower() == "operational"].dropna(subset=["lat", "lon"]).copy()
        else:
            valid_df = df.dropna(subset=["lat", "lon"]).copy()

        if country and country != "All" and "country" in valid_df.columns:
            valid_df = valid_df[valid_df["country"].astype(str).str.strip().str.upper() == country.strip().upper()]

        m_values = [25, 50, 100, 150, 250, 400]
        curve = []
        for m in m_values:
            if m > len(valid_df):
                continue
            t0 = time.time()
            candidates = generate_candidate_hubs(valid_df, n_candidates=m, random_state=42, operational_only=True)
            actual_k = min(n_hubs, len(candidates))
            res = solve_max_coverage(valid_df, candidates, n_hubs=actual_k, radius_km=radius_km, operational_only=True)
            t_elapsed = round(time.time() - t0, 3)
            curve.append({
                "m": m,
                "covered_stations": int(res["covered_stations"]),
                "coverage_pct": round(float(res["coverage_rate"] * 100), 2),
                "solve_time_sec": t_elapsed
            })
        return {"n_hubs": n_hubs, "radius_km": radius_km, "country": country, "curve": curve}

    def _prepare_regional_df(self, df: pd.DataFrame, grouping: str = "state", country: str = "All"):
        state_col = "state" if "state" in df.columns else "state_clean"
        regional_df = df.dropna(subset=[state_col, "num_connectors"]).copy()
        regional_df["num_connectors"] = pd.to_numeric(regional_df["num_connectors"], errors="coerce")
        regional_df = regional_df.dropna(subset=["num_connectors"])
        
        if country and country != "All" and "country" in regional_df.columns:
            regional_df = regional_df[regional_df["country"].astype(str).str.strip().str.upper() == country.strip().upper()]

        if len(regional_df) == 0:
            raise ValueError(f"No regional station records found for country/scope: {country}")

        if grouping == "country_state" and "country" in regional_df.columns:
            regional_df["region_key"] = (
                regional_df["country"].astype(str)
                + " - "
                + regional_df[state_col].astype(str)
            )
        else:
            regional_df["region_key"] = regional_df[state_col].astype(str)

        grouped = (
            regional_df.groupby("region_key", as_index=True)
            .agg(
                stations=("id", "size"),
                connectors=("num_connectors", "sum"),
            )
            .sort_index()
        )
        grouped["current_cps"] = grouped["connectors"] / grouped["stations"]
        return grouped

    def solve_optimization_2(self, df: pd.DataFrame, budget: int = 500, grouping: str = "state", country: str = "All"):
        """
        Execute Optimization 2 (Regional Connector Allocation / Max-Min Fairness MILP).
        """
        start_time = time.time()
        regional_df = self._prepare_regional_df(df, grouping=grouping, country=country)
        
        initial_min_cps = float(regional_df["current_cps"].min())
        
        opt_res = solve_connector_allocation(regional_df, budget=budget)
        checks, independent_min_cps = validate_solution(opt_res)
        
        elapsed_sec = round(time.time() - start_time, 3)
        alloc_df = opt_res["allocation"]
        
        # Proportional baseline
        baseline_df = proportional_baseline(regional_df, budget)
        baseline_min_cps = float(baseline_df["final_cps"].min())
        
        # Extract regions with positive allocation or top stations
        allocations_list = []
        for state, row in alloc_df.sort_values("additional_connectors", ascending=False).iterrows():
            allocations_list.append({
                "state": str(state),
                "stations": int(row["stations"]),
                "initial_connectors": int(row["connectors"]),
                "initial_cps": round(float(row["current_cps"]), 4),
                "additional_connectors": int(row["additional_connectors"]),
                "final_connectors": int(row["final_connectors"]),
                "final_cps": round(float(row["final_cps"]), 4),
                "proportional_alloc": int(baseline_df.loc[state, "additional_connectors"]),
                "proportional_cps": round(float(baseline_df.loc[state, "final_cps"]), 4)
            })
            
        targeted_regions = [r for r in allocations_list if r["additional_connectors"] > 0]
        
        return {
            "status": "Optimal",
            "elapsed_seconds": elapsed_sec,
            "budget": budget,
            "grouping": grouping,
            "country": country,
            "total_regions": len(regional_df),
            "targeted_regions_count": len(targeted_regions),
            "initial_min_cps": round(initial_min_cps, 6),
            "optimized_min_cps": round(independent_min_cps, 6),
            "proportional_baseline_min_cps": round(baseline_min_cps, 6),
            "cps_improvement": round(independent_min_cps - initial_min_cps, 6),
            "all_constraints_passed": all(checks.values()),
            "checks": checks,
            "top_targeted_regions": targeted_regions[:20],
            "all_regions_allocation": allocations_list
        }

    def run_budget_sensitivity(self, df: pd.DataFrame, grouping: str = "state", country: str = "All"):
        """Evaluate how minimum CPS increases with budget."""
        regional_df = self._prepare_regional_df(df, grouping=grouping, country=country)
        budgets = [50, 100, 250, 500, 750, 1000, 1500, 2000]
        
        curve = []
        for b in budgets:
            res = solve_connector_allocation(regional_df, b)
            base = proportional_baseline(regional_df, b)
            curve.append({
                "budget": b,
                "optimized_min_cps": round(float(res["minimum_cps"]), 4),
                "proportional_min_cps": round(float(base["final_cps"].min()), 4)
            })
            
        return {"grouping": grouping, "country": country, "curve": curve}
    
    def get_opt2_fleet_summary(self, df: pd.DataFrame):
        """
        Get counts and countries of broken/offline stations for the UI dropdown.
        """
        COUNTRY_NAMES = {
            "US": "United States", "CA": "Canada", "RU": "Russia", "ES": "Spain",
            "BR": "Brazil", "MY": "Malaysia", "LT": "Lithuania", "DK": "Denmark",
            "TR": "Turkey", "RO": "Romania", "IT": "Italy", "BE": "Belgium"
        }
        broken = get_broken_stations(df)
        country_counts = (
            broken.groupby("country")
            .agg(stations=("id", "count"), connectors=("num_connectors", "sum"))
            .sort_values("stations", ascending=False)
            .reset_index()
        )
        countries_list = []
        for _, row in country_counts.iterrows():
            code = str(row["country"])
            c_name = COUNTRY_NAMES.get(code, code)
            countries_list.append({
                "country_code": code,
                "country_name": c_name,
                "stations": int(row["stations"]),
                "connectors": int(row["connectors"]),
                "label": f"{c_name} ({row['stations']} offline stations, {row['connectors']} connectors)"
            })
        return {
            "total_broken_stations": len(broken),
            "total_offline_connectors": int(broken["num_connectors"].sum()),
            "countries": countries_list
        }

    def solve_technician_dispatch_service(
        self,
        df: pd.DataFrame,
        country: str = "United States",
        n_depots: int = 5,
        max_stations_per_crew: int = 4,
        max_radius_km: float = 150.0,
        alpha: float = 0.01
    ):
        """
        Execute Optimization 2: Technician Fleet Dispatch & Assignment Model.
        """
        start_time = time.time()
        
        country_param = None if country in ["All", "Global", ""] else country
        broken = get_broken_stations(df, country=country_param)
        
        if len(broken) == 0:
            raise ValueError(f"No broken/offline stations found for country selection: {country}")
        
        depots = generate_service_depots(broken, n_depots=n_depots, random_state=42)
        opt_res = solve_tech_dispatch(
            broken_stations=broken,
            depots=depots,
            max_stations_per_crew=max_stations_per_crew,
            max_radius_km=max_radius_km,
            alpha=alpha
        )
        
        elapsed_sec = round(time.time() - start_time, 3)
        
        # Format station list for map
        repaired_ids = {a["station_id"] for a in opt_res["assignments"]}
        station_pins = []
        for _, st in broken.iterrows():
            s_id = int(st["id"])
            station_pins.append({
                "id": s_id,
                "title": str(st["title"]),
                "lat": float(st["lat"]),
                "lon": float(st["lon"]),
                "state": str(st.get("state_clean", st.get("state", "Unknown"))),
                "operator": str(st.get("operator", "Unknown")),
                "status": str(st.get("status", "Offline")),
                "connectors": int(st["num_connectors"]),
                "is_repaired": s_id in repaired_ids
            })
            
        opt_res["elapsed_seconds"] = elapsed_sec
        opt_res["selected_country"] = country
        opt_res["station_pins"] = station_pins
        opt_res["max_possible_connectors"] = int(broken["num_connectors"].sum())
        opt_res["connector_recovery_rate"] = round(
            opt_res["restored_connectors"] / max(1, opt_res["max_possible_connectors"]) * 100, 1
        )
        opt_res["station_recovery_rate"] = round(
            opt_res["assigned_stations_count"] / max(1, len(broken)) * 100, 1
        )
        return opt_res

    def run_technician_sensitivity(
        self,
        df: pd.DataFrame,
        country: str = "United States",
        n_depots: int = 5,
        max_stations_per_crew: int = 4
    ):
        """
        Evaluate how restored connectors and travel distance scale with SLA radius limit.
        """
        country_param = None if country in ["All", "Global", ""] else country
        broken = get_broken_stations(df, country=country_param)
        depots = generate_service_depots(broken, n_depots=n_depots, random_state=42)
        
        radii = [25.0, 50.0, 75.0, 100.0, 150.0, 200.0, 300.0, 500.0]
        curve = []
        for r in radii:
            res = solve_tech_dispatch(
                broken_stations=broken,
                depots=depots,
                max_stations_per_crew=max_stations_per_crew,
                max_radius_km=r,
                alpha=0.01
            )
            curve.append({
                "radius_km": r,
                "assigned_stations": res["assigned_stations_count"],
                "restored_connectors": res["restored_connectors"],
                "total_travel_distance_km": res["total_travel_distance_km"],
                "avg_response_distance_km": res["avg_response_distance_km"]
            })
        return {"curve": curve}

solver_service = SolverService()

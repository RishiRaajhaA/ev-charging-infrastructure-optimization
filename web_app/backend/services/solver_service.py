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
    haversine_matrix
)
from optimization.optimization_2_connector_allocation import (
    solve_connector_allocation,
    proportional_baseline,
    validate_solution
)

class SolverService:
    def solve_optimization_1(self, df: pd.DataFrame, n_hubs: int = 10, radius_km: float = 50.0, n_candidates: int = 100):
        """
        Execute Optimization 1 (Facility Location / Maximum Coverage MIP).
        """
        start_time = time.time()
        
        valid_df = df.dropna(subset=["lat", "lon"]).copy()
        candidates = generate_candidate_hubs(valid_df, n_candidates=n_candidates, random_state=42)
        
        opt_res = solve_max_coverage(
            valid_df,
            candidates,
            n_hubs=n_hubs,
            radius_km=radius_km
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
                "state": str(row.get("state_clean", row.get("state", "Unknown"))),
                "operator": str(row.get("operator", "Unknown")),
                "stations_covered": stations_covered_by_this_hub
            })
            
        # Monte Carlo random baseline benchmark (100 trials)
        cand_coords = candidates[["lat", "lon"]].to_numpy()
        all_dists = haversine_matrix(station_coords, cand_coords)
        np.random.seed(42)
        random_coverages = []
        for _ in range(100):
            chosen = np.random.choice(len(candidates), size=min(n_hubs, len(candidates)), replace=False)
            covered = np.sum(np.min(all_dists[:, chosen], axis=1) <= radius_km)
            random_coverages.append(int(covered))
            
        random_mean = round(float(np.mean(random_coverages)), 1)
        random_min = int(np.min(random_coverages))
        random_max = int(np.max(random_coverages))
        improvement = int(opt_res["covered_stations"] - random_mean)
        improvement_pct = round(float(improvement / random_mean * 100), 1) if random_mean > 0 else 0
        
        # Find which stations are covered for map visualization
        min_hub_dist = np.min(dist_matrix, axis=1) if len(selected_hubs) > 0 else np.full(len(valid_df), np.inf)
        is_covered_mask = min_hub_dist <= radius_km
        
        return {
            "status": "Optimal",
            "elapsed_seconds": elapsed_sec,
            "n_hubs": n_hubs,
            "radius_km": radius_km,
            "n_candidates": len(candidates),
            "total_stations": len(valid_df),
            "covered_stations": int(opt_res["covered_stations"]),
            "coverage_rate": round(float(opt_res["coverage_rate"] * 100), 2),
            "selected_hubs": selected_hubs,
            "baseline_benchmark": {
                "method": "100-Trial Monte Carlo Random Baseline",
                "random_mean": random_mean,
                "random_min": random_min,
                "random_max": random_max,
                "optimal_stations": int(opt_res["covered_stations"]),
                "improvement_stations": improvement,
                "improvement_pct": improvement_pct,
                "distribution_sample": random_coverages[:25]
            }
        }

    def run_k_sensitivity(self, df: pd.DataFrame, radius_km: float = 50.0, n_candidates: int = 100):
        """Evaluate coverage as K increases."""
        valid_df = df.dropna(subset=["lat", "lon"]).copy()
        candidates = generate_candidate_hubs(valid_df, n_candidates=n_candidates, random_state=42)
        
        k_values = [1, 2, 3, 5, 8, 10, 15, 20, 25, 30]
        curve = []
        for k in k_values:
            if k > len(candidates):
                continue
            res = solve_max_coverage(valid_df, candidates, n_hubs=k, radius_km=radius_km)
            curve.append({
                "k": k,
                "covered_stations": int(res["covered_stations"]),
                "coverage_pct": round(float(res["coverage_rate"] * 100), 2)
            })
        return {"radius_km": radius_km, "curve": curve}

    def run_radius_sensitivity(self, df: pd.DataFrame, n_hubs: int = 10, n_candidates: int = 100):
        """Evaluate coverage as Radius increases."""
        valid_df = df.dropna(subset=["lat", "lon"]).copy()
        candidates = generate_candidate_hubs(valid_df, n_candidates=n_candidates, random_state=42)
        
        r_values = [10, 25, 50, 75, 100, 150, 200]
        curve = []
        for r in r_values:
            res = solve_max_coverage(valid_df, candidates, n_hubs=n_hubs, radius_km=r)
            curve.append({
                "radius_km": r,
                "covered_stations": int(res["covered_stations"]),
                "coverage_pct": round(float(res["coverage_rate"] * 100), 2)
            })
        return {"n_hubs": n_hubs, "curve": curve}

    def _prepare_regional_df(self, df: pd.DataFrame):
        regional_df = df.dropna(subset=["state_clean", "num_connectors"]).copy()
        regional_df = (
            regional_df.groupby("state_clean", as_index=True)
            .agg(
                stations=("id", "size"),
                connectors=("num_connectors", "sum"),
            )
            .sort_index()
        )
        regional_df["current_cps"] = regional_df["connectors"] / regional_df["stations"]
        return regional_df

    def solve_optimization_2(self, df: pd.DataFrame, budget: int = 500):
        """
        Execute Optimization 2 (Regional Connector Allocation / Max-Min Fairness MILP).
        """
        start_time = time.time()
        regional_df = self._prepare_regional_df(df)
        
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
            "total_regions": len(regional_df),
            "targeted_regions_count": len(targeted_regions),
            "initial_min_cps": round(initial_min_cps, 6),
            "optimized_min_cps": round(independent_min_cps, 6),
            "proportional_baseline_min_cps": round(baseline_min_cps, 6),
            "cps_improvement": round(independent_min_cps - initial_min_cps, 6),
            "all_constraints_passed": all(checks.values()),
            "checks": checks,
            "top_targeted_regions": targeted_regions[:15],
            "all_regions_allocation": allocations_list
        }

    def run_budget_sensitivity(self, df: pd.DataFrame):
        """Evaluate how minimum CPS increases with budget."""
        regional_df = self._prepare_regional_df(df)
        budgets = [50, 100, 200, 350, 500, 750, 1000, 1500, 2000]
        
        curve = []
        for b in budgets:
            res = solve_connector_allocation(regional_df, b)
            base = proportional_baseline(regional_df, b)
            curve.append({
                "budget": b,
                "optimized_min_cps": round(float(res["minimum_cps"]), 4),
                "proportional_min_cps": round(float(base["final_cps"].min()), 4)
            })
            
        return {"curve": curve}

solver_service = SolverService()

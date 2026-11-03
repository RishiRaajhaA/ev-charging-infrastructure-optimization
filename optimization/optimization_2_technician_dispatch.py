"""
Optimization 2: Technician Repair & Maintenance Dispatch
---------------------------------------------------------
Operations Research Topic: Assignment Models with Different Types of Constraints

Goal:
    Given N broken/offline EV charging stations (status in 'Temporarily Unavailable'
    or 'Not Operational') and M regional technician repair service depots, assign
    broken stations to technician crews to maximize the total number of restored
    connectors while minimizing total dispatch travel distance.

Real-World Context:
    Charger reliability and plug downtime is the #1 pain point in public EV infrastructure.
    In our dataset, 312 stations (484 physical connectors) are offline.
    A charging network operator dispatches regional field technician crews to repair
    these sites within contractual Service Level Agreement (SLA) response radiuses.

Mathematical Formulation:
    Decision Variables:
        x_ij in {0, 1} : 1 if technician depot i is assigned to repair station j, 0 otherwise.
        z_j in {0, 1}  : 1 if broken station j is successfully repaired, 0 otherwise.

    Objective:
        max sum_j (C_j * z_j) - alpha * sum_i sum_j (d_ij * x_ij)
        where:
            C_j   = number of connectors restored at station j (from `num_connectors`)
            d_ij  = Haversine great-circle distance between depot i and station j (km)
            alpha = travel distance penalty parameter (e.g. 0.001)

    Constraints:
        1. Single Assignment:
           sum_i x_ij = z_j <= 1           for all stations j
        2. Crew Shift Workload Capacity:
           sum_j x_ij <= K_i               for all depots i
        3. SLA Travel Distance Limit:
           d_ij * x_ij <= D_max            for all (i, j)
        4. Binary Integrality:
           x_ij in {0, 1}, z_j in {0, 1}
"""

from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import milp, LinearConstraint, Bounds
from scipy.sparse import lil_matrix, csr_matrix
from sklearn.cluster import KMeans


EARTH_RADIUS_KM = 6371.0
DATA_PATH = Path(__file__).parent.parent / "data" / "ev_stations_2025.csv"


def haversine_matrix(points_a, points_b):
    """
    Calculate great-circle distances in kilometers between two sets of GPS coordinates.
    points_a: (M, 2) array of [lat, lon]
    points_b: (N, 2) array of [lat, lon]
    returns: (M, N) matrix of distances in km
    """
    a = np.radians(np.asarray(points_a, dtype=float))
    b = np.radians(np.asarray(points_b, dtype=float))

    lat1 = a[:, 0][:, None]
    lon1 = a[:, 1][:, None]
    lat2 = b[:, 0][None, :]
    lon2 = b[:, 1][None, :]

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    h = (
        np.sin(dlat / 2.0) ** 2
        + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2
    )
    h = np.clip(h, 0.0, 1.0)
    return 2.0 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(h))


def get_broken_stations(df, country=None, state=None, operator=None):
    """
    Extract offline/broken charging stations from the dataset.
    Identifies records with status in 'Temporarily Unavailable' or 'Not Operational'.
    """
    valid = df.dropna(subset=["lat", "lon"]).copy()
    valid["status_clean"] = valid["status"].astype(str).str.strip().str.lower()
    
    offline_mask = valid["status_clean"].isin([
        "temporarily unavailable",
        "not operational",
        "temporarily unavailable / under repair"
    ])
    broken = valid[offline_mask].copy().reset_index(drop=True)

    COUNTRY_MAP = {
        "united states": "US", "usa": "US", "us": "US",
        "canada": "CA", "ca": "CA",
        "spain": "ES", "es": "ES",
        "russia": "RU", "ru": "RU",
        "malaysia": "MY", "my": "MY",
        "united kingdom": "GB", "uk": "GB", "gb": "GB",
        "germany": "DE", "de": "DE",
        "france": "FR", "fr": "FR",
        "netherlands": "NL", "nl": "NL"
    }

    if country and str(country).strip().upper() not in ["ALL", "GLOBAL", ""]:
        c_str = str(country).strip()
        c_code = COUNTRY_MAP.get(c_str.lower(), c_str.upper())
        broken = broken[
            (broken["country"].astype(str).str.upper() == c_code) |
            (broken["country"].astype(str).str.lower() == c_str.lower())
        ].copy().reset_index(drop=True)

    if state and str(state).strip().upper() not in ["ALL", ""]:
        broken = broken[broken["state"].astype(str).str.lower() == str(state).strip().lower()].copy().reset_index(drop=True)

    if operator and str(operator).strip().upper() not in ["ALL", ""]:
        broken = broken[broken["operator"].astype(str).str.lower() == str(operator).strip().lower()].copy().reset_index(drop=True)

    broken["num_connectors"] = pd.to_numeric(broken["num_connectors"], errors="coerce").fillna(1).astype(int)
    # Ensure minimum 1 connector
    broken["num_connectors"] = broken["num_connectors"].clip(lower=1)
    
    return broken


def generate_service_depots(broken_stations, n_depots=5, random_state=42):
    """
    Generate realistic regional technician service depots located at
    central geographic anchors of the broken stations cluster.
    """
    if len(broken_stations) == 0:
        return pd.DataFrame(columns=["depot_id", "title", "lat", "lon", "capacity"])

    coords = broken_stations[["lat", "lon"]].to_numpy()
    n_clusters = min(n_depots, len(broken_stations))

    kmeans = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10)
    kmeans.fit(coords)
    centers = kmeans.cluster_centers_

    depots = []
    for idx, (c_lat, c_lon) in enumerate(centers):
        # Find closest town or station title to label the depot realistically
        dists = haversine_matrix([[c_lat, c_lon]], coords)[0]
        closest_idx = np.argmin(dists)
        closest_station = broken_stations.iloc[closest_idx]
        town_label = closest_station.get("town", "")
        if pd.isna(town_label) or not str(town_label).strip():
            town_label = closest_station.get("state", f"Region {idx+1}")

        depots.append({
            "depot_id": idx + 1,
            "title": f"Technician Depot {idx + 1} ({town_label})",
            "lat": float(c_lat),
            "lon": float(c_lon),
            "capacity": 4
        })

    return pd.DataFrame(depots)


def solve_technician_dispatch(
    broken_stations: pd.DataFrame,
    depots: pd.DataFrame,
    max_stations_per_crew: int = 4,
    max_radius_km: float = 150.0,
    alpha: float = 0.001,
    time_limit: int = 60
):
    """
    Solve the Binary Integer Programming Assignment Model with Capacity & SLA constraints.
    """
    M = len(depots)
    N = len(broken_stations)

    if M == 0 or N == 0:
        return {
            "success": False,
            "message": "Empty depots or broken stations set.",
            "assigned_stations_count": 0,
            "unassigned_stations_count": N,
            "restored_connectors": 0,
            "total_travel_distance_km": 0.0,
            "assignments": [],
            "routes": [],
            "depot_summary": []
        }

    depot_coords = depots[["lat", "lon"]].to_numpy()
    station_coords = broken_stations[["lat", "lon"]].to_numpy()
    dists = haversine_matrix(depot_coords, station_coords)  # shape (M, N)

    C = broken_stations["num_connectors"].to_numpy(dtype=float)

    # Variables:
    # First M*N vars: x_ij for depot i and station j
    # Next N vars: z_j for each station j (1 if repaired, 0 otherwise)
    n_vars = M * N + N

    # Objective: maximize sum(C_j * z_j) - alpha * sum(d_ij * x_ij)
    # SciPy minimizes: c_obj
    c_obj = np.zeros(n_vars)
    c_obj[:M * N] = alpha * dists.flatten()
    c_obj[M * N:] = -C

    # Constraints:
    # 1. Linking: sum_i x_ij - z_j = 0  (N constraints)
    # 2. Crew Capacity: sum_j x_ij <= K_i  (M constraints)
    n_constraints = N + M
    A = lil_matrix((n_constraints, n_vars), dtype=float)
    lower = np.zeros(n_constraints)
    upper = np.zeros(n_constraints)

    # Constraint 1: sum_i x_ij - z_j = 0
    for j in range(N):
        for i in range(M):
            A[j, i * N + j] = 1.0
        A[j, M * N + j] = -1.0
        lower[j] = 0.0
        upper[j] = 0.0

    # Constraint 2: sum_j x_ij <= K_i
    for i in range(M):
        row = N + i
        for j in range(N):
            A[row, i * N + j] = 1.0
        lower[row] = 0.0
        upper[row] = float(max_stations_per_crew)

    # SLA Distance Bound: if d_ij > max_radius_km, force x_ij = 0
    var_upper = np.ones(n_vars)
    for i in range(M):
        for j in range(N):
            if dists[i, j] > max_radius_km:
                var_upper[i * N + j] = 0.0

    bounds = Bounds(np.zeros(n_vars), var_upper)
    integrality = np.ones(n_vars)
    constraints = LinearConstraint(csr_matrix(A), lower, upper)

    # Solve via SciPy HiGHS solver
    res = milp(
        c=c_obj,
        integrality=integrality,
        bounds=bounds,
        constraints=constraints,
        options={"time_limit": time_limit}
    )

    if not res.success:
        raise RuntimeError(f"Solver failed: {res.message}")

    x_sol = res.x[:M * N].reshape((M, N))
    z_sol = res.x[M * N:]

    # Parse assignments
    assignments = []
    routes = []
    depot_summary = []

    for i in range(M):
        depot_info = depots.iloc[i].to_dict()
        assigned_indices = np.where(x_sol[i] > 0.5)[0]
        
        depot_assigned_stations = []
        depot_dist = 0.0
        depot_connectors = 0

        for j in assigned_indices:
            st = broken_stations.iloc[j]
            dist_km = float(dists[i, j])
            conn_count = int(st["num_connectors"])
            
            depot_dist += dist_km
            depot_connectors += conn_count

            assign_record = {
                "depot_id": int(depot_info["depot_id"]),
                "depot_title": str(depot_info["title"]),
                "station_id": int(st["id"]),
                "station_title": str(st["title"]),
                "operator": str(st.get("operator", "Unknown")),
                "status": str(st.get("status", "Offline")),
                "station_lat": float(st["lat"]),
                "station_lon": float(st["lon"]),
                "distance_km": round(dist_km, 2),
                "connectors_restored": conn_count
            }
            assignments.append(assign_record)
            depot_assigned_stations.append(assign_record)

            # Route line for Leaflet mapping
            routes.append({
                "depot_id": int(depot_info["depot_id"]),
                "depot_coords": [float(depot_info["lat"]), float(depot_info["lon"])],
                "station_id": int(st["id"]),
                "station_coords": [float(st["lat"]), float(st["lon"])],
                "distance_km": round(dist_km, 2)
            })

        depot_summary.append({
            "depot_id": int(depot_info["depot_id"]),
            "title": str(depot_info["title"]),
            "lat": float(depot_info["lat"]),
            "lon": float(depot_info["lon"]),
            "assigned_count": len(assigned_indices),
            "max_capacity": max_stations_per_crew,
            "utilization_pct": round(len(assigned_indices) / max_stations_per_crew * 100, 1) if max_stations_per_crew > 0 else 0.0,
            "total_distance_km": round(depot_dist, 2),
            "connectors_restored": depot_connectors
        })

    assigned_count = int(np.sum(z_sol > 0.5))
    unassigned_count = int(N - assigned_count)
    total_dist = float(np.sum(dists * x_sol))
    total_connectors = int(np.sum(C[z_sol > 0.5]))
    avg_dist = round(total_dist / assigned_count, 2) if assigned_count > 0 else 0.0

    return {
        "success": True,
        "assigned_stations_count": assigned_count,
        "unassigned_stations_count": unassigned_count,
        "total_offline_stations": N,
        "restored_connectors": total_connectors,
        "total_travel_distance_km": round(total_dist, 2),
        "avg_response_distance_km": avg_dist,
        "assignments": assignments,
        "routes": routes,
        "depot_summary": depot_summary,
        "solver_status": res.status,
        "objective_value": round(float(-res.fun), 4)
    }


def validate_solution(result, broken_stations, depots, max_stations_per_crew=4, max_radius_km=150.0):
    """
    Independently validate that all mathematical constraints are satisfied.
    """
    checks = {}
    assignments = result["assignments"]
    depot_summary = result["depot_summary"]

    # 1. Capacity constraint
    capacity_pass = all(d["assigned_count"] <= max_stations_per_crew for d in depot_summary)
    checks["crew_workload_capacity"] = capacity_pass

    # 2. SLA distance limit
    sla_pass = all(a["distance_km"] <= max_radius_km + 1e-3 for a in assignments)
    checks["sla_distance_limit"] = sla_pass

    # 3. Single assignment uniqueness (no station assigned twice)
    assigned_station_ids = [a["station_id"] for a in assignments]
    uniqueness_pass = len(assigned_station_ids) == len(set(assigned_station_ids))
    checks["single_assignment_uniqueness"] = uniqueness_pass

    # 4. Connector conservation
    total_restored = sum(a["connectors_restored"] for a in assignments)
    checks["connector_count_matches"] = (total_restored == result["restored_connectors"])

    checks["all_checks_passed"] = all(checks.values())
    return checks

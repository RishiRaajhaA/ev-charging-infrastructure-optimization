"""
Optimization 1: EV Charging Hub Location Selection
---------------------------------------------------

Prototype formulation:
- Candidate locations are generated from existing station coordinates using
  spherical K-means clustering.
- Each cluster is represented by the nearest real charging station, ensuring
  proposed hubs are located at realistic observed locations.
- A Mixed-Integer Programming (MIP) maximum-coverage model selects K hubs.
- A station is considered geographically covered if it is within a user-defined
  radius of at least one selected hub.

This is the first prototype. The final UI can expose:
    - country/region filter
    - number of hubs K
    - coverage radius R
    - optional sparsity weighting

The model intentionally does NOT assume EV traffic, population, demand,
revenue, or electricity consumption because those variables are absent from
the dataset.
"""

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from scipy.optimize import milp, LinearConstraint, Bounds
from scipy.sparse import lil_matrix, csr_matrix


EARTH_RADIUS_KM = 6371.0


def haversine_matrix(points_a, points_b):
    """Return pairwise great-circle distances in km."""
    a = np.radians(np.asarray(points_a, dtype=float))
    b = np.radians(np.asarray(points_b, dtype=float))

    lat1 = a[:, 0][:, None]
    lon1 = a[:, 1][:, None]
    lat2 = b[:, 0][None, :]
    lon2 = b[:, 1][None, :]

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    h = (
        np.sin(dlat / 2) ** 2
        + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    )

    return EARTH_RADIUS_KM * 2 * np.arcsin(np.sqrt(np.clip(h, 0, 1)))


def generate_candidate_hubs(df, n_candidates=100, random_state=42, operational_only=True, country=None):
    """
    Generate candidate hub locations from observed stations.

    K-means is performed on 3D unit-sphere coordinates to avoid treating
    latitude/longitude as ordinary Cartesian coordinates. Each cluster is
    represented by the observed station nearest to its cluster centroid.
    """
    geo = df.dropna(subset=["lat", "lon"]).copy()
    if operational_only and "status" in geo.columns:
        geo = geo[geo["status"].astype(str).str.strip().str.lower() == "operational"]
    if country and country != "All" and "country" in geo.columns:
        geo = geo[geo["country"].astype(str).str.strip().str.upper() == country.strip().upper()]

    if len(geo) < n_candidates:
        n_candidates = len(geo)

    lat = np.radians(geo["lat"].to_numpy())
    lon = np.radians(geo["lon"].to_numpy())

    X = np.column_stack([
        np.cos(lat) * np.cos(lon),
        np.cos(lat) * np.sin(lon),
        np.sin(lat),
    ])

    model = KMeans(
        n_clusters=n_candidates,
        random_state=random_state,
        n_init=10,
    )
    labels = model.fit_predict(X)

    centers = model.cluster_centers_
    centers /= np.linalg.norm(centers, axis=1, keepdims=True)

    candidate_indices = []

    for cluster_id in range(n_candidates):
        members = np.where(labels == cluster_id)[0]
        if len(members) == 0:
            continue

        distances = np.sum(
            (X[members] - centers[cluster_id]) ** 2,
            axis=1,
        )

        candidate_indices.append(
            geo.index[members[np.argmin(distances)]]
        )

    candidates = (
        df.loc[candidate_indices]
        .drop_duplicates(subset=["id"])
        .reset_index(drop=True)
    )

    return candidates


def solve_max_coverage(
    df,
    candidates,
    n_hubs=10,
    radius_km=50,
    time_limit=120,
    operational_only=True,
    country=None,
):
    """
    Solve the maximum-coverage MIP (MCLP).

    Decision variables:
        y_j in {0, 1}: candidate hub j is selected
        z_i in [0, 1]: station i is covered (continuous relaxation naturally yields {0,1})

    Objective:
        maximize total number of covered operational stations: sum_i z_i

    Constraints:
        sum_j y_j <= n_hubs
        z_i <= sum(y_j for candidate j within radius of station i)
        y_j in {0, 1}, 0 <= z_i <= 1
    """
    station_data = df.dropna(subset=["lat", "lon"]).copy()
    if operational_only and "status" in station_data.columns:
        station_data = station_data[station_data["status"].astype(str).str.strip().str.lower() == "operational"]
    if country and country != "All" and "country" in station_data.columns:
        station_data = station_data[station_data["country"].astype(str).str.strip().str.upper() == country.strip().upper()]

    station_coords = station_data[["lat", "lon"]].to_numpy()
    candidate_coords = candidates[["lat", "lon"]].to_numpy()

    distances = haversine_matrix(station_coords, candidate_coords)
    neighbors = [np.flatnonzero(row <= radius_km) for row in distances]

    covered_rows = [
        i for i, candidate_neighbors in enumerate(neighbors)
        if len(candidate_neighbors) > 0
    ]

    n_candidates = len(candidates)
    n_covered_rows = len(covered_rows)
    n_variables = n_candidates + n_covered_rows

    # First n_candidates variables = y_j
    # Remaining variables = z_i for stations that have at least one candidate
    A = lil_matrix(
        (n_covered_rows + 1, n_variables),
        dtype=float,
    )

    lower = np.full(n_covered_rows + 1, -np.inf)
    upper = np.full(n_covered_rows + 1, np.inf)

    for row, station_idx in enumerate(covered_rows):
        A[row, n_candidates + row] = 1
        A[row, neighbors[station_idx]] = -1
        upper[row] = 0

    # At most K hubs
    A[n_covered_rows, :n_candidates] = 1
    upper[n_covered_rows] = n_hubs

    objective = np.zeros(n_variables)
    objective[n_candidates:] = -1  # maximize coverage via minimization

    # Exact standard relaxation: y_j binary (1), z_i continuous in [0, 1] (0)
    # Since z_i is maximized under z_i <= sum(y_j) and upper bound 1, z_i* is guaranteed integer {0, 1}
    integrality = np.zeros(n_variables)
    integrality[:n_candidates] = 1  # y_j binary
    integrality[n_candidates:] = 0  # z_i continuous

    result = milp(
        c=objective,
        integrality=integrality,
        bounds=Bounds(
            np.zeros(n_variables),
            np.ones(n_variables),
        ),
        constraints=LinearConstraint(
            csr_matrix(A),
            lower,
            upper,
        ),
        options={"time_limit": time_limit},
    )

    if not result.success:
        raise RuntimeError(result.message)

    selected_indices = np.flatnonzero(result.x[:n_candidates] > 0.5)
    selected_hubs = candidates.iloc[selected_indices].copy()

    coverage = int(round(-result.fun))

    # Coverage at the station level
    station_covered = np.zeros(len(station_data), dtype=bool)
    for station_idx in covered_rows:
        if np.any(result.x[neighbors[station_idx]] > 0.5):
            station_covered[station_idx] = True

    coverage_rate = station_covered.mean()

    gap = getattr(result, "mip_gap", 0.0)
    gap_str = f"{gap * 100:.2f}%" if gap is not None else "0.00%"

    return {
        "selected_hubs": selected_hubs,
        "covered_stations": int(station_covered.sum()),
        "total_stations": len(station_data),
        "coverage_rate": coverage_rate,
        "n_hubs": len(selected_hubs),
        "radius_km": radius_km,
        "solver_status": "Optimal" if result.status == 0 else result.message,
        "solver_message": str(result.message),
        "optimality_gap": gap_str,
        "candidate_restriction_notice": f"Globally optimal with respect to discrete candidate set J (|J| = {n_candidates}).",
        "solver_result": result,
    }


def greedy_max_coverage(
    df,
    candidates,
    n_hubs=10,
    radius_km=50,
    operational_only=True,
    country=None,
):
    """
    Deterministic Greedy Forward-Selection Heuristic Benchmark for MCLP.
    At each step, greedily selects the candidate that covers the maximum
    number of currently uncovered stations.
    """
    station_data = df.dropna(subset=["lat", "lon"]).copy()
    if operational_only and "status" in station_data.columns:
        station_data = station_data[station_data["status"].astype(str).str.strip().str.lower() == "operational"]
    if country and country != "All" and "country" in station_data.columns:
        station_data = station_data[station_data["country"].astype(str).str.strip().str.upper() == country.strip().upper()]

    station_coords = station_data[["lat", "lon"]].to_numpy()
    candidate_coords = candidates[["lat", "lon"]].to_numpy()

    distances = haversine_matrix(station_coords, candidate_coords)
    coverage_mask = distances <= radius_km

    k_to_pick = min(n_hubs, len(candidates))
    uncovered = np.ones(len(station_data), dtype=bool)
    selected_candidate_indices = []

    for _ in range(k_to_pick):
        marginal_gains = np.sum(coverage_mask & uncovered[:, None], axis=0)
        for idx in selected_candidate_indices:
            marginal_gains[idx] = -1

        best_candidate = int(np.argmax(marginal_gains))
        if marginal_gains[best_candidate] <= 0:
            break
        selected_candidate_indices.append(best_candidate)
        uncovered &= ~coverage_mask[:, best_candidate]

    selected_hubs = candidates.iloc[selected_candidate_indices].copy()
    covered_stations = int(np.sum(~uncovered))
    coverage_rate = covered_stations / len(station_data) if len(station_data) > 0 else 0.0

    return {
        "selected_hubs": selected_hubs,
        "covered_stations": covered_stations,
        "total_stations": len(station_data),
        "coverage_rate": coverage_rate,
        "n_hubs": len(selected_hubs),
        "radius_km": radius_km,
        "method": "Greedy Forward Selection Heuristic"
    }


if __name__ == "__main__":
    import os
    DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "ev_stations_2025.csv")

    df = pd.read_csv(DATA_PATH)

    candidates = generate_candidate_hubs(
        df,
        n_candidates=100,
    )

    result = solve_max_coverage(
        df,
        candidates,
        n_hubs=10,
        radius_km=50,
    )

    print("\n=== Optimization 1: Maximum Coverage MIP (MCLP) ===")
    print(f"Total dataset records: {len(df):,}")
    print(f"Operational stations evaluated: {result['total_stations']:,}")
    print(f"Candidate hubs generated: {len(candidates)}")
    print(f"Hubs selected (K): {result['n_hubs']}")
    print(f"Coverage radius (R): {result['radius_km']} km")
    print(f"Covered operational stations: {result['covered_stations']:,}")
    print(f"Coverage rate: {result['coverage_rate']:.2%}")
    print(f"Solver termination status: {result['solver_status']}")
    print(f"Optimality gap: {result['optimality_gap']} (Proven Global Optimum over Candidate Set)")

    greedy_res = greedy_max_coverage(
        df,
        candidates,
        n_hubs=10,
        radius_km=50,
    )
    print("\n=== Baseline Comparison: Greedy Heuristic vs Optimal MIP ===")
    print(f"Greedy heuristic coverage: {greedy_res['covered_stations']:,} ({greedy_res['coverage_rate']:.2%})")
    print(f"Optimal MIP coverage:      {result['covered_stations']:,} ({result['coverage_rate']:.2%})")
    diff = result['covered_stations'] - greedy_res['covered_stations']
    print(f"MIP Advantage over Greedy: +{diff:,} operational stations")

    print("\nSelected candidate hubs:")
    print(
        result["selected_hubs"][
            ["id", "title", "lat", "lon", "state", "country"]
        ].to_string(index=False)
    )

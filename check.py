
import pandas as pd
import numpy as np
import folium
from sklearn.neighbors import BallTree

# -----------------------------
# 1. Load and clean the dataset
# -----------------------------
df = pd.read_csv("data/ev_stations_2025.csv")

df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
df["lon"] = pd.to_numeric(df["lon"], errors="coerce")

df = df.dropna(subset=["lat", "lon", "country", "status"])

# Select one country for meaningful geographical analysis.
# CA = Canada, US = United States, IN = India, etc.
COUNTRY = "CA"

stations = df[
    (df["country"] == COUNTRY) &
    (df["status"].str.strip().str.lower() == "operational")
].copy()

if stations.empty:
    raise ValueError(f"No operational stations found for {COUNTRY}")

# Earth's approximate radius in kilometres
EARTH_RADIUS_KM = 6371.0
SERVICE_RADIUS_KM = 5.0

# BallTree uses latitude/longitude in radians with haversine distance
station_coords = np.radians(stations[["lat", "lon"]].to_numpy())
tree = BallTree(station_coords, metric="haversine")

print("Country:", COUNTRY)
print("Operational stations:", len(stations))

# ---------------------------------------------
# 2. Generate candidate points within the region
# ---------------------------------------------
# Sample a grid at approximately 5 km latitude spacing.
# Longitude spacing is adjusted for latitude.
min_lat, max_lat = stations["lat"].min(), stations["lat"].max()
min_lon, max_lon = stations["lon"].min(), stations["lon"].max()

candidate_points = []

latitudes = np.arange(min_lat, max_lat + 0.025, 0.05)

for lat in latitudes:
    # Approximately 5 km longitude spacing at this latitude
    lon_step = 5.0 / (111.32 * max(abs(np.cos(np.radians(lat))), 0.01))
    longitudes = np.arange(min_lon, max_lon + lon_step, lon_step)

    for lon in longitudes:
        candidate_points.append((lat, lon))

candidates = pd.DataFrame(
    candidate_points, columns=["lat", "lon"]
)

# ---------------------------------------------
# 3. Find nearest operational charging station
# ---------------------------------------------
candidate_coords = np.radians(candidates[["lat", "lon"]].to_numpy())

distances, indices = tree.query(candidate_coords, k=1)

candidates["nearest_distance_km"] = (
    distances[:, 0] * EARTH_RADIUS_KM
)

candidates["nearest_station"] = (
    stations.iloc[indices[:, 0]]["title"].to_numpy()
)

# Flag locations outside the selected service radius
underserved = candidates[
    candidates["nearest_distance_km"] > SERVICE_RADIUS_KM
].copy()

underserved = underserved.sort_values(
    "nearest_distance_km", ascending=False
)

print("\nCandidate grid points:", len(candidates))
print("Potentially underserved candidate points:", len(underserved))
print(
    "Percentage outside service radius:",
    round(100 * len(underserved) / len(candidates), 2), "%"
)

print("\nTop 20 candidate locations:")
print(underserved.head(20).to_string(index=False))

# Save results for further analysis
underserved.to_csv("potential_underserved_locations.csv", index=False)

# ---------------------------------------------
# 4. Visualize the results on an interactive map
# ---------------------------------------------
center = [stations["lat"].median(), stations["lon"].median()]

m = folium.Map(location=center, zoom_start=5)

# Existing operational charging stations
for _, row in stations.iterrows():
    folium.CircleMarker(
        location=[row["lat"], row["lon"]],
        radius=2,
        color="blue",
        fill=True,
        fill_opacity=0.65,
        popup=f"Existing station: {row['title']}"
    ).add_to(m)

# Potentially underserved candidate locations
# Display the most isolated points to keep the map readable.
for _, row in underserved.head(1000).iterrows():
    folium.CircleMarker(
        location=[row["lat"], row["lon"]],
        radius=3,
        color="red",
        fill=True,
        fill_opacity=0.6,
        popup=(
            f"Candidate location<br>"
            f"Nearest station: {row['nearest_distance_km']:.2f} km"
        )
    ).add_to(m)

m.save("ev_coverage_analysis.html")

print("\nSaved:")
print("- potential_underserved_locations.csv")
print("- ev_coverage_analysis.html")
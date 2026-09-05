import pandas as pd
import matplotlib.pyplot as plt
import os

# Create output directory
os.makedirs("assets", exist_ok=True)

# Load dataset
df = pd.read_csv("data/ev_stations_2025.csv")

# Color palette matching LaTeX Beamer theme
navy = '#192B46'
blue = '#305D96'
teal = '#238287'
light_bg = '#F4F7FA'

# --- CHART 1: Geographic Distribution Map ---
fig, ax = plt.subplots(figsize=(6, 4.2), dpi=300)
fig.patch.set_facecolor('white')
ax.set_facecolor(light_bg)

valid_geo = df.dropna(subset=['lat', 'lon'])
ax.scatter(valid_geo['lon'], valid_geo['lat'], c=teal, alpha=0.45, s=10, edgecolors='none')

ax.set_title("Geospatial Distribution of EV Stations", fontsize=11, fontweight='bold', color=navy, pad=10)
ax.set_xlabel("Longitude", fontsize=9, fontweight='bold', color=navy)
ax.set_ylabel("Latitude", fontsize=9, fontweight='bold', color=navy)
ax.tick_params(colors=navy, labelsize=8)
ax.grid(True, linestyle='--', alpha=0.5, color='gray')
for spine in ax.spines.values():
    spine.set_color(navy)
    spine.set_linewidth(1.0)

plt.tight_layout()
plt.savefig("assets/dataset_geo_map.png", dpi=300, bbox_inches='tight')
plt.close()

# --- CHART 2: Top Regions Distribution ---
if 'state' in df.columns:
    state_counts = df['state'].value_counts().head(8)
    fig, ax = plt.subplots(figsize=(6, 4.2), dpi=300)
    fig.patch.set_facecolor('white')
    ax.set_facecolor(light_bg)

    bars = ax.barh(state_counts.index[::-1], state_counts.values[::-1], color=blue, edgecolor=navy, linewidth=0.8, height=0.6)
    
    for bar in bars:
        width = bar.get_width()
        ax.text(width + 10, bar.get_y() + bar.get_height()/2, f'{int(width):,}', 
                ha='left', va='center', fontsize=8, fontweight='bold', color=navy)

    ax.set_title("Top Regions by Station Count", fontsize=11, fontweight='bold', color=navy, pad=10)
    ax.set_xlabel("Number of Stations", fontsize=9, fontweight='bold', color=navy)
    ax.set_ylabel("Region / State", fontsize=9, fontweight='bold', color=navy)
    ax.tick_params(colors=navy, labelsize=8)
    ax.grid(True, linestyle='--', alpha=0.4, color='gray')
    for spine in ax.spines.values():
        spine.set_color(navy)
        spine.set_linewidth(1.0)

    plt.tight_layout()
    plt.savefig("assets/dataset_top_regions.png", dpi=300, bbox_inches='tight')
    plt.close()

print("Visuals generated successfully in assets/!")

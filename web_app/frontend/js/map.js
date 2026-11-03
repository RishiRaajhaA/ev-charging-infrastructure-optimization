/**
 * Leaflet Map Controller
 */

export class MapController {
    constructor(elementId, initialCenter = [35.0, -40.0], initialZoom = 3) {
        this.elementId = elementId;
        this.map = null;
        this.stationsLayer = null;
        this.hubsLayer = null;
        this.radiusLayer = null;
        this.initialCenter = initialCenter;
        this.initialZoom = initialZoom;
        this.init();
    }

    init() {
        const container = document.getElementById(this.elementId);
        if (!container) return;

        // Define world bounds [-85, -180] to [85, 180] to prevent map wrapping and duplication
        const worldBounds = L.latLngBounds(L.latLng(-85, -180), L.latLng(85, 180));

        // Create Leaflet map locked to single world view
        this.map = L.map(this.elementId, {
            zoomControl: true,
            preferCanvas: true,
            minZoom: 2,
            maxZoom: 17,
            maxBounds: worldBounds,
            maxBoundsViscosity: 1.0,
            worldCopyJump: false
        }).setView(this.initialCenter, this.initialZoom);

        // ESRI Dark Gray Basemap (noWrap: true prevents horizontal duplication)
        const darkBase = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}', {
            attribution: 'Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ',
            maxZoom: 16,
            noWrap: true,
            bounds: worldBounds
        }).addTo(this.map);

        // ESRI Dark Gray Reference Labels
        const darkLabels = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}', {
            attribution: '',
            maxZoom: 16,
            opacity: 0.75,
            noWrap: true,
            bounds: worldBounds
        }).addTo(this.map);

        // Satellite Basemap
        const satellite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
            attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping',
            maxZoom: 18,
            noWrap: true,
            bounds: worldBounds
        });

        // OpenStreetMap Standard Basemap
        const osm = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxZoom: 19,
            noWrap: true,
            bounds: worldBounds
        });

        // Layer Controls (Dark, Satellite, Streets)
        const baseMaps = {
            "Dark Theme": L.layerGroup([darkBase, darkLabels]),
            "Satellite": satellite,
            "Standard Street": osm
        };

        L.control.layers(baseMaps, null, { position: 'topright' }).addTo(this.map);

        this.stationsLayer = L.layerGroup().addTo(this.map);
        this.radiusLayer = L.layerGroup().addTo(this.map);
        this.routesLayer = L.layerGroup().addTo(this.map);
        this.hubsLayer = L.layerGroup().addTo(this.map);
    }

    invalidateSize() {
        if (this.map) {
            setTimeout(() => this.map.invalidateSize(), 200);
        }
    }

    renderStations(stations = []) {
        this.stationsLayer.clearLayers();
        if (!stations.length) return;

        const markers = [];
        stations.forEach(st => {
            const color = st.is_operational ? '#10B981' : (st.is_offline ? '#EF4444' : '#F59E0B');
            const marker = L.circleMarker([st.lat, st.lon], {
                radius: 3.5,
                fillColor: color,
                color: color,
                weight: 1,
                opacity: 0.8,
                fillOpacity: 0.6
            });

            marker.bindPopup(`
                <div style="font-family: var(--font-body); font-size: 12px; color: #0F172A; min-width: 160px;">
                    <div style="font-weight: bold; margin-bottom: 4px; color: #0F172A;">${st.title}</div>
                    <div><strong>State:</strong> ${st.state}</div>
                    <div><strong>Operator:</strong> ${st.operator}</div>
                    <div><strong>Connectors:</strong> ${st.num_connectors}</div>
                    <div><strong>Status:</strong> <span style="color: ${color}; font-weight: 600;">${st.status}</span></div>
                </div>
            `);

            this.stationsLayer.addLayer(marker);
            markers.push([st.lat, st.lon]);
        });

        if (markers.length > 0 && markers.length <= 500) {
            this.map.fitBounds(L.latLngBounds(markers), { padding: [40, 40] });
        }
    }

    renderOpt1Results(stations = [], selectedHubs = [], radiusKm = 50) {
        this.stationsLayer.clearLayers();
        this.radiusLayer.clearLayers();
        this.hubsLayer.clearLayers();

        // 1. Render existing station points
        stations.forEach(st => {
            const marker = L.circleMarker([st.lat, st.lon], {
                radius: 3,
                fillColor: '#64748B',
                color: '#475569',
                weight: 1,
                opacity: 0.5,
                fillOpacity: 0.35
            });
            this.stationsLayer.addLayer(marker);
        });

        // 2. Render coverage radius circles around hubs
        selectedHubs.forEach(hub => {
            const circle = L.circle([hub.lat, hub.lon], {
                radius: radiusKm * 1000, // meters
                color: '#00F2FE',
                fillColor: '#00F2FE',
                fillOpacity: 0.12,
                weight: 1.5,
                dashArray: '4, 6'
            });
            this.radiusLayer.addLayer(circle);
        });

        // 3. Render Selected Hubs
        const hubPoints = [];
        selectedHubs.forEach((hub, idx) => {
            const hubIcon = L.divIcon({
                className: 'custom-hub-marker',
                html: `
                    <div style="position: relative; width: 26px; height: 26px;">
                        <div class="hub-pulse-ring"></div>
                        <div class="hub-marker-icon">★</div>
                    </div>
                `,
                iconSize: [26, 26],
                iconAnchor: [13, 13]
            });

            const marker = L.marker([hub.lat, hub.lon], { icon: hubIcon });
            marker.bindPopup(`
                <div style="font-family: var(--font-body); font-size: 13px; color: #0F172A; min-width: 200px;">
                    <div style="background: linear-gradient(135deg, #00F2FE, #4FACFE); color: #080C15; padding: 4px 8px; border-radius: 4px; font-weight: 800; font-size: 11px; margin-bottom: 6px; display: inline-block;">
                        SELECTED CHARGING HUB #${idx + 1}
                    </div>
                    <div style="font-weight: 700; font-size: 14px; margin-bottom: 4px; color: #0F172A;">${hub.title}</div>
                    <div><strong>Region / State:</strong> ${hub.state}</div>
                    <div><strong>Operator:</strong> ${hub.operator}</div>
                    <div><strong>Covered Stations in Radius:</strong> <span style="color: #0284C7; font-weight: 800;">${hub.stations_covered.toLocaleString()}</span></div>
                    <div><strong>Coordinates:</strong> ${hub.lat.toFixed(4)}, ${hub.lon.toFixed(4)}</div>
                </div>
            `);

            this.hubsLayer.addLayer(marker);
            hubPoints.push([hub.lat, hub.lon]);
        });

        if (hubPoints.length > 0) {
            this.map.fitBounds(L.latLngBounds(hubPoints), { padding: [60, 60], maxZoom: 7 });
        }
    }

    renderOpt2Dispatch(stationPins = [], depots = [], routes = []) {
        this.stationsLayer.clearLayers();
        this.radiusLayer.clearLayers();
        this.hubsLayer.clearLayers();
        if (this.routesLayer) this.routesLayer.clearLayers();

        const allCoords = [];

        // 1. Render route vectors from depots to assigned stations
        routes.forEach(rt => {
            const polyline = L.polyline([rt.depot_coords, rt.station_coords], {
                color: '#00F2FE',
                weight: 2.5,
                opacity: 0.85,
                dashArray: '5, 8'
            });

            polyline.bindPopup(`
                <div style="font-family: var(--font-body); font-size: 12px; color: #0F172A;">
                    <div style="font-weight: bold; color: #0284C7; margin-bottom: 2px;">DISPATCH ROUTE</div>
                    <div><strong>Depot:</strong> ${rt.depot_id}</div>
                    <div><strong>Distance:</strong> ${rt.distance_km} km</div>
                </div>
            `);

            if (this.routesLayer) this.routesLayer.addLayer(polyline);
            else this.radiusLayer.addLayer(polyline);
        });

        // 2. Render offline station pins
        stationPins.forEach(st => {
            const isRepaired = st.is_repaired;
            const color = isRepaired ? '#10B981' : '#EF4444';
            const marker = L.circleMarker([st.lat, st.lon], {
                radius: isRepaired ? 6 : 4,
                fillColor: color,
                color: isRepaired ? '#FFFFFF' : '#EF4444',
                weight: isRepaired ? 2 : 1,
                opacity: 0.9,
                fillOpacity: isRepaired ? 0.9 : 0.5
            });

            marker.bindPopup(`
                <div style="font-family: var(--font-body); font-size: 12px; color: #0F172A; min-width: 170px;">
                    <div style="font-weight: bold; margin-bottom: 4px; color: #0F172A;">${st.title}</div>
                    <div><strong>Status:</strong> <span style="color: ${isRepaired ? '#10B981' : '#EF4444'}; font-weight: bold;">${isRepaired ? 'DISPATCHED FOR REPAIR' : 'UNASSIGNED / OFFLINE'}</span></div>
                    <div><strong>State:</strong> ${st.state}</div>
                    <div><strong>Connectors:</strong> ${st.connectors}</div>
                    <div><strong>Operator:</strong> ${st.operator}</div>
                </div>
            `);

            this.stationsLayer.addLayer(marker);
            allCoords.push([st.lat, st.lon]);
        });

        // 3. Render Technician Service Depots
        depots.forEach(dep => {
            const depotIcon = L.divIcon({
                className: 'custom-depot-marker',
                html: `
                    <div style="position: relative; width: 30px; height: 30px;">
                        <div class="hub-pulse-ring" style="border-color: #00F2FE;"></div>
                        <div style="width: 30px; height: 30px; border-radius: 50%; background: linear-gradient(135deg, #00F2FE, #0284C7); border: 2px solid #FFFFFF; display: flex; align-items: center; justify-content: center; box-shadow: 0 0 15px rgba(0,242,254,0.7); font-size: 14px;">🔧</div>
                    </div>
                `,
                iconSize: [30, 30],
                iconAnchor: [15, 15]
            });

            const marker = L.marker([dep.lat, dep.lon], { icon: depotIcon });
            marker.bindPopup(`
                <div style="font-family: var(--font-body); font-size: 13px; color: #0F172A; min-width: 200px;">
                    <div style="background: linear-gradient(135deg, #00F2FE, #0284C7); color: #080C15; padding: 4px 8px; border-radius: 4px; font-weight: 800; font-size: 11px; margin-bottom: 6px; display: inline-block;">
                        TECHNICIAN DEPOT #${dep.depot_id}
                    </div>
                    <div style="font-weight: 700; font-size: 14px; margin-bottom: 4px; color: #0F172A;">${dep.title}</div>
                    <div><strong>Crew Workload:</strong> ${dep.assigned_count} / ${dep.max_capacity} stations (${dep.utilization_pct}%)</div>
                    <div><strong>Restored Connectors:</strong> <span style="color: #10B981; font-weight: bold;">${dep.connectors_restored}</span></div>
                    <div><strong>Total Travel:</strong> ${dep.total_distance_km} km</div>
                </div>
            `);

            this.hubsLayer.addLayer(marker);
            allCoords.push([dep.lat, dep.lon]);
        });

        if (allCoords.length > 0) {
            this.map.fitBounds(L.latLngBounds(allCoords), { padding: [50, 50], maxZoom: 8 });
        }
    }
}


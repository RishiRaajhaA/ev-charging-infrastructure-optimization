import { Api } from './api.js';
import { MapController } from './map.js';
import { ChartController } from './charts.js';
import { UI } from './ui.js';

class App {
    constructor() {
        this.currentView = 'dashboard';
        this.stats = null;
        this.explorerMap = null;
        this.opt1Map = null;
        this.opt2Map = null;
        this.lastOpt1Result = null;
        this.lastOpt2Result = null;
        this.scenarios = { A: null, B: null };
        this.filteredStations = [];
    }

    async init() {
        this.setupNavigation();
        this.setupEventListeners();
        
        // Initialize maps
        this.explorerMap = new MapController('explorer-map');
        this.opt1Map = new MapController('opt1-map');
        this.opt2Map = document.getElementById('opt2-map') ? new MapController('opt2-map') : null;

        // Load initial stats & options
        await this.loadInitialData();
    }

    setupNavigation() {
        const navItems = document.querySelectorAll('.nav-item');
        navItems.forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const target = item.getAttribute('data-view');
                this.switchView(target);
            });
        });
    }

    switchView(viewName) {
        this.currentView = viewName;

        // Update nav active classes
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.toggle('active', item.getAttribute('data-view') === viewName);
        });

        // Update view sections
        document.querySelectorAll('.view-section').forEach(sec => {
            sec.classList.toggle('active', sec.id === `view-${viewName}`);
        });

        // Update page title
        const titles = {
            dashboard: 'Executive Network Dashboard',
            explorer: 'Data Explorer & Geospatial Studio',
            opt1: 'Optimization 1: Charging Hub Location (Maximum Coverage MIP - MCLP)',
            opt2: 'Optimization 2: Regional Infrastructure Parity (Max-Min Fairness MILP)',
            scenarios: 'Strategic Scenario Comparator',
            methodology: 'Operations Research Formulations & Course Alignment'
        };
        const pageTitleEl = document.getElementById('page-title');
        if (pageTitleEl) pageTitleEl.textContent = titles[viewName] || 'EV Optima';

        // Invalidate map sizes when navigating to views with maps
        if (viewName === 'explorer') {
            this.explorerMap.invalidateSize();
            this.applyExplorerFilters();
        } else if (viewName === 'opt1') {
            this.opt1Map.invalidateSize();
        } else if (viewName === 'opt2' && this.opt2Map) {
            this.opt2Map.invalidateSize();
        }
    }

    async loadInitialData() {
        try {
            this.stats = await Api.getStats();
            this.renderDashboardStats();
            
            // Populate filter options
            const filterOpts = await Api.getFilterOptions();
            this.populateFilterDropdowns(filterOpts);
            
            // Load initial stations for explorer map
            await this.applyExplorerFilters();
        } catch (err) {
            UI.showToast(`Error initializing data: ${err.message}`, 'error');
        }
    }

    renderDashboardStats() {
        if (!this.stats) return;

        // Update KPI tiles
        document.getElementById('kpi-total-stations').textContent = this.stats.total_stations.toLocaleString();
        document.getElementById('kpi-total-connectors').textContent = this.stats.total_connectors.toLocaleString();
        document.getElementById('kpi-avg-cps').textContent = this.stats.avg_connectors.toFixed(2);
        document.getElementById('kpi-op-ratio').textContent = `${(this.stats.operational_ratio * 100).toFixed(1)}%`;
        const opSub = document.querySelector('#kpi-op-ratio + .kpi-sub');
        if (opSub) {
            opSub.textContent = `${this.stats.operational_count.toLocaleString()} Active (312 Off, 387 Plan)`;
        }
        document.getElementById('kpi-states-count').textContent = this.stats.num_states.toLocaleString();
        document.getElementById('kpi-missing-states').textContent = this.stats.missing_states.toLocaleString();

        // Update sidebar dataset badge
        const badgeEl = document.getElementById('sidebar-dataset-badge');
        const filenameEl = document.getElementById('sidebar-dataset-filename');
        if (badgeEl && filenameEl) {
            badgeEl.className = `dataset-badge ${this.stats.is_custom ? 'custom' : 'sample'}`;
            badgeEl.textContent = this.stats.is_custom ? 'Custom' : 'Sample';
            filenameEl.textContent = this.stats.filename;
        }

        // Render dashboard charts
        ChartController.renderTopRegions('chart-top-regions', this.stats.top_regions);
        ChartController.renderStatusDonut(
            'chart-status-donut',
            this.stats.operational_count,
            this.stats.offline_count,
            this.stats.planned_unknown_count,
            this.stats.total_stations
        );
    }

    populateFilterDropdowns(options) {
        // Country dropdown for Explorer
        const countrySelect = document.getElementById('filter-country');
        if (countrySelect && options.countries) {
            countrySelect.innerHTML = '<option value="All" selected>All Countries (Global Network)</option>' +
                options.countries.map(c => `<option value="${c.code}">${c.name} — ${c.count.toLocaleString()} stns</option>`).join('');
        }

        // State / Region dropdown for Explorer
        const stateSelect = document.getElementById('filter-state');
        if (stateSelect) {
            stateSelect.innerHTML = '<option value="All">All States / Regions</option>' + 
                options.states.map(s => `<option value="${s}">${s}</option>`).join('');
        }

        // Operator dropdown for Explorer
        const opSelect = document.getElementById('filter-operator');
        if (opSelect) {
            opSelect.innerHTML = '<option value="All">All Operators</option>' + 
                options.operators.map(op => `<option value="${op}">${op}</option>`).join('');
        }

        // Country dropdown for Optimization 1
        const opt1CountrySelect = document.getElementById('opt1-country');
        if (opt1CountrySelect && options.countries) {
            opt1CountrySelect.innerHTML = '<option value="All" selected>Global Network (9,301 Operational Stations)</option>' +
                options.countries.map(c => `<option value="${c.code}">${c.name} — ${c.count.toLocaleString()} stations</option>`).join('');
        }

        // Country dropdown for Optimization 2
        const opt2CountrySelect = document.getElementById('opt2-country');
        if (opt2CountrySelect && options.countries) {
            opt2CountrySelect.innerHTML = '<option value="All" selected>Global Fleet (403 Modeled States / Regions)</option>' +
                options.countries
                    .filter(c => c.regions_count > 0)
                    .map(c => `<option value="${c.code}">${c.name} — ${c.regions_count} modeled regions (${c.count} stations)</option>`).join('');
        }
    }

    async applyExplorerFilters() {
        const country = document.getElementById('filter-country')?.value || 'All';
        const state = document.getElementById('filter-state')?.value || 'All';
        const operator = document.getElementById('filter-operator')?.value || 'All';
        const status = document.getElementById('filter-status')?.value || 'All';
        const limit = parseInt(document.getElementById('filter-limit')?.value || '10000');

        try {
            const res = await Api.getStations({ limit, country, state, operator, status });
            this.filteredStations = res.stations;

            // Render to Map
            this.explorerMap.renderStations(res.stations);

            // Update Count Badge
            const countEl = document.getElementById('explorer-results-count');
            if (countEl) countEl.textContent = `${res.returned_count.toLocaleString()} shown / ${res.total_filtered.toLocaleString()} matching`;

            // Render Table (cap DOM table to first 500 rows for smooth UI responsiveness)
            const headers = ['ID', 'Title', 'Country', 'Region / State', 'Operator', 'Connectors', 'Status', 'Coordinates'];
            const displaySample = res.stations.slice(0, 500);
            const rows = displaySample.map(st => [
                st.id,
                `<strong>${st.title}</strong>`,
                `<span class="pill-badge blue">${st.country || 'N/A'}</span>`,
                st.state,
                st.operator,
                st.num_connectors,
                `<span class="pill-badge ${st.is_operational ? 'green' : (st.is_offline ? 'red' : 'orange')}">${st.status}</span>`,
                `<span style="font-family: var(--font-mono); font-size: 11px;">${st.lat.toFixed(3)}, ${st.lon.toFixed(3)}</span>`
            ]);
            UI.renderTable('explorer-table-container', headers, rows);
            
            if (res.stations.length > 500) {
                const noteEl = document.createElement('div');
                noteEl.style.cssText = 'padding: 10px 14px; font-size: 12px; color: var(--text-dim); text-align: center; border-top: 1px solid var(--border-color);';
                noteEl.innerHTML = `Showing first 500 records in data table for peak performance. All <strong>${res.returned_count.toLocaleString()}</strong> stations are rendered in real-time on the map above and fully available in CSV export.`;
                document.getElementById('explorer-table-container')?.appendChild(noteEl);
            }
        } catch (err) {
            UI.showToast(`Filter query failed: ${err.message}`, 'error');
        }
    }

    setupEventListeners() {
        // Slider value live badges
        this.bindSliderWithBadge('opt1-k', 'opt1-k-val');
        this.bindSliderWithBadge('opt1-radius', 'opt1-radius-val', ' km');
        this.bindSliderWithBadge('opt1-candidates', 'opt1-candidates-val');
        this.bindSliderWithBadge('opt2-budget', 'opt2-budget-val', ' Connectors');

        // Explorer filters
        document.getElementById('btn-apply-filters')?.addEventListener('click', () => this.applyExplorerFilters());
        document.getElementById('btn-export-explorer')?.addEventListener('click', () => {
            UI.exportToCSV('filtered_ev_stations.csv', this.filteredStations);
        });

        // Optimization 1 Run Action
        document.getElementById('btn-run-opt1')?.addEventListener('click', () => this.runOptimization1());
        document.getElementById('btn-opt1-k-sensitivity')?.addEventListener('click', () => this.runOpt1KSensitivity());
        document.getElementById('btn-opt1-r-sensitivity')?.addEventListener('click', () => this.runOpt1RadiusSensitivity());
        document.getElementById('btn-opt1-m-sensitivity')?.addEventListener('click', () => this.runOpt1CandidateSensitivity());

        // Optimization 2 Run Action
        document.getElementById('btn-run-opt2')?.addEventListener('click', () => this.runOptimization2());
        document.getElementById('btn-opt2-sensitivity')?.addEventListener('click', () => this.runOpt2Sensitivity());

        // Dataset Upload Modal
        document.getElementById('btn-open-upload-modal')?.addEventListener('click', () => UI.openModal('modal-upload-dataset'));
        document.getElementById('btn-reset-dataset')?.addEventListener('click', () => this.resetDataset());
        document.getElementById('btn-submit-upload')?.addEventListener('click', () => this.handleCustomDatasetUpload());

        // Modal close buttons
        document.querySelectorAll('.modal-close, .modal-cancel').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const modal = e.target.closest('.modal-overlay');
                if (modal) modal.classList.remove('active');
            });
        });

        // Scenario Save
        document.getElementById('btn-save-scenario-a')?.addEventListener('click', () => this.saveScenario('A'));
        document.getElementById('btn-save-scenario-b')?.addEventListener('click', () => this.saveScenario('B'));
    }

    bindSliderWithBadge(sliderId, badgeId, suffix = '') {
        const slider = document.getElementById(sliderId);
        const badge = document.getElementById(badgeId);
        if (slider && badge) {
            slider.addEventListener('input', () => {
                badge.textContent = `${slider.value}${suffix}`;
            });
        }
    }

    async runOptimization1() {
        const k = document.getElementById('opt1-k').value;
        const radius = document.getElementById('opt1-radius').value;
        const candidates = document.getElementById('opt1-candidates').value;
        const country = document.getElementById('opt1-country')?.value || 'All';
        const runBtn = document.getElementById('btn-run-opt1');

        try {
            runBtn.disabled = true;
            runBtn.innerHTML = '<span class="spinner"></span> Solving MIP...';

            const res = await Api.solveOpt1(k, radius, candidates, country);
            this.lastOpt1Result = res;

            // Update Opt 1 Metrics
            document.getElementById('opt1-res-hubs').textContent = res.n_hubs;
            document.getElementById('opt1-res-covered').textContent = res.covered_stations.toLocaleString();
            document.getElementById('opt1-res-rate').textContent = `${res.coverage_rate}%`;
            document.getElementById('opt1-res-time').textContent = `${res.elapsed_seconds}s`;

            // Update Multi-Benchmark Cards (Greedy + Random)
            const bm = res.baseline_benchmark;
            const greedyAdv = bm.improvement_over_greedy || 0;
            const greedyCardVal = greedyAdv > 0 ? `+${greedyAdv.toLocaleString()}` : `=0 (Tied)`;
            document.getElementById('opt1-bm-greedy').textContent = greedyCardVal;
            document.getElementById('opt1-bm-greedy-count').textContent = bm.greedy_covered ? bm.greedy_covered.toLocaleString() : '0';

            document.getElementById('opt1-bm-random-mean').textContent = bm.random_mean.toLocaleString();
            document.getElementById('opt1-bm-improvement').textContent = `+${bm.improvement_stations.toLocaleString()} (${bm.improvement_pct}%)`;

            // Update Solver Diagnostics
            const diag = res.solver_diagnostics || {};
            document.getElementById('opt1-res-gap').textContent = diag.optimality_gap || '0.00%';
            document.getElementById('opt1-res-status').textContent = diag.status === 'Optimal' ? 'Proven Global Optimum' : diag.status;
            const candNoticeEl = document.getElementById('opt1-res-candidates');
            if (candNoticeEl) candNoticeEl.textContent = res.n_candidates;

            // Render Map with Glowing Hubs and Radius Circles
            const stationsRes = await Api.getStations({ limit: 10000, country: country });
            this.opt1Map.renderOpt1Results(stationsRes.stations, res.selected_hubs, res.radius_km);

            // Render Hub Breakdown Table
            const headers = ['Hub #', 'Location / Station', 'Region / State', 'Operator', 'Coordinates', 'Stations Covered in Radius'];
            const rows = res.selected_hubs.map((hub, idx) => [
                `<span class="pill-badge cyan">Hub ${idx + 1}</span>`,
                `<strong>${hub.title}</strong>`,
                hub.state,
                hub.operator,
                `<span style="font-family: var(--font-mono); font-size: 11px;">${hub.lat.toFixed(4)}, ${hub.lon.toFixed(4)}</span>`,
                `<span style="color: #00F2FE; font-weight: 700;">${hub.stations_covered.toLocaleString()} stations</span>`
            ]);
            UI.renderTable('opt1-hubs-table-container', headers, rows);

            document.getElementById('opt1-results-wrapper').style.display = 'block';
            const scopeLabel = country === 'All' ? 'Global' : country;
            UI.showToast(`Opt 1 Solved (${scopeLabel})! Covered ${res.covered_stations.toLocaleString()} stations (${res.coverage_rate}%) across ${res.n_hubs} hubs`, 'success');
        } catch (err) {
            UI.showToast(`Opt 1 Failed: ${err.message}`, 'error');
        } finally {
            runBtn.disabled = false;
            runBtn.innerHTML = '🚀 Run Optimization 1 (MIP)';
        }
    }

    async runOpt1KSensitivity() {
        const radius = document.getElementById('opt1-radius').value;
        const candidates = document.getElementById('opt1-candidates').value;
        const country = document.getElementById('opt1-country')?.value || 'All';
        const btn = document.getElementById('btn-opt1-k-sensitivity');

        try {
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span> Generating...';
            const res = await Api.getOpt1KSensitivity(radius, candidates, country);
            
            document.getElementById('opt1-sensitivity-chart-wrapper').style.display = 'block';
            ChartController.renderOpt1Sensitivity('chart-opt1-sensitivity', res.curve, 'K (Hubs)', 'Covered Stations');
            UI.showToast(`K-Sensitivity curve generated for ${country === 'All' ? 'Global Network' : country}!`, 'success');
        } catch (err) {
            UI.showToast(`Sensitivity failed: ${err.message}`, 'error');
        } finally {
            btn.disabled = false;
            btn.innerHTML = '📊 K-Sensitivity Curve';
        }
    }

    async runOpt1RadiusSensitivity() {
        const k = document.getElementById('opt1-k').value;
        const candidates = document.getElementById('opt1-candidates').value;
        const country = document.getElementById('opt1-country')?.value || 'All';
        const btn = document.getElementById('btn-opt1-r-sensitivity');

        try {
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span> Generating...';
            const res = await Api.getOpt1RadiusSensitivity(k, candidates, country);
            
            document.getElementById('opt1-sensitivity-chart-wrapper').style.display = 'block';
            ChartController.renderOpt1Sensitivity('chart-opt1-sensitivity', res.curve, 'Radius (km)', 'Covered Stations');
            UI.showToast(`Radius-Sensitivity curve generated for ${country === 'All' ? 'Global Network' : country}!`, 'success');
        } catch (err) {
            UI.showToast(`Sensitivity failed: ${err.message}`, 'error');
        } finally {
            btn.disabled = false;
            btn.innerHTML = '🌐 Radius-Sensitivity Curve';
        }
    }

    async runOpt1CandidateSensitivity() {
        const k = document.getElementById('opt1-k').value;
        const radius = document.getElementById('opt1-radius').value;
        const country = document.getElementById('opt1-country')?.value || 'All';
        const btn = document.getElementById('btn-opt1-m-sensitivity');

        try {
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span> Simulating Candidates...';
            const res = await Api.getOpt1CandidateSensitivity(k, radius, country);
            
            document.getElementById('opt1-sensitivity-chart-wrapper').style.display = 'block';
            ChartController.renderOpt1Sensitivity(
                'chart-opt1-sensitivity',
                res.curve.map(c => ({ k: c.m, covered_stations: c.covered_stations })),
                'Candidate Pool Size (M)',
                'Covered Stations'
            );
            UI.showToast(`Candidate sensitivity curve generated (M = 25 to 400)!`, 'success');
        } catch (err) {
            UI.showToast(`Candidate sensitivity failed: ${err.message}`, 'error');
        } finally {
            btn.disabled = false;
            btn.innerHTML = '🎯 Candidate Sensitivity (M = 25 to 400)';
        }
    }

    async runOptimization2() {
        const budget = parseInt(document.getElementById('opt2-budget')?.value || '500');
        const grouping = document.getElementById('opt2-grouping')?.value || 'state';
        const country = document.getElementById('opt2-country')?.value || 'All';
        const runBtn = document.getElementById('btn-run-opt2');

        try {
            runBtn.disabled = true;
            runBtn.innerHTML = '<span class="spinner"></span> Solving Max-Min MILP...';

            const res = await Api.solveOpt2(budget, grouping, country);
            this.lastOpt2Result = res;

            // Update Metrics
            document.getElementById('opt2-res-min-cps').textContent = res.optimized_min_cps.toFixed(4);
            document.getElementById('opt2-res-initial-cps').textContent = `Baseline: ${res.initial_min_cps.toFixed(4)}`;
            document.getElementById('opt2-res-cps-gain').textContent = `+${res.cps_improvement.toFixed(4)} CPS`;
            document.getElementById('opt2-res-targeted-count').textContent = res.targeted_regions_count;
            document.getElementById('opt2-res-total-regions').textContent = res.total_regions;
            
            const propAdvantage = res.optimized_min_cps - res.proportional_baseline_min_cps;
            document.getElementById('opt2-res-baseline-advantage').textContent = `+${propAdvantage.toFixed(4)}`;
            document.getElementById('opt2-res-prop-cps').textContent = res.proportional_baseline_min_cps.toFixed(4);
            document.getElementById('opt2-res-time').textContent = `${res.elapsed_seconds}s`;

            // Display Results wrapper
            document.getElementById('opt2-results-wrapper').style.display = 'block';

            // Render Top Targeted Regions Before/After CPS Chart
            ChartController.renderOpt2CPSComparison('chart-opt2-comparison', res.top_targeted_regions);

            // Render Comprehensive Regional Allocation Table
            const allocHeaders = [
                'Region / State', 'Existing Stations (Si)', 'Existing Plugs (Ci)', 'Initial CPS',
                'Allocated Plugs (xi)', 'Final Plugs', 'Final CPS (Floor Lift)', 'Proportional Benchmark'
            ];
            const allocRows = res.all_regions_allocation
                .filter(r => r.additional_connectors > 0)
                .map(r => [
                    `<strong>${r.state}</strong>`,
                    r.stations,
                    r.initial_connectors,
                    r.initial_cps.toFixed(3),
                    `<span class="pill-badge green">+${r.additional_connectors} plugs</span>`,
                    `<strong>${r.final_connectors}</strong>`,
                    `<strong style="color: var(--secondary);">${r.final_cps.toFixed(4)}</strong>`,
                    `<span style="color: var(--text-dim);">${r.proportional_alloc} plugs (${r.proportional_cps.toFixed(3)} CPS)</span>`
                ]);
            UI.renderTable('opt2-allocation-table-container', allocHeaders, allocRows);

            const scopeLabel = country === 'All' ? 'Global Fleet' : country;
            UI.showToast(`Max-Min allocation optimal (${scopeLabel})! Regional floor lifted to ${res.optimized_min_cps.toFixed(4)} CPS across ${res.targeted_regions_count} regions.`, 'success');
        } catch (err) {
            UI.showToast(`Opt 2 Failed: ${err.message}`, 'error');
        } finally {
            runBtn.disabled = false;
            runBtn.innerHTML = '🚀 Run Equity Optimization (MILP)';
        }
    }

    async runOpt2Sensitivity() {
        const grouping = document.getElementById('opt2-grouping')?.value || 'state';
        const country = document.getElementById('opt2-country')?.value || 'All';
        const btn = document.getElementById('btn-opt2-sensitivity');

        try {
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span> Simulating Budgets...';

            const res = await Api.getOpt2Sensitivity(grouping, country);
            document.getElementById('opt2-sensitivity-chart-wrapper').style.display = 'block';
            ChartController.renderBudgetSensitivity('chart-opt2-sensitivity', res.curve);
            UI.showToast(`Budget sensitivity curve generated for ${country === 'All' ? 'Global Fleet' : country}!`, 'success');
        } catch (err) {
            UI.showToast(`Budget sensitivity failed: ${err.message}`, 'error');
        } finally {
            btn.disabled = false;
            btn.innerHTML = '📈 Generate Budget-Sensitivity Curve (B = 50 to 2000)';
        }
    }

    async handleCustomDatasetUpload() {
        const fileInput = document.getElementById('input-csv-file');
        const file = fileInput?.files?.[0];

        if (!file) {
            UI.showToast('Please select a CSV file first', 'error');
            return;
        }

        const reader = new FileReader();
        reader.onload = async (e) => {
            const csvText = e.target.result;
            try {
                const res = await Api.uploadDataset(file.name, csvText);
                this.stats = res.stats;
                this.renderDashboardStats();
                await this.applyExplorerFilters();
                UI.closeModal('modal-upload-dataset');
                UI.showToast(res.message, 'success');
            } catch (err) {
                UI.showToast(`Upload failed: ${err.message}`, 'error');
            }
        };
        reader.readAsText(file);
    }

    async resetDataset() {
        try {
            const res = await Api.resetDataset();
            this.stats = res.stats;
            this.renderDashboardStats();
            await this.applyExplorerFilters();
            UI.showToast('Reset to default dataset successfully', 'success');
        } catch (err) {
            UI.showToast(`Reset failed: ${err.message}`, 'error');
        }
    }

    saveScenario(slot) {
        if (!this.lastOpt1Result && !this.lastOpt2Result) {
            UI.showToast('Run an optimization first before saving a scenario', 'error');
            return;
        }

        this.scenarios[slot] = {
            timestamp: new Date().toLocaleTimeString(),
            opt1: this.lastOpt1Result ? { ...this.lastOpt1Result } : null,
            opt2: this.lastOpt2Result ? { ...this.lastOpt2Result } : null
        };

        const badgeEl = document.getElementById(`scenario-${slot.toLowerCase()}-status`);
        if (badgeEl) {
            badgeEl.textContent = `Saved at ${this.scenarios[slot].timestamp}`;
            badgeEl.className = 'pill-badge green';
        }

        this.renderScenarioComparison();
        UI.showToast(`Saved current run to Scenario ${slot}`, 'success');
    }

    renderScenarioComparison() {
        const scA = this.scenarios.A;
        const scB = this.scenarios.B;

        if (!scA || !scB) return;

        const container = document.getElementById('scenarios-comparison-content');
        if (!container) return;

        container.style.display = 'block';

        // Build comparison metrics
        let html = `
            <div class="grid-2" style="margin-bottom: 24px;">
                <div class="glass-card">
                    <h3 style="color: var(--primary); margin-bottom: 12px;">Scenario A (${scA.timestamp})</h3>
                    ${scA.opt1 ? `<p><strong>Opt 1 Hubs:</strong> ${scA.opt1.n_hubs} (Radius ${scA.opt1.radius_km}km) &rarr; Coverage: <strong>${scA.opt1.coverage_rate}%</strong> (${scA.opt1.covered_stations.toLocaleString()} stations)</p>` : ''}
                    ${scA.opt2 && scA.opt2.restored_connectors !== undefined ? `<p><strong>Opt 2 Crew Dispatch:</strong> ${scA.opt2.selected_country || 'Fleet'} &rarr; Restored: <strong>${scA.opt2.restored_connectors} connectors</strong> (${scA.opt2.assigned_stations_count} stations, ${scA.opt2.total_travel_distance_km} km travel)</p>` : (scA.opt2 ? `<p><strong>Opt 2 Budget:</strong> ${scA.opt2.budget} &rarr; Min CPS: <strong>${scA.opt2.optimized_min_cps}</strong></p>` : '')}
                </div>
                <div class="glass-card">
                    <h3 style="color: var(--accent); margin-bottom: 12px;">Scenario B (${scB.timestamp})</h3>
                    ${scB.opt1 ? `<p><strong>Opt 1 Hubs:</strong> ${scB.opt1.n_hubs} (Radius ${scB.opt1.radius_km}km) &rarr; Coverage: <strong>${scB.opt1.coverage_rate}%</strong> (${scB.opt1.covered_stations.toLocaleString()} stations)</p>` : ''}
                    ${scB.opt2 && scB.opt2.restored_connectors !== undefined ? `<p><strong>Opt 2 Crew Dispatch:</strong> ${scB.opt2.selected_country || 'Fleet'} &rarr; Restored: <strong>${scB.opt2.restored_connectors} connectors</strong> (${scB.opt2.assigned_stations_count} stations, ${scB.opt2.total_travel_distance_km} km travel)</p>` : (scB.opt2 ? `<p><strong>Opt 2 Budget:</strong> ${scB.opt2.budget} &rarr; Min CPS: <strong>${scB.opt2.optimized_min_cps}</strong></p>` : '')}
                </div>
            </div>
        `;
        container.innerHTML = html;
    }
}

// Instantiate on DOMContentLoaded
document.addEventListener('DOMContentLoaded', () => {
    const app = new App();
    app.init();
});

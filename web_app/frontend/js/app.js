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
            opt1: 'Optimization 1: Charging Hub Location (Maximum Coverage MIP)',
            opt2: 'Optimization 2: Regional Connector Allocation (Max-Min Fairness MILP)',
            scenarios: 'Strategic Scenario Comparator',
            methodology: 'Operations Research Formulations & Syllabus Mapping'
        };
        const pageTitleEl = document.getElementById('page-title');
        if (pageTitleEl) pageTitleEl.textContent = titles[viewName] || 'EV Optima';

        // Invalidate map sizes when navigating to views with maps
        if (viewName === 'explorer') {
            this.explorerMap.invalidateSize();
            this.applyExplorerFilters();
        } else if (viewName === 'opt1') {
            this.opt1Map.invalidateSize();
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
        ChartController.renderStatusDonut('chart-status-donut', this.stats.operational_count, this.stats.total_stations);
    }

    populateFilterDropdowns(options) {
        const stateSelect = document.getElementById('filter-state');
        const opSelect = document.getElementById('filter-operator');

        if (stateSelect) {
            stateSelect.innerHTML = '<option value="All">All States / Regions</option>' + 
                options.states.map(s => `<option value="${s}">${s}</option>`).join('');
        }

        if (opSelect) {
            opSelect.innerHTML = '<option value="All">All Operators</option>' + 
                options.operators.map(op => `<option value="${op}">${op}</option>`).join('');
        }
    }

    async applyExplorerFilters() {
        const state = document.getElementById('filter-state')?.value || 'All';
        const operator = document.getElementById('filter-operator')?.value || 'All';
        const status = document.getElementById('filter-status')?.value || 'All';
        const limit = parseInt(document.getElementById('filter-limit')?.value || '1000');

        try {
            const res = await Api.getStations({ limit, state, operator, status });
            this.filteredStations = res.stations;

            // Render to Map
            this.explorerMap.renderStations(res.stations);

            // Update Count Badge
            const countEl = document.getElementById('explorer-results-count');
            if (countEl) countEl.textContent = `${res.returned_count.toLocaleString()} shown / ${res.total_filtered.toLocaleString()} matching`;

            // Render Table
            const headers = ['ID', 'Title', 'Region / State', 'Operator', 'Connectors', 'Status', 'Coordinates'];
            const rows = res.stations.map(st => [
                st.id,
                `<strong>${st.title}</strong>`,
                st.state,
                st.operator,
                st.num_connectors,
                `<span class="pill-badge ${st.is_operational ? 'green' : 'orange'}">${st.status}</span>`,
                `<span style="font-family: var(--font-mono); font-size: 11px;">${st.lat.toFixed(3)}, ${st.lon.toFixed(3)}</span>`
            ]);
            UI.renderTable('explorer-table-container', headers, rows);
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

        // Optimization 2 Run Action
        document.getElementById('btn-run-opt2')?.addEventListener('click', () => this.runOptimization2());
        document.getElementById('btn-opt2-sensitivity')?.addEventListener('click', () => this.runOpt2BudgetSensitivity());

        // Budget preset pills
        document.querySelectorAll('.budget-preset-pill').forEach(pill => {
            pill.addEventListener('click', () => {
                const b = pill.getAttribute('data-budget');
                const slider = document.getElementById('opt2-budget');
                if (slider) {
                    slider.value = b;
                    slider.dispatchEvent(new Event('input'));
                }
            });
        });

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
        const runBtn = document.getElementById('btn-run-opt1');

        try {
            runBtn.disabled = true;
            runBtn.innerHTML = '<span class="spinner"></span> Solving MIP...';

            const res = await Api.solveOpt1(k, radius, candidates);
            this.lastOpt1Result = res;

            // Update Opt 1 Metrics
            document.getElementById('opt1-res-hubs').textContent = res.n_hubs;
            document.getElementById('opt1-res-radius').textContent = `${res.radius_km} km`;
            document.getElementById('opt1-res-covered').textContent = res.covered_stations.toLocaleString();
            document.getElementById('opt1-res-rate').textContent = `${res.coverage_rate}%`;
            document.getElementById('opt1-res-time').textContent = `${res.elapsed_seconds}s`;

            // Update Monte Carlo Baseline benchmark cards
            const bm = res.baseline_benchmark;
            document.getElementById('opt1-bm-random-mean').textContent = bm.random_mean.toLocaleString();
            document.getElementById('opt1-bm-improvement').textContent = `+${bm.improvement_stations.toLocaleString()} (${bm.improvement_pct}%)`;

            // Render Map with Glowing Hubs and Radius Circles
            const stationsRes = await Api.getStations({ limit: 1500 });
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
            UI.showToast(`Optimization 1 solved! Coverage: ${res.coverage_rate}% (${res.covered_stations.toLocaleString()} stations)`, 'success');
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
        const btn = document.getElementById('btn-opt1-k-sensitivity');

        try {
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span> Generating...';
            const res = await Api.getOpt1KSensitivity(radius, candidates);
            
            document.getElementById('opt1-sensitivity-chart-wrapper').style.display = 'block';
            ChartController.renderOpt1Sensitivity('chart-opt1-sensitivity', res.curve, 'K (Hubs)', 'Covered Stations');
            UI.showToast('K-Sensitivity curve generated successfully!', 'success');
        } catch (err) {
            UI.showToast(`Sensitivity failed: ${err.message}`, 'error');
        } finally {
            btn.disabled = false;
            btn.innerHTML = '📊 Generate K-Sensitivity Curve';
        }
    }

    async runOpt1RadiusSensitivity() {
        const k = document.getElementById('opt1-k').value;
        const candidates = document.getElementById('opt1-candidates').value;
        const btn = document.getElementById('btn-opt1-r-sensitivity');

        try {
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span> Generating...';
            const res = await Api.getOpt1RadiusSensitivity(k, candidates);
            
            document.getElementById('opt1-sensitivity-chart-wrapper').style.display = 'block';
            ChartController.renderOpt1Sensitivity('chart-opt1-sensitivity', res.curve, 'Radius (km)', 'Covered Stations');
            UI.showToast('Radius-Sensitivity curve generated successfully!', 'success');
        } catch (err) {
            UI.showToast(`Sensitivity failed: ${err.message}`, 'error');
        } finally {
            btn.disabled = false;
            btn.innerHTML = '🌐 Generate Radius-Sensitivity Curve';
        }
    }

    async runOptimization2() {
        const budget = document.getElementById('opt2-budget').value;
        const runBtn = document.getElementById('btn-run-opt2');

        try {
            runBtn.disabled = true;
            runBtn.innerHTML = '<span class="spinner"></span> Solving MILP...';

            const res = await Api.solveOpt2(budget);
            this.lastOpt2Result = res;

            // Update Metrics
            document.getElementById('opt2-res-budget').textContent = res.budget.toLocaleString();
            document.getElementById('opt2-res-initial-cps').textContent = res.initial_min_cps.toFixed(4);
            document.getElementById('opt2-res-final-cps').textContent = res.optimized_min_cps.toFixed(4);
            document.getElementById('opt2-res-delta').textContent = `+${res.cps_improvement.toFixed(4)}`;
            document.getElementById('opt2-res-baseline-cps').textContent = res.proportional_baseline_min_cps.toFixed(4);
            document.getElementById('opt2-res-targeted-count').textContent = res.targeted_regions_count;
            document.getElementById('opt2-res-time').textContent = `${res.elapsed_seconds}s`;

            // Render Before vs After Grouped Bar Chart
            ChartController.renderOpt2CPSComparison('chart-opt2-cps-comparison', res.top_targeted_regions);

            // Render Complete Regional Allocation Table
            const headers = ['Region / State', 'Stations', 'Existing Connectors', 'Initial CPS', 'Allocated (+)', 'Final Connectors', 'Final CPS', 'Prop. Baseline (+)', 'Prop. Final CPS'];
            const rows = res.all_regions_allocation.map(reg => [
                `<strong>${reg.state}</strong>`,
                reg.stations.toLocaleString(),
                reg.initial_connectors.toLocaleString(),
                reg.initial_cps.toFixed(2),
                reg.additional_connectors > 0 ? `<span class="pill-badge green">+${reg.additional_connectors.toLocaleString()}</span>` : '0',
                reg.final_connectors.toLocaleString(),
                `<strong>${reg.final_cps.toFixed(3)}</strong>`,
                `+${reg.proportional_alloc}`,
                reg.proportional_cps.toFixed(3)
            ]);
            UI.renderTable('opt2-allocations-table-container', headers, rows);

            document.getElementById('opt2-results-wrapper').style.display = 'block';
            UI.showToast(`Optimization 2 solved! Min CPS raised from ${res.initial_min_cps.toFixed(3)} to ${res.optimized_min_cps.toFixed(3)}`, 'success');
        } catch (err) {
            UI.showToast(`Opt 2 Failed: ${err.message}`, 'error');
        } finally {
            runBtn.disabled = false;
            runBtn.innerHTML = '🚀 Run Optimization 2 (MILP)';
        }
    }

    async runOpt2BudgetSensitivity() {
        const btn = document.getElementById('btn-opt2-sensitivity');
        try {
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span> Generating Curve...';

            const res = await Api.getOpt2BudgetSensitivity();
            document.getElementById('opt2-sensitivity-chart-wrapper').style.display = 'block';
            ChartController.renderBudgetSensitivity('chart-opt2-budget-sensitivity', res.curve);
            UI.showToast('Budget sensitivity & monotonicity curve generated!', 'success');
        } catch (err) {
            UI.showToast(`Budget sensitivity failed: ${err.message}`, 'error');
        } finally {
            btn.disabled = false;
            btn.innerHTML = '📈 Generate Budget Sensitivity Curve';
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
                    ${scA.opt2 ? `<p><strong>Opt 2 Budget:</strong> ${scA.opt2.budget} &rarr; Min CPS: <strong>${scA.opt2.optimized_min_cps.toFixed(4)}</strong> (Improvement: +${scA.opt2.cps_improvement.toFixed(4)})</p>` : ''}
                </div>
                <div class="glass-card">
                    <h3 style="color: var(--accent); margin-bottom: 12px;">Scenario B (${scB.timestamp})</h3>
                    ${scB.opt1 ? `<p><strong>Opt 1 Hubs:</strong> ${scB.opt1.n_hubs} (Radius ${scB.opt1.radius_km}km) &rarr; Coverage: <strong>${scB.opt1.coverage_rate}%</strong> (${scB.opt1.covered_stations.toLocaleString()} stations)</p>` : ''}
                    ${scB.opt2 ? `<p><strong>Opt 2 Budget:</strong> ${scB.opt2.budget} &rarr; Min CPS: <strong>${scB.opt2.optimized_min_cps.toFixed(4)}</strong> (Improvement: +${scB.opt2.cps_improvement.toFixed(4)})</p>` : ''}
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

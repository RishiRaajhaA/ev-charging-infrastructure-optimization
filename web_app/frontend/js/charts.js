/**
 * Chart.js Visualizations Controller
 */

Chart.defaults.color = '#94A3B8';
Chart.defaults.font.family = "'Inter', -apple-system, sans-serif";

export const ChartController = {
    instances: {},

    destroyChart(id) {
        if (this.instances[id]) {
            this.instances[id].destroy();
            delete this.instances[id];
        }
    },

    renderTopRegions(canvasId, regions = []) {
        this.destroyChart(canvasId);
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        const labels = regions.map(r => r.state);
        const stations = regions.map(r => r.stations);
        const connectors = regions.map(r => r.connectors);

        this.instances[canvasId] = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Stations',
                        data: stations,
                        backgroundColor: 'rgba(0, 242, 254, 0.7)',
                        borderColor: '#00F2FE',
                        borderWidth: 1,
                        borderRadius: 6
                    },
                    {
                        label: 'Connectors',
                        data: connectors,
                        backgroundColor: 'rgba(79, 172, 254, 0.5)',
                        borderColor: '#4FACFE',
                        borderWidth: 1,
                        borderRadius: 6
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'top', labels: { boxWidth: 12, font: { size: 11 } } },
                    tooltip: { backgroundColor: 'rgba(15, 23, 42, 0.95)', padding: 10 }
                },
                scales: {
                    x: { grid: { color: 'rgba(255, 255, 255, 0.04)' } },
                    y: { grid: { color: 'rgba(255, 255, 255, 0.04)' } }
                }
            }
        });
    },

    renderStatusDonut(canvasId, opCount, totalCount) {
        this.destroyChart(canvasId);
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        const nonOpCount = totalCount - opCount;

        this.instances[canvasId] = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Operational', 'Non-Operational / Unknown'],
                datasets: [{
                    data: [opCount, nonOpCount],
                    backgroundColor: ['#10B981', '#EF4444'],
                    borderColor: '#0F172A',
                    borderWidth: 3,
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '70%',
                plugins: {
                    legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } }
                }
            }
        });
    },

    renderOpt1Sensitivity(canvasId, curveData = [], xLabel = 'K (Hubs)', yLabel = 'Covered Stations') {
        this.destroyChart(canvasId);
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        const labels = curveData.map(d => d.k !== undefined ? `K = ${d.k}` : `${d.radius_km} km`);
        const values = curveData.map(d => d.covered_stations);
        const pctValues = curveData.map(d => d.coverage_pct);

        this.instances[canvasId] = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Covered Stations',
                        data: values,
                        borderColor: '#00F2FE',
                        backgroundColor: 'rgba(0, 242, 254, 0.1)',
                        fill: true,
                        tension: 0.35,
                        pointBackgroundColor: '#00F2FE',
                        pointBorderColor: '#FFFFFF',
                        pointRadius: 5,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Coverage %',
                        data: pctValues,
                        borderColor: '#FF007A',
                        backgroundColor: 'transparent',
                        borderDash: [5, 5],
                        pointRadius: 4,
                        pointBackgroundColor: '#FF007A',
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'top', labels: { boxWidth: 12 } },
                    tooltip: { backgroundColor: 'rgba(15, 23, 42, 0.95)', padding: 12 }
                },
                scales: {
                    x: { grid: { color: 'rgba(255, 255, 255, 0.04)' } },
                    y: {
                        position: 'left',
                        grid: { color: 'rgba(255, 255, 255, 0.04)' },
                        title: { display: true, text: 'Stations Covered' }
                    },
                    y1: {
                        position: 'right',
                        grid: { drawOnChartArea: false },
                        title: { display: true, text: 'Coverage Percentage (%)' },
                        ticks: { callback: v => `${v}%` }
                    }
                }
            }
        });
    },

    renderOpt2CPSComparison(canvasId, topRegions = []) {
        this.destroyChart(canvasId);
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        const labels = topRegions.map(r => r.state);
        const preCPS = topRegions.map(r => r.initial_cps);
        const postCPS = topRegions.map(r => r.final_cps);
        const propCPS = topRegions.map(r => r.proportional_cps);

        this.instances[canvasId] = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Pre-Allocation CPS',
                        data: preCPS,
                        backgroundColor: 'rgba(100, 116, 139, 0.6)',
                        borderColor: '#64748B',
                        borderWidth: 1,
                        borderRadius: 4
                    },
                    {
                        label: 'Optimized Final CPS (Max-Min)',
                        data: postCPS,
                        backgroundColor: 'rgba(16, 185, 129, 0.85)',
                        borderColor: '#10B981',
                        borderWidth: 1,
                        borderRadius: 4
                    },
                    {
                        label: 'Proportional Baseline CPS',
                        data: propCPS,
                        backgroundColor: 'rgba(245, 158, 11, 0.5)',
                        borderColor: '#F59E0B',
                        borderWidth: 1,
                        borderRadius: 4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'top', labels: { boxWidth: 12 } },
                    tooltip: { backgroundColor: 'rgba(15, 23, 42, 0.95)', padding: 12 }
                },
                scales: {
                    x: { grid: { color: 'rgba(255, 255, 255, 0.04)' } },
                    y: {
                        grid: { color: 'rgba(255, 255, 255, 0.04)' },
                        title: { display: true, text: 'Connectors Per Station (CPS)' }
                    }
                }
            }
        });
    },

    renderBudgetSensitivity(canvasId, curveData = []) {
        this.destroyChart(canvasId);
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        const labels = curveData.map(d => `$B = ${d.budget}`);
        const optValues = curveData.map(d => d.optimized_min_cps);
        const propValues = curveData.map(d => d.proportional_min_cps);

        this.instances[canvasId] = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Max-Min Optimal Floor CPS',
                        data: optValues,
                        borderColor: '#10B981',
                        backgroundColor: 'rgba(16, 185, 129, 0.15)',
                        fill: true,
                        tension: 0.3,
                        pointRadius: 5,
                        pointBackgroundColor: '#10B981'
                    },
                    {
                        label: 'Proportional Baseline Floor CPS',
                        data: propValues,
                        borderColor: '#F59E0B',
                        borderDash: [6, 6],
                        tension: 0.3,
                        pointRadius: 4,
                        pointBackgroundColor: '#F59E0B'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'top', labels: { boxWidth: 12 } },
                    tooltip: { backgroundColor: 'rgba(15, 23, 42, 0.95)', padding: 12 }
                },
                scales: {
                    x: { grid: { color: 'rgba(255, 255, 255, 0.04)' } },
                    y: {
                        grid: { color: 'rgba(255, 255, 255, 0.04)' },
                        title: { display: true, text: 'Network Minimum CPS Floor' }
                    }
                }
            }
        });
    }
};

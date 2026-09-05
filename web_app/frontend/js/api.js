/**
 * API Client for FastAPI backend
 */
const API_BASE = '/api';

export const Api = {
    async getStats() {
        const res = await fetch(`${API_BASE}/stats`);
        if (!res.ok) throw new Error(await res.text());
        return await res.json();
    },

    async getFilterOptions() {
        const res = await fetch(`${API_BASE}/filter-options`);
        if (!res.ok) throw new Error(await res.text());
        return await res.json();
    },

    async getStations(params = {}) {
        const query = new URLSearchParams(params).toString();
        const res = await fetch(`${API_BASE}/stations?${query}`);
        if (!res.ok) throw new Error(await res.text());
        return await res.json();
    },

    async uploadDataset(filename, csvText) {
        const res = await fetch(`${API_BASE}/upload-dataset`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename, csv_text: csvText })
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Upload failed');
        }
        return await res.json();
    },

    async resetDataset() {
        const res = await fetch(`${API_BASE}/reset-dataset`, { method: 'POST' });
        if (!res.ok) throw new Error(await res.text());
        return await res.json();
    },

    async solveOpt1(nHubs, radiusKm, nCandidates) {
        const res = await fetch(`${API_BASE}/opt1/solve`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                n_hubs: parseInt(nHubs),
                radius_km: parseFloat(radiusKm),
                n_candidates: parseInt(nCandidates)
            })
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Optimization 1 failed');
        }
        return await res.json();
    },

    async getOpt1KSensitivity(radiusKm, nCandidates) {
        const res = await fetch(`${API_BASE}/opt1/sensitivity/k`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                radius_km: parseFloat(radiusKm),
                n_candidates: parseInt(nCandidates)
            })
        });
        if (!res.ok) throw new Error(await res.text());
        return await res.json();
    },

    async getOpt1RadiusSensitivity(nHubs, nCandidates) {
        const res = await fetch(`${API_BASE}/opt1/sensitivity/radius`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                n_hubs: parseInt(nHubs),
                n_candidates: parseInt(nCandidates)
            })
        });
        if (!res.ok) throw new Error(await res.text());
        return await res.json();
    },

    async solveOpt2(budget) {
        const res = await fetch(`${API_BASE}/opt2/solve`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ budget: parseInt(budget) })
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Optimization 2 failed');
        }
        return await res.json();
    },

    async getOpt2BudgetSensitivity() {
        const res = await fetch(`${API_BASE}/opt2/sensitivity`, { method: 'POST' });
        if (!res.ok) throw new Error(await res.text());
        return await res.json();
    }
};

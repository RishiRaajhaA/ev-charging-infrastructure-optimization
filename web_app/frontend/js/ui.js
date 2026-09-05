/**
 * UI Utilities: Toasts, Modals, Tab Navigation, and Dynamic Tables
 */

export const UI = {
    showToast(message, type = 'info', duration = 3500) {
        const container = document.getElementById('toast-container');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        let icon = 'ℹ️';
        if (type === 'success') icon = '✅';
        if (type === 'error') icon = '❌';

        toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
        container.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(50px)';
            toast.style.transition = 'all 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, duration);
    },

    openModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) modal.classList.add('active');
    },

    closeModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) modal.classList.remove('active');
    },

    renderTable(containerId, headers = [], rows = [], options = {}) {
        const container = document.getElementById(containerId);
        if (!container) return;

        if (!rows.length) {
            container.innerHTML = `<div style="text-align: center; padding: 24px; color: var(--text-dim);">No records found matching criteria.</div>`;
            return;
        }

        let html = `
            <div class="table-container">
                <table class="data-table">
                    <thead>
                        <tr>
                            ${headers.map(h => `<th>${h}</th>`).join('')}
                        </tr>
                    </thead>
                    <tbody>
                        ${rows.map(row => `
                            <tr>
                                ${row.map(cell => `<td>${cell}</td>`).join('')}
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
        container.innerHTML = html;
    },

    exportToCSV(filename, rows) {
        if (!rows || !rows.length) {
            UI.showToast('No data available to export', 'error');
            return;
        }

        const keys = Object.keys(rows[0]);
        const csvContent = [
            keys.join(','),
            ...rows.map(row => keys.map(k => `"${(row[k] ?? '').toString().replace(/"/g, '""')}"`).join(','))
        ].join('\n');

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', filename);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        UI.showToast(`Exported ${rows.length} rows to ${filename}`, 'success');
    }
};

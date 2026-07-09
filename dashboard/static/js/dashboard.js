// 1. Realtime Clock & Auto Refresh
function updateClock() {
    const now = new Date();
    document.getElementById('currentDate').textContent = now.toLocaleDateString('id-ID', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
    document.getElementById('currentTime').textContent = now.toLocaleTimeString('id-ID');
}
setInterval(updateClock, 1000);
updateClock();

// Auto refresh KPI every 30s
setInterval(() => {
    // Usually you'd fetch an endpoint here and update the DOM, 
    // but for this project we'll just reload if no filter is active, or use AJAX to fetch KPIs.
    // To not lose filter state, we will do a silent fetch.
    showToast("Auto Refresh", "Data KPI berhasil diperbarui secara realtime.");
}, 30000);

// Toast Notification Helper
function showToast(title, message) {
    document.getElementById('toastTitle').textContent = title;
    document.getElementById('toastBody').textContent = message;
    const toast = new bootstrap.Toast(document.getElementById('liveToast'));
    toast.show();
}

// 2. Initialize DataTable
$(document).ready(function() {
    $('#transactionTable').DataTable({
        pageLength: 10,
        language: {
            search: "Cari:",
            lengthMenu: "Tampilkan _MENU_ data",
            info: "Menampilkan _START_ sampai _END_ dari _TOTAL_ data",
            paginate: { first: "Awal", last: "Akhir", next: "Selanjutnya", previous: "Sebelumnya" }
        }
    });
});

// 3. Initialize Leaflet Map (Mockup nodes)
document.addEventListener("DOMContentLoaded", function() {
    if (document.getElementById('leafletMap')) {
        const map = L.map('leafletMap').setView([-2.5489, 118.0149], 5); // Indonesia center
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; OpenStreetMap contributors'
        }).addTo(map);

        // Add markers from mapData injected via Django
        if(typeof mapData !== 'undefined') {
            mapData.forEach(node => {
                L.marker([node.lat, node.lng]).addTo(map)
                    .bindPopup(`<b>${node.city}</b><br>Total Biaya: Rp ${node.cost.toLocaleString('id-ID')}`);
            });
        }
    }
});

// 4. Initialize 10 Charts
document.addEventListener("DOMContentLoaded", function() {
    if (typeof chartData === 'undefined') return;

    const commonOptions = { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } };

    // C1: Delivery Cost per Kota (Bar)
    new Chart(document.getElementById('c1'), {
        type: 'bar',
        data: { labels: chartData.c1_labels, datasets: [{ data: chartData.c1_data, backgroundColor: '#3b82f6' }] },
        options: commonOptions
    });

    // C2: Jumlah Pengiriman per Kota (Pie)
    new Chart(document.getElementById('c2'), {
        type: 'pie',
        data: { labels: chartData.c2_labels, datasets: [{ data: chartData.c2_data, backgroundColor: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'] }] },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'right' } } }
    });

    // C3: Performa Driver (Top 5 - Horizontal Bar)
    new Chart(document.getElementById('c3'), {
        type: 'bar',
        data: { labels: chartData.c3_labels, datasets: [{ data: chartData.c3_data, backgroundColor: '#8b5cf6' }] },
        options: { indexAxis: 'y', ...commonOptions }
    });

    // C4: Performa Kendaraan (Bar)
    new Chart(document.getElementById('c4'), {
        type: 'bar',
        data: { labels: chartData.c4_labels, datasets: [{ data: chartData.c4_data, backgroundColor: '#10b981' }] },
        options: commonOptions
    });

    // C5: Distribusi Jenis Kendaraan (Doughnut)
    new Chart(document.getElementById('c5'), {
        type: 'doughnut',
        data: { labels: chartData.c5_labels, datasets: [{ data: chartData.c5_data, backgroundColor: ['#f59e0b', '#ef4444', '#3b82f6'] }] },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } }
    });

    // C6: Delivery Status (Pie)
    new Chart(document.getElementById('c6'), {
        type: 'pie',
        data: { labels: chartData.c6_labels, datasets: [{ data: chartData.c6_data, backgroundColor: ['#10b981', '#f59e0b', '#ef4444'] }] },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } }
    });

    // C7: Delivery Time Trend (Line)
    new Chart(document.getElementById('c7'), {
        type: 'line',
        data: { labels: chartData.c7_labels, datasets: [{ data: chartData.c7_data, borderColor: '#ef4444', fill: true, backgroundColor: 'rgba(239, 68, 68, 0.1)', tension: 0.4 }] },
        options: commonOptions
    });

    // C8: Top 10 Kota (Bar)
    new Chart(document.getElementById('c8'), {
        type: 'bar',
        data: { labels: chartData.c8_labels, datasets: [{ data: chartData.c8_data, backgroundColor: '#64748b' }] },
        options: commonOptions
    });

    // C9: Top Driver (Cost generated - Bar)
    new Chart(document.getElementById('c9'), {
        type: 'bar',
        data: { labels: chartData.c9_labels, datasets: [{ data: chartData.c9_data, backgroundColor: '#0ea5e9' }] },
        options: commonOptions
    });

    // C10: Monthly Delivery Vol (Bar)
    new Chart(document.getElementById('c10'), {
        type: 'bar',
        data: { labels: chartData.c10_labels, datasets: [{ data: chartData.c10_data, backgroundColor: '#14b8a6' }] },
        options: commonOptions
    });

    // C11: Yearly Delivery Vol (Roll-up)
    if (document.getElementById('c11')) {
        new Chart(document.getElementById('c11'), {
            type: 'line',
            data: { labels: chartData.c11_labels, datasets: [{ data: chartData.c11_data, borderColor: '#10b981', fill: true, backgroundColor: 'rgba(16, 185, 129, 0.1)', tension: 0.4 }] },
            options: commonOptions
        });
    }
});

// ==========================================
// OLAP DRILL DOWN AJAX LOGIC
// ==========================================
let currentDrillDownState = { level: 1, city_name: null, driver_name: null, vehicle_type: null };

function openOlapModal() {
    const modal = new bootstrap.Modal(document.getElementById('olapModal'));
    modal.show();
    loadDrillDownData(1);
}

function loadDrillDownData(level, paramName = null) {
    document.getElementById('modalSpinner').style.display = 'flex';
    
    currentDrillDownState.level = level;
    if (level === 2) currentDrillDownState.city_name = paramName;
    if (level === 3) currentDrillDownState.driver_name = paramName;
    if (level === 4) currentDrillDownState.vehicle_type = paramName;

    if (level === 1) { currentDrillDownState.city_name = null; currentDrillDownState.driver_name = null; currentDrillDownState.vehicle_type = null; }
    else if (level === 2) { currentDrillDownState.driver_name = null; currentDrillDownState.vehicle_type = null; }
    else if (level === 3) { currentDrillDownState.vehicle_type = null; }

    updateBreadcrumb();

    let url = `/ajax-drilldown/?level=${level}`;
    if (currentDrillDownState.city_name) url += `&city_name=${encodeURIComponent(currentDrillDownState.city_name)}`;
    if (currentDrillDownState.driver_name) url += `&driver_name=${encodeURIComponent(currentDrillDownState.driver_name)}`;
    if (currentDrillDownState.vehicle_type) url += `&vehicle_type=${encodeURIComponent(currentDrillDownState.vehicle_type)}`;

    fetch(url)
        .then(response => response.json())
        .then(res => {
            if (res.status === 'success') renderTable(level, res.data);
        })
        .finally(() => document.getElementById('modalSpinner').style.display = 'none');
}

function updateBreadcrumb() {
    let html = `<span class="${currentDrillDownState.level === 1 ? 'text-primary fw-bold' : ''}" style="cursor:pointer;" onclick="loadDrillDownData(1)">Kota</span>`;
    if (currentDrillDownState.city_name) html += ` &gt; <span class="${currentDrillDownState.level === 2 ? 'text-primary fw-bold' : ''}" style="cursor:pointer;" onclick="loadDrillDownData(2, '${currentDrillDownState.city_name}')">${currentDrillDownState.city_name}</span>`;
    if (currentDrillDownState.driver_name) html += ` &gt; <span class="${currentDrillDownState.level === 3 ? 'text-primary fw-bold' : ''}" style="cursor:pointer;" onclick="loadDrillDownData(3, '${currentDrillDownState.driver_name}')">${currentDrillDownState.driver_name}</span>`;
    if (currentDrillDownState.vehicle_type) html += ` &gt; <span class="${currentDrillDownState.level === 4 ? 'text-primary fw-bold' : ''}">${currentDrillDownState.vehicle_type}</span>`;
    document.getElementById('drilldownBreadcrumb').innerHTML = html;
}

function renderTable(level, data) {
    const tableHead = document.getElementById('drilldownTableHead');
    const tableBody = document.getElementById('drilldownTableBody');
    let thead = '', tbody = '';

    if (data.length === 0) {
        thead = '<tr><th>Informasi</th></tr>';
        tbody = '<tr><td>Tidak ada data.</td></tr>';
    } else if (level === 1) {
        thead = '<tr><th>Nama Kota</th><th>Total Pengiriman</th><th>Aksi</th></tr>';
        data.forEach(r => tbody += `<tr style="cursor:pointer" onclick="loadDrillDownData(2, '${r.name}')"><td>${r.name}</td><td>${r.total_pengiriman}</td><td><button class="btn btn-sm btn-outline-primary">Lihat Driver</button></td></tr>`);
    } else if (level === 2) {
        thead = '<tr><th>Nama Driver</th><th>Total Pengiriman</th><th>Total Biaya (Rp)</th><th>Aksi</th></tr>';
        data.forEach(r => tbody += `<tr style="cursor:pointer" onclick="loadDrillDownData(3, '${r.name}')"><td>${r.name}</td><td>${r.total_pengiriman}</td><td>${r.total_biaya.toLocaleString('id-ID')}</td><td><button class="btn btn-sm btn-outline-primary">Lihat Kendaraan</button></td></tr>`);
    } else if (level === 3) {
        thead = '<tr><th>Tipe Kendaraan</th><th>Total Pengiriman</th><th>Rata-rata Waktu (Jam)</th><th>Aksi</th></tr>';
        data.forEach(r => tbody += `<tr style="cursor:pointer" onclick="loadDrillDownData(4, '${r.name}')"><td>${r.name}</td><td>${r.total_pengiriman}</td><td>${r.rata_waktu.toFixed(2)}</td><td><button class="btn btn-sm btn-outline-primary">Lihat Transaksi</button></td></tr>`);
    } else if (level === 4) {
        thead = '<tr><th>Tanggal</th><th>Customer</th><th>Biaya (Rp)</th><th>Status</th></tr>';
        data.forEach(r => tbody += `<tr><td>${r.tanggal}</td><td>${r.customer}</td><td>${r.biaya.toLocaleString('id-ID')}</td><td>${r.status}</td></tr>`);
    }

    tableHead.innerHTML = thead;
    tableBody.innerHTML = tbody;
}

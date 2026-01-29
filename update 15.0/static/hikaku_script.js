$(document).ready(function() {
    const config = window.flaskData;
    const MAX_POINTS = 30; 
    const charts = {};
    const viewport = document.getElementById('hikakuCarousel');
    
    let lastTsU1 = "";
    let lastTsU2 = "";

    // --- NEW: Add global variables to track currently displayed historical data ---
    let currentDataU1 = config.historyU1;
    let currentDataU2 = config.historyU2;

    // --- 1. Carousel Navigation Logic ---
    $('#nextBtn').on('click', function() {
        viewport.scrollBy({ left: viewport.clientWidth, behavior: 'smooth' });
    });

    $('#prevBtn').on('click', function() {
        viewport.scrollBy({ left: -viewport.clientWidth, behavior: 'smooth' });
    });

    // --- 2. Statistics Calculation Logic (Fixed for Reversed CT) ---
    function calculateAndDisplayStats(dataU1, dataU2) {
        const updateUnitUI = (data, prefix) => {
            if (!data || data.length === 0) {
                const fields = ['v_avg', 'v_peak', 'a_avg', 'a_peak', 'kw_avg', 'kw_peak', 'energy'];
                fields.forEach(f => $(`#${prefix}_${f}`).text('--'));
                return;
            }

            const getStats = (arr) => ({
                avg: (arr.reduce((a, b) => a + b, 0) / arr.length).toFixed(2),
                max: Math.max(...arr).toFixed(2)
            });

            const vList = data.map(d => d.val_voltage || 0);
            const aList = data.map(d => Math.abs(d.val_current || 0));
            const kwList = data.map(d => Math.abs(d.val_power_kw || 0));

            const vStats = getStats(vList);
            const aStats = getStats(aList);
            const kwStats = getStats(kwList);
            
            const firstEnergy = data[0].val_energy_kwh || 0;
            const lastEnergy = data[data.length - 1].val_energy_kwh || 0;
            const energyDelta = Math.abs(lastEnergy - firstEnergy).toFixed(2);

            $(`#${prefix}_v_avg`).text(vStats.avg);
            $(`#${prefix}_v_peak`).text(vStats.max);
            $(`#${prefix}_a_avg`).text(aStats.avg);
            $(`#${prefix}_a_peak`).text(aStats.max);
            $(`#${prefix}_kw_avg`).text(kwStats.avg);
            $(`#${prefix}_kw_peak`).text(kwStats.max);
            $(`#${prefix}_energy`).text(energyDelta);
        };

        updateUnitUI(dataU1, 'u1');
        updateUnitUI(dataU2, 'u2');
    }

    // --- 3. Chart Creation Helpers ---
    function createLineChart(id, color, maxVal) {
        const canvas = document.getElementById(id);
        if (!canvas) return null;
        return new Chart(canvas.getContext('2d'), {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    borderColor: color,
                    backgroundColor: color + '33',
                    fill: true,
                    tension: 0.1,
                    borderWidth: 2,
                    fullDates: [] 
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { min: 0, max: maxVal, ticks: { font: { size: 10 } } },
                    x: { ticks: { maxTicksLimit: 8, font: { size: 9 } } }
                },
                elements: { point: { radius: 0 } },
                animation: false 
            }
        });
    }

    // --- 4. Initialize All Charts ---
    charts.histU1 = createLineChart('currentChart24h_U1', '#3B82F6', 70.0); 
    charts.histU2 = createLineChart('currentChart24h_U2', '#FBBF24', 70.0); 
    charts.liveU1 = createLineChart('currentChart_U1', '#3B82F6', 70.0); 
    charts.liveU2 = createLineChart('currentChart_U2', '#FBBF24', 70.0); 

    const weeklyCanvas = document.getElementById('weeklyLoadChart');
    if (weeklyCanvas) {
        charts.weekly = new Chart(weeklyCanvas.getContext('2d'), {
            type: 'bar',
            data: {
                labels: [],
                datasets: [
                    { label: 'LAN - 17', backgroundColor: '#3B82F6', data: [] },
                    { label: 'LAN - 13', backgroundColor: '#FBBF24', data: [] }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { beginAtZero: true, suggestedMax: 15, title: { display: true, text: '平均電流 (A)' } }
                },
                plugins: { legend: { display: true, position: 'bottom' } }
            }
        });
    }

    const energyCanvas = document.getElementById('weeklyEnergyChart');
    if (energyCanvas) {
        charts.weeklyEnergy = new Chart(energyCanvas.getContext('2d'), {
            type: 'bar',
            data: {
                labels: [],
                datasets: [
                    { label: 'LAN - 17', backgroundColor: '#10B981', data: [] },
                    { label: 'LAN - 13', backgroundColor: '#34D399', data: [] }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { beginAtZero: true, title: { display: true, text: '電力量 (kWh)' } }
                },
                plugins: { legend: { display: true, position: 'bottom' } }
            }
        });
    }

    // --- 5. Data Update Functions ---
    function updateHistoryCharts(chart, data) {
        chart.data.labels = data.map(d => d.timestamp.split(' ')[1]);
        chart.data.datasets[0].data = data.map(d => Math.abs(d.val_current || 0));
        chart.data.datasets[0].fullDates = data.map(d => d.timestamp);
        chart.update(); 
    }

    function updateLiveChart(chart, data) {
        const time = data.timestamp.split(' ')[1];
        chart.data.labels.push(time);
        chart.data.datasets[0].data.push(Math.abs(data.val_current || 0));
        chart.data.datasets[0].fullDates.push(data.timestamp);
        if (chart.data.labels.length > MAX_POINTS) {
            chart.data.labels.shift();
            chart.data.datasets[0].data.shift();
            chart.data.datasets[0].fullDates.shift();
        }
        chart.update('none'); 
    }

    function loadWeeklyCharts() {
        $.getJSON('/api/weekly_summary', function(res) {
            if (charts.weekly && res.labels) {
                charts.weekly.data.labels = res.labels;
                charts.weekly.data.datasets[0].data = res.u1.map(Math.abs);
                charts.weekly.data.datasets[1].data = res.u2.map(Math.abs);
                charts.weekly.update();
            }
        });
        $.getJSON('/api/weekly_energy_summary', function(res) {
            if (charts.weeklyEnergy && res.labels) {
                charts.weeklyEnergy.data.labels = res.labels;
                charts.weeklyEnergy.data.datasets[0].data = res.u1.map(Math.abs);
                charts.weeklyEnergy.data.datasets[1].data = res.u2.map(Math.abs);
                charts.weeklyEnergy.update();
            }
        });
    }

    // --- 6. Initial Execution ---
    if (config.historyU1 && config.historyU2) {
        updateHistoryCharts(charts.histU1, config.historyU1);
        updateHistoryCharts(charts.histU2, config.historyU2);
        calculateAndDisplayStats(config.historyU1, config.historyU2);
        
        config.historyU1.slice(-MAX_POINTS).forEach(d => updateLiveChart(charts.liveU1, d));
        config.historyU2.slice(-MAX_POINTS).forEach(d => updateLiveChart(charts.liveU2, d));
    }
    loadWeeklyCharts();

    // --- 7. Polling ---
    setInterval(() => {
        $.getJSON(config.apiUrlU1, (data) => {
            if (data && data.timestamp !== lastTsU1) {
                updateLiveChart(charts.liveU1, data);
                lastTsU1 = data.timestamp;
                $('#lastUpdated').text("最終更新: " + data.timestamp.split(' ')[1]);
            }
        });
        $.getJSON(config.apiUrlU2, (data) => {
            if (data && data.timestamp !== lastTsU2) {
                updateLiveChart(charts.liveU2, data);
                lastTsU2 = data.timestamp;
            }
        });
    }, config.readIntervalMs);

    // --- 8. Events ---
    $(".date-picker").datepicker({ dateFormat: "yy-mm-dd" });

    $('#historyForm').on('submit', function(e) {
        e.preventDefault();
        const start = $('#startDate').val();
        const end = $('#endDate').val();
        if (!start || !end) return;

        const $btn = $(this).find('button[type="submit"]');
        $btn.prop('disabled', true).html('<span class="spinner-border spinner-border-sm"></span>');

        $.when(
            $.getJSON('/api/unit01/history', { start_date: start, end_date: end }),
            $.getJSON('/api/unit02/history', { start_date: start, end_date: end })
        ).done(function(res1, res2) {
            // FIX: Update the global data variables so Export button uses the new results
            currentDataU1 = res1[0];
            currentDataU2 = res2[0];

            updateHistoryCharts(charts.histU1, currentDataU1);
            updateHistoryCharts(charts.histU2, currentDataU2);
            calculateAndDisplayStats(currentDataU1, currentDataU2);
            
            const rangeText = `${start} 〜 ${end}`;
            $('#currentRangeText').text(`表示範囲: ${rangeText}`);
            $('[id^="titleU1"], [id^="titleU2"]').each(function() {
                let currentText = $(this).text().split('[')[0].trim();
                $(this).text(`${currentText} [${rangeText}]`);
            });
        }).always(() => { $btn.prop('disabled', false).text('データ読込'); });
    });

    $('#exportCsvBtn').on('click', function() {
        // FIX: Now uses currentDataU1/U2 which reflects the date picker results
        const d1 = currentDataU1;
        const d2 = currentDataU2;

        let csv = "\ufeffTimestamp,Unit01_A,Unit01_kW,Unit02_A,Unit02_kW\n";
        const maxLen = Math.max(d1.length, d2.length);

        for (let i = 0; i < maxLen; i++) {
            const row1 = d1[i] || {};
            const row2 = d2[i] || {};
            const ts = row1.timestamp || row2.timestamp || "";
            const a1 = Math.abs(row1.val_current || 0);
            const p1 = Math.abs(row1.val_power_kw || 0);
            const a2 = Math.abs(row2.val_current || 0);
            const p2 = Math.abs(row2.val_power_kw || 0);
            csv += `${ts},${a1},${p1},${a2},${p2}\n`;
        }

        const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8;' }));
        const link = document.createElement("a");
        link.href = url;
        link.download = `hikaku_export_${new Date().toISOString().slice(0,10)}.csv`;
        link.click();
    });

    $('#resetLiveBtn').on('click', function() {
        location.reload(); 
    });
});

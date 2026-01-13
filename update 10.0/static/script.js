$(document).ready(function() {
    // 1. Configuration & Initialization
    const config = window.flaskData;
    let voltageChart, currentChart, voltageChart24h, currentChart24h;
    let currentData = config.history; 
    let lastTimestamp = ""; 

    // Constants for the "Live" rolling window
    const MAX_POINTS = 30; 

    // Initialize Date Pickers
    $(".date-picker").datepicker({ dateFormat: "yy-mm-dd" });

    // Initial Chart Render
    renderCharts(currentData);

    // 2. Real-time Data Polling
    setInterval(updateLiveMetrics, config.readIntervalMs);

    function updateLiveMetrics() {
        $.getJSON(config.apiUrl, function(data) {
            if (data.error || data.timestamp === lastTimestamp) return;
            lastTimestamp = data.timestamp;

            // Update UI Cards
            $('#live-voltage').text(data.val_voltage.toFixed(2));
            $('#live-current').text(data.val_current.toFixed(3));
            $('#live-energy').text(data.val_energy_kwh.toFixed(3));
            $('#lastUpdated').text("最終更新: " + data.timestamp.split(' ')[1]);

            // Update Real-time Log Table
            const newRow = `<tr>
                <td class="text-secondary">${data.timestamp.split(' ')[1]}</td>
                <td>${data.val_voltage.toFixed(2)}</td>
                <td>${data.val_current.toFixed(3)}</td>
                <td>${data.val_energy_kwh.toFixed(3)}</td>
            </tr>`;
            $('#logTableBody').prepend(newRow);
            if ($('#logTableBody tr').length > 10) $('#logTableBody tr:last').remove();

            // Update only the "Live" charts on the right side
            updateChartsRealtime(data);
        });
    }

    // 3. Chart Management
    function renderCharts(data) {
        // Prepare data for 24h/History (Left)
        const histLabels = data.map(d => d.timestamp.split(' ')[1]);
        const histFullDates = data.map(d => d.timestamp);
        const histVoltages = data.map(d => d.val_voltage);
        const histCurrents = data.map(d => d.val_current);

        // Prepare data for Live Scrolling (Right)
        const liveSlice = data.slice(-MAX_POINTS);
        const liveLabels = liveSlice.map(d => d.timestamp.split(' ')[1]);
        const liveFullDates = liveSlice.map(d => d.timestamp);
        const liveVoltages = liveSlice.map(d => d.val_voltage);
        const liveCurrents = liveSlice.map(d => d.val_current);

        // Helper to generate options
        const getOptions = (chartType, minVal, maxVal) => {
            return {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { 
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            title: function(context) {
                                const fullDate = context[0].dataset.fullDates[context[0].dataIndex];
                                // If it's the live chart, just show time. Otherwise, show full date.
                                return chartType === 'live' ? fullDate.split(' ')[1] : fullDate;
                            }
                        }
                    }
                },
                scales: {
                    x: { ticks: { maxTicksLimit: 8, font: { size: 9 } }, grid: { display: false } },
                    y: { 
                        beginAtZero: false, 
                        font: { size: 10 },
                        min: minVal,
                        max: maxVal
                    }
                },
                elements: { point: { radius: 0 }, line: { borderWidth: 2, tension: 0.1 } },
                animation: false
            };
        };

        // Destroy all existing charts
        [voltageChart, currentChart, voltageChart24h, currentChart24h].forEach(c => c && c.destroy());

        // --- RENDER 24H / HISTORY CHARTS (LEFT SIDE) ---
        voltageChart24h = new Chart(document.getElementById('voltageChart24h'), {
            type: 'line',
            data: { labels: histLabels, datasets: [{ data: histVoltages, borderColor: '#4CAF50', fill: true, fullDates: histFullDates }] },
            options: getOptions('history', 180, 220)
        });

        currentChart24h = new Chart(document.getElementById('currentChart24h'), {
            type: 'line',
            data: { labels: histLabels, datasets: [{ data: histCurrents, borderColor: '#FBBF24', fill: true, fullDates: histFullDates }] },
            options: getOptions('history', 0, 70.0)
        });

        // --- RENDER LIVE SCROLLING CHARTS (RIGHT SIDE) ---
        voltageChart = new Chart(document.getElementById('voltageChart'), {
            type: 'line',
            data: { labels: liveLabels, datasets: [{ data: liveVoltages, borderColor: '#4CAF50', fill: true, fullDates: liveFullDates }] },
            options: getOptions('live', 195, 205)
        });

        currentChart = new Chart(document.getElementById('currentChart'), {
            type: 'line',
            data: { labels: liveLabels, datasets: [{ data: liveCurrents, borderColor: '#FBBF24', fill: true, fullDates: liveFullDates }] },
            options: getOptions('live', 0, 70.0)
        });
    }

    function updateChartsRealtime(point) {
        const time = point.timestamp.split(' ')[1];
        
        // We only push live updates to the Right Side charts
        [voltageChart, currentChart].forEach((chart, i) => {
            chart.data.labels.push(time);
            chart.data.datasets[0].fullDates.push(point.timestamp);
            
            const val = (i === 0) ? point.val_voltage : point.val_current;
            chart.data.datasets[0].data.push(val);

            if (chart.data.labels.length > MAX_POINTS) {
                chart.data.labels.shift();
                chart.data.datasets[0].data.shift();
                chart.data.datasets[0].fullDates.shift();
            }
            chart.update('none');
        });
    }

    // 4. History Search (Updates the 24h charts and updates currentData for CSV)
    $('#historyForm').on('submit', function(e) {
        e.preventDefault();
        const start = $('#startDate').val();
        const end = $('#endDate').val();
        const $btn = $(this).find('button[type="submit"]');
        if (!start || !end) return;

        $btn.prop('disabled', true).html('<span class="spinner-border spinner-border-sm me-1"></span>');

        $.getJSON(`/api/${config.unitId}/history`, { start_date: start, end_date: end }, function(data) {
            if (data.length === 0) {
                alert("データが見つかりませんでした。");
                return;
            }
            currentData = data;
            
            // --- NEW: DYNAMIC TITLE UPDATE ---
            // Format the dates slightly for the title (optional, or just use start/end)
            const rangeTitle = `${start} ～ ${end}`;
            $('#cChartTitle').text(`電流履歴 ${rangeTitle} (A)`);
            $('#vChartTitle').text(`電圧履歴 ${rangeTitle} (V)`);
            
            $('#currentRangeText').text(`表示範囲: ${start} 〜 ${end}`);
            renderCharts(data); 
        }).fail(() => alert("通信エラー")).always(() => $btn.prop('disabled', false).text('読込'));
    });

    // 5. Export CSV
    $('#exportCsvBtn').on('click', function() {
        let csv = "Timestamp,Voltage(V),Current(A),Energy(kWh)\n";
        currentData.forEach(r => csv += `${r.timestamp},${r.val_voltage},${r.val_current},${r.val_energy_kwh}\n`);
        const link = document.createElement("a");
        link.setAttribute("href", 'data:text/csv;charset=utf-8,' + encodeURIComponent(csv));
        link.setAttribute("download", `export_${config.unitId}.csv`);
        link.click();
    });

    // 6. Reset to Live Mode
    $('#resetLiveBtn').on('click', () => location.reload());
});

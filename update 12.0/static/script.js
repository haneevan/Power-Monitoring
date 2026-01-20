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

    // Initial Setup: Create the chart objects once
    initCharts(currentData);

    // 2. Real-time Data Polling
    setInterval(updateLiveMetrics, config.readIntervalMs);

    function updateLiveMetrics() {
        $.getJSON(config.apiUrl, function(data) {
            if (data.error || data.timestamp === lastTimestamp) return;
            lastTimestamp = data.timestamp;

            // Update UI Cards
            $('#live-voltage').text(data.val_voltage.toFixed(2));
            $('#live-current').text(data.val_current.toFixed(3));
            $('#live-power').text(data.val_power_w.toFixed(1)); // Updated for Power card
            $('#live-energy').text(data.val_energy_kwh.toFixed(3));
            $('#lastUpdated').text("最終更新: " + data.timestamp.split(' ')[1]);

            // Update Real-time Log Table (Power now shown in W)
            const newRow = `<tr>
                <td class="text-secondary">${data.timestamp.split(' ')[1]}</td>
                <td>${data.val_voltage.toFixed(2)}</td>
                <td>${data.val_current.toFixed(3)}</td>
                <td>${data.val_power_w.toFixed(1)}</td> 
            </tr>`;
            $('#logTableBody').prepend(newRow);
            if ($('#logTableBody tr').length > 10) $('#logTableBody tr:last').remove();

            // Update only the "Live" charts on the right side
            updateChartsRealtime(data);
        });
    }

    // 3. Chart Management
    function initCharts(data) {
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
                                return chartType === 'live' ? fullDate.split(' ')[1] : fullDate;
                            }
                        }
                    }
                },
                scales: {
                    x: { ticks: { maxTicksLimit: 8, font: { size: 9 } }, grid: { display: false } },
                    y: { beginAtZero: false, font: { size: 10 }, min: minVal, max: maxVal }
                },
                elements: { point: { radius: 0 }, line: { borderWidth: 2, tension: 0.1 } },
                animation: false
            };
        };

        // RENDER HISTORY CHARTS (LEFT SIDE)
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

        // RENDER LIVE CHARTS (RIGHT SIDE)
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

    function updateHistoryOnly(data) {
        const labels = data.map(d => d.timestamp.split(' ')[1]);
        const fullDates = data.map(d => d.timestamp);
        
        voltageChart24h.data.labels = labels;
        voltageChart24h.data.datasets[0].data = data.map(d => d.val_voltage);
        voltageChart24h.data.datasets[0].fullDates = fullDates;
        voltageChart24h.update();

        currentChart24h.data.labels = labels;
        currentChart24h.data.datasets[0].data = data.map(d => d.val_current);
        currentChart24h.data.datasets[0].fullDates = fullDates;
        currentChart24h.update();
    }

    function updateChartsRealtime(point) {
        const time = point.timestamp.split(' ')[1];
        
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

    // 4. History Search
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
            
            const rangeTitle = `${start} ～ ${end}`;
            $('#cChartTitle').text(`電流履歴 ${rangeTitle} (A)`);
            $('#vChartTitle').text(`電圧履歴 ${rangeTitle} (V)`);
            $('#currentRangeText').text(`表示範囲: ${start} 〜 ${end}`);
            
            updateHistoryOnly(data);

        }).fail(() => alert("通信エラー")).always(() => $btn.prop('disabled', false).text('読込'));
    });

    // 5. Export CSV (Updated with Power column)
    $('#exportCsvBtn').on('click', function() {
        let csv = "Timestamp,Voltage(V),Current(A),Power(W),Energy(kWh)\n";
        currentData.forEach(r => {
            csv += `${r.timestamp},${r.val_voltage},${r.val_current},${r.val_power_w},${r.val_energy_kwh}\n`;
        });
        const link = document.createElement("a");
        link.setAttribute("href", 'data:text/csv;charset=utf-8,' + encodeURIComponent(csv));
        link.setAttribute("download", `export_${config.unitId}.csv`);
        link.click();
    });

    // 6. Reset to Live Mode
    $('#resetLiveBtn').on('click', function() {
        currentData = config.history; 
        updateHistoryOnly(config.history); 
        
        $('#cChartTitle').text('電流履歴 24h (A)');
        $('#vChartTitle').text('電圧履歴 24h (V)');
        $('#currentRangeText').text('表示範囲: 直近 24 時間');
        $('#startDate, #endDate').val('');
    });
});

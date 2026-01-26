$(document).ready(function() {
    // 1. Configuration & Initialization
    const config = window.flaskData;
    let voltageChart, currentChart, voltageChart24h, currentChart24h;
    let currentData = config.history; 
    let lastTimestamp = ""; 

    const MAX_POINTS = 30; 

    $(".date-picker").datepicker({ dateFormat: "yy-mm-dd" });

    // Initialize charts with the history passed from Flask
    initCharts(currentData);

    // 2. Real-time Data Polling
    setInterval(updateLiveMetrics, config.readIntervalMs);

    function updateLiveMetrics() {
        $.getJSON(config.apiUrl, function(data) {
            // Guard clause: error or duplicate data
            if (data.error || data.timestamp === lastTimestamp) return;
            lastTimestamp = data.timestamp;

            // --- Update UI Cards (Voltage & Current) ---
            $('#live-voltage').text(data.val_voltage.toFixed(2));
            $('#live-current').text(data.val_current.toFixed(3));
            
            // --- Handle Power (kW) with Solar Export Logic ---
            const kwVal = data.val_power_kw !== undefined ? data.val_power_kw : 0.0;
            const powerElement = $('#live-power');
            const powerLabel = powerElement.closest('.card').find('p');
            
            powerElement.text(kwVal.toFixed(3));

            if (kwVal < 0) {
                // Solar Export Mode (Generating more than consuming)
                powerLabel.text("電力 (売電/Solar Export)");
                powerElement.css('color', '#10B981'); // Emerald Green
            } else {
                // Consumption Mode (Buying from grid)
                powerLabel.text("電力 (買電/Consumption)");
                powerElement.css('color', '#FF0000'); // Standard Red
            }
            
            // --- Update Energy & Timestamp ---
            $('#live-energy').text(data.val_energy_kwh.toFixed(3));
            $('#lastUpdated').text("最終更新: " + data.timestamp.split(' ')[1]);

            // --- Update Real-time Log Table ---
            // Highlight row in light green if it's solar export
            const rowClass = kwVal < 0 ? 'table-success' : '';
            const newRow = `<tr class="${rowClass}">
                <td class="text-secondary">${data.timestamp.split(' ')[1]}</td>
                <td>${data.val_voltage.toFixed(2)}</td>
                <td>${data.val_current.toFixed(3)}</td>
                <td class="fw-bold">${kwVal.toFixed(3)}</td>
                <td>${data.val_energy_kwh.toFixed(3)}</td>
            </tr>`;
            
            $('#logTableBody').prepend(newRow);
            
            // Keep only the latest 10 rows
            if ($('#logTableBody tr').length > 10) {
                $('#logTableBody tr:last').remove();
            }

            // --- Update Live Charts ---
            updateChartsRealtime(data);
        });
    }

    // 3. Chart Management
    function initCharts(data) {
        const histLabels = data.map(d => d.timestamp.split(' ')[1]);
        const histFullDates = data.map(d => d.timestamp);
        const histVoltages = data.map(d => d.val_voltage);
        const histCurrents = data.map(d => d.val_current);

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

        voltageChart24h = new Chart(document.getElementById('voltageChart24h'), {
            type: 'line',
            data: { labels: histLabels, datasets: [{ data: histVoltages, borderColor: '#4CAF50', fill: true, fullDates: histFullDates }] },
            options: getOptions('history', 180, 230)
        });

        currentChart24h = new Chart(document.getElementById('currentChart24h'), {
            type: 'line',
            data: { labels: histLabels, datasets: [{ data: histCurrents, borderColor: '#FBBF24', fill: true, fullDates: histFullDates }] },
            options: getOptions('history', 0, 70.0)
        });

        voltageChart = new Chart(document.getElementById('voltageChart'), {
            type: 'line',
            data: { labels: liveLabels, datasets: [{ data: liveVoltages, borderColor: '#4CAF50', fill: true, fullDates: liveFullDates }] },
            options: getOptions('live', 190, 210)
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

    // 5. Export CSV
    $('#exportCsvBtn').on('click', function() {
        let csv = "Timestamp,Voltage(V),Current(A),Power(kW),Energy(kWh)\n";
        currentData.forEach(r => {
            const p = (r.val_power_kw !== undefined && r.val_power_kw !== null) ? r.val_power_kw : 0.0;
            csv += `${r.timestamp},${r.val_voltage},${r.val_current},${p},${r.val_energy_kwh}\n`;
        });
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.setAttribute("href", url);
        link.setAttribute("download", `export_${config.unitId}_${new Date().toISOString().slice(0,10)}.csv`);
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

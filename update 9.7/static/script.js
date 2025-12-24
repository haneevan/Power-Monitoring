$(document).ready(function() {
    // 1. Configuration & Initialization
    const config = window.flaskData;
    let voltageChart, currentChart;
    let currentData = config.history; 
    let lastTimestamp = ""; 

    // Constants for the "Rolling window" (10 minutes)
    const MAX_POINTS = 600; 

    // Initialize Date Pickers
    $(".date-picker").datepicker({ dateFormat: "yy-mm-dd" });

    // Initial Chart Render
    renderCharts(currentData.slice(-MAX_POINTS));

    // 2. Real-time Data Polling
    setInterval(updateLiveMetrics, config.readIntervalMs);

    function updateLiveMetrics() {
        $.getJSON(config.apiUrl, function(data) {
            if (data.error) return;
            if (data.timestamp === lastTimestamp) return;
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

            updateChartsRealtime(data);
        });
    }

    // 3. Chart Management
    function renderCharts(data) {
        const displayLabels = data.map(d => d.timestamp.split(' ')[1]);
        const fullTimestamps = data.map(d => d.timestamp); 
        const voltages = data.map(d => d.val_voltage);
        const currents = data.map(d => d.val_current);

        const rangeText = $('#currentRangeText').text();
        const isLiveMode = rangeText.includes('直近') || rangeText.includes('24 時間');

        // Helper to generate options with SMART TOOLTIP logic
        const getOptions = (isLive, minVal, maxVal) => {
            return {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { 
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            title: function(context) {
                                const ds = context[0].dataset;
                                const idx = context[0].dataIndex;
                                const fullDate = ds.fullDates[idx];
                                
                                // Get the current display label text
                                const currentRange = $('#currentRangeText').text();
                                
                                // SMART CHECK:
                                // If label contains "直近" (Live), show only Time.
                                // Otherwise (History), show full YYYY-MM-DD HH:MM:SS.
                                if (currentRange.includes('直近')) {
                                    return fullDate.split(' ')[1]; 
                                } else {
                                    return fullDate;
                                }
                            }
                        }
                    }
                },
                scales: {
                    x: { ticks: { maxTicksLimit: 10, font: { size: 10 } }, grid: { display: false } },
                    y: { 
                        beginAtZero: true, 
                        font: { size: 10 },
                        min: isLive ? minVal : undefined,
                        max: isLive ? maxVal : undefined
                    }
                },
                elements: { point: { radius: 0 }, line: { borderWidth: 2, tension: 0.1 } },
                animation: false
            };
        };

        if (voltageChart) voltageChart.destroy();
        if (currentChart) currentChart.destroy();

        // Voltage Chart
        const vCtx = document.getElementById('voltageChart').getContext('2d');
        voltageChart = new Chart(vCtx, {
            type: 'line',
            data: {
                labels: displayLabels,
                datasets: [{ 
                    data: voltages, 
                    borderColor: '#4CAF50', 
                    backgroundColor: 'rgba(76, 175, 80, 0.1)', 
                    fill: true,
                    fullDates: fullTimestamps 
                }]
            },
            options: getOptions(isLiveMode, 180, 220)
        });

        // Current Chart
        const cCtx = document.getElementById('currentChart').getContext('2d');
        currentChart = new Chart(cCtx, {
            type: 'line',
            data: {
                labels: displayLabels,
                datasets: [{ 
                    data: currents, 
                    borderColor: '#FBBF24', 
                    backgroundColor: 'rgba(251, 191, 36, 0.1)', 
                    fill: true,
                    fullDates: fullTimestamps 
                }]
            },
            options: getOptions(isLiveMode, 0, 3.0)
        });
    }

    function updateChartsRealtime(point) {
        const rangeText = $('#currentRangeText').text();
        if (rangeText.includes('直近') || rangeText.includes('24 時間')) {
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
    }

    // 4. History Search
    $('#historyForm').on('submit', function(e) {
        e.preventDefault();
        const start = $('#startDate').val();
        const end = $('#endDate').val();
        const $btn = $(this).find('button[type="submit"]');
        if (!start || !end) return;

        $btn.prop('disabled', true).html('<span class="spinner-border spinner-border-sm me-1"></span> 読込中...');

        $.getJSON(`/api/${config.unitId}/history`, { start_date: start, end_date: end }, function(data) {
            if (data.length === 0) {
                alert("データが見つかりませんでした。");
                return;
            }
            currentData = data;
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
    $('#resetLiveBtn').on('click', function() {
        const $btn = $(this);
        const originalHtml = $btn.html();
        $btn.prop('disabled', true).html('<span class="spinner-border spinner-border-sm"></span>');

        const today = new Date().toISOString().split('T')[0];
        $.getJSON(`/api/${config.unitId}/history`, { start_date: today, end_date: today }, function(data) {
            $('#currentRangeText').text("表示範囲: 直近 10 分間");
            $('#startDate, #endDate').val('');
            if (data && data.length > 0) {
                const liveWindow = data.slice(-MAX_POINTS);
                currentData = liveWindow;
                renderCharts(liveWindow);
            } else { location.reload(); }
        }).always(() => $btn.prop('disabled', false).html(originalHtml));
    });

    $('#manualRefreshBtn').on('click', () => location.reload());
});

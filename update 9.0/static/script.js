$(document).ready(function() {
    // 1. Configuration & Initialization
    const config = window.flaskData;
    let voltageChart, currentChart;
    let currentData = config.history; 
    let lastTimestamp = ""; 

    // Constants for the "Rolling 5 Minute" window
    // 300 points = 5 minutes * 60 seconds
    const MAX_POINTS = 600; 

    // Initialize Date Pickers
    $(".date-picker").datepicker({ dateFormat: "yy-mm-dd" });

    // Initial Chart Render (Show last 5 mins of history if available)
    const initialWindow = currentData.slice(-MAX_POINTS);
    renderCharts(initialWindow);

    // 2. Real-time Data Polling
    setInterval(updateLiveMetrics, config.readIntervalMs);

    function updateLiveMetrics() {
        $.getJSON(config.apiUrl, function(data) {
            if (data.error) return;

            // Prevent double-logging by checking the timestamp
            if (data.timestamp === lastTimestamp) return;
            lastTimestamp = data.timestamp;

            // Update UI Cards
            $('#live-voltage').text(data.val_voltage.toFixed(2));
            $('#live-current').text(data.val_current.toFixed(3));
            $('#live-energy').text(data.val_energy_kwh.toFixed(3));
            $('#lastUpdated').text("最終更新: " + data.timestamp.split(' ')[1]);

            // Update Real-time Log Table (Last 10 entries)
            const newRow = `<tr>
                <td class="text-secondary">${data.timestamp.split(' ')[1]}</td>
                <td>${data.val_voltage.toFixed(2)}</td>
                <td>${data.val_current.toFixed(3)}</td>
                <td>${data.val_energy_kwh.toFixed(3)}</td>
            </tr>`;
            
            $('#logTableBody').prepend(newRow);
            if ($('#logTableBody tr').length > 10) {
                $('#logTableBody tr:last').remove();
            }

            // Update Charts with the new point
            updateChartsRealtime(data);
        });
    }

    // 3. Chart Management
    function renderCharts(data) {
        const labels = data.map(d => d.timestamp.split(' ')[1]);
        const voltages = data.map(d => d.val_voltage);
        const currents = data.map(d => d.val_current);

        // Check if we are in Live View (Last 24h/5m) or History Search View
        const isLiveMode = $('#currentRangeText').text().includes('24 時間') || 
                           $('#currentRangeText').text().includes('直近');

        const commonOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { 
                    ticks: { maxTicksLimit: 10, font: { size: 10 } },
                    grid: { display: false }
                },
                y: { 
                    beginAtZero: true,
                    font: { size: 10 } 
                }
            },
            elements: { 
                point: { radius: 0 }, 
                line: { borderWidth: 2, tension: 0.1 } 
            },
            animation: false
        };

        if (voltageChart) voltageChart.destroy();
        if (currentChart) currentChart.destroy();

        // Voltage Chart: Fixed at 0 to 210V
        const vCtx = document.getElementById('voltageChart').getContext('2d');
        voltageChart = new Chart(vCtx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{ data: voltages, borderColor: '#4CAF50', backgroundColor: 'rgba(76, 175, 80, 0.1)', fill: true }]
            },
            options: JSON.parse(JSON.stringify(commonOptions))
        });

        if (isLiveMode) {
            voltageChart.options.scales.y.min = 0;
            voltageChart.options.scales.y.max = 210;
        }

        // Current Chart: Fixed at 0 to 0.35A
        const cCtx = document.getElementById('currentChart').getContext('2d');
        currentChart = new Chart(cCtx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{ data: currents, borderColor: '#FBBF24', backgroundColor: 'rgba(251, 191, 36, 0.1)', fill: true }]
            },
            options: JSON.parse(JSON.stringify(commonOptions))
        });

        if (isLiveMode) {
            currentChart.options.scales.y.min = 0;
            currentChart.options.scales.y.max = 0.35;
        }

        voltageChart.update();
        currentChart.update();
    }

    function updateChartsRealtime(point) {
        // Only shift the window if in Live Mode
        if ($('#currentRangeText').text().includes('24 時間') || $('#currentRangeText').text().includes('直近')) {
            const time = point.timestamp.split(' ')[1];
            
            // Handle Voltage Update
            voltageChart.data.labels.push(time);
            voltageChart.data.datasets[0].data.push(point.val_voltage);
            
            // Handle Current Update
            currentChart.data.labels.push(time);
            currentChart.data.datasets[0].data.push(point.val_current);

            // Maintain the 5-minute rolling window (300 points)
            if (voltageChart.data.labels.length > MAX_POINTS) {
                voltageChart.data.labels.shift();
                voltageChart.data.datasets[0].data.shift();
                currentChart.data.labels.shift();
                currentChart.data.datasets[0].data.shift();
            }
            
            voltageChart.update('none');
            currentChart.update('none');
        }
    }

    // 4. History & Exports
    $('#historyForm').on('submit', function(e) {
        e.preventDefault();
        const start = $('#startDate').val();
        const end = $('#endDate').val();

        $.getJSON(`/api/${config.unitId}/history`, { start_date: start, end_date: end }, function(data) {
            if (data.length === 0) {
                alert("指定された期間のデータが見つかりませんでした。");
                return;
            }
            currentData = data;
            $('#currentRangeText').text(`表示範囲: ${start} 〜 ${end}`);
            renderCharts(data); // Will use auto-scaling for historical view
        });
    });

    // 5. Export CSV button
    $('#exportCsvBtn').on('click', function() {
        let csvContent = "data:text/csv;charset=utf-8,Timestamp,Voltage(V),Current(A),Energy(kWh)\n";
        currentData.forEach(row => {
            csvContent += `${row.timestamp},${row.val_voltage},${row.val_current},${row.val_energy_kwh}\n`;
        });
        const link = document.createElement("a");
        link.setAttribute("href", encodeURI(csvContent));
        link.setAttribute("download", `export_${config.unitId}.csv`);
        link.click();
    });


    //6. Reset chart graph button
    $('#resetLiveBtn').on('click', function() {
    // 1. Reset the range text (Ensure typo "示" is fixed to "表示")
    $('#currentRangeText').text("表示範囲: 直近 10 分間");

    // 2. Clear the date inputs
    $('#startDate, #endDate').val('');

    // 3. Fetch exactly the last 600 points
    $.getJSON(`/api/${config.unitId}/history`, { limit: 600 }, function(data) {
        if (data && data.length > 0) {
            renderCharts(data);
            
            // Reset the metric cards to the absolute latest values
            const latest = data[data.length - 1];
            $('#live-voltage').text(latest.val_voltage.toFixed(2));
            $('#live-current').text(latest.val_current.toFixed(3));
            $('#live-energy').text(latest.val_energy_kwh.toFixed(3));
            
            console.log("Dashboard reset to 10-minute live mode.");
        }
    });
});

    $('#manualRefreshBtn').on('click', () => location.reload());
});

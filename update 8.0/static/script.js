$(document).ready(function() {
    // 1. Initialize Variables and Charts
    const config = window.flaskData;
    let voltageChart, currentChart;
    let currentData = config.history; // Holds the currently displayed dataset

    // Initialize Date Pickers (jQuery UI)
    $(".date-picker").datepicker({
        dateFormat: "yy-mm-dd"
    });

    // Initial Chart Render
    renderCharts(currentData);

    // 2. Real-time Data Polling
    setInterval(updateLiveMetrics, config.readIntervalMs);

    function updateLiveMetrics() {
        $.getJSON(config.apiUrl, function(data) {
            if (data.error) return;

            // Update Metric Cards
            $('#live-voltage').text(data.val_voltage.toFixed(2));
            $('#live-current').text(data.val_current.toFixed(3));
            $('#live-energy').text(data.val_energy_kwh.toFixed(3));
            $('#lastUpdated').text("最終更新: " + data.timestamp.split(' ')[1]);

            // Add to the log table (at the top)
            const newRow = `<tr>
                <td class="text-secondary">${data.timestamp.split(' ')[1]}</td>
                <td>${data.val_voltage.toFixed(2)}</td>
                <td>${data.val_current.toFixed(3)}</td>
                <td>${data.val_energy_kwh.toFixed(3)}</td>
            </tr>`;
            
            $('#logTableBody').prepend(newRow);
            
            // Keep only the last 10 rows for performance
            if ($('#logTableBody tr').length > 10) {
                $('#logTableBody tr:last').remove();
            }

            // Update Charts in real-time (optional: only if showing default range)
            updateChartsRealtime(data);
        });
    }

    // 3. Chart Rendering Logic
    function renderCharts(data) {
        const labels = data.map(d => d.timestamp.split(' ')[1]);
        const voltages = data.map(d => d.val_voltage);
        const currents = data.map(d => d.val_current);

        const commonOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { ticks: { maxTicksLimit: 10, font: { size: 10 } } },
                y: { beginAtZero: false, font: { size: 10 } }
            },
            elements: { point: { radius: 0 }, line: { borderWidth: 2 } },
            animation: false
        };

        if (voltageChart) voltageChart.destroy();
        if (currentChart) currentChart.destroy();

        const vCtx = document.getElementById('voltageChart').getContext('2d');
        voltageChart = new Chart(vCtx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{ data: voltages, borderColor: '#4CAF50', backgroundColor: 'rgba(76, 175, 80, 0.1)', fill: true }]
            },
            options: commonOptions
        });

        const cCtx = document.getElementById('currentChart').getContext('2d');
        currentChart = new Chart(cCtx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{ data: currents, borderColor: '#FBBF24', backgroundColor: 'rgba(251, 191, 36, 0.1)', fill: true }]
            },
            options: commonOptions
        });
    }

    function updateChartsRealtime(point) {
        // Only push to chart if we are not looking at a historical search
        if ($('#currentRangeText').text().includes('時間')) {
            const time = point.timestamp.split(' ')[1];
            
            voltageChart.data.labels.push(time);
            voltageChart.data.datasets[0].data.push(point.val_voltage);
            
            currentChart.data.labels.push(time);
            currentChart.data.datasets[0].data.push(point.val_current);

            // Shift if more than 50 points
            if (voltageChart.data.labels.length > 50) {
                voltageChart.data.labels.shift();
                voltageChart.data.datasets[0].data.shift();
                currentChart.data.labels.shift();
                currentChart.data.datasets[0].data.shift();
            }
            voltageChart.update('none');
            currentChart.update('none');
        }
    }

    // 4. History Search Functionality
    $('#historyForm').on('submit', function(e) {
        e.preventDefault();
        const start = $('#startDate').val();
        const end = $('#endDate').val();
        const unitId = config.unitId;

        $.getJSON(`/api/${unitId}/history`, { start_date: start, end_date: end }, function(data) {
            if (data.length === 0) {
                alert("指定された期間のデータが見つかりませんでした。");
                return;
            }
            currentData = data;
            renderCharts(data);
            
            // Re-fill the log table with historical data
            let tableHtml = "";
            data.slice().reverse().slice(0, 50).forEach(item => {
                tableHtml += `<tr>
                    <td class="text-secondary">${item.timestamp}</td>
                    <td>${item.val_voltage.toFixed(2)}</td>
                    <td>${item.val_current.toFixed(3)}</td>
                    <td>${item.val_energy_kwh.toFixed(3)}</td>
                </tr>`;
            });
            $('#logTableBody').html(tableHtml);
            $('#currentRangeText').text(`表示範囲: ${start} 〜 ${end}`);
        });
    });

    // 5. CSV Export Functionality
    $('#exportCsvBtn').on('click', function() {
        let csvContent = "data:text/csv;charset=utf-8,";
        csvContent += "Timestamp,Voltage(V),Current(A),Energy(kWh)\n";
        
        currentData.forEach(function(row) {
            csvContent += `${row.timestamp},${row.val_voltage},${row.val_current},${row.val_energy_kwh}\n`;
        });

        const encodedUri = encodeURI(csvContent);
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", `export_${config.unitId}_${new Date().getTime()}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    });

    // Manual Refresh Button
    $('#manualRefreshBtn').on('click', function() {
        location.reload();
    });
});

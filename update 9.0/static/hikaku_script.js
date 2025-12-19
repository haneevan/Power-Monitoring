$(document).ready(function() {
    const config = window.flaskData;
    const MAX_POINTS = 600; // 10 minutes of data at 1s intervals
    const charts = {};

    // 1. Initialize jQuery UI Date Pickers
    $(".date-picker").datepicker({
        dateFormat: "yy-mm-dd"
    });

    // 2. Real-time Clock Function
    function updateClock() {
        const now = new Date();
        const timeString = now.getHours().toString().padStart(2, '0') + ":" + 
                           now.getMinutes().toString().padStart(2, '0') + ":" + 
                           now.getSeconds().toString().padStart(2, '0');
        $('#lastUpdated').text("最終更新: " + timeString);
    }
    updateClock();
    setInterval(updateClock, 1000);

    // 3. Chart Creation Helper Function
    function createChart(id, color, maxVal) {
        const ctx = document.getElementById(id).getContext('2d');
        return new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    borderColor: color,
                    backgroundColor: color + '1A', // 10% opacity fill
                    fill: true,
                    tension: 0.1,
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { 
                        min: 0, 
                        max: maxVal,
                        ticks: { font: { size: 10 } }
                    },
                    x: {
                        ticks: { maxTicksLimit: 10, font: { size: 10 } }
                    }
                },
                elements: { point: { radius: 0 } },
                animation: false
            }
        });
    }

    // 4. Initialize the 4 Unique Charts
    charts.v1 = createChart('vChartU1', '#3B82F6', 210);  // Unit 01 Voltage
    charts.c1 = createChart('cChartU1', '#3B82F6', 0.35); // Unit 01 Current
    charts.v2 = createChart('vChartU2', '#FBBF24', 210);  // Unit 02 Voltage
    charts.c2 = createChart('cChartU2', '#FBBF24', 0.35); // Unit 02 Current

    // 5. Initial Data Load (History from Flask)
    if (config.historyU1 && config.historyU2) {
        config.historyU1.forEach(d => addDataToChart(charts.v1, charts.c1, d));
        config.historyU2.forEach(d => addDataToChart(charts.v2, charts.c2, d));
    }

    function addDataToChart(vChart, cChart, data) {
        const time = data.timestamp.split(' ')[1];
        vChart.data.labels.push(time);
        vChart.data.datasets[0].data.push(data.val_voltage);
        
        cChart.data.labels.push(time);
        cChart.data.datasets[0].data.push(data.val_current);

        if (vChart.data.labels.length > MAX_POINTS) {
            vChart.data.labels.shift();
            vChart.data.datasets[0].data.shift();
            cChart.data.labels.shift();
            cChart.data.datasets[0].data.shift();
        }
        vChart.update('none');
        cChart.update('none');
    }

    // 6. Real-time Polling Logic
    setInterval(() => {
        // Only poll if we are in "Live Mode"
        if ($('#currentRangeText').text().includes('直近')) {
            $.getJSON('/api/unit01/latest', (data) => addDataToChart(charts.v1, charts.c1, data));
            $.getJSON('/api/unit02/latest', (data) => addDataToChart(charts.v2, charts.c2, data));
        }
    }, config.readIntervalMs);

    // 7. History Search (Read Button)
    $('#historyForm').on('submit', function(e) {
        e.preventDefault();
        const start = $('#startDate').val();
        const end = $('#endDate').val();

        $('#currentRangeText').text(`表示範囲: ${start} 〜 ${end}`);

        // Simultaneous fetch for both units
        $.when(
            $.getJSON('/api/unit01/history', { start_date: start, end_date: end }),
            $.getJSON('/api/unit02/history', { start_date: start, end_date: end })
        ).done(function(res1, res2) {
            updateStaticCharts(charts.v1, charts.c1, res1[0]);
            updateStaticCharts(charts.v2, charts.c2, res2[0]);
        });
    });

    function updateStaticCharts(vChart, cChart, data) {
        vChart.data.labels = data.map(d => d.timestamp.split(' ')[1]);
        vChart.data.datasets[0].data = data.map(d => d.val_voltage);
        
        cChart.data.labels = data.map(d => d.timestamp.split(' ')[1]);
        cChart.data.datasets[0].data = data.map(d => d.val_current);

        vChart.update();
        cChart.update();
    }

    // 8. CSV Export (Fixed Logic)
    $('#exportCsvBtn').on('click', function() {
        const labels = charts.v1.data.labels;
        if (labels.length === 0) {
            alert("出力するデータがありません。");
            return;
        }

        let csvRows = ["Time,U1_Voltage(V),U1_Current(A),U2_Voltage(V),U2_Current(A)"];
        for (let i = 0; i < labels.length; i++) {
            csvRows.push([
                labels[i],
                charts.v1.data.datasets[0].data[i] || 0,
                charts.c1.data.datasets[0].data[i] || 0,
                charts.v2.data.datasets[0].data[i] || 0,
                charts.c2.data.datasets[0].data[i] || 0
            ].join(","));
        }

        const blob = new Blob([csvRows.join("\n")], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = `comparison_export_${new Date().getTime()}.csv`;
        link.click();
    });

    // 9. Reset to Live Mode
    $('#resetLiveBtn').on('click', function() {
        location.reload(); 
    });
});

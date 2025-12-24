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
    function createChart(id, color, maxVal, minVal = 0) {
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
                        min: minVal, 
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
    charts.v1 = createChart('vChartU1', '#3B82F6', 220, 180);  // Unit 01 Voltage
    charts.c1 = createChart('cChartU1', '#3B82F6', 3.0, 0.0); // Unit 01 Current
    charts.v2 = createChart('vChartU2', '#FBBF24', 220, 180);  // Unit 02 Voltage
    charts.c2 = createChart('cChartU2', '#FBBF24', 3.0, 0.0); // Unit 02 Current

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

    // 7. History Search (Read Button with Loading Spinner)
    $('#historyForm').on('submit', function(e) {
        e.preventDefault();
        const start = $('#startDate').val();
        const end = $('#endDate').val();
        const $btn = $(this).find('button[type="submit"]');

        if (!start || !end) return;

        // --- Start Loading State ---
        // Disable button and add a spinner icon
        $btn.prop('disabled', true).html(
            '<span class="spinner-border spinner-border-sm me-1"></span> 読込中...'
        );

        // Simultaneous fetch for both units
        $.when(
            $.getJSON('/api/unit01/history', { start_date: start, end_date: end }),
            $.getJSON('/api/unit02/history', { start_date: start, end_date: end })
        ).done(function(res1, res2) {
            updateStaticCharts(charts.v1, charts.c1, res1[0]);
            updateStaticCharts(charts.v2, charts.c2, res2[0]);

            $('#currentRangeText').text(`表示範囲: ${start} 〜 ${end}`);
        }).always(function() {
            // --- End Loading State ---
            // Re-enable button and restore original text regardless of success/fail
            $btn.prop('disabled', false).text('読込');
        });
    });
    
   // 8. Static Chart 
    function updateStaticCharts(vChart, cChart, data) {
        if (!data || data.length === 0) return;

        // a. Create organized labels for the X-axis (Time only)
        const displayLabels = data.map(d => d.timestamp.split(' ')[1]);
        
        // b. Store the full timestamps for the tooltip
        const fullTimestamps = data.map(d => d.timestamp);
        
        vChart.data.labels = displayLabels;
        vChart.data.datasets[0].data = data.map(d => d.val_voltage);
        // Custom property to store full dates
        vChart.data.datasets[0].fullDates = fullTimestamps; 
        
        cChart.data.labels = displayLabels;
        cChart.data.datasets[0].data = data.map(d => d.val_current);
        cChart.data.datasets[0].fullDates = fullTimestamps;

        // C. Keep your ideal scales
        vChart.options.scales.y.min = 180;
        vChart.options.scales.y.max = 220; 
        cChart.options.scales.y.min = 0;
        cChart.options.scales.y.max = 10;

        // d. Force the Tooltip to show the full date + time
        const tooltipConfig = {
            callbacks: {
                title: function(context) {
                    // Pull the full date from our custom property
                    const index = context[0].dataIndex;
                    return context[0].dataset.fullDates[index];
                }
            }
        };

        vChart.options.plugins.tooltip = tooltipConfig;
        cChart.options.plugins.tooltip = tooltipConfig;

        vChart.update();
        cChart.update();
    }

    // 9. CSV Export (Fixed Logic)
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

    // 10. Reset to Live Mode
    $('#resetLiveBtn').on('click', function() {
        location.reload(); 
    });
});

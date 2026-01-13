$(document).ready(function() {
    const config = window.flaskData;
    const MAX_POINTS = 30; 
    const charts = {};

    // 1. Initialize jQuery UI Date Pickers
    $(".date-picker").datepicker({ dateFormat: "yy-mm-dd" });

    // 2. Real-time Clock Logic
    function updateClock() {
        const now = new Date();
        const timeString = now.getHours().toString().padStart(2, '0') + ":" + 
                           now.getMinutes().toString().padStart(2, '0') + ":" + 
                           now.getSeconds().toString().padStart(2, '0');
        $('#lastUpdated').text("最終更新: " + timeString);
    }
    updateClock();
    setInterval(updateClock, 1000);

    // 3. Chart Creation Helper (Focus on Current Only)
    function createChart(id, color, maxVal) {
        const canvas = document.getElementById(id);
        if (!canvas) return null;
        const ctx = canvas.getContext('2d');
        return new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    borderColor: color,
                    backgroundColor: color + '1A', 
                    fill: true,
                    tension: 0.1,
                    borderWidth: 2,
                    fullDates: [] // Custom property for tooltips
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { 
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            title: (context) => context[0].dataset.fullDates[context[0].dataIndex] || context[0].label
                        }
                    }
                },
                scales: {
                    y: { min: 0, max: maxVal, ticks: { font: { size: 10 } } },
                    x: { ticks: { maxTicksLimit: 8, font: { size: 10 } } }
                },
                elements: { point: { radius: 0 } },
                animation: false
            }
        });
    }

    // 4. Initialize the 4 Current Charts (Escaping IDs with dots)
    // History Top (24h)
    charts.histU1 = createChart('currentChart24h.U1', '#3B82F6', 70.0); 
    charts.histU2 = createChart('currentChart24h.U2', '#FBBF24', 70.0); 
    // Live Bottom (30s)
    charts.liveU1 = createChart('currentChart.U1', '#3B82F6', 70.0); 
    charts.liveU2 = createChart('currentChart.U2', '#FBBF24', 70.0); 

    // 5. Initial Data Load
    if (config.historyU1 && config.historyU2) {
        updateHistoryCharts(charts.histU1, config.historyU1);
        updateHistoryCharts(charts.histU2, config.historyU2);
        
        // Fill initial live charts with the last few points
        config.historyU1.slice(-MAX_POINTS).forEach(d => updateLiveChart(charts.liveU1, d));
        config.historyU2.slice(-MAX_POINTS).forEach(d => updateLiveChart(charts.liveU2, d));
    }

    function updateHistoryCharts(chart, data) {
        chart.data.labels = data.map(d => d.timestamp.split(' ')[1]);
        chart.data.datasets[0].data = data.map(d => d.val_current);
        chart.data.datasets[0].fullDates = data.map(d => d.timestamp);
        chart.update();
    }

    function updateLiveChart(chart, data) {
        const time = data.timestamp.split(' ')[1];
        chart.data.labels.push(time);
        chart.data.datasets[0].data.push(data.val_current);
        chart.data.datasets[0].fullDates.push(data.timestamp);

        if (chart.data.labels.length > MAX_POINTS) {
            chart.data.labels.shift();
            chart.data.datasets[0].data.shift();
            chart.data.datasets[0].fullDates.shift();
        }
        chart.update('none');
    }

    // 6. Real-time Polling (Both Units)
    setInterval(() => {
        $.getJSON(config.apiUrlU1, (data) => updateLiveChart(charts.liveU1, data));
        $.getJSON(config.apiUrlU2, (data) => updateLiveChart(charts.liveU2, data));
    }, config.readIntervalMs);

    // 7. History Search
    $('#historyForm').on('submit', function(e) {
        e.preventDefault();
        const start = $('#startDate').val();
        const end = $('#endDate').val();
        const $btn = $(this).find('button[type="submit"]');

        $btn.prop('disabled', true).html('<span class="spinner-border spinner-border-sm"></span>');

        $.when(
            $.getJSON('/api/unit01/history', { start_date: start, end_date: end }),
            $.getJSON('/api/unit02/history', { start_date: start, end_date: end })
        ).done(function(res1, res2) {
            updateHistoryCharts(charts.histU1, res1[0]);
            updateHistoryCharts(charts.histU2, res2[0]);
            
            const rangeText = `${start} 〜 ${end}`;
            $('#currentRangeText').text(`表示範囲: ${rangeText}`);
            $('#titleU1Hist').text(`UNIT 01: 電流履歴 ${rangeText} (A)`);
            $('#titleU2Hist').text(`UNIT 02: 電流履歴 ${rangeText} (A)`);
        }).always(() => $btn.prop('disabled', false).text('データ読込'));
    });

    // 8. CSV Export (Comparing both units in one file)
    $('#exportCsvBtn').on('click', function() {
        const dataU1 = charts.histU1.data.datasets[0].data;
        const dataU2 = charts.histU2.data.datasets[0].data;
        const labels = charts.histU1.data.datasets[0].fullDates;

        let csv = "Timestamp,Unit01_Current(A),Unit02_Current(A)\n";
        labels.forEach((time, i) => {
            csv += `${time},${dataU1[i] || 0},${dataU2[i] || 0}\n`;
        });

        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = `comparison_${config.unitId || 'units'}.csv`;
        link.click();
    });

    $('#resetLiveBtn').on('click', () => location.reload());
});

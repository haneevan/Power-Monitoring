$(document).ready(function() {
    // 1. Configuration & Initialization
    const config = window.flaskData;
    const MAX_POINTS = 30; // Matches dashboard sliding window
    const charts = {};
    
    // Track timestamps to prevent duplicate points in live view
    let lastTsU1 = "";
    let lastTsU2 = "";

    // 2. Initialize jQuery UI Date Pickers
    $(".date-picker").datepicker({ dateFormat: "yy-mm-dd" });

    // 3. Chart Creation Helper (Styled to match Main Dashboard exactly)
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
                    backgroundColor: color + '33', // 0.2 opacity fill like dashboard
                    fill: true,
                    tension: 0.1,  // Organic smooth curve
                    borderWidth: 2,
                    fullDates: [] 
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { 
                    legend: { display: false },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        callbacks: {
                            title: (context) => context[0].dataset.fullDates[context[0].dataIndex] || context[0].label
                        }
                    }
                },
                scales: {
                    y: { 
                        min: 0, 
                        max: maxVal, 
                        ticks: { font: { size: 10 } },
                        grid: { color: '#f0f0f0' }
                    },
                    x: { 
                        ticks: { maxTicksLimit: 10, font: { size: 9 } },
                        grid: { display: false }
                    }
                },
                elements: { point: { radius: 0 } }, // Professional look (no dots)
                animation: false // No jumping during updates
            }
        });
    }

    // 4. Initialize the 4 Charts (Using underscore IDs for compatibility)
    charts.histU1 = createChart('currentChart24h_U1', '#3B82F6', 70.0); 
    charts.histU2 = createChart('currentChart24h_U2', '#FBBF24', 70.0); 
    charts.liveU1 = createChart('currentChart_U1', '#3B82F6', 70.0); 
    charts.liveU2 = createChart('currentChart_U2', '#FBBF24', 70.0); 

    // 5. Initial Data Load from Flask
    if (config.historyU1 && config.historyU2) {
        updateHistoryCharts(charts.histU1, config.historyU1);
        updateHistoryCharts(charts.histU2, config.historyU2);
        
        // Populate live charts for the sliding effect
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

    // 6. Real-time Polling (Matches main page logic)
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

    // 7. History Search (Dual AJAX Fetch)
    $('#historyForm').on('submit', function(e) {
        e.preventDefault();
        const start = $('#startDate').val();
        const end = $('#endDate').val();
        const $btn = $(this).find('button[type="submit"]');

        if(!start || !end) return;
        $btn.prop('disabled', true).html('<span class="spinner-border spinner-border-sm"></span>');

        $.when(
            $.getJSON('/api/unit01/history', { start_date: start, end_date: end }),
            $.getJSON('/api/unit02/history', { start_date: start, end_date: end })
        ).done(function(res1, res2) {
            updateHistoryCharts(charts.histU1, res1[0]);
            updateHistoryCharts(charts.histU2, res2[0]);
            
            const rangeText = `${start} 〜 ${end}`;
            $('#titleU1Hist').text(`UNIT 01: 電流履歴 ${rangeText}(A)`);
            $('#titleU2Hist').text(`UNIT 02: 電流履歴 ${rangeText}(A)`);
            $('#currentRangeText').text(`表示範囲: ${rangeText}`);
        }).fail(() => alert("通信エラー"))
          .always(() => $btn.prop('disabled', false).text('データ読込'));
    });

    // 8. CSV Export
    $('#exportCsvBtn').on('click', function() {
        const d1 = charts.histU1.data.datasets[0].data;
        const d2 = charts.histU2.data.datasets[0].data;
        const labels = charts.histU1.data.datasets[0].fullDates;

        let csv = "Timestamp,Unit01_Current(A),Unit02_Current(A)\n";
        labels.forEach((time, i) => {
            csv += `${time},${d1[i] || 0},${d2[i] || 0}\n`;
        });

        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = `comparison_report.csv`;
        link.click();
    });

    // 9. FIXED Reset to Live Mode (No Refresh)
    $('#resetLiveBtn').on('click', function() {
        // Reset charts back to initial 24h data from Flask
        updateHistoryCharts(charts.histU1, config.historyU1);
        updateHistoryCharts(charts.histU2, config.historyU2);
        
        // Reset Titles and Range Text
        $('#titleU1Hist').text('UNIT 01: 電流履歴 24h(A)');
        $('#titleU2Hist').text('UNIT 02: 電流履歴 24h(A)');
        $('#currentRangeText').text('表示範囲: 過去24時間');
        
        // Clear input fields
        $('#startDate, #endDate').val('');
    });
});

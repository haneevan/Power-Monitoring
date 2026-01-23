$(document).ready(function() {
    const config = window.flaskData;
    const MAX_POINTS = 30; 
    const charts = {};
    const viewport = document.getElementById('hikakuCarousel');
    
    let lastTsU1 = "";
    let lastTsU2 = "";

    // --- 1. Carousel Navigation Logic ---
    $('#nextBtn').on('click', function() {
        viewport.scrollBy({ left: viewport.clientWidth, behavior: 'smooth' });
    });

    $('#prevBtn').on('click', function() {
        viewport.scrollBy({ left: -viewport.clientWidth, behavior: 'smooth' });
    });

    // --- 2. Statistics Calculation Logic ---
    function calculateAndDisplayStats(dataU1, dataU2) {
        const updateUnitUI = (data, prefix) => {
            if (!data || data.length === 0) {
                const fields = ['v_avg', 'v_peak', 'a_avg', 'a_peak', 'kw_avg', 'kw_peak', 'energy'];
                fields.forEach(f => $(`#${prefix}_${f}`).text('--'));
                return;
            }

            const getStats = (arr) => ({
                avg: (arr.reduce((a, b) => a + b, 0) / arr.length).toFixed(2),
                max: Math.max(...arr).toFixed(2)
            });

            const vList = data.map(d => d.val_voltage || 0);
            const aList = data.map(d => d.val_current || 0);
            const kwList = data.map(d => d.val_power_kw || 0);

            const vStats = getStats(vList);
            const aStats = getStats(aList);
            const kwStats = getStats(kwList);
            const energy = (data[data.length - 1].val_energy_kwh || 0).toFixed(2);

            $(`#${prefix}_v_avg`).text(vStats.avg);
            $(`#${prefix}_v_peak`).text(vStats.max);
            $(`#${prefix}_a_avg`).text(aStats.avg);
            $(`#${prefix}_a_peak`).text(aStats.max);
            $(`#${prefix}_kw_avg`).text(kwStats.avg);
            $(`#${prefix}_kw_peak`).text(kwStats.max);
            $(`#${prefix}_energy`).text(energy);
        };

        updateUnitUI(dataU1, 'u1');
        updateUnitUI(dataU2, 'u2');
    }

    // --- 3. Chart Creation Helpers ---
    function createLineChart(id, color, maxVal) {
        const canvas = document.getElementById(id);
        if (!canvas) return null;
        return new Chart(canvas.getContext('2d'), {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    borderColor: color,
                    backgroundColor: color + '33',
                    fill: true,
                    tension: 0.1,
                    borderWidth: 2,
                    fullDates: [] 
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { min: 0, max: maxVal, ticks: { font: { size: 10 } } },
                    x: { ticks: { maxTicksLimit: 8, font: { size: 9 } } }
                },
                elements: { point: { radius: 0 } },
                animation: false 
            }
        });
    }

    // --- 4. Initialize All Charts ---
    // History & Live Line Charts
    charts.histU1 = createLineChart('currentChart24h_U1', '#3B82F6', 70.0); 
    charts.histU2 = createLineChart('currentChart24h_U2', '#FBBF24', 70.0); 
    charts.liveU1 = createLineChart('currentChart_U1', '#3B82F6', 70.0); 
    charts.liveU2 = createLineChart('currentChart_U2', '#FBBF24', 70.0); 

    // Weekly Bar Chart (Grouped)
    const weeklyCanvas = document.getElementById('weeklyLoadChart');
    if (weeklyCanvas) {
        charts.weekly = new Chart(weeklyCanvas.getContext('2d'), {
            type: 'bar',
            data: {
                labels: [],
                datasets: [
                    { label: 'Unit 01', backgroundColor: '#3B82F6', data: [] },
                    { label: 'Unit 02', backgroundColor: '#FBBF24', data: [] }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { 
                        beginAtZero: true, 
                        suggestedMax: 13, // Scale to match line charts
                        title: { display: true, text: '平均電流 (A)' } 
                    }
                },
                plugins: { legend: { display: true, position: 'bottom' } }
            }
        });
    }

    // --- 5. Data Handling Functions ---
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

    function loadWeeklyChart() {
        console.log("Fetching weekly summary data..."); // Debug check
        $.getJSON('/api/weekly_summary', function(response) {
            if (charts.weekly && response.labels) {
                charts.weekly.data.labels = response.labels;
                charts.weekly.data.datasets[0].data = response.u1;
                charts.weekly.data.datasets[1].data = response.u2;
                charts.weekly.update();
            }
        }).fail(function() { console.error("Could not load weekly summary API."); });
    }

    // --- 6. Initial Execution ---
    if (config.historyU1 && config.historyU2) {
        updateHistoryCharts(charts.histU1, config.historyU1);
        updateHistoryCharts(charts.histU2, config.historyU2);
        calculateAndDisplayStats(config.historyU1, config.historyU2);
        
        config.historyU1.slice(-MAX_POINTS).forEach(d => updateLiveChart(charts.liveU1, d));
        config.historyU2.slice(-MAX_POINTS).forEach(d => updateLiveChart(charts.liveU2, d));
    }
    
    // Trigger Weekly Summary Load
    loadWeeklyChart();

    // --- 7. Polling & Events ---
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

    $(".date-picker").datepicker({ dateFormat: "yy-mm-dd" });

    $('#historyForm').on('submit', function(e) {
    e.preventDefault();
    const start = $('#startDate').val();
    const end = $('#endDate').val();
    
    if (!start || !end) return; // Prevent empty searches

    const $btn = $(this).find('button[type="submit"]');
    $btn.prop('disabled', true).html('<span class="spinner-border spinner-border-sm"></span>');

    $.when(
        $.getJSON('/api/unit01/history', { start_date: start, end_date: end }),
        $.getJSON('/api/unit02/history', { start_date: start, end_date: end })
    ).done(function(res1, res2) {
        // 1. Update the Charts
        updateHistoryCharts(charts.histU1, res1[0]);
        updateHistoryCharts(charts.histU2, res2[0]);
        
        // 2. Update the Statistics Cards
        calculateAndDisplayStats(res1[0], res2[0]);
        
        // 3. UPDATE THE TITLES (The RangeTitle logic)
        const rangeText = `${start} 〜 ${end}`;
        $('#currentRangeText').text(`表示範囲: ${rangeText}`);
        $('#titleU1Hist').text(`UNIT 01: 電流履歴 [${rangeText}] (A)`);
        $('#titleU2Hist').text(`UNIT 02: 電流履歴 [${rangeText}] (A)`);
        $('#titleU1S2Statistics').text(`UNIT 01 統計詳細 [${rangeText}]`);
        $('#titleU2S2Statistics').text(`UNIT 01 統計詳細 [${rangeText}]`)

    }).always(() => {
        $btn.prop('disabled', false).text('データ読込');
    });
});

    $('#exportCsvBtn').on('click', function() {
        const d1 = charts.histU1.data.datasets[0].data;
        const l1 = charts.histU1.data.datasets[0].fullDates;
        const d2 = charts.histU2.data.datasets[0].data;
        const l2 = charts.histU2.data.datasets[0].fullDates;

        let csv = "\ufeffTimestamp,Unit01_Current(A),Unit02_Current(A)\n";
        const rows = Math.max(d1.length, d2.length);

        for (let i = 0; i < rows; i++) {
            const ts = l1[i] || l2[i] || "";
            const v1 = d1[i] !== undefined ? d1[i] : "";
            const v2 = d2[i] !== undefined ? d2[i] : "";
            csv += `${ts},${v1},${v2}\n`;
        }

        const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8;' }));
        const link = document.createElement("a");
        link.setAttribute("href", url);
        link.setAttribute("download", `hikaku_export_${new Date().toISOString().slice(0,10)}.csv`);
        link.click();
    });
    
// --- RESET BUTTON FIX ---
$('#resetLiveBtn').on('click', function() {
    // 1. Check if initial history data exists in config
    if (config.historyU1 && config.historyU2) {
        // 2. Re-render the History Charts with the original 24h data
        updateHistoryCharts(charts.histU1, config.historyU1);
        updateHistoryCharts(charts.histU2, config.historyU2);
        
        // 3. Re-calculate the top statistics cards for the original 24h
        calculateAndDisplayStats(config.historyU1, config.historyU2);
    }
    
    // 4. Reset the UI text elements
    $('#currentRangeText').text('表示範囲: 過去24時間');
    $('#titleU1Hist').text('UNIT 01: 電流履歴 24h(A)');
    $('#titleU2Hist').text('UNIT 02: 電流履歴 24h(A)');
    $('#titleU1S2Statistics').text('UNIT 01 統計詳細過去24ｈ');
    $('#titleU2S2Statistics').text('UNIT 02 統計詳細過去24ｈ');
    
    // 5. Clear the input fields in the date picker
    $('#startDate, #endDate').val('');
    
    console.log("History charts reset to initial 24h data.");
});    

});

// file name = script.js (FINAL FIXED VERSION)

// --- 1. Get Dynamic Data from Window Object ---
const READ_INTERVAL_MS = window.flaskData.readIntervalMs;
const API_URL = window.flaskData.apiUrl;
const HISTORY_HOURS = window.flaskData.historyHours;
let historyData = window.flaskData.history; 
let voltageChartInstance, currentChartInstance; // REMOVED: energyChartInstance


// --- 2. Live Data Fetcher (Unchanged) ---
function updateLiveMetrics() {
    fetch(API_URL)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.val_voltage) {
                document.getElementById('live-voltage').textContent = data.val_voltage.toFixed(2);
                document.getElementById('live-current').textContent = data.val_current.toFixed(3);
                document.getElementById('live-energy').textContent = data.val_energy_kwh.toFixed(3);
                
                const now = new Date();
                document.getElementById('lastUpdated').textContent = `Last Updated: ${now.toLocaleTimeString('ja-JP', { hour12: false })}`; 
            }
        })
        .catch(error => {
            console.error("Failed to fetch live data:", error);
        });
}

document.getElementById('manualRefreshBtn').addEventListener('click', function() {
    window.location.reload(true); 
});

setInterval(updateLiveMetrics, READ_INTERVAL_MS); 
updateLiveMetrics();


// --- Date Picker Initialization (Unchanged) ---
$(function() {
    $(".date-picker").datepicker({
        dateFormat: 'yy-mm-dd',
        showAnim: 'slideDown', 
        changeMonth: true,
        changeYear: true,
        showButtonPanel: true
    });
});


// --- 3. Chart Rendering Core Function ---

// Configuration for charts - FIXED FOR TIME AXIS AND DARK MODE
const chartDefaults = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: { display: true, labels: { color: '#B0B0B0' } }, // Dark Mode: Light gray legend text
        title: { display: false }, 
    },
    scales: {
        x: {
            // CRITICAL FIX 1: Set the scale type to 'time'
            type: 'time', 
            time: {
                // The format of the timestamp string coming from the server
                parser: 'yyyy-MM-dd HH:mm:ss', 
                unit: 'hour', 
                displayFormats: {
                    hour: 'MMM d HH:mm',
                    day: 'MMM d',
                    week: 'MMM d',
                    month: 'MMM yyyy'
                }
            },
            ticks: { 
                maxTicksLimit: 12, 
                color: '#B0B0B0', // Dark Mode: Light gray ticks
                source: 'auto', 
            }, 
            grid: { color: '#333333' }, // Dark Mode: Darker grid lines
        },
        y: {
            ticks: { color: '#B0B0B0' }, // Dark Mode: Light gray ticks
            grid: { color: '#333333' }, // Dark Mode: Darker grid lines
            beginAtZero: false 
        }
    }
};

function renderCharts(data, rangeDescription = `Last ${HISTORY_HOURS} hrs`) {
    // Destroy existing charts
    if (voltageChartInstance) voltageChartInstance.destroy();
    if (currentChartInstance) currentChartInstance.destroy();

    if (data.length === 0) {
        alert("No data found for the selected date range.");
        return; 
    }
    
    const MAX_CHART_POINTS = 5000; 
    const dataSlice = data.slice(-MAX_CHART_POINTS); 
    
    // CRITICAL FIX 2: Pass the FULL timestamp string as the label.
    const labels = dataSlice.map(item => item.timestamp); 
    
    const voltageData = dataSlice.map(item => parseFloat(item.val_voltage));
    const currentData = dataSlice.map(item => parseFloat(item.val_current));

    // Update the card titles 
    document.querySelector('#voltageChart').closest('.card').querySelector('.card-title').textContent = `Voltage (V) History (${rangeDescription})`;
    document.querySelector('#currentChart').closest('.card').querySelector('.card-title').textContent = `Current (A) History (${rangeDescription})`;


    // A. Voltage History Chart
    const voltageCtx = document.getElementById('voltageChart').getContext('2d');
    voltageChartInstance = new Chart(voltageCtx, {
        type: 'line',
        data: {
            labels: labels, // Uses full timestamp string for correct scaling
            datasets: [{
                label: 'Voltage (V)',
                data: voltageData,
                borderColor: '#FFC107', 
                backgroundColor: 'rgba(255, 193, 7, 0.1)',
                tension: 0.3,
                borderWidth: 2,
                pointRadius: 0,
                fill: false, 
            }]
        },
        options: {
            ...chartDefaults,
            scales: {...chartDefaults.scales, y: {...chartDefaults.scales.y, beginAtZero: false}}, 
        }
    });

    // B. Current History Chart
    const currentCtx = document.getElementById('currentChart').getContext('2d');
    currentChartInstance = new Chart(currentCtx, {
        type: 'line',
        data: {
            labels: labels, // Uses full timestamp string for correct scaling
            datasets: [{
                label: 'Current (A)',
                data: currentData,
                borderColor: '#DC3545', 
                backgroundColor: 'rgba(220, 53, 69, 0.1)',
                tension: 0.3,
                borderWidth: 2,
                pointRadius: 0,
                fill: false, 
            }]
        },
        options: {
            ...chartDefaults,
            scales: {...chartDefaults.scales, y: {...chartDefaults.scales.y, beginAtZero: true}}, 
        }
    });
}


// --- 4. Date Range Submission Logic (Unchanged) ---
const historyForm = document.getElementById('historyForm');
const currentRangeText = document.getElementById('currentRangeText');

historyForm.addEventListener('submit', function(event) {
    event.preventDefault(); 
    
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    
    if (!startDate || !endDate) {
        alert("Please select both a start and an end date.");
        return;
    }
    
    const rangeDescription = `${startDate} to ${endDate}`;
    const rangeApiUrl = `/api/history?start_date=${startDate}&end_date=${endDate}`;
    
    fetch(rangeApiUrl)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            historyData = data; 
            
            // Render charts with new data and the date range description
            renderCharts(historyData, rangeDescription); 
            
            // Update the range display text
            currentRangeText.textContent = `Showing data from ${rangeDescription}`;
        })
        .catch(error => {
            console.error("Failed to fetch historical data:", error);
            alert("Error loading data for the selected range. Please check the date format (YYYY-MM-DD) and ensure the server is running.");
        });
});


// --- 5. Initial Chart Render (Unchanged) ---
const initialRange = currentRangeText.textContent.replace('Showing default history (', '').replace(')', '').trim();

// Render charts using the data injected from Flask on initial load
renderCharts(historyData, initialRange);

// file name = static/script.js

// --- 1. Get Dynamic Data from Window Object ---
const READ_INTERVAL_MS = window.flaskData.readIntervalMs;
const API_URL = window.flaskData.apiUrl;
const historyData = window.flaskData.history;


// --- 2. Live Data Fetcher ---
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
            } else {
                console.warn("Received empty data from /api/latest");
            }
        })
        .catch(error => {
            console.error("Failed to fetch live data:", error);
        });
}

document.getElementById('manualRefreshBtn').addEventListener('click', function() {
    window.location.reload(true); 
});

// Start the real-time update loop
setInterval(updateLiveMetrics, READ_INTERVAL_MS); 
updateLiveMetrics();


// --- 3. Chart Rendering ---
// This entire section uses the 'historyData' variable retrieved above.

// If historyData is empty, exit gracefully
if (historyData.length === 0) {
    console.log("No historical data to render charts.");
    // Exit the script execution early
    // return; 
}

// Use the last 500 points
const dataSlice = historyData.slice(-500); 
const labels = dataSlice.map(item => item.timestamp.split(' ')[1]); 

// Ensure values are explicitly parsed as floats
const voltageData = dataSlice.map(item => parseFloat(item.val_voltage));
const currentData = dataSlice.map(item => parseFloat(item.val_current));

// Configuration for dark mode charts
const chartDefaults = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: { display: true, labels: { color: '#e0e0e0' } },
        title: { display: false },
    },
    scales: {
        x: {
            ticks: {
                maxTicksLimit: 12, 
                color: '#888'
            },
            grid: { color: '#333' },
        },
        y: {
            ticks: { color: '#888' },
            grid: { color: '#333' },
            beginAtZero: false 
        }
    }
};

// A. Voltage History Chart
const voltageCtx = document.getElementById('voltageChart').getContext('2d');
new Chart(voltageCtx, {
    type: 'line',
    data: {
        labels: labels,
        datasets: [{
            label: 'Voltage (V)',
            data: voltageData,
            borderColor: '#FFC107', 
            backgroundColor: 'rgba(255, 193, 7, 0.2)',
            tension: 0.3,
            borderWidth: 2,
            pointRadius: 0,
            fill: true,
        }]
    },
    options: chartDefaults
});


// B. Current History Chart
const currentCtx = document.getElementById('currentChart').getContext('2d');
new Chart(currentCtx, {
    type: 'line',
    data: {
        labels: labels,
        datasets: [{
            label: 'Current (A)',
            data: currentData,
            borderColor: '#DC3545', 
            backgroundColor: 'rgba(220, 53, 69, 0.2)',
            tension: 0.3,
            borderWidth: 2,
            pointRadius: 0,
            fill: true,
        }]
    },
    options: chartDefaults
});

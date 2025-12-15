// file name = script.js

// --- 1. Get Dynamic Data from Window Object ---
const READ_INTERVAL_MS = window.flaskData.readIntervalMs;
const API_URL = window.flaskData.apiUrl;
const HISTORY_HOURS = window.flaskData.historyHours;
let historyData = window.flaskData.history; 
let voltageChartInstance, currentChartInstance; 


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
                document.getElementById('live-energy').textContent = data.val_energy_kwh.toFixed(2);
                
                const now = new Date();
                // Japanese locale for consistent time display
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

// Start the real-time update loop
setInterval(updateLiveMetrics, READ_INTERVAL_MS); 
updateLiveMetrics();


// --- Date Picker Initialization ---
$(function() {
    $(".date-picker").datepicker({
        dateFormat: 'yy-mm-dd', // YYYY-MM-DD format for API
        showAnim: 'slideDown', 
        changeMonth: true,
        changeYear: true,
        showButtonPanel: true
    });
});


// --- 3. Chart Rendering Core Function (FIXED) ---

const chartDefaults = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: { display: true, labels: { color: '#333' } },
        title: { display: false }, 
    },
    scales: {
        x: {
            // FIX 1: Set scale type to 'time'
            type: 'time', 
            time: {
                // Configure parsing for the timestamp string format from Python/SQLite
                parser: 'yyyy-MM-dd HH:mm:ss', 
                unit: 'hour', // Default starting unit
                displayFormats: {
                    minute: 'HH:mm',
                    hour: 'MMM dd, HH:mm',
                    day: 'MMM dd',
                    month: 'MMM yyyy'
                },
                tooltipFormat: 'yyyy-MM-dd HH:mm:ss', // Detailed tooltip format
            },
            ticks: { maxTicksLimit: 12, color: '#6C757D' }, 
            grid: { color: '#E9ECEF' }, 
        },
        y: {
            ticks: { color: '#6C757D' },
            grid: { color: '#E9ECEF' },
            beginAtZero: false 
        }
    }
};

function renderCharts(data, rangeDescription = `Last ${HISTORY_HOURS} hrs`) {
    // Destroy existing charts if they exist
    if (voltageChartInstance) voltageChartInstance.destroy();
    if (currentChartInstance) currentChartInstance.destroy();

    if (data.length === 0) {
        alert("No data found for the selected date range.");
        return; 
    }
    
    // --- CHART RANGE MODIFICATION ---
    const MAX_CHART_POINTS = 5000; 
    const dataSlice = data.slice(-MAX_CHART_POINTS); 
    // --------------------------------
    
    // FIX 2: Prepare data in {x: timestamp, y: value} format for Time Scale
    const voltageData = dataSlice.map(item => ({
        x: item.timestamp,
        y: parseFloat(item.val_voltage)
    }));
    const currentData = dataSlice.map(item => ({
        x: item.timestamp,
        y: parseFloat(item.val_current)
    }));
    
    // The labels array is no longer strictly necessary for plotting, 
    // but the datasets structure is critical.
    const labels = dataSlice.map(item => item.timestamp); 

    // Update the card titles (H5 elements) for better visibility
    document.querySelector('#voltageChart').closest('.card').querySelector('.card-title').textContent = `Voltage (V) History (${rangeDescription})`;
    document.querySelector('#currentChart').closest('.card').querySelector('.card-title').textContent = `Current (A) History (${rangeDescription})`;

    // A. Voltage History Chart
    const voltageCtx = document.getElementById('voltageChart').getContext('2d');
    voltageChartInstance = new Chart(voltageCtx, {
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
    currentChartInstance = new Chart(currentCtx, {
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
}


// --- 4. Date Range Submission Logic ---

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


// --- 5. Initial Chart Render ---

// Get initial range text from HTML (e.g., "Last 24 hrs")
const initialRange = currentRangeText.textContent.replace('Showing default history (', '').replace(')', '').trim();

// Render charts using the data injected from Flask on initial load
renderCharts(historyData, initialRange);

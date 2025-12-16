// file name = script.js

// --- 1. Get Dynamic Data from Window Object ---
const READ_INTERVAL_MS = window.flaskData.readIntervalMs;
const API_URL = window.flaskData.apiUrl;
const HISTORY_HOURS = window.flaskData.historyHours;
let historyData = window.flaskData.history; 
let voltageChartInstance, currentChartInstance; 

// Utility function to format timestamp string into a readable label
// This logic is adapted from your history.js for cross-day display.
function formatTimestampForLabel(timestampStr, isMultiDay) {
    const d = new Date(timestampStr);
    
    // Check if the date object is valid
    if (isNaN(d)) {
        console.error("Invalid timestamp:", timestampStr);
        return timestampStr; // Return raw string if parsing failed
    }
    
    // Japanese locale formatting options
    const dateOptions = { month: '2-digit', day: '2-digit' };
    const timeOptions = { hour: '2-digit', minute: '2-digit', hour12: false };

    if (isMultiDay) {
        // Example: "03/15 10:30"
        return d.toLocaleDateString('ja-JP', dateOptions) + ' ' + d.toLocaleTimeString('ja-JP', timeOptions);
    } else {
        // Example: "10:30"
        return d.toLocaleTimeString('ja-JP', timeOptions);
    }
}


// --- 2. Live Data Fetcher (No change) ---
function updateLiveMetrics() {
    // ... (Keep existing updateLiveMetrics function) ...
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
                // Japanese locale for consistent time display
                document.getElementById('lastUpdated').textContent = `最終更新日: ${now.toLocaleTimeString('ja-JP', { hour12: false })}`; 
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


// --- Date Picker Initialization (No change) ---
$(function() {
    $(".date-picker").datepicker({
        dateFormat: 'yy-mm-dd', // YYYY-MM-DD format for API
        showAnim: 'slideDown', 
        changeMonth: true,
        changeYear: true,
        showButtonPanel: true
    });
});


// --- 3. Chart Rendering Core Function (MAJOR REVISION) ---

// Define the chart defaults using the Category Scale approach
const chartDefaults = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: { display: true, labels: { color: '#333' } },
        title: { display: false }, 
    },
    scales: {
        x: {
            // REVERTED to default Category Scale. We manually format the labels.
            type: 'category', 
            ticks: { 
                maxTicksLimit: 12, 
                color: '#6C757D',
                // Tweak to prevent label overlap on dense data
                autoSkip: true, 
            }, 
            grid: { color: '#E9ECEF' }, 
        },
        y: {
            ticks: { color: '#6C757D' },
            grid: { color: '#E9ECEF' },
            beginAtZero: false 
        }
    }
};

function renderCharts(data, rangeDescription = `過去 ${HISTORY_HOURS} 時間`, startDateStr = null, endDateStr = null) {
    // Destroy existing charts if they exist
    if (voltageChartInstance) voltageChartInstance.destroy();
    if (currentChartInstance) currentChartInstance.destroy();

    if (data.length === 0) {
        alert("No data found for the selected date range.");
        return; 
    }
    
    // --- Determine if we are plotting multi-day data ---
    // If the start and end dates are different (and provided), treat as multi-day.
    const isMultiDay = (startDateStr !== endDateStr) && (startDateStr && endDateStr);

    // --- Prepare data for Chart.js (Category Scale) ---
    
    // 1. Create formatted string labels (X-axis) using the utility function
    const labels = data.map(item => 
        formatTimestampForLabel(item.timestamp, isMultiDay)
    );

    // 2. Create simple arrays of Y-values
    const voltageData = data.map(item => parseFloat(item.val_voltage));
    const currentData = data.map(item => parseFloat(item.val_current));

    // Update the card titles (H5 elements)
    document.querySelector('#voltageChart').closest('.card').querySelector('.card-title').textContent = `電圧履歴(V)  (${rangeDescription})`;
    document.querySelector('#currentChart').closest('.card').querySelector('.card-title').textContent = `電流履歴(A)  (${rangeDescription})`;

    // A. Voltage History Chart
    const voltageCtx = document.getElementById('voltageChart').getContext('2d');
    voltageChartInstance = new Chart(voltageCtx, {
        type: 'line',
        data: {
            labels: labels, // Use the manually formatted string labels
            datasets: [{ 
                label: 'Voltage (V)',
                data: voltageData, // Use the simple array of numbers
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
            labels: labels, // Use the manually formatted string labels
            datasets: [{
                label: 'Current (A)',
                data: currentData, // Use the simple array of numbers
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


// --- 4. Date Range Submission Logic (MINOR REVISION) ---

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
    
    const rangeDescription = `${startDate} ～ ${endDate}`;
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
            
            // Pass start and end dates to renderCharts to control label formatting
            renderCharts(historyData, rangeDescription, startDate, endDate); 
            
            // Update the range display text
            currentRangeText.textContent = `${rangeDescription} のデータを表示中`;
        })
        .catch(error => {
            console.error("Failed to fetch historical data:", error);
            alert("Error loading data for the selected range. Please check the date format (YYYY-MM-DD) and ensure the server is running.");
        });
});


// --- 5. Initial Chart Render (MINOR REVISION) ---

// Get initial range text from HTML (e.g., "Last 24 hrs")
const initialRange = currentRangeText.textContent.replace('Showing default history (', '').replace(')', '').trim();

// On initial load, treat it as single day unless HISTORY_HOURS > 24
// We don't have the explicit start/end date strings here, so we default isMultiDay to false
renderCharts(historyData, initialRange, null, null);

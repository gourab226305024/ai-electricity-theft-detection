// ============================================
// CONFIGURATION - YOUR FASTAPI BACKEND URL
// ============================================
const API_BASE_URL = 'http://127.0.0.1:8000';

const API_ENDPOINTS = {
    generate: `${API_BASE_URL}/generate`,
    detect: `${API_BASE_URL}/detect`,
    root: `${API_BASE_URL}/`,
};

// ============================================
// GLOBAL STATE
// ============================================
let chart = null;
let currentMode = 'normal';
let detectionHistory = [];
let autoRefreshInterval = null;
let statsData = {
    totalReadings: 0,
    averageConsumption: 0,
    peakConsumption: 0,
    lowestConsumption: 0,
    anomaliesDetected: 0,
    uptime: 0
};

// ============================================
// INITIALIZATION
// ============================================
document.addEventListener('DOMContentLoaded', function() {
    console.log('Dashboard initialized. Backend:', API_BASE_URL);
    initializeUI();
    testBackendConnection();
    startUptimeCounter();
});

function initializeUI() {
    document.getElementById('meterId').textContent = 'SM-LIVE-001';
    document.getElementById('meterArea').textContent = 'Main Grid';
    document.getElementById('tariffType').textContent = 'Commercial';
    document.getElementById('meterMode').textContent = 'Live Data';
    document.getElementById('systemStatus').textContent = 'Active';
    
    // Initialize stats
    updateStats();
}

function testBackendConnection() {
    try {
        console.log('Testing backend connection...');
        const response = fetch(API_ENDPOINTS.root);
        if (response.ok) {
            console.log('✅ Backend connected');
            updateConnectionStatus(true);
        } else {
            console.error('❌ Backend responded with error');
            updateConnectionStatus(false);
        }
    } catch (error) {
        console.error('❌ Backend connection failed:', error);
        updateConnectionStatus(false);
        showErrorMessage('Cannot connect to backend. Make sure FastAPI server is running on port 8000');
    }
}

function startUptimeCounter() {
    setInterval(() => {
        statsData.uptime++;
        updateStats();
    }, 1000);
}

// ============================================
// MODE SWITCHING & DATA GENERATION
// ============================================

async function loadNormalUsage() {
    try {
        console.log('Switching to NORMAL mode...');
        const response = await fetch(`${API_ENDPOINTS.generate}/normal`);
        
        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Mode switched:', data);
        
        currentMode = 'normal';
        detectionHistory = [];
        clearChart();
        startAutoRefresh();
        await runDetection();
        updateConnectionStatus(true);
    } catch (error) {
        console.error('Error loading normal usage:', error);
        showErrorMessage('Failed to switch to normal mode: ' + error.message);
        updateConnectionStatus(false);
    }
}

async function loadTheftScenario() {
    try {
        console.log('Switching to THEFT mode...');
        const response = await fetch(`${API_ENDPOINTS.generate}/theft`);
        
        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Mode switched:', data);
        
        currentMode = 'theft';
        detectionHistory = [];
        clearChart();
        startAutoRefresh();
        await runDetection();
        updateConnectionStatus(true);
    } catch (error) {
        console.error('Error loading theft scenario:', error);
        showErrorMessage('Failed to switch to theft mode: ' + error.message);
        updateConnectionStatus(false);
    }
}

// ============================================
// ANOMALY DETECTION
// ============================================

async function runDetection() {
    try {
        console.log('Running anomaly detection...');
        const response = await fetch(API_ENDPOINTS.detect);
        
        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }
        
        const detectionData = await response.json();
        console.log('Detection result:', detectionData);
        
        // Add to history
        detectionHistory.push({
            timestamp: new Date().toLocaleTimeString(),
            consumption: detectionData.consumption,
            risk_score: detectionData.risk_score,
            anomaly: detectionData.anomaly,
            reason: detectionData.reason
        });
        
        // Keep only last 30 readings
        if (detectionHistory.length > 30) {
            detectionHistory.shift();
        }
        
        // Update statistics
        updateStatisticsFromHistory();
        
        // Update UI
        updateChart(detectionHistory);
        updateStatus(detectionData);
        updateConnectionStatus(true);
        
    } catch (error) {
        console.error('Error in anomaly detection:', error);
        showErrorMessage('Detection failed: ' + error.message);
        updateConnectionStatus(false);
    }
}

function updateStatisticsFromHistory() {
    if (detectionHistory.length === 0) return;
    
    const consumptionValues = detectionHistory.map(h => h.consumption);
    const riskScores = detectionHistory.map(h => h.risk_score);
    
    statsData.totalReadings = detectionHistory.length;
    statsData.averageConsumption = (consumptionValues.reduce((a, b) => a + b, 0) / consumptionValues.length).toFixed(2);
    statsData.peakConsumption = Math.max(...consumptionValues).toFixed(2);
    statsData.lowestConsumption = Math.min(...consumptionValues).toFixed(2);
    statsData.anomaliesDetected = detectionHistory.filter(h => h.anomaly === 1).length;
}

function startAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
    }
    
    autoRefreshInterval = setInterval(() => {
        runDetection();
    }, 2000);
    
    console.log('Auto-refresh started (every 2 seconds)');
}

function stopAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
        console.log('Auto-refresh stopped');
    }
}

async function refreshData() {
    console.log('Manual refresh triggered');
    await runDetection();
}

function showErrorState() {
    stopAutoRefresh();
    updateStatus({
        consumption: 0,
        risk_score: 0,
        anomaly: 0,
        reason: '❌ Simulated error state'
    });
    updateConnectionStatus(false);
}

function exportData() {
    if (detectionHistory.length === 0) {
        alert('No data to export');
        return;
    }
    
    const csv = 'Timestamp,Consumption (kWh),Risk Score (%),Anomaly\n' + 
        detectionHistory.map(h => `${h.timestamp},${h.consumption},${h.risk_score},${h.anomaly}`).join('\n');
    
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `meter-data-${new Date().toISOString().slice(0,10)}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
    
    console.log('Data exported to CSV');
}

// ============================================
// CHART UPDATE
// ============================================

function updateChart(history) {
    const ctx = document.getElementById('consumptionChart').getContext('2d');
    
    const labels = history.map(item => item.timestamp);
    const consumptionValues = history.map(item => item.consumption);
    const riskScoreValues = history.map(item => item.risk_score);
    
    const hasAnomaly = history.some(item => item.anomaly === 1);
    const borderColor = hasAnomaly ? '#e74c3c' : '#3498db';
    const backgroundColor = hasAnomaly ? 'rgba(231, 76, 60, 0.05)' : 'rgba(52, 152, 219, 0.05)';
    
    if (chart) {
        chart.destroy();
    }
    
    chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Consumption (kWh)',
                    data: consumptionValues,
                    borderColor: borderColor,
                    backgroundColor: backgroundColor,
                    borderWidth: 2.5,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 4,
                    pointBackgroundColor: borderColor,
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    pointHoverRadius: 6,
                    yAxisID: 'y',
                },
                {
                    label: 'Risk Score (%)',
                    data: riskScoreValues,
                    borderColor: '#f39c12',
                    backgroundColor: 'rgba(243, 156, 18, 0.05)',
                    borderWidth: 2,
                    borderDash: [5, 5],
                    fill: false,
                    tension: 0.4,
                    pointRadius: 2,
                    pointBackgroundColor: '#f39c12',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 1,
                    pointHoverRadius: 4,
                    yAxisID: 'y1',
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 16,
                        font: { size: 13, weight: '500' },
                        color: '#2c3e50'
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(44, 62, 80, 0.9)',
                    padding: 12,
                    titleFont: { size: 13, weight: '600' },
                    bodyFont: { size: 12 },
                    borderColor: '#3498db',
                    borderWidth: 1,
                }
            },
            scales: {
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: 'Consumption (kWh)',
                        color: '#3498db',
                        font: { weight: '600' }
                    },
                    ticks: {
                        font: { size: 12 },
                        color: '#7f8c8d',
                    },
                    grid: {
                        color: 'rgba(200, 200, 200, 0.1)',
                        drawBorder: false
                    }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    min: 0,
                    max: 100,
                    title: {
                        display: true,
                        text: 'Risk Score (%)',
                        color: '#f39c12',
                        font: { weight: '600' }
                    },
                    ticks: {
                        font: { size: 12 },
                        color: '#7f8c8d',
                        callback: function(value) {
                            return value + '%';
                        }
                    },
                    grid: {
                        drawOnChartArea: false,
                        drawBorder: false
                    }
                },
                x: {
                    ticks: {
                        font: { size: 11 },
                        color: '#7f8c8d',
                        maxRotation: 45,
                        minRotation: 0
                    },
                    grid: {
                        display: false,
                        drawBorder: false
                    }
                }
            }
        }
    });
    
    document.getElementById('chartInfo').textContent = `Live data: ${labels.length} readings | Mode: ${currentMode.toUpperCase()}`;
}

function clearChart() {
    if (chart) {
        chart.destroy();
        chart = null;
    }
}

// ============================================
// STATUS UPDATE
// ============================================

function updateStatus(detectionData) {
    const consumption = detectionData.consumption || 0;
    const riskScore = detectionData.risk_score || 0;
    const anomaly = detectionData.anomaly || 0;
    const reason = detectionData.reason || 'No data';
    
    const state = anomaly === 1 ? 'Suspicious' : 'Normal';
    const riskLevel = getRiskLevel(riskScore);
    
    document.getElementById('consumptionState').textContent = state;
    
    const scoreElement = document.getElementById('riskScore');
    scoreElement.textContent = riskScore + '%';
    scoreElement.className = `status-value risk-${riskLevel}`;
    
    const badgeElement = document.getElementById('riskLevel');
    badgeElement.textContent = riskLevel.charAt(0).toUpperCase() + riskLevel.slice(1);
    badgeElement.className = `risk-badge risk-badge-${riskLevel}`;
    
    document.getElementById('reasonText').textContent = reason;
    
    const reasonEl = document.getElementById('reasonText');
    if (anomaly === 1) {
        reasonEl.style.borderColor = '#e74c3c';
        reasonEl.style.backgroundColor = '#fef5f5';
    } else {
        reasonEl.style.borderColor = '#95a5a6';
        reasonEl.style.backgroundColor = '#fafbfc';
    }
    
    // Update knob indicator
    updateKnobIndicator(consumption);
}

function updateStats() {
    document.getElementById('totalReadings').textContent = statsData.totalReadings;
    document.getElementById('avgConsumption').textContent = statsData.averageConsumption + ' kWh';
    document.getElementById('peakConsumption').textContent = statsData.peakConsumption + ' kWh';
    document.getElementById('anomalyCount').textContent = statsData.anomaliesDetected;
    document.getElementById('systemUptime').textContent = formatUptime(statsData.uptime);
}

function formatUptime(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return `${hours}h ${minutes}m ${secs}s`;
}

function getRiskLevel(score) {
    if (score < 33) return 'low';
    if (score < 66) return 'medium';
    return 'high';
}

function updateConnectionStatus(isConnected) {
    const badge = document.getElementById('connectionStatus');
    if (isConnected) {
        badge.className = 'status-badge status-active';
        badge.textContent = 'Connected';
    } else {
        badge.className = 'status-badge status-inactive';
        badge.textContent = 'Disconnected';
    }
}

function showErrorMessage(message) {
    console.error(message);
    document.getElementById('reasonText').textContent = `❌ ${message}`;
    document.getElementById('reasonText').style.borderColor = '#e74c3c';
    document.getElementById('reasonText').style.backgroundColor = '#fef5f5';
}

// ============================================
// THEME TOGGLE
// ============================================

function toggleDarkMode() {
    document.body.classList.toggle('dark-mode');
    localStorage.setItem('darkMode', document.body.classList.contains('dark-mode'));
}

// Load dark mode preference
if (localStorage.getItem('darkMode') === 'true') {
    document.body.classList.add('dark-mode');
}
function updateKnobIndicator(consumption) {
    const rawValue = Math.round((consumption / 50.0) * 1023);
    const percentage = Math.round((rawValue / 1023) * 100);
    const degrees = (rawValue / 1023) * 360;
    
    document.getElementById('knobPointer').style.transform = `rotate(${degrees}deg)`;
    document.getElementById('knobValue').textContent = rawValue;
    document.getElementById('knobRaw').textContent = `${rawValue}/1023`;
    document.getElementById('knobConsumption').textContent = consumption.toFixed(2) + ' kWh';
    document.getElementById('knobPosition').textContent = percentage + '%';
}
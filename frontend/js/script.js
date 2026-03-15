document.addEventListener("DOMContentLoaded", () => {
    const analyzeBtn = document.getElementById('analyzeBtn');
    
    analyzeBtn.addEventListener('click', () => {
        const fileInput = document.getElementById('csvFileInput');
        const statusBox = document.getElementById('statusIndicator');
        
        if (fileInput.files.length === 0) {
            statusBox.innerText = "Please select a processed CSV file first.";
            statusBox.className = "status-box risk";
            return;
        }

        const formData = new FormData();
        formData.append("file", fileInput.files[0]);

        statusBox.innerText = "Analyzing data with HMM...";
        statusBox.className = "status-box";

        fetch('http://127.0.0.1:8000/api/market-status', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => { throw new Error(err.detail); });
            }
            return response.json();
        })
        .then(data => updateDashboard(data))
        .catch(error => {
            statusBox.innerText = `Error: ${error.message}`;
            statusBox.className = "status-box risk";
        });
    });
});

function updateDashboard(data) {
    const statusBox = document.getElementById('statusIndicator');
    statusBox.innerText = `AI Signal: ${data.current_status} | Regime: ${data.current_regime_id} | VIX: ${data.latest_vix.toFixed(2)}`;
    
    if (data.current_status.includes("Safe")) {
        statusBox.className = "status-box safe";
    } else {
        statusBox.className = "status-box risk";
    }

    const trace = {
        x: data.chart_data.dates,
        y: data.chart_data.prices,
        type: 'scatter',
        mode: 'lines+markers',
        marker: {
            color: data.chart_data.regimes,
            colorscale: 'Viridis', 
            size: 6
        },
        line: { color: '#cccccc', width: 1 },
        name: 'S&P 500'
    };

    const layout = {
        title: 'S&P 500 Price (Colored by Hidden Markov Regime)',
        xaxis: { title: 'Date' },
        yaxis: { title: 'Price' },
        hovermode: 'closest'
    };

    Plotly.newPlot('chart', [trace], layout);
}
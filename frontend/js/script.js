const API_BASE = "http://127.0.0.1:8000";
let _lastCsvData = null; // restored from cache on load

document.addEventListener("DOMContentLoaded", () => {
    checkBackendHealth();
    loadAnalysisPlots();
    setupTabs();
    setupDarkMode();
    setupWhatIfSliders();
    restoreLastResult();

    document.getElementById("analyzeBtn").addEventListener("click", runCsvAnalysis);
    document.getElementById("resetBtn").addEventListener("click", resetDashboard);
    document.getElementById("manualCheckBtn").addEventListener("click", runManualCheck);
    document.getElementById("loadDefaultsBtn").addEventListener("click", loadDefaultValues);
    document.getElementById("modelInfoBtn").addEventListener("click", toggleModelInfo);
    document.getElementById("userGuideBtn").addEventListener("click", toggleUserGuide);
    document.getElementById("exportPdfBtn").addEventListener("click", exportPdf);
});

// ── Dark Mode ─────────────────────────────────────────────────────────────────

function setupDarkMode() {
    const btn = document.getElementById("darkModeBtn");
    const saved = localStorage.getItem("theme") || "light";
    document.documentElement.setAttribute("data-theme", saved);
    btn.innerText = saved === "dark" ? "☀️" : "🌙";

    btn.addEventListener("click", () => {
        const current = document.documentElement.getAttribute("data-theme");
        const next = current === "dark" ? "light" : "dark";
        document.documentElement.setAttribute("data-theme", next);
        localStorage.setItem("theme", next);
        btn.innerText = next === "dark" ? "☀️" : "🌙";
    });
}

// ── Tabs ──────────────────────────────────────────────────────────────────────

function setupTabs() {
    document.querySelectorAll(".tab-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
            document.querySelectorAll(".tab-content").forEach(c => c.classList.add("hidden"));
            btn.classList.add("active");
            document.getElementById(`tab-${btn.dataset.tab}`).classList.remove("hidden");
        });
    });
}

// ── Health Check ──────────────────────────────────────────────────────────────

async function checkBackendHealth() {
    const statusBox = document.getElementById("statusIndicator");
    try {
        const res = await fetch(`${API_BASE}/api/health`);
        const data = await res.json();
        if (!data.model_loaded) {
            statusBox.innerText = "⚠️ Backend running but model not loaded. Run src/train.py first.";
            statusBox.className = "status-box risk";
        }
    } catch {
        statusBox.innerText = "⚠️ Cannot reach backend. Make sure uvicorn is running on port 8000.";
        statusBox.className = "status-box risk";
    }
}

// ── Restore Last Result ───────────────────────────────────────────────────────

async function restoreLastResult() {
    try {
        const res = await fetch(`${API_BASE}/api/last-result`);
        if (!res.ok) return;
        const data = await res.json();
        _lastCsvData = data;
        updateDashboard(data, true);
    } catch { /* no cached result */ }
}

// ── User Guide ────────────────────────────────────────────────────────────────

function toggleUserGuide() {
    const panel = document.getElementById("userGuidePanel");
    const modelPanel = document.getElementById("modelInfoPanel");
    modelPanel.classList.add("hidden"); // close model info if open
    panel.classList.toggle("hidden");
}

// ── Model Info ────────────────────────────────────────────────────────────────

async function toggleModelInfo() {
    const panel = document.getElementById("modelInfoPanel");
    const guidePanel = document.getElementById("userGuidePanel");
    guidePanel.classList.add("hidden"); // close user guide if open
    if (!panel.classList.contains("hidden")) {
        panel.classList.add("hidden");
        return;
    }
    try {
        const res  = await fetch(`${API_BASE}/api/model-info`);
        const info = await res.json();
        panel.innerHTML = `
            <strong>Model Info</strong>
            <ul>
                <li>Regimes: <b>${info.n_regimes}</b></li>
                <li>Covariance: <b>${info.covariance_type}</b></li>
                ${info.trained_at ? `<li>Trained: <b>${new Date(info.trained_at).toLocaleString()}</b></li>` : ""}
                ${info.dataset_rows ? `<li>Dataset rows: <b>${info.dataset_rows}</b></li>` : ""}
                ${info.date_range ? `<li>Date range: <b>${info.date_range}</b></li>` : ""}
                ${info.train_split ? `<li>Train split: <b>${info.train_split}</b></li>` : ""}
            </ul>
            <details>
                <summary>Regime feature means</summary>
                <pre>${JSON.stringify(info.regime_means, null, 2)}</pre>
            </details>
        `;
        panel.classList.remove("hidden");
    } catch {
        panel.innerHTML = "<p>Could not load model info.</p>";
        panel.classList.remove("hidden");
    }
}

// ── CSV Analysis ──────────────────────────────────────────────────────────────

async function runCsvAnalysis() {
    const fileInput = document.getElementById("csvFileInput");
    const statusBox = document.getElementById("statusIndicator");
    const days = parseInt(document.getElementById("daysInput").value) || 250;

    if (fileInput.files.length === 0) {
        statusBox.innerText = "Please select a processed CSV file first.";
        statusBox.className = "status-box risk";
        return;
    }

    setLoading(true, "analyzeBtn", "Analyzing...", "Analyze Market Data");
    statusBox.innerText = "Analyzing data with HMM...";
    statusBox.className = "status-box";

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);

    try {
        const res = await fetch(`${API_BASE}/api/market-status?days=${days}`, {
            method: "POST", body: formData,
        });
        if (!res.ok) { const e = await res.json(); throw new Error(e.detail || "Server error"); }
        const data = await res.json();
        _lastCsvData = data;
        updateDashboard(data, true);
    } catch (error) {
        statusBox.innerText = `Error: ${error.message}`;
        statusBox.className = "status-box risk";
    } finally {
        setLoading(false, "analyzeBtn", "Analyzing...", "Analyze Market Data");
    }
}

// ── Manual Check ──────────────────────────────────────────────────────────────

async function runManualCheck() {
    const statusBox = document.getElementById("statusIndicator");
    const fields = {
        returns:    document.getElementById("f_returns").value,
        volatility: document.getElementById("f_volatility").value,
        RSI:        document.getElementById("f_rsi").value,
        momentum:   document.getElementById("f_momentum").value,
        VIX:        document.getElementById("f_vix").value,
    };

    const missing = Object.entries(fields).filter(([, v]) => v === "").map(([k]) => k);
    if (missing.length > 0) {
        statusBox.innerText = `Please fill in: ${missing.join(", ")}`;
        statusBox.className = "status-box risk";
        return;
    }

    const payload = Object.fromEntries(Object.entries(fields).map(([k, v]) => [k, parseFloat(v)]));
    setLoading(true, "manualCheckBtn", "Checking...", "Check Market Signal");
    statusBox.innerText = "Running HMM prediction...";
    statusBox.className = "status-box";

    try {
        const res = await fetch(`${API_BASE}/api/manual-check`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        if (!res.ok) { const e = await res.json(); throw new Error(e.detail || "Server error"); }
        const data = await res.json();
        updateDashboard(data, false);

        // Sync sliders to the submitted values
        syncSlidersFromForm();
        document.getElementById("whatIfSection").classList.remove("hidden");
    } catch (error) {
        statusBox.innerText = `Error: ${error.message}`;
        statusBox.className = "status-box risk";
    } finally {
        setLoading(false, "manualCheckBtn", "Checking...", "Check Market Signal");
    }
}

// ── Default Values ────────────────────────────────────────────────────────────

function loadDefaultValues() {
    document.getElementById("f_returns").value    = "0.0012";
    document.getElementById("f_volatility").value = "0.0085";
    document.getElementById("f_rsi").value        = "58.4";
    document.getElementById("f_momentum").value   = "0.032";
    document.getElementById("f_vix").value        = "16.5";
}

// ── What-If Sliders ───────────────────────────────────────────────────────────

function setupWhatIfSliders() {
    const sliders = ["returns", "volatility", "rsi", "momentum", "vix"];
    sliders.forEach(name => {
        const slider = document.getElementById(`sl_${name}`);
        const label  = document.getElementById(`sl_${name}_val`);
        slider.addEventListener("input", () => {
            label.innerText = slider.value;
            debounceWhatIf();
        });
    });
}

function syncSlidersFromForm() {
    const map = { returns: "f_returns", volatility: "f_volatility", rsi: "f_rsi", momentum: "f_momentum", vix: "f_vix" };
    Object.entries(map).forEach(([slKey, formId]) => {
        const val = document.getElementById(formId).value;
        if (val) {
            document.getElementById(`sl_${slKey}`).value = val;
            document.getElementById(`sl_${slKey}_val`).innerText = val;
        }
    });
}

let _whatIfTimer = null;
function debounceWhatIf() {
    clearTimeout(_whatIfTimer);
    _whatIfTimer = setTimeout(runWhatIf, 400);
}

async function runWhatIf() {
    const payload = {
        returns:    parseFloat(document.getElementById("sl_returns").value),
        volatility: parseFloat(document.getElementById("sl_volatility").value),
        RSI:        parseFloat(document.getElementById("sl_rsi").value),
        momentum:   parseFloat(document.getElementById("sl_momentum").value),
        VIX:        parseFloat(document.getElementById("sl_vix").value),
    };

    const box = document.getElementById("whatIfResult");
    try {
        const res  = await fetch(`${API_BASE}/api/manual-check`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Server error");
        }
        const data = await res.json();
        const safe = data.current_status.includes("Safe");
        box.className = `whatif-result ${safe ? "safe" : "risk"}`;
        box.innerText = `Signal: ${data.current_status} | Regime: ${data.current_regime_id} | VIX: ${data.latest_vix.toFixed(2)}`;
    } catch (err) {
        box.className = "whatif-result risk";
        box.innerText = `Error: ${err.message}`;
    }
}

// ── Reset ─────────────────────────────────────────────────────────────────────

function resetDashboard() {
    document.getElementById("csvFileInput").value = "";
    document.getElementById("statusIndicator").innerText = "Awaiting Data...";
    document.getElementById("statusIndicator").className = "status-box";
    document.getElementById("regimeLegend").classList.add("hidden");
    document.getElementById("chart").innerHTML = "";
    document.getElementById("vixChart").innerHTML = "";
    document.getElementById("interpretation").classList.add("hidden");
    document.getElementById("exportBar").classList.add("hidden");
    document.getElementById("lastAnalyzed").classList.add("hidden");
    _lastCsvData = null;
}

// ── Dashboard Update ──────────────────────────────────────────────────────────

function updateDashboard(data, hasChart) {
    const statusBox = document.getElementById("statusIndicator");
    statusBox.innerText = `AI Signal: ${data.current_status} | Regime: ${data.current_regime_id} | VIX: ${data.latest_vix.toFixed(2)}`;
    statusBox.className = data.current_status.includes("Safe") ? "status-box safe" : "status-box risk";

    if (data.analyzed_at) {
        const ts = document.getElementById("lastAnalyzed");
        ts.innerText = `Last analyzed: ${new Date(data.analyzed_at).toLocaleString()}`;
        ts.classList.remove("hidden");
    }

    renderRegimeLegend(data.regime_legend, data.current_regime_id);

    if (hasChart && data.chart_data) {
        renderChart(data);
        renderVixChart(data);
        renderInterpretation(data);
        document.getElementById("exportBar").classList.remove("hidden");
    } else {
        document.getElementById("chart").innerHTML = "";
        document.getElementById("vixChart").innerHTML = "";
        document.getElementById("interpretation").classList.add("hidden");
        document.getElementById("exportBar").classList.add("hidden");
    }
}

// ── Regime Legend ─────────────────────────────────────────────────────────────

function renderRegimeLegend(legend, currentRegime) {
    const container = document.getElementById("regimeLegend");
    container.innerHTML = "<strong>Regime Legend:</strong> ";
    container.classList.remove("hidden");

    Object.entries(legend).forEach(([id, info]) => {
        const pill = document.createElement("span");
        const isCurrent = parseInt(id) === currentRegime;
        pill.className = `regime-pill ${info.label.includes("Low") ? "safe-pill" : "risk-pill"} ${isCurrent ? "current-pill" : ""}`;
        pill.title = `Click to highlight Regime ${id} on chart`;
        pill.innerText = `Regime ${id}: ${info.label} (VIX avg: ${info.avg_vix})${isCurrent ? " ◀ now" : ""}`;
        pill.style.cursor = "pointer";
        pill.addEventListener("click", () => highlightRegime(parseInt(id)));
        container.appendChild(pill);
    });
}

// ── Price Chart ───────────────────────────────────────────────────────────────

const COLORS = ["#2196F3", "#4CAF50", "#FF9800", "#E91E63", "#9C27B0", "#00BCD4"];
let _highlightedRegime = null;

function renderChart(data) {
    const regimes = [...new Set(data.chart_data.regimes)].sort();

    const traces = regimes.map((regime, i) => {
        const indices = data.chart_data.regimes
            .map((r, idx) => (r === regime ? idx : null)).filter(idx => idx !== null);
        return {
            x: indices.map(idx => data.chart_data.dates[idx]),
            y: indices.map(idx => data.chart_data.prices[idx]),
            type: "scatter", mode: "markers",
            marker: { color: COLORS[i % COLORS.length], size: 5 },
            name: `Regime ${regime} (${data.regime_legend[regime]?.label ?? ""})`,
        };
    });

    Plotly.newPlot("chart", traces, {
        title: `S&P 500 — Last ${data.chart_data.dates.length} Trading Days (Colored by Regime)`,
        xaxis: { title: "Date" }, yaxis: { title: "Price" },
        hovermode: "closest", legend: { orientation: "h", y: -0.2 },
    }, { responsive: true });
}

function highlightRegime(regimeId) {
    if (!_lastCsvData) return;
    _highlightedRegime = _highlightedRegime === regimeId ? null : regimeId;
    const data    = _lastCsvData;
    const regimes = [...new Set(data.chart_data.regimes)].sort();

    const traces = regimes.map((regime, i) => {
        const indices = data.chart_data.regimes
            .map((r, idx) => (r === regime ? idx : null)).filter(idx => idx !== null);
        const dimmed = _highlightedRegime !== null && regime !== _highlightedRegime;
        return {
            x: indices.map(idx => data.chart_data.dates[idx]),
            y: indices.map(idx => data.chart_data.prices[idx]),
            type: "scatter", mode: "markers",
            marker: { color: COLORS[i % COLORS.length], size: dimmed ? 3 : 7, opacity: dimmed ? 0.15 : 1 },
            name: `Regime ${regime} (${data.regime_legend[regime]?.label ?? ""})`,
        };
    });

    Plotly.react("chart", traces, {
        title: `S&P 500 — Last ${data.chart_data.dates.length} Trading Days (Colored by Regime)`,
        xaxis: { title: "Date" }, yaxis: { title: "Price" },
        hovermode: "closest", legend: { orientation: "h", y: -0.2 },
    }, { responsive: true });
}

// ── VIX Chart ─────────────────────────────────────────────────────────────────

function renderVixChart(data) {
    if (!data.chart_data.vix) return;
    const regimes = [...new Set(data.chart_data.regimes)].sort();

    const traces = regimes.map((regime, i) => {
        const indices = data.chart_data.regimes
            .map((r, idx) => (r === regime ? idx : null)).filter(idx => idx !== null);
        return {
            x: indices.map(idx => data.chart_data.dates[idx]),
            y: indices.map(idx => data.chart_data.vix[idx]),
            type: "scatter", mode: "markers",
            marker: { color: COLORS[i % COLORS.length], size: 4 },
            name: `Regime ${regime}`,
            showlegend: false,
        };
    });

    Plotly.newPlot("vixChart", traces, {
        title: "VIX Over Time (Colored by Regime)",
        xaxis: { title: "Date" }, yaxis: { title: "VIX" },
        hovermode: "closest", height: 280,
    }, { responsive: true });
}

// ── Chart Interpretation ──────────────────────────────────────────────────────

function renderInterpretation(data) {
    const box      = document.getElementById("interpretation");
    const legend   = data.regime_legend;
    const current  = data.current_regime_id;
    const isSafe   = data.current_status.includes("Safe");
    const totalDays = data.chart_data.dates.length;

    const regimeCounts = {};
    data.chart_data.regimes.forEach(r => { regimeCounts[r] = (regimeCounts[r] || 0) + 1; });

    const dominant    = Object.entries(regimeCounts).sort((a, b) => b[1] - a[1])[0];
    const dominantPct = ((dominant[1] / totalDays) * 100).toFixed(0);

    const breakdownLines = Object.entries(regimeCounts).sort((a, b) => a[0] - b[0])
        .map(([id, count]) => {
            const pct  = ((count / totalDays) * 100).toFixed(0);
            const info = legend[id];
            return `<span class="regime-pill ${info.label.includes("Low") ? "safe-pill" : "risk-pill"}">
                Regime ${id} (${info.label}): ${pct}% — avg VIX ${info.avg_vix}
            </span>`;
        }).join("");

    const currentInfo = legend[current];
    const currentDesc = isSafe
        ? `The most recent data point is in <strong>Regime ${current}</strong>, a <strong>low-risk</strong> zone (avg VIX ${currentInfo.avg_vix}). This corresponds to calm or bullish conditions.`
        : `The most recent data point is in <strong>Regime ${current}</strong>, a <strong>high-risk</strong> zone (avg VIX ${currentInfo.avg_vix}). The model suggests reducing exposure or moving to cash.`;

    const vix = data.latest_vix;
    const vixDesc = vix < 15 ? "Very low — market complacency, low expected volatility."
        : vix < 20 ? "Moderate — relatively stable market environment."
        : vix < 30 ? "Elevated — increased uncertainty and market stress."
        : "Very high — significant fear and volatility in the market.";

    box.innerHTML = `
        <h3>Chart Interpretation</h3>
        <p>Each dot is one trading day, colored by the HMM-assigned regime based on returns, volatility, RSI, momentum, and VIX. Click a regime pill above to highlight it on the chart.</p>
        <div class="interp-section">
            <strong>Regime breakdown (last ${totalDays} days)</strong>
            <div class="regime-breakdown">${breakdownLines}</div>
            <p>Regime <strong>${dominant[0]}</strong> dominated, covering <strong>${dominantPct}%</strong> of the window.</p>
        </div>
        <div class="interp-section">
            <strong>Current signal</strong>
            <p>${currentDesc}</p>
        </div>
        <div class="interp-section">
            <strong>VIX context</strong>
            <p>${vixDesc} (Current: <strong>${vix.toFixed(2)}</strong>)</p>
        </div>
        <div class="interp-section interp-note">
            <strong>How to read:</strong> Same-color clusters = consistent regime. Frequent color changes = transitional market. Regime numbers are arbitrary — the model is unsupervised.
        </div>
    `;
    box.classList.remove("hidden");
}

// ── Analysis Plots ────────────────────────────────────────────────────────────

async function loadAnalysisPlots() {
    try {
        const res  = await fetch(`${API_BASE}/api/figures`);
        const data = await res.json();
        if (!data.figures || data.figures.length === 0) return;

        const section = document.getElementById("plotsSection");
        const grid    = document.getElementById("plotsGrid");
        section.classList.remove("hidden");

        data.figures.forEach(filename => {
            const wrapper = document.createElement("div");
            wrapper.className = "plot-card";
            const title = document.createElement("p");
            title.innerText = filename.replace(/_/g, " ").replace(".png", "");
            const img = document.createElement("img");
            img.src = `${API_BASE}/api/figures/${filename}`;
            img.alt = filename;
            img.loading = "lazy";
            wrapper.appendChild(title);
            wrapper.appendChild(img);
            grid.appendChild(wrapper);
        });
    } catch { /* silent */ }
}

// ── PDF Export ────────────────────────────────────────────────────────────────

async function exportPdf() {
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF({ orientation: "portrait", unit: "mm", format: "a4" });
    const pageW = doc.internal.pageSize.getWidth();
    let y = 15;

    doc.setFontSize(18);
    doc.text("AI Market Regime Monitor — Report", pageW / 2, y, { align: "center" });
    y += 8;

    doc.setFontSize(10);
    doc.setTextColor(100);
    doc.text(`Generated: ${new Date().toLocaleString()}`, pageW / 2, y, { align: "center" });
    y += 10;

    if (_lastCsvData) {
        doc.setFontSize(13);
        doc.setTextColor(0);
        doc.text("Signal", 14, y); y += 6;
        doc.setFontSize(11);
        doc.text(`Status: ${_lastCsvData.current_status}`, 14, y); y += 5;
        doc.text(`Regime: ${_lastCsvData.current_regime_id}`, 14, y); y += 5;
        doc.text(`VIX: ${_lastCsvData.latest_vix.toFixed(2)}`, 14, y); y += 5;
        doc.text(`Analyzed at: ${new Date(_lastCsvData.analyzed_at).toLocaleString()}`, 14, y); y += 10;

        doc.setFontSize(13);
        doc.text("Regime Legend", 14, y); y += 6;
        doc.setFontSize(10);
        Object.entries(_lastCsvData.regime_legend).forEach(([id, info]) => {
            doc.text(`  Regime ${id}: ${info.label} — avg VIX ${info.avg_vix}`, 14, y); y += 5;
        });
        y += 5;
    }

    // Capture charts
    for (const id of ["chart", "vixChart", "interpretation"]) {
        const el = document.getElementById(id);
        if (!el || el.classList.contains("hidden") || el.innerHTML.trim() === "") continue;
        const canvas = await html2canvas(el, { scale: 1.5, useCORS: true });
        const imgData = canvas.toDataURL("image/png");
        const imgH = (canvas.height * (pageW - 28)) / canvas.width;
        if (y + imgH > 280) { doc.addPage(); y = 15; }
        doc.addImage(imgData, "PNG", 14, y, pageW - 28, imgH);
        y += imgH + 8;
    }

    doc.save("market-regime-report.pdf");
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function setLoading(isLoading, btnId, loadingText, defaultText) {
    const spinner = document.getElementById("spinner");
    const btn     = document.getElementById(btnId);
    spinner.classList.toggle("hidden", !isLoading);
    btn.disabled  = isLoading;
    btn.innerText = isLoading ? loadingText : defaultText;
}

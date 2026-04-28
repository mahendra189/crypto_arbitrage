// ── Data fetching ────────────────────────────────────────────────────────────
async function fetchData() {
    try {
        const response = await fetch('data.json?t=' + Date.now());
        if (!response.ok) throw new Error('Network response was not ok');
        const data = await response.json();

        updateOpportunities(data.top_opportunities || []);
        updateLogs(data.logs || []);
        updateStrategyCounts(data.top_opportunities || []);
        
        if (data.network_graph) {
            updateNetworkGraph(data.network_graph);
        }
        if (data.predictions) {
            updatePredictions(data.predictions);
        }

        if (data.live_prices) {
            updateIndices(data.live_prices);
        }
        
        updateScannerStatus(data.scan_state || 'live');
    } catch (error) {
        console.error('Error fetching data:', error);
    }
}

// ── Scanner Control ──────────────────────────────────────────────────────────
async function toggleScanner() {
    try {
        const res = await fetch('/api/scanner/toggle', { method: 'POST' });
        const data = await res.json();
        const btn = document.getElementById('toggle-scanner-btn');
        if (data.running) {
            btn.textContent = 'Pause Scanner';
            btn.style.color = 'var(--neon-blue)';
            btn.style.borderColor = 'rgba(14, 165, 233, 0.5)';
        } else {
            btn.textContent = 'Start Scanner';
            btn.style.color = 'var(--neon-green)';
            btn.style.borderColor = 'rgba(16, 185, 129, 0.5)';
        }
        // Force immediate fetch to update status
        fetchData();
    } catch (err) {
        console.error('Toggle failed:', err);
    }
}

function updateScannerStatus(state) {
    const statusDiv = document.getElementById('scanner-status');
    const pulseDiv = document.getElementById('scanner-pulse');
    
    if (state === 'paused') {
        statusDiv.style.color = 'var(--text-secondary)';
        statusDiv.innerHTML = 'Scanner Paused <div class="pulse-dot" id="scanner-pulse" style="background-color: var(--text-secondary); box-shadow: none; animation: none;"></div>';
    } else if (state === 'degraded') {
        statusDiv.style.color = 'var(--neon-red)';
        statusDiv.innerHTML = 'Scanner Degraded <div class="pulse-dot" id="scanner-pulse" style="background-color: var(--neon-red); box-shadow: 0 0 10px var(--neon-red);"></div>';
    } else {
        statusDiv.style.color = 'var(--neon-green)';
        statusDiv.innerHTML = 'Scanner Running <div class="pulse-dot" id="scanner-pulse"></div>';
    }
}

// ── Strategy count cards ─────────────────────────────────────────────────────
function updateStrategyCounts(opportunities) {
    const counts = { triangular: 0, cross_broker: 0, statistical: 0, funding_rate: 0 };
    opportunities.forEach(o => { counts[o.type] = (counts[o.type] || 0) + 1; });

    const el = (id) => document.getElementById(id);
    if (el('count-triangular')) el('count-triangular').textContent = counts.triangular;
    if (el('count-cross'))      el('count-cross').textContent      = counts.cross_broker;
    if (el('count-stat'))       el('count-stat').textContent        = counts.statistical;
    if (el('count-funding'))    el('count-funding').textContent     = counts.funding_rate;
}

// ── Opportunity table ────────────────────────────────────────────────────────
function updateOpportunities(opportunities) {
    const tbody = document.getElementById('opp-list');
    tbody.innerHTML = '';
    
    if (opportunities.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; color: var(--text-secondary)">Waiting for market data...</td></tr>';
        return;
    }

    opportunities.forEach((opp, index) => {
        let typeBadge = '';
        let grossProfit = 0;
        let netProfit = 0;
        
        if (opp.type === 'triangular') {
            typeBadge = '<span class="badge badge-triangular">TRI</span>';
            grossProfit = opp.raw_profit !== undefined ? opp.raw_profit : 0;
            netProfit = opp.net_profit !== undefined ? opp.net_profit : 0;
        } else if (opp.type === 'cross_broker') {
            typeBadge = '<span class="badge badge-cross">CROSS</span>';
            grossProfit = opp.gross_profit_pct !== undefined ? opp.gross_profit_pct : 0;
            netProfit = opp.profit_pct !== undefined ? opp.profit_pct : 0;
        } else if (opp.type === 'funding_rate') {
            typeBadge = '<span class="badge badge-funding">FUND</span>';
            grossProfit = opp.raw_profit !== undefined ? opp.raw_profit : 0;
            netProfit = opp.net_profit !== undefined ? opp.net_profit : 0;
        } else if (opp.type === 'statistical') {
            typeBadge = '<span class="badge badge-stat">STAT</span>';
            grossProfit = opp.raw_profit !== undefined ? opp.raw_profit : 0;
            netProfit = opp.net_profit !== undefined ? opp.net_profit : 0;
        } else {
            typeBadge = `<span class="badge badge-cross">${opp.type.toUpperCase()}</span>`;
            grossProfit = opp.raw_profit !== undefined ? opp.raw_profit : 0;
            netProfit = opp.net_profit !== undefined ? opp.net_profit : 0;
        }

        const paperReturn = opp.paper_return_pct !== undefined ? opp.paper_return_pct : 0;
        const estPnl = opp.paper_estimated_pnl_usdt !== undefined ? opp.paper_estimated_pnl_usdt : 0;

        const grossClass = grossProfit > 0 ? 'profit-positive' : 'profit-negative';
        const netClass = netProfit > 0 ? 'profit-positive' : 'profit-negative';
        const returnClass = paperReturn > 0 ? 'profit-positive' : 'profit-negative';
        const pnlClass = estPnl > 0 ? 'profit-positive' : 'profit-negative';

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${index + 1}</td>
            <td>${typeBadge} ${opp.path.replace(/→/g, '<span style="color:#475569">→</span>')}</td>
            <td class="${grossClass}">${(grossProfit > 0 ? '+' : '') + grossProfit.toFixed(3)}%</td>
            <td class="${netClass}">${(netProfit > 0 ? '+' : '') + netProfit.toFixed(3)}%</td>
            <td class="${returnClass}">${(paperReturn > 0 ? '+' : '') + paperReturn.toFixed(3)}%</td>
            <td class="${pnlClass}">${(estPnl > 0 ? '+' : '') + '$' + estPnl.toFixed(2)}</td>
        `;
        tbody.appendChild(tr);
    });
}

// ── Log console ──────────────────────────────────────────────────────────────
function updateLogs(logs) {
    const consoleDiv = document.getElementById('log-console');
    const atBottom = consoleDiv.scrollHeight - consoleDiv.clientHeight <= consoleDiv.scrollTop + 50;

    let html = '';
    logs.forEach(log => {
        let spanClass = '';
        if (log.includes('[SIGNAL]'))  spanClass = 'log-signal';
        else if (log.includes('[ERROR]'))   spanClass = 'log-error';
        else if (log.includes('[WARNING]')) spanClass = 'log-warning';
        else if (log.includes('[INFO]'))    spanClass = 'log-info';
        else if (log.includes('[DEBUG]'))   spanClass = 'log-debug';

        html += `<div class="${spanClass}">${log.replace(/→/g, '&rarr;')}</div>`;
    });

    consoleDiv.innerHTML = html;

    if (atBottom || consoleDiv.scrollTop === 0) {
        consoleDiv.scrollTop = consoleDiv.scrollHeight;
    }
}

// ── Live price indices ───────────────────────────────────────────────────────
function updateIndices(livePrices) {
    const indicesDiv = document.getElementById('market-indices');
    if (!indicesDiv || !livePrices) return;

    const formatPrice = (price) => {
        const val = parseFloat(price);
        return val < 1000
            ? val.toFixed(2)
            : val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    };

    const symbols = [
        { key: 'BTCUSDT', name: 'BTC' },
        { key: 'ETHUSDT', name: 'ETH' },
        { key: 'BNBUSDT', name: 'BNB' },
        { key: 'SOLUSDT', name: 'SOL' },
        { key: 'XRPUSDT', name: 'XRP' },
    ];

    let html = '';
    symbols.forEach(sym => {
        if (livePrices[sym.key]) {
            html += `<div class="index-item"><span class="idx-name">${sym.name}</span><span class="idx-price">$${formatPrice(livePrices[sym.key])}</span></div>`;
        }
    });

    if (html !== '') indicesDiv.innerHTML = html;
}

// ── Init ─────────────────────────────────────────────────────────────────────
fetchData();
setInterval(fetchData, 1500);

// ── Network Graph ────────────────────────────────────────────────────────────
let networkInstance = null;
let networkNodes = null;
let networkEdges = null;

function updateNetworkGraph(graphData) {
    if (typeof vis === 'undefined' || !graphData) return;

    const container = document.getElementById('network-graph');
    if (!container) return;

    const nodesMap = new Map();
    const edgesList = [];

    for (const [source, targets] of Object.entries(graphData)) {
        if (!nodesMap.has(source)) {
            nodesMap.set(source, { id: source, label: source });
        }
        
        for (const [target, rate] of Object.entries(targets)) {
            if (!nodesMap.has(target)) {
                nodesMap.set(target, { id: target, label: target });
            }
            
            edgesList.push({
                id: `${source}-${target}`,
                from: source,
                to: target,
                arrows: 'to',
                title: `Rate: ${parseFloat(rate).toFixed(6)}`, // Tooltip on hover
                color: { color: 'rgba(148, 163, 184, 0.2)', highlight: '#10b981' }
            });
        }
    }

    const nodesArr = Array.from(nodesMap.values());

    if (!networkInstance) {
        networkNodes = new vis.DataSet(nodesArr);
        networkEdges = new vis.DataSet(edgesList);

        const data = { nodes: networkNodes, edges: networkEdges };
        const options = {
            nodes: {
                shape: 'dot',
                size: 20,
                font: { color: '#f8fafc', size: 14, face: 'Inter' },
                borderWidth: 2,
                color: { 
                    border: '#1e293b', 
                    background: '#3b82f6',
                    highlight: { border: '#f8fafc', background: '#0ea5e9' }
                }
            },
            edges: {
                smooth: { type: 'dynamic' },
                selectionWidth: 2
            },
            physics: {
                barnesHut: {
                    gravitationalConstant: -3000,
                    centralGravity: 0.3,
                    springLength: 150,
                    springConstant: 0.04,
                    damping: 0.09
                },
                stabilization: { iterations: 150 }
            },
            interaction: {
                hover: true,
                tooltipDelay: 200
            }
        };

        networkInstance = new vis.Network(container, data, options);
    } else {
        // Update nodes and edges dynamically without redrawing everything
        networkNodes.update(nodesArr);
        
        // For edges, we just update the title (rate) so it stays real-time
        networkEdges.update(edgesList.map(e => ({ id: e.id, title: e.title })));
    }
}

// ── Market Predictions ───────────────────────────────────────────────────────
function updatePredictions(predictions) {
    const container = document.getElementById('predictions-container');
    if (!container || !predictions) return;

    let html = '';
    
    // Sort by volatility (most volatile first)
    const sorted = Object.entries(predictions).sort((a, b) => b[1].volatility - a[1].volatility);

    if (sorted.length === 0) {
        container.innerHTML = '<div style="text-align:center; color: var(--text-secondary); margin-top: 2rem;">Collecting market data...</div>';
        return;
    }

    sorted.forEach(([symbol, data]) => {
        const trendColor = data.trend === 'BULLISH' ? 'var(--neon-green)' : (data.trend === 'BEARISH' ? 'var(--neon-red)' : 'var(--text-secondary)');
        const pctColor = data.change_pct > 0 ? 'var(--neon-green)' : (data.change_pct < 0 ? 'var(--neon-red)' : 'var(--text-secondary)');
        const pctPrefix = data.change_pct > 0 ? '+' : '';
        
        let priceStr = data.predicted_next;
        if (priceStr < 1) priceStr = priceStr.toFixed(5);
        else if (priceStr < 100) priceStr = priceStr.toFixed(3);
        else priceStr = priceStr.toFixed(2);

        html += `
            <div style="background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.05); padding: 0.75rem; border-radius: 8px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 0.4rem;">
                    <span style="font-weight: 600; color: var(--neon-blue);">${symbol.replace('USDT', '')}</span>
                    <span style="font-weight: bold; font-size: 0.75rem; color: ${trendColor}; border: 1px solid ${trendColor}; padding: 2px 6px; border-radius: 4px;">
                        ${data.trend}
                    </span>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 0.85rem; color: var(--text-secondary);">
                    <span>Volatility: ${data.volatility.toFixed(2)}%</span>
                    <span style="color: ${pctColor}">${pctPrefix}${data.change_pct.toFixed(2)}%</span>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 0.85rem; margin-top: 0.3rem;">
                    <span>Next Expected:</span>
                    <span style="color: var(--text-primary); font-family: 'JetBrains Mono', monospace;">$${priceStr}</span>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

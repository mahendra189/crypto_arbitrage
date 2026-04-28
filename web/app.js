// ── Data fetching ────────────────────────────────────────────────────────────
async function fetchData() {
    try {
        const response = await fetch('data.json?t=' + Date.now());
        if (!response.ok) throw new Error('Network response was not ok');
        const data = await response.json();

        updateOpportunities(data.top_opportunities || []);
        updateLogs(data.logs || []);
        updateStrategyCounts(data.top_opportunities || []);

        if (data.live_prices) {
            updateIndices(data.live_prices);
        }
    } catch (error) {
        console.error('Error fetching data:', error);
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
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color: var(--text-secondary)">Waiting for market data...</td></tr>';
        return;
    }

    opportunities.forEach((opp, index) => {
        let typeBadge = '';
        let profitDisplay = '';
        
        if (opp.type === 'triangular') {
            typeBadge = '<span class="badge badge-triangular">TRI</span>';
            const netClass = opp.net_profit > 0 ? 'profit-positive' : 'profit-negative';
            profitDisplay = `
                <td class="${netClass}">${(opp.net_profit > 0 ? '+' : '') + opp.net_profit.toFixed(3)}%</td>
            `;
        } else if (opp.type === 'cross_broker') {
            typeBadge = '<span class="badge badge-cross">CROSS</span>';
            const grossProfitClass = opp.gross_profit_pct > 0 ? 'profit-positive' : 'profit-negative';
            const netProfitClass = opp.profit_pct > 0 ? 'profit-positive' : 'profit-negative';
            
            profitDisplay = `
                <td class="${grossProfitClass}">${(opp.gross_profit_pct > 0 ? '+' : '') + opp.gross_profit_pct.toFixed(3)}%</td>
                <td class="${netProfitClass}">${(opp.profit_pct > 0 ? '+' : '') + opp.profit_pct.toFixed(3)}%</td>
            `;
        } else if (opp.type === 'funding_rate') {
            typeBadge = '<span class="badge badge-funding">FUND</span>';
            const grossProfitClass = opp.gross_yield_8h > 0 ? 'profit-positive' : 'profit-negative';
            const netProfitClass = opp.net_profit > 0 ? 'profit-positive' : 'profit-negative';
            
            profitDisplay = `
                <td class="${grossProfitClass}">${(opp.gross_yield_8h * 100).toFixed(3)}%</td>
                <td class="${netProfitClass}">${(opp.net_profit > 0 ? '+' : '') + opp.net_profit.toFixed(3)}%</td>
            `;
        }
        
        // For triangular arbitrage, show same value in both columns
        let grossPnLDisplay = '';
        let netPnLDisplay = '';
        
        if (opp.type === 'triangular') {
            const netClass = opp.net_profit > 0 ? 'profit-positive' : 'profit-negative';
            grossPnLDisplay = `<td class="${netClass}">${(opp.net_profit > 0 ? '+' : '') + opp.net_profit.toFixed(3)}%</td>`;
            netPnLDisplay = `<td class="${netClass}">${(opp.net_profit > 0 ? '+' : '') + opp.net_profit.toFixed(3)}%</td>`;
        } else if (opp.type === 'cross_broker' || opp.type === 'funding_rate') {
            // Already handled in profitDisplay above
            grossPnLDisplay = '';
            netPnLDisplay = '';
        } else {
            grossPnLDisplay = `<td class="profit-negative">-</td>`;
            netPnLDisplay = `<td class="profit-negative">-</td>`;
        }
        
        const tr = document.createElement('tr');
        if (opp.type === 'triangular') {
            tr.innerHTML = `
                <td>${index + 1}</td>
                <td>${typeBadge} ${opp.path.replace(/→/g, '<span style="color:#475569">→</span>')}</td>
                ${profitDisplay}
                ${grossPnLDisplay}
                ${netPnLDisplay}
            `;
        } else {
            tr.innerHTML = `
                <td>${index + 1}</td>
                <td>${typeBadge} ${opp.path.replace(/→/g, '<span style="color:#475569">→</span>')}</td>
                <td>-</td>
                ${profitDisplay}
            `;
        }
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

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
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; color: var(--text-secondary)">Waiting for market data...</td></tr>';
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
            grossProfit = opp.gross_yield_8h !== undefined ? opp.gross_yield_8h * 100 : 0;
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
        const conf = opp.confidence !== undefined ? (opp.confidence * 100).toFixed(0) + '%' : '-';

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
            <td>${conf}</td>
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

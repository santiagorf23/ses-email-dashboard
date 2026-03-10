/**
 * MailTrack — SES Dashboard
 * js/charts.js
 *
 * Módulo de gráficos con Chart.js 4.x.
 * Migración futura → React: cada función se convierte en un
 * componente que usa useRef(canvasRef) + useEffect.
 *
 * Dependencias:
 *   - Chart.js 4.4.x  (CDN o npm install chart.js)
 *   - alerts.js       (AlertsModule)
 *   - styles.css      (variables CSS)
 *
 * Namespace global: ChartsModule
 *   ChartsModule.init(config)          — punto de entrada principal
 *   ChartsModule.loadFromAPI(token)    — carga datos reales
 *   ChartsModule.renderAll(data)       — renderiza toda la página
 *   ChartsModule.setTheme(theme)       — actualiza al cambiar tema
 *   ChartsModule.setPeriod(days)       — filtra por período
 *   ChartsModule.setDomain(domain)     — filtra por dominio
 *   ChartsModule.DEMO_DATA             — datos de prueba
 */

const ChartsModule = (() => {

    /* ─────────────────────────────────────────────────
       ESTADO INTERNO
       → React: useState / useReducer en <AnalyticsPage>
       ───────────────────────────────────────────────── */
    let _state = {
        period: 30,
        domain: '',
        theme: 'dark',
        apiBase: 'http://localhost:8000/api',
        token: '',
        instances: {},   // { chartId: Chart }
        rawItems: [],
        stats: null,
    };

    /* ─────────────────────────────────────────────────
       DATOS DE PRUEBA
       Genera 90 días de datos realistas con variación
       aleatoria seeded para reproducibilidad.
       → React: exportar como /fixtures/analytics.json
       ───────────────────────────────────────────────── */
    const DEMO_DATA = (() => {
        const stats = {
            total_sent: 540,
            total_delivered: 517,
            total_bounce: 11,
            total_open: 210,
            total_complaint: 1,
            delivery_rate: 95.7,
            bounce_rate: 2.03,
            complaint_rate: 0.18,
        };

        // Genera N días de series de tiempo con ruido realista
        function timeSeries(days) {
            const now = new Date();
            const items = [];
            const domains = ['gmail.com', 'hotmail.com', 'yahoo.com', 'outlook.com', 'empresa.co'];
            const statuses = ['delivered', 'delivered', 'delivered', 'delivered', 'delivered', 'bounce', 'open', 'complaint'];

            for (let d = days - 1; d >= 0; d--) {
                const date = new Date(now);
                date.setDate(date.getDate() - d);

                // Volumen diario con pico entre semana
                const isWeekend = date.getDay() === 0 || date.getDay() === 6;
                const baseVol = isWeekend ? 8 : 22;
                const vol = baseVol + Math.floor(Math.sin(d * 0.4) * 6 + Math.random() * 8);

                for (let i = 0; i < vol; i++) {
                    const status = statuses[Math.floor(Math.random() * statuses.length)];
                    const domain = domains[Math.floor(Math.random() * domains.length)];
                    items.push({
                        id: d * 100 + i,
                        email_to: `user${i}@${domain}`,
                        subject: `Correo de prueba #${d * 100 + i}`,
                        status: status,
                        created_at: date.toISOString(),
                    });
                }
            }
            return items;
        }

        return { stats, items: timeSeries(90) };
    })();

    /* ─────────────────────────────────────────────────
       §A  INICIALIZACIÓN
       → React: useEffect(() => { fetchData() }, [period])
       ───────────────────────────────────────────────── */
    function init({ apiBase, token, theme } = {}) {
        if (apiBase) _state.apiBase = apiBase;
        if (token) _state.token = token;
        if (theme) _state.theme = theme;

        _state.theme = localStorage.getItem('mt_theme') || 'dark';
        _bindControls();
        _applyTheme(_state.theme);
    }

    function _bindControls() {
        // Period pills
        document.querySelectorAll('.an-pill[data-days]').forEach(btn => {
            btn.addEventListener('click', () => {
                setPeriod(parseInt(btn.dataset.days));
            });
        });

        // Domain select
        const domSel = document.getElementById('an-domain');
        if (domSel) domSel.addEventListener('change', () => setDomain(domSel.value));

        // Refresh button
        const refBtn = document.getElementById('btn-refresh');
        if (refBtn) refBtn.addEventListener('click', () => {
            refBtn.classList.add('spinning');
            loadFromAPI().finally(() => {
                setTimeout(() => refBtn.classList.remove('spinning'), 600);
                AlertsModule?.showToast('✓ Datos actualizados');
            });
        });

        // Theme toggle
        const themeBtn = document.getElementById('btn-theme');
        if (themeBtn) themeBtn.addEventListener('click', () => {
            const next = _state.theme === 'dark' ? 'light' : 'dark';
            setTheme(next);
            localStorage.setItem('mt_theme', next);
        });
    }

    /* ─────────────────────────────────────────────────
       §B  DATA LOADING
       → React: custom hook useAnalyticsData(period)
       ───────────────────────────────────────────────── */
    async function loadFromAPI() {
        _showLoading();
        try {
            // Stats endpoint
            const statsRes = await _apiFetch('/emails/stats');

            // Paginar todos los emails (límite 100/página)
            let items = [], page = 1, pages = 1;
            do {
                const res = await _apiFetch(`/emails?page=${page}&per_page=100`);
                items.push(...(res.items || []));
                pages = res.pages || 1;
                page++;
            } while (page <= pages && page <= 20); // safety cap 2000

            _state.rawItems = items;
            _state.stats = statsRes;

            _populateDomainSelector(items);
            renderAll({ stats: statsRes, items });

            // Marcar alert container como cargado (evita el demo fallback)
            const ac = document.getElementById('alert-container');
            if (ac) ac.dataset.loaded = 'true';
            AlertsModule?.render(ac, statsRes);

        } catch (err) {
            console.warn('[ChartsModule] API no disponible, usando datos de prueba.', err.message);
            _useDemoData();
        }
    }

    function _useDemoData() {
        _state.rawItems = DEMO_DATA.items;
        _state.stats = DEMO_DATA.stats;
        _populateDomainSelector(DEMO_DATA.items);
        renderAll({ stats: DEMO_DATA.stats, items: DEMO_DATA.items });

        const ac = document.getElementById('alert-container');
        if (ac) {
            ac.dataset.loaded = 'true';
            AlertsModule?.render(ac, DEMO_DATA.stats);
        }
    }

    async function _apiFetch(path) {
        const headers = _state.token ? { Authorization: `Bearer ${_state.token}` } : {};
        const res = await fetch(_state.apiBase + path, { headers });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
    }

    /* ─────────────────────────────────────────────────
       §C  PUBLIC CONTROLS
       → React: state setters + useEffect re-renders
       ───────────────────────────────────────────────── */
    function setPeriod(days) {
        _state.period = days;
        document.querySelectorAll('.an-pill[data-days]').forEach(b =>
            b.classList.toggle('active', parseInt(b.dataset.days) === days)
        );
        if (_state.rawItems.length) renderAll({ stats: _state.stats, items: _state.rawItems });
    }

    function setDomain(domain) {
        _state.domain = domain;
        if (_state.rawItems.length) renderAll({ stats: _state.stats, items: _state.rawItems });
    }

    function setTheme(theme) {
        _state.theme = theme;
        _applyTheme(theme);
        if (_state.rawItems.length) renderAll({ stats: _state.stats, items: _state.rawItems });
    }

    function _applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme === 'light' ? 'light' : '');
        if (theme !== 'light') document.documentElement.removeAttribute('data-theme');
        const btn = document.getElementById('btn-theme');
        if (btn) btn.textContent = theme === 'light' ? '☾' : '☀';
    }

    /* ─────────────────────────────────────────────────
       §D  MAIN RENDER ORCHESTRATOR
       → React: <AnalyticsPage> renders child components
       ───────────────────────────────────────────────── */
    function renderAll({ stats, items }) {
        // Filter by domain
        const filtered = _state.domain
            ? items.filter(e => (e.email_to || '').includes('@' + _state.domain))
            : items;

        // Build time series buckets
        const { labels, sentArr, deliveredArr, bounceArr, openArr, complaintArr } =
            _buildTimeSeries(filtered, _state.period);

        // Compute KPIs
        const totalSent = stats.total_sent || 0;
        const totalDelivered = stats.total_delivered || 0;
        const totalBounce = stats.total_bounce || 0;
        const totalOpen = stats.total_open || 0;
        const totalComplaint = stats.total_complaint || 0;
        const delivRate = stats.delivery_rate || 0;
        const bounceRate = parseFloat(stats.bounce_rate) || 0;
        const openRate = totalSent > 0 ? (totalOpen / totalSent * 100).toFixed(1) : 0;

        // Domain distribution
        const domainMap = {};
        filtered.forEach(e => {
            const m = (e.email_to || '').match(/@([^\s>]+)/);
            if (m) domainMap[m[1]] = (domainMap[m[1]] || 0) + 1;
        });
        const domainEntries = Object.entries(domainMap).sort((a, b) => b[1] - a[1]).slice(0, 8);

        // Render KPI cards
        _renderKPIRow({ totalSent, totalDelivered, totalBounce, totalOpen, delivRate, bounceRate, openRate });

        // Render charts
        _destroyAll();
        const cc = _chartColors();

        _renderLineChart('chart-trend', labels, sentArr, deliveredArr, cc);
        _renderBarChart('chart-bar', labels, deliveredArr, bounceArr, cc);
        _renderDonutChart('chart-donut', { totalDelivered, totalOpen, totalBounce, totalComplaint, totalSent });
        _renderAreaChart('chart-opens', labels, openArr, cc.yellow, cc);
        _renderIssuesChart('chart-issues', labels, bounceArr, complaintArr, cc);
        _renderDomainsTable(domainEntries, filtered.length);

        // Update chart subtitles with period
        document.querySelectorAll('[data-period-label]').forEach(el => {
            el.textContent = `últimos ${_state.period} días`;
        });
    }

    /* ─────────────────────────────────────────────────
       §E  TIME SERIES BUILDER
       → React: useMemo(() => buildSeries(items, period), [items, period])
       ───────────────────────────────────────────────── */
    function _buildTimeSeries(items, days) {
        const TZ = 'America/Bogota';
        const now = new Date();
        const buckets = {};

        for (let i = days - 1; i >= 0; i--) {
            const d = new Date(now);
            d.setDate(d.getDate() - i);
            const key = d.toLocaleDateString('es-CO', { day: '2-digit', month: 'short', timeZone: TZ });
            buckets[key] = { sent: 0, delivered: 0, bounce: 0, open: 0, complaint: 0 };
        }

        items.forEach(e => {
            const key = new Date(e.created_at)
                .toLocaleDateString('es-CO', { day: '2-digit', month: 'short', timeZone: TZ });
            if (!buckets[key]) return;
            const st = (e.status || '').toLowerCase();
            buckets[key].sent++;
            if (st === 'delivery' || st === 'delivered') buckets[key].delivered++;
            else if (st === 'bounce') buckets[key].bounce++;
            else if (st === 'complaint') buckets[key].complaint++;
            else if (st === 'open') buckets[key].open++;
        });

        const labels = Object.keys(buckets);
        const sentArr = labels.map(k => buckets[k].sent);
        const deliveredArr = labels.map(k => buckets[k].delivered);
        const bounceArr = labels.map(k => buckets[k].bounce);
        const openArr = labels.map(k => buckets[k].open);
        const complaintArr = labels.map(k => buckets[k].complaint);

        return { labels, sentArr, deliveredArr, bounceArr, openArr, complaintArr };
    }

    /* ─────────────────────────────────────────────────
       §F  KPI CARDS RENDERER
       → React: <KPIRow> + <KPICard label color ... />
       ───────────────────────────────────────────────── */
    function _renderKPIRow({ totalSent, totalDelivered, totalBounce, totalOpen, delivRate, bounceRate, openRate }) {
        const container = document.getElementById('kpi-container');
        if (!container) return;

        const fmt = n => Number(n).toLocaleString('es-CO');

        const cards = [
            {
                label: 'Enviados', icon: '📤', colorClass: 'c-blue',
                val: fmt(totalSent), delta: '100%', deltaType: 'neu',
                sub: 'correos en total',
            },
            {
                label: 'Entregados', icon: '✅', colorClass: 'c-green',
                val: fmt(totalDelivered), delta: delivRate + '%', deltaType: delivRate >= 95 ? 'good' : delivRate >= 85 ? 'warn' : 'bad',
                sub: 'tasa de entrega',
            },
            {
                label: 'Tasa apertura', icon: '👁', colorClass: 'c-yellow',
                val: openRate + '%', delta: fmt(totalOpen), deltaType: openRate >= 20 ? 'good' : 'neu',
                sub: 'correos abiertos',
            },
            {
                label: 'Bounce rate', icon: '⚠', colorClass: bounceRate >= 2 ? 'c-red' : 'c-orange',
                val: bounceRate + '%', delta: fmt(totalBounce), deltaType: bounceRate >= 5 ? 'bad' : bounceRate >= 2 ? 'warn' : 'good',
                sub: 'límite seguro < 2%',
            },
        ];

        const arrows = { good: '↑', bad: '↓', warn: '⚠', neu: '' };

        container.innerHTML = cards.map(c => `
      <div class="kpi-card ${c.colorClass}">
        <div class="kc-label">${c.label} <span class="kc-icon">${c.icon}</span></div>
        <div class="kc-val">${c.val}</div>
        <div class="kc-delta ${c.deltaType}">${arrows[c.deltaType] || ''} ${c.delta}</div>
        <div class="kc-sub">${c.sub}</div>
      </div>`).join('');
    }

    /* ─────────────────────────────────────────────────
       §G  CHART.JS RENDERERS
       → React: cada función → componente con useRef + useEffect
       ───────────────────────────────────────────────── */

    // Shared base options — → React: chartDefaultOptions.js
    function _baseOptions(cc, { stacked = false } = {}) {
        return {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: _state.theme === 'light' ? '#fff' : '#18181b',
                    borderColor: _state.theme === 'light' ? '#e2e6ec' : '#2a303a',
                    borderWidth: 1,
                    titleColor: _state.theme === 'light' ? '#111827' : '#f0f2f5',
                    bodyColor: _state.theme === 'light' ? '#4b5563' : '#8b95a6',
                    titleFont: { family: 'Syne, sans-serif', weight: '700', size: 12 },
                    bodyFont: { family: 'DM Mono, monospace', size: 11 },
                    padding: 10,
                    cornerRadius: 8,
                },
            },
            scales: {
                x: {
                    stacked: stacked,
                    grid: { color: cc.grid, drawBorder: false },
                    ticks: { color: cc.tick, font: { family: 'DM Mono, monospace', size: 10 }, maxRotation: 0, maxTicksLimit: 7 },
                    border: { display: false },
                },
                y: {
                    stacked: stacked,
                    grid: { color: cc.grid, drawBorder: false },
                    ticks: { color: cc.tick, font: { family: 'DM Mono, monospace', size: 10 }, precision: 0 },
                    border: { display: false },
                    beginAtZero: true,
                },
            },
        };
    }

    // → React: <TrendChart labels sent delivered />
    function _renderLineChart(id, labels, sentArr, deliveredArr, cc) {
        const canvas = document.getElementById(id);
        if (!canvas) return;
        _state.instances[id] = new Chart(canvas.getContext('2d'), {
            type: 'line',
            data: {
                labels,
                datasets: [
                    {
                        label: 'Enviados', data: sentArr,
                        borderColor: cc.blue, backgroundColor: _rgba(cc.blue, .08),
                        fill: true, tension: .4, borderWidth: 2,
                        pointRadius: 3, pointBackgroundColor: cc.blue, pointHoverRadius: 5,
                    },
                    {
                        label: 'Entregados', data: deliveredArr,
                        borderColor: cc.green, backgroundColor: _rgba(cc.green, .08),
                        fill: true, tension: .4, borderWidth: 2,
                        pointRadius: 3, pointBackgroundColor: cc.green, pointHoverRadius: 5,
                    },
                ],
            },
            options: _baseOptions(cc),
        });
    }

    // → React: <ComparisonBarChart labels delivered bounce />
    function _renderBarChart(id, labels, deliveredArr, bounceArr, cc) {
        const canvas = document.getElementById(id);
        if (!canvas) return;
        _state.instances[id] = new Chart(canvas.getContext('2d'), {
            type: 'bar',
            data: {
                labels,
                datasets: [
                    {
                        label: 'Entregados', data: deliveredArr,
                        backgroundColor: _rgba(cc.green, .75),
                        borderRadius: 3, barPercentage: .6, categoryPercentage: .7,
                    },
                    {
                        label: 'Bounce', data: bounceArr,
                        backgroundColor: _rgba(cc.red, .75),
                        borderRadius: 3, barPercentage: .6, categoryPercentage: .7,
                    },
                ],
            },
            options: _baseOptions(cc),
        });
    }

    // → React: <DistributionDonut segments onHover />
    function _renderDonutChart(id, { totalDelivered, totalOpen, totalBounce, totalComplaint, totalSent }) {
        const canvas = document.getElementById(id);
        if (!canvas) return;

        const pending = Math.max(0, totalSent - totalDelivered - totalBounce - totalComplaint);
        const cc = _chartColors();

        const segments = [
            { label: 'Entregados', value: totalDelivered, color: cc.green },
            { label: 'Abiertos', value: totalOpen, color: cc.yellow },
            { label: 'Bounce', value: totalBounce, color: cc.red },
            { label: 'Complaint', value: totalComplaint, color: cc.orange },
            { label: 'Pendiente', value: pending, color: _state.theme === 'light' ? '#d1d5db' : '#27272a' },
        ].filter(s => s.value > 0);

        _state.instances[id] = new Chart(canvas.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: segments.map(s => s.label),
                datasets: [{
                    data: segments.map(s => s.value),
                    backgroundColor: segments.map(s => s.color),
                    borderColor: _state.theme === 'light' ? '#ffffff' : '#0d0f12',
                    borderWidth: 3,
                    hoverOffset: 6,
                }],
            },
            options: {
                responsive: false, cutout: '68%',
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: _state.theme === 'light' ? '#fff' : '#18181b',
                        borderColor: _state.theme === 'light' ? '#e2e6ec' : '#2a303a',
                        borderWidth: 1, cornerRadius: 8, padding: 10,
                        titleColor: _state.theme === 'light' ? '#111827' : '#f0f2f5',
                        bodyColor: _state.theme === 'light' ? '#4b5563' : '#8b95a6',
                        titleFont: { family: 'Syne', weight: '700', size: 12 },
                        bodyFont: { family: 'DM Mono', size: 11 },
                        callbacks: {
                            label: ctx => ` ${ctx.label}: ${Number(ctx.parsed).toLocaleString('es-CO')} (${(ctx.parsed / totalSent * 100).toFixed(1)}%)`,
                        },
                    },
                },
            },
        });

        // Render leyenda del donut
        const legendEl = document.getElementById('donut-legend-list');
        if (legendEl) {
            const tot = segments.reduce((a, s) => a + s.value, 0) || 1;
            legendEl.innerHTML = segments.map(s => `
        <div class="dli">
          <span class="dli-dot" style="background:${s.color}"></span>
          <span class="dli-name">${s.label}</span>
          <span class="dli-val">${Number(s.value).toLocaleString('es-CO')}</span>
          <span class="dli-pct">${(s.value / tot * 100).toFixed(1)}%</span>
        </div>`).join('');
        }
    }

    // → React: <AreaChart label color data />
    function _renderAreaChart(id, labels, data, color, cc) {
        const canvas = document.getElementById(id);
        if (!canvas) return;
        _state.instances[id] = new Chart(canvas.getContext('2d'), {
            type: 'line',
            data: {
                labels,
                datasets: [{
                    label: 'Abiertos', data,
                    borderColor: color, backgroundColor: _rgba(color, .10),
                    fill: true, tension: .4, borderWidth: 2,
                    pointRadius: 2, pointBackgroundColor: color,
                }],
            },
            options: _baseOptions(cc),
        });
    }

    // → React: <IssuesChart bounce complaint />
    function _renderIssuesChart(id, labels, bounceArr, complaintArr, cc) {
        const canvas = document.getElementById(id);
        if (!canvas) return;
        _state.instances[id] = new Chart(canvas.getContext('2d'), {
            type: 'line',
            data: {
                labels,
                datasets: [
                    {
                        label: 'Bounce', data: bounceArr,
                        borderColor: cc.red, backgroundColor: _rgba(cc.red, .08),
                        fill: true, tension: .4, borderWidth: 2, pointRadius: 2,
                        pointBackgroundColor: cc.red,
                    },
                    {
                        label: 'Complaint', data: complaintArr,
                        borderColor: cc.orange, backgroundColor: _rgba(cc.orange, .08),
                        fill: true, tension: .4, borderWidth: 1.5, borderDash: [4, 3],
                        pointRadius: 2, pointBackgroundColor: cc.orange,
                    },
                ],
            },
            options: _baseOptions(cc),
        });
    }

    // → React: <DomainsTable rows maxCount />
    function _renderDomainsTable(entries, total) {
        const table = document.getElementById('domains-table');
        if (!table) return;
        const max = entries[0]?.[1] || 1;
        table.innerHTML = `
      <thead>
        <tr>
          <th style="width:32px">#</th>
          <th>Dominio</th>
          <th>Envíos</th>
          <th>%</th>
          <th class="col-bar">Volumen</th>
        </tr>
      </thead>
      <tbody>
        ${entries.map(([dom, cnt], i) => `
          <tr>
            <td class="t-mono" style="color:var(--text3)">${i + 1}</td>
            <td class="col-email">@${dom}</td>
            <td class="t-mono">${Number(cnt).toLocaleString('es-CO')}</td>
            <td class="t-mono" style="color:var(--text3)">${(cnt / total * 100).toFixed(1)}%</td>
            <td class="col-bar">
              <div class="mini-bar-track">
                <div class="mini-bar-fill" style="width:${(cnt / max * 100).toFixed(1)}%"></div>
              </div>
            </td>
          </tr>`).join('')}
      </tbody>`;
    }

    /* ─────────────────────────────────────────────────
       §H  DOMAIN SELECTOR
       ───────────────────────────────────────────────── */
    function _populateDomainSelector(items) {
        const sel = document.getElementById('an-domain');
        if (!sel) return;
        const current = _state.domain;
        const domains = new Set();
        items.forEach(e => {
            const m = (e.email_to || '').match(/@([^\s>]+)/);
            if (m) domains.add(m[1]);
        });
        const opts = ['<option value="">Todos los dominios</option>'];
        [...domains].sort().forEach(d => {
            opts.push(`<option value="${d}" ${d === current ? 'selected' : ''}>${d}</option>`);
        });
        sel.innerHTML = opts.join('');
    }

    /* ─────────────────────────────────────────────────
       §I  UTILITIES
       ───────────────────────────────────────────────── */
    function _chartColors() {
        const light = _state.theme === 'light';
        return {
            grid: light ? 'rgba(0,0,0,.06)' : 'rgba(255,255,255,.04)',
            tick: light ? '#6b7280' : '#52525b',
            blue: light ? '#2563eb' : '#60a5fa',
            green: light ? '#16a34a' : '#4ade80',
            red: light ? '#dc2626' : '#f87171',
            orange: light ? '#ea580c' : '#fb923c',
            yellow: light ? '#d97706' : '#fbbf24',
        };
    }

    function _rgba(hex, alpha) {
        const r = parseInt(hex.slice(1, 3), 16);
        const g = parseInt(hex.slice(3, 5), 16);
        const b = parseInt(hex.slice(5, 7), 16);
        return `rgba(${r},${g},${b},${alpha})`;
    }

    function _destroyAll() {
        Object.values(_state.instances).forEach(c => { try { c.destroy(); } catch { } });
        _state.instances = {};
    }

    function _showLoading() {
        const body = document.getElementById('an-content');
        if (body) body.innerHTML = '<div class="u-loading">Cargando analítica…</div>';
    }

    /* ─────────────────────────────────────────────────
       PUBLIC API
       ───────────────────────────────────────────────── */
    return {
        init,
        loadFromAPI,
        renderAll,
        setPeriod,
        setDomain,
        setTheme,
        DEMO_DATA,
    };

})();


/* ═══════════════════════════════════════════════════
   BOOT — se ejecuta al cargar la página
   En producción: pasar token desde backend session
   ═══════════════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('ses_token') || '';

    ChartsModule.init({ token });

    // Intentar API real; si falla, caer a demo data automáticamente
    ChartsModule.loadFromAPI().catch(() => {
        // loadFromAPI ya maneja el fallback internamente
    });
});
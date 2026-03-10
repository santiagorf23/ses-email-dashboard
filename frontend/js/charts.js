/**
 * MailTrack — SES Dashboard
 * js/charts.js  v3
 *
 * ─ Carga datos REALES del backend; fallback a demo si la API no responde.
 * ─ Sidebar colapsable con nav, períodos y config de alertas.
 * ─ Filtros: período rápido (7/30/90d) + rango de fechas custom + dominio.
 * ─ Exportación: CSV y Excel (.xls) sin dependencias externas.
 *
 * Dependencias: Chart.js 4.x  ·  alerts.js (AlertsModule)
 */
const ChartsModule = (() => {

    /* ══════════════════════════════════════════════
       ESTADO INTERNO
    ══════════════════════════════════════════════ */
    const _s = {
        period: 30,
        domain: '',
        dateFrom: null,
        dateTo: null,
        theme: localStorage.getItem('mt_theme') || 'dark',
        apiBase: 'http://localhost:8000/api',
        token: localStorage.getItem('ses_token') || '',
        charts: {},
        rawItems: [],
        stats: null,
    };

    /* ══════════════════════════════════════════════
       DATOS DE DEMO (fallback cuando no hay API)
    ══════════════════════════════════════════════ */
    const DEMO_DATA = (() => {
        const stats = {
            total_sent: 540, total_delivered: 517, total_bounce: 11,
            total_open: 210, total_complaint: 1,
            delivery_rate: 95.7, bounce_rate: 2.03, complaint_rate: 0.18,
        };
        const domains = ['gmail.com', 'hotmail.com', 'yahoo.com', 'outlook.com', 'empresa.co'];
        const statuses = ['delivered', 'delivered', 'delivered', 'delivered', 'bounce', 'open', 'complaint', 'delivered'];
        const items = [];
        const now = new Date();
        for (let d = 89; d >= 0; d--) {
            const date = new Date(now);
            date.setDate(date.getDate() - d);
            const vol = (date.getDay() === 0 || date.getDay() === 6) ? 8 : 22;
            for (let i = 0; i < vol; i++) {
                items.push({
                    id: d * 100 + i,
                    email_to: `user${i}@${domains[i % domains.length]}`,
                    subject: `Correo #${d * 100 + i}`,
                    status: statuses[(d + i) % statuses.length],
                    created_at: date.toISOString(),
                });
            }
        }
        return { stats, items };
    })();

    /* ══════════════════════════════════════════════
       INIT
    ══════════════════════════════════════════════ */
    function init() {
        _s.theme = localStorage.getItem('mt_theme') || 'dark';
        _applyTheme(_s.theme);
        _buildSidebar();   // inyecta HTML del sidebar
        _bindControls();   // event listeners sobre todos los controles
        _restoreSidebar(); // colapso persistido
    }

    /* ══════════════════════════════════════════════
       SIDEBAR — construido por JS para evitar duplicar HTML
    ══════════════════════════════════════════════ */
    function _buildSidebar() {
        const sb = document.getElementById('an-sidebar');
        if (!sb) return;
        const name = localStorage.getItem('ses_username') || 'Administrador';
        const initials = name.charAt(0).toUpperCase();

        sb.innerHTML = `
      <!-- Expand strip (visible when collapsed) -->
      <div class="sb-expand-strip" id="btn-sidebar-expand" title="Expandir menú">›</div>

      <!-- Brand + collapse -->
      <div class="asb-brand">
        <div class="asb-logo">✦</div>
        <span class="asb-name">Mail<em>Track</em></span>
        <button class="asb-collapse" id="btn-sidebar-collapse" title="Colapsar">‹</button>
      </div>

      <!-- Navegación -->
      <nav class="asb-nav" aria-label="Navegación">

        <span class="asb-section-label">Vistas</span>

        <a href="index.html" class="asb-item" title="Bandeja de envíos">
          <span class="asb-item-dot" style="background:var(--blue)"></span>
          <span class="asb-item-label">Bandeja de envíos</span>
        </a>
        <a href="analytics.html" class="asb-item active" title="Analítica">
          <span class="asb-item-dot" style="background:var(--accent)"></span>
          <span class="asb-item-label">Analítica</span>
        </a>

        <span class="asb-section-label" style="margin-top:8px">Período</span>

        <div id="sidebar-period-pills" style="display:flex;flex-direction:column;gap:2px">
          <button class="asb-item sb-period" data-days="7"  title="Últimos 7 días">
            <span class="asb-item-dot" style="background:var(--text3)"></span>
            <span class="asb-item-label">Últimos 7 días</span>
          </button>
          <button class="asb-item sb-period" data-days="30" title="Últimos 30 días">
            <span class="asb-item-dot" style="background:var(--accent)"></span>
            <span class="asb-item-label">Últimos 30 días</span>
          </button>
          <button class="asb-item sb-period" data-days="90" title="Últimos 90 días">
            <span class="asb-item-dot" style="background:var(--text3)"></span>
            <span class="asb-item-label">Últimos 90 días</span>
          </button>
        </div>

        <span class="asb-section-label" style="margin-top:8px">Alertas</span>

        <button class="asb-item" id="btn-alert-settings" title="Configurar umbrales">
          <span class="asb-item-dot" style="background:var(--yellow)"></span>
          <span class="asb-item-label">Configurar umbrales</span>
        </button>

      </nav>

      <!-- Footer -->
      <div class="asb-footer">
        <div class="asb-avatar">${initials}</div>
        <div class="asb-footer-info">
          <div class="asb-footer-name">${name}</div>
          <div class="asb-footer-role">acceso interno</div>
        </div>
        <button class="asb-theme-btn" id="btn-theme" title="Cambiar tema">☀</button>
      </div>`;
    }

    function _restoreSidebar() {
        // Slight delay so sidebar HTML is rendered first
        setTimeout(() => {
            if (localStorage.getItem('sb_an_collapsed') === '1') {
                const sb = document.getElementById('an-sidebar');
                const btn = document.getElementById('btn-sidebar-collapse');
                const strip = document.getElementById('btn-sidebar-expand');
                sb?.classList.add('collapsed');
                if (btn) btn.textContent = '›';
                if (strip) strip.style.display = 'flex';
            }
        }, 50);
    }

    /* ══════════════════════════════════════════════
       EVENT BINDING
    ══════════════════════════════════════════════ */
    function _bindControls() {

        /* ── Period pills (topbar) ── */
        document.querySelectorAll('.an-pill[data-days]').forEach(b =>
            b.addEventListener('click', () => setPeriod(parseInt(b.dataset.days)))
        );

        /* ── Period pills (sidebar) ── */
        document.querySelectorAll('.sb-period[data-days]').forEach(b =>
            b.addEventListener('click', () => setPeriod(parseInt(b.dataset.days)))
        );

        /* ── Domain select ── */
        const domSel = document.getElementById('an-domain');
        if (domSel) domSel.addEventListener('change', () => { _s.domain = domSel.value; _rerender(); });

        /* ── Date range inputs ── */
        const df = document.getElementById('date-from');
        const dt = document.getElementById('date-to');
        if (df) df.addEventListener('change', () => {
            _s.dateFrom = df.value ? new Date(df.value + 'T00:00:00') : null;
            if (df.value) { _s.period = 0; _clearPeriodPills(); }
            _rerender();
        });
        if (dt) dt.addEventListener('change', () => {
            _s.dateTo = dt.value ? new Date(dt.value + 'T23:59:59') : null;
            if (dt.value) { _s.period = 0; _clearPeriodPills(); }
            _rerender();
        });

        /* ── Refresh ── */
        const rb = document.getElementById('btn-refresh');
        if (rb) rb.addEventListener('click', () => {
            rb.classList.add('spinning');
            loadFromAPI().finally(() => {
                setTimeout(() => rb.classList.remove('spinning'), 700);
                AlertsModule?.showToast('✓ Datos actualizados');
            });
        });

        /* ── Theme toggle ── */
        // Puede estar en la topbar o en el footer del sidebar (o en ambos).
        // Usamos delegación para capturarlo donde sea.
        document.addEventListener('click', e => {
            const btn = e.target.closest('#btn-theme');
            if (!btn) return;
            const next = _s.theme === 'dark' ? 'light' : 'dark';
            setTheme(next);
            localStorage.setItem('mt_theme', next);
        });

        /* ── Export dropdown ── */
        const eb = document.getElementById('btn-export');
        const ed = document.getElementById('export-dropdown');
        if (eb && ed) {
            eb.addEventListener('click', e => {
                e.stopPropagation();
                const open = ed.classList.toggle('open');
                eb.classList.toggle('open', open);
                eb.setAttribute('aria-expanded', open);
            });
            document.addEventListener('click', () => {
                eb.classList.remove('open');
                ed.classList.remove('open');
                eb.setAttribute('aria-expanded', 'false');
            });
            document.getElementById('export-csv')?.addEventListener('click', () => exportCSV());
            document.getElementById('export-excel')?.addEventListener('click', () => exportExcel());
        }

        /* ── Alert settings ── */
        document.addEventListener('click', e => {
            if (e.target.closest('#btn-alert-settings')) AlertsModule?.openSettings();
        });

        /* ── Mobile hamburger ── */
        document.getElementById('btn-mobile-menu')?.addEventListener('click', _toggleMobileSidebar);
        document.getElementById('sidebar-overlay')?.addEventListener('click', _toggleMobileSidebar);

        /* ── Sidebar collapse/expand (desktop) ── */
        document.addEventListener('click', e => {
            const isCollapse = e.target.closest('#btn-sidebar-collapse');
            const isExpand = e.target.closest('#btn-sidebar-expand');
            if (!isCollapse && !isExpand) return;
            const sb = document.getElementById('an-sidebar');
            const colBtn = document.getElementById('btn-sidebar-collapse');
            const expStrip = document.getElementById('btn-sidebar-expand');
            if (!sb) return;
            const collapsed = sb.classList.toggle('collapsed');
            if (colBtn) colBtn.textContent = collapsed ? '›' : '‹';
            if (expStrip) expStrip.style.display = collapsed ? 'flex' : 'none';
            localStorage.setItem('sb_an_collapsed', collapsed ? '1' : '0');
        });
    }

    function _toggleMobileSidebar() {
        const sb = document.getElementById('an-sidebar');
        const ov = document.getElementById('sidebar-overlay');
        sb?.classList.toggle('open');
        ov?.classList.toggle('show');
    }

    function _clearPeriodPills() {
        document.querySelectorAll('.an-pill[data-days]').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.sb-period[data-days]').forEach(b => {
            b.querySelector('.asb-item-dot').style.background = 'var(--text3)';
        });
    }

    /* ══════════════════════════════════════════════
       CARGA DE DATOS
    ══════════════════════════════════════════════ */
    async function loadFromAPI() {
        _showSkeletons();
        try {
            const stats = await _fetch('/emails/stats');
            let items = [], page = 1, pages = 1;
            do {
                const res = await _fetch(`/emails?page=${page}&per_page=100`);
                items.push(...(res.items || []));
                pages = res.pages || 1;
                page++;
            } while (page <= pages && page <= 20); // safety cap 2 000 correos

            _s.rawItems = items;
            _s.stats = stats;
            window._lastStats = stats;

            _populateDomainSelector(items);
            renderAll();
            AlertsModule?.render(document.getElementById('alert-container'), stats);

        } catch (err) {
            console.warn('[ChartsModule] API no disponible, usando datos demo.', err.message);
            _useDemoData();
        }
    }

    function _useDemoData() {
        _s.rawItems = DEMO_DATA.items;
        _s.stats = DEMO_DATA.stats;
        window._lastStats = DEMO_DATA.stats;
        _populateDomainSelector(DEMO_DATA.items);
        renderAll();
        AlertsModule?.render(document.getElementById('alert-container'), DEMO_DATA.stats);
    }

    async function _fetch(path) {
        const headers = _s.token ? { Authorization: `Bearer ${_s.token}` } : {};
        const res = await fetch(_s.apiBase + path, { headers });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
    }

    /* ══════════════════════════════════════════════
       CONTROLES PÚBLICOS
    ══════════════════════════════════════════════ */
    function setPeriod(days) {
        _s.period = days;
        _s.dateFrom = null;
        _s.dateTo = null;

        // Limpiar inputs de fecha
        const df = document.getElementById('date-from');
        const dt = document.getElementById('date-to');
        if (df) df.value = '';
        if (dt) dt.value = '';

        // Actualizar pills de topbar
        document.querySelectorAll('.an-pill[data-days]').forEach(b =>
            b.classList.toggle('active', parseInt(b.dataset.days) === days)
        );

        // Actualizar pills del sidebar
        document.querySelectorAll('.sb-period[data-days]').forEach(b => {
            const active = parseInt(b.dataset.days) === days;
            b.querySelector('.asb-item-dot').style.background = active ? 'var(--accent)' : 'var(--text3)';
        });

        // Actualizar etiquetas en subtítulos de gráficas
        document.querySelectorAll('[data-period-label]').forEach(el => {
            el.textContent = days === 0 ? 'rango personalizado' : `últimos ${days} días`;
        });

        _rerender();
    }

    function setTheme(t) {
        _s.theme = t;
        _applyTheme(t);
        _rerender();
    }

    function _applyTheme(theme) {
        if (theme === 'light') document.documentElement.setAttribute('data-theme', 'light');
        else document.documentElement.removeAttribute('data-theme');
        document.querySelectorAll('#btn-theme').forEach(b => {
            b.textContent = theme === 'light' ? '☾' : '☀';
        });
    }

    function _rerender() {
        if (_s.rawItems.length) renderAll();
    }

    /* ══════════════════════════════════════════════
       RENDER PRINCIPAL
    ══════════════════════════════════════════════ */
    function renderAll() {
        const filtered = _applyFilters(_s.rawItems);
        const series = _buildSeries(filtered);
        const kpis = _computeKPIs(filtered);
        const domains = _domainMap(filtered);

        _destroyCharts();
        const cc = _colors();

        _renderKPIs(kpis);
        _renderLineChart('chart-trend', series, cc);
        _renderBarChart('chart-bar', series, cc);
        _renderDonut('chart-donut', kpis, cc);
        _renderArea('chart-opens', series.labels, series.openArr, cc.yellow, cc);
        _renderIssues('chart-issues', series, cc);
        _renderDomainTable(domains, filtered.length);
    }

    /* ── Filtros ── */
    function _applyFilters(items) {
        let out = items;
        if (_s.domain) {
            out = out.filter(e => (e.email_to || '').includes('@' + _s.domain));
        }
        if (_s.period > 0) {
            const cutoff = new Date();
            cutoff.setDate(cutoff.getDate() - _s.period);
            out = out.filter(e => new Date(e.created_at) >= cutoff);
        } else if (_s.dateFrom || _s.dateTo) {
            if (_s.dateFrom) out = out.filter(e => new Date(e.created_at) >= _s.dateFrom);
            if (_s.dateTo) out = out.filter(e => new Date(e.created_at) <= _s.dateTo);
        }
        return out;
    }

    /* ── Series de tiempo ── */
    function _buildSeries(items) {
        const TZ = 'America/Bogota';
        const now = new Date();
        const days = _s.period > 0 ? _s.period : _calcCustomDays();
        const buckets = {};

        for (let i = days - 1; i >= 0; i--) {
            const d = new Date(now);
            d.setDate(d.getDate() - i);
            const k = d.toLocaleDateString('es-CO', { day: '2-digit', month: 'short', timeZone: TZ });
            buckets[k] = { sent: 0, delivered: 0, bounce: 0, open: 0, complaint: 0 };
        }

        items.forEach(e => {
            const k = new Date(e.created_at).toLocaleDateString('es-CO', { day: '2-digit', month: 'short', timeZone: TZ });
            if (!buckets[k]) return;
            const st = (e.status || '').toLowerCase();
            buckets[k].sent++;
            if (st === 'delivery' || st === 'delivered') buckets[k].delivered++;
            else if (st === 'bounce') buckets[k].bounce++;
            else if (st === 'complaint') buckets[k].complaint++;
            else if (st === 'open') buckets[k].open++;
        });

        const labels = Object.keys(buckets);
        return {
            labels,
            sentArr: labels.map(k => buckets[k].sent),
            deliveredArr: labels.map(k => buckets[k].delivered),
            bounceArr: labels.map(k => buckets[k].bounce),
            openArr: labels.map(k => buckets[k].open),
            complaintArr: labels.map(k => buckets[k].complaint),
        };
    }

    function _calcCustomDays() {
        if (_s.dateFrom && _s.dateTo) {
            return Math.max(1, Math.ceil((_s.dateTo - _s.dateFrom) / 86400000));
        }
        return 30;
    }

    /* ── KPIs calculados sobre ítems filtrados ── */
    function _computeKPIs(items) {
        let delivered = 0, bounce = 0, open = 0, complaint = 0;
        items.forEach(e => {
            const st = (e.status || '').toLowerCase();
            if (st === 'delivery' || st === 'delivered') delivered++;
            else if (st === 'bounce') bounce++;
            else if (st === 'complaint') complaint++;
            else if (st === 'open') open++;
        });
        const total = items.length;
        const delivRate = total > 0 ? (delivered / total * 100).toFixed(1) : (parseFloat(_s.stats?.delivery_rate) || 0);
        const bounceRate = total > 0 ? (bounce / total * 100).toFixed(2) : (parseFloat(_s.stats?.bounce_rate) || 0);
        const openRate = total > 0 ? (open / total * 100).toFixed(1) : 0;
        return { total, delivered, bounce, open, complaint, delivRate, bounceRate, openRate };
    }

    /* ── Mapa de dominios ── */
    function _domainMap(items) {
        const m = {};
        items.forEach(e => {
            const match = (e.email_to || '').match(/@([^\s>]+)/);
            if (match) m[match[1]] = (m[match[1]] || 0) + 1;
        });
        return Object.entries(m).sort((a, b) => b[1] - a[1]).slice(0, 8);
    }

    /* ══════════════════════════════════════════════
       RENDERERS
    ══════════════════════════════════════════════ */
    function _renderKPIs({ total, delivered, bounce, open, delivRate, bounceRate, openRate }) {
        const c = document.getElementById('kpi-container'); if (!c) return;
        const fmt = n => Number(n).toLocaleString('es-CO');
        const arrows = { good: '↑', bad: '↓', warn: '⚠', neu: '' };
        c.innerHTML = [
            {
                label: 'Enviados', icon: '📤', col: 'c-blue',
                val: fmt(total), delta: 'período selec.', dType: 'neu', sub: 'correos en el período'
            },
            {
                label: 'Entregados', icon: '✅', col: 'c-green',
                val: fmt(delivered), delta: delivRate + '%',
                dType: +delivRate >= 95 ? 'good' : +delivRate >= 85 ? 'warn' : 'bad', sub: 'tasa de entrega'
            },
            {
                label: 'Tasa apertura', icon: '👁', col: 'c-yellow',
                val: openRate + '%', delta: fmt(open),
                dType: +openRate >= 20 ? 'good' : 'neu', sub: 'correos abiertos'
            },
            {
                label: 'Bounce rate', icon: '⚠', col: +bounceRate >= 2 ? 'c-red' : 'c-orange',
                val: bounceRate + '%', delta: fmt(bounce),
                dType: +bounceRate >= 5 ? 'bad' : +bounceRate >= 2 ? 'warn' : 'good', sub: 'límite seguro <2%'
            },
        ].map(({ label, icon, col, val, delta, dType, sub }) => `
      <div class="kpi-card ${col}">
        <div class="kc-label">${label}<span class="kc-icon">${icon}</span></div>
        <div class="kc-val">${val}</div>
        <div class="kc-delta ${dType}">${arrows[dType] || ''} ${delta}</div>
        <div class="kc-sub">${sub}</div>
      </div>`).join('');
    }

    function _baseOpts(cc) {
        const light = _s.theme === 'light';
        return {
            responsive: true, maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: light ? '#fff' : '#18181b',
                    borderColor: light ? '#e2e6ec' : '#2a303a', borderWidth: 1,
                    titleColor: light ? '#111827' : '#f0f2f5',
                    bodyColor: light ? '#4b5563' : '#8b95a6',
                    titleFont: { family: 'Syne', weight: '700', size: 12 },
                    bodyFont: { family: 'DM Mono', size: 11 },
                    padding: 10, cornerRadius: 8,
                },
            },
            scales: {
                x: {
                    grid: { color: cc.grid, drawBorder: false }, border: { display: false },
                    ticks: { color: cc.tick, font: { family: 'DM Mono', size: 10 }, maxRotation: 0, maxTicksLimit: 7 }
                },
                y: {
                    grid: { color: cc.grid, drawBorder: false }, border: { display: false },
                    ticks: { color: cc.tick, font: { family: 'DM Mono', size: 10 }, precision: 0 }, beginAtZero: true
                },
            },
        };
    }

    function _renderLineChart(id, { labels, sentArr, deliveredArr }, cc) {
        const cv = document.getElementById(id); if (!cv) return;
        const wrap = cv.closest('.chart-canvas-wrap');

        // Zoom-hint badge
        let hint = wrap?.querySelector('.chart-zoom-hint');
        if (!hint && wrap) {
            hint = document.createElement('div');
            hint.className = 'chart-zoom-hint';
            hint.textContent = 'click para detallar';
            wrap.style.position = 'relative';
            wrap.appendChild(hint);
        }

        const opts = _baseOpts(cc);
        // Enhanced click: highlight the point's day across all charts
        opts.onClick = (_evt, elements) => {
            if (!elements.length) return;
            const idx = elements[0].index;
            const label = labels[idx];
            AlertsModule?.showToast(`📅 ${label} · ${sentArr[idx]} enviados · ${deliveredArr[idx]} entregados`, 'ok', 3500);
            if (hint) { hint.classList.add('hidden'); setTimeout(() => hint.classList.remove('hidden'), 2500); }
        };
        // Hide hint after first interaction
        opts.plugins.tooltip.afterBody = () => { if (hint) hint.classList.add('hidden'); };

        _s.charts[id] = new Chart(cv.getContext('2d'), {
            type: 'line', data: {
                labels, datasets: [
                    {
                        label: 'Enviados', data: sentArr, borderColor: cc.blue, backgroundColor: _rgba(cc.blue, .08),
                        fill: true, tension: .4, borderWidth: 2, pointRadius: 3, pointBackgroundColor: cc.blue, pointHoverRadius: 5
                    },
                    {
                        label: 'Entregados', data: deliveredArr, borderColor: cc.green, backgroundColor: _rgba(cc.green, .08),
                        fill: true, tension: .4, borderWidth: 2, pointRadius: 3, pointBackgroundColor: cc.green, pointHoverRadius: 5
                    },
                ]
            }, options: opts
        });
    }

    function _renderBarChart(id, { labels, deliveredArr, bounceArr }, cc) {
        const cv = document.getElementById(id); if (!cv) return;
        _s.charts[id] = new Chart(cv.getContext('2d'), {
            type: 'bar', data: {
                labels, datasets: [
                    { label: 'Entregados', data: deliveredArr, backgroundColor: _rgba(cc.green, .75), borderRadius: 3, barPercentage: .6, categoryPercentage: .7 },
                    { label: 'Bounce', data: bounceArr, backgroundColor: _rgba(cc.red, .75), borderRadius: 3, barPercentage: .6, categoryPercentage: .7 },
                ]
            }, options: _baseOpts(cc)
        });
    }

    function _renderDonut(id, { total, delivered, open, bounce, complaint }, cc) {
        const cv = document.getElementById(id); if (!cv) return;
        const pending = Math.max(0, total - delivered - bounce - complaint);
        const segs = [
            { label: 'Entregados', value: delivered, color: cc.green },
            { label: 'Abiertos', value: open, color: cc.yellow },
            { label: 'Bounce', value: bounce, color: cc.red },
            { label: 'Complaint', value: complaint, color: cc.orange },
            { label: 'Pendiente', value: pending, color: _s.theme === 'light' ? '#d1d5db' : '#27272a' },
        ].filter(s => s.value > 0);

        _s.charts[id] = new Chart(cv.getContext('2d'), {
            type: 'doughnut', data: {
                labels: segs.map(s => s.label),
                datasets: [{
                    data: segs.map(s => s.value), backgroundColor: segs.map(s => s.color),
                    borderColor: _s.theme === 'light' ? '#fff' : '#0d0f12', borderWidth: 3, hoverOffset: 6
                }],
            }, options: {
                responsive: false, cutout: '68%', plugins: {
                    legend: { display: false }, tooltip: {
                        backgroundColor: _s.theme === 'light' ? '#fff' : '#18181b',
                        borderColor: _s.theme === 'light' ? '#e2e6ec' : '#2a303a', borderWidth: 1,
                        titleColor: _s.theme === 'light' ? '#111827' : '#f0f2f5',
                        bodyColor: _s.theme === 'light' ? '#4b5563' : '#8b95a6',
                        titleFont: { family: 'Syne', weight: '700', size: 12 }, bodyFont: { family: 'DM Mono', size: 11 },
                        padding: 10, cornerRadius: 8,
                        callbacks: { label: ctx => ` ${ctx.label}: ${Number(ctx.parsed).toLocaleString('es-CO')} (${total > 0 ? (ctx.parsed / total * 100).toFixed(1) : 0}%)` },
                    }
                }
            }
        });

        // Click on a donut segment → highlight matching KPI card
        _s.charts[id].options.onClick = (_evt, elements) => {
            if (!elements.length) return;
            const label = segs[elements[0].index]?.label?.toLowerCase();
            document.querySelectorAll('.kpi-card').forEach(c => c.classList.remove('chart-highlight'));
            const map = { entregados: 1, abiertos: 2, bounce: 3, complaint: 3 };
            const idx = map[label];
            if (idx !== undefined) {
                const cards = document.querySelectorAll('.kpi-card');
                cards[idx]?.classList.add('chart-highlight');
                setTimeout(() => cards[idx]?.classList.remove('chart-highlight'), 2200);
            }
        };

        const leg = document.getElementById('donut-legend-list');
        if (leg) {
            const tot = segs.reduce((a, s) => a + s.value, 0) || 1;
            leg.innerHTML = segs.map(s => `
        <div class="dli">
          <span class="dli-dot" style="background:${s.color}"></span>
          <span class="dli-name">${s.label}</span>
          <span class="dli-val">${Number(s.value).toLocaleString('es-CO')}</span>
          <span class="dli-pct">${(s.value / tot * 100).toFixed(1)}%</span>
        </div>`).join('');
        }
    }

    function _renderArea(id, labels, data, color, cc) {
        const cv = document.getElementById(id); if (!cv) return;
        _s.charts[id] = new Chart(cv.getContext('2d'), {
            type: 'line', data: {
                labels, datasets: [
                    {
                        label: 'Abiertos', data, borderColor: color, backgroundColor: _rgba(color, .10),
                        fill: true, tension: .4, borderWidth: 2, pointRadius: 2, pointBackgroundColor: color
                    },
                ]
            }, options: _baseOpts(cc)
        });
    }

    function _renderIssues(id, { labels, bounceArr, complaintArr }, cc) {
        const cv = document.getElementById(id); if (!cv) return;
        _s.charts[id] = new Chart(cv.getContext('2d'), {
            type: 'line', data: {
                labels, datasets: [
                    { label: 'Bounce', data: bounceArr, borderColor: cc.red, backgroundColor: _rgba(cc.red, .08), fill: true, tension: .4, borderWidth: 2, pointRadius: 2 },
                    { label: 'Complaint', data: complaintArr, borderColor: cc.orange, backgroundColor: _rgba(cc.orange, .08), fill: true, tension: .4, borderWidth: 1.5, borderDash: [4, 3], pointRadius: 2 },
                ]
            }, options: _baseOpts(cc)
        });
    }

    function _renderDomainTable(entries, total) {
        const t = document.getElementById('domains-table'); if (!t) return;
        const tbody = t.querySelector('tbody'); if (!tbody) return;
        const max = entries[0]?.[1] || 1;
        tbody.innerHTML = entries.length
            ? entries.map(([dom, cnt], i) => `
          <tr>
            <td class="t-mono" style="color:var(--text3);width:32px">${i + 1}</td>
            <td class="col-email">@${dom}</td>
            <td class="t-mono">${Number(cnt).toLocaleString('es-CO')}</td>
            <td class="t-mono" style="color:var(--text3)">${total > 0 ? (cnt / total * 100).toFixed(1) : 0}%</td>
            <td class="col-bar">
              <div class="mini-bar-track">
                <div class="mini-bar-fill" style="width:${(cnt / max * 100).toFixed(1)}%"></div>
              </div>
            </td>
          </tr>`).join('')
            : '<tr><td colspan="5" style="text-align:center;padding:20px;color:var(--text3);font-size:12px">Sin datos para el período seleccionado</td></tr>';
    }

    /* ── Selector de dominio ── */
    function _populateDomainSelector(items) {
        const sel = document.getElementById('an-domain'); if (!sel) return;
        const cur = _s.domain;
        const doms = new Set();
        items.forEach(e => {
            const m = (e.email_to || '').match(/@([^\s>]+)/);
            if (m) doms.add(m[1]);
        });
        sel.innerHTML = [
            '<option value="">Todos los dominios</option>',
            ...[...doms].sort().map(d => `<option value="${d}"${d === cur ? ' selected' : ''}>${d}</option>`),
        ].join('');
    }

    /* ── Skeleton loader ── */
    function _showSkeletons() {
        const c = document.getElementById('kpi-container');
        if (c) c.innerHTML = Array(4).fill('<div class="kpi-card"><div class="u-skeleton" style="height:80px"></div></div>').join('');
    }

    /* ══════════════════════════════════════════════
       EXPORTACIÓN
    ══════════════════════════════════════════════ */
    function exportCSV() {
        const items = _applyFilters(_s.rawItems);
        if (!items.length) { AlertsModule?.showToast('Sin datos para exportar', 'warn'); return; }

        const header = ['ID', 'Destinatario', 'Asunto', 'Estado', 'Fecha'];
        const rows = items.map(e => [
            e.id,
            `"${(e.email_to || '').replace(/"/g, '""')}"`,
            `"${(e.subject || '').replace(/"/g, '""')}"`,
            e.status || '',
            new Date(e.created_at).toLocaleString('es-CO', { timeZone: 'America/Bogota' }),
        ]);
        const csv = [header, ...rows].map(r => r.join(',')).join('\n');
        const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8' });
        _download(blob, `mailtrack-${_dateTag()}.csv`);
        AlertsModule?.showToast('✓ CSV descargado', 'ok');
        _closeExportMenu();
    }

    function exportExcel() {
        const items = _applyFilters(_s.rawItems);
        if (!items.length) { AlertsModule?.showToast('Sin datos para exportar', 'warn'); return; }

        const kpis = _computeKPIs(items);
        const rows = [
            ['MailTrack — Reporte de Analítica'],
            ['Generado:', new Date().toLocaleString('es-CO', { timeZone: 'America/Bogota' })],
            ['Período:', _s.period > 0 ? `Últimos ${_s.period} días` : 'Rango personalizado'],
            ['Dominio:', _s.domain || 'Todos'],
            [],
            ['RESUMEN'],
            ['Total enviados', kpis.total],
            ['Entregados', kpis.delivered],
            ['Bounce', kpis.bounce],
            ['Abiertos', kpis.open],
            ['Tasa de entrega', kpis.delivRate + '%'],
            ['Bounce rate', kpis.bounceRate + '%'],
            ['Open rate', kpis.openRate + '%'],
            [],
            ['DETALLE DE CORREOS'],
            ['ID', 'Destinatario', 'Asunto', 'Estado', 'Fecha'],
            ...items.map(e => [
                e.id, e.email_to || '', e.subject || '', e.status || '',
                new Date(e.created_at).toLocaleString('es-CO', { timeZone: 'America/Bogota' }),
            ]),
        ];
        const esc = v => String(v ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        const xml = `<?xml version="1.0" encoding="UTF-8"?>
<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"
          xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">
<Worksheet ss:Name="Analítica"><Table>
${rows.map(r => `<Row>${r.map(c => `<Cell><Data ss:Type="String">${esc(c)}</Data></Cell>`).join('')}</Row>`).join('\n')}
</Table></Worksheet></Workbook>`;

        const blob = new Blob([xml], { type: 'application/vnd.ms-excel;charset=utf-8' });
        _download(blob, `mailtrack-${_dateTag()}.xls`);
        AlertsModule?.showToast('✓ Excel descargado', 'ok');
        _closeExportMenu();
    }

    function _closeExportMenu() {
        document.getElementById('btn-export')?.classList.remove('open');
        document.getElementById('export-dropdown')?.classList.remove('open');
    }

    function _download(blob, filename) {
        const url = URL.createObjectURL(blob);
        const a = Object.assign(document.createElement('a'), { href: url, download: filename });
        document.body.appendChild(a); a.click(); document.body.removeChild(a);
        setTimeout(() => URL.revokeObjectURL(url), 1000);
    }

    function _dateTag() { return new Date().toISOString().slice(0, 10); }

    /* ══════════════════════════════════════════════
       UTILIDADES
    ══════════════════════════════════════════════ */
    function _colors() {
        const l = _s.theme === 'light';
        return {
            grid: l ? 'rgba(0,0,0,.06)' : 'rgba(255,255,255,.04)',
            tick: l ? '#6b7280' : '#52525b',
            blue: l ? '#2563eb' : '#60a5fa',
            green: l ? '#16a34a' : '#4ade80',
            red: l ? '#dc2626' : '#f87171',
            orange: l ? '#ea580c' : '#fb923c',
            yellow: l ? '#d97706' : '#fbbf24',
        };
    }

    function _rgba(hex, a) {
        const r = parseInt(hex.slice(1, 3), 16);
        const g = parseInt(hex.slice(3, 5), 16);
        const b = parseInt(hex.slice(5, 7), 16);
        return `rgba(${r},${g},${b},${a})`;
    }

    function _destroyCharts() {
        Object.values(_s.charts).forEach(c => { try { c.destroy(); } catch { /* ignore */ } });
        _s.charts = {};
    }

    /* ══════════════════════════════════════════════
       API PÚBLICA
    ══════════════════════════════════════════════ */
    /* Expose read-only snapshot for reports.js */
    function getSnapshot() {
        const filtered = _applyFilters(_s.rawItems);
        return {
            period: _s.period,
            domain: _s.domain,
            dateFrom: _s.dateFrom,
            dateTo: _s.dateTo,
            stats: _s.stats,
            kpis: _computeKPIs(filtered),
            filtered,
            charts: _s.charts,   // live Chart instances
        };
    }

    return { init, loadFromAPI, renderAll, setPeriod, setTheme, exportCSV, exportExcel, getSnapshot };

})();

/* ── BOOT ── */
document.addEventListener('DOMContentLoaded', () => {
    ChartsModule.init();
    ChartsModule.loadFromAPI().catch(() => { /* loadFromAPI maneja el fallback internamente */ });
});
/**
 * MailTrack — SES Dashboard
 * js/reports.js  v1
 *
 * Genera reportes PDF con:
 *  - Portada con logo, fecha y rango de análisis
 *  - Métricas KPI destacadas
 *  - Captura PNG de las 4 gráficas (Chart.js canvas → base64)
 *  - Tabla de top dominios
 *  - Pie de página con versión y marca
 *
 * Dependencias:
 *  - jsPDF 2.x  (cargado desde CDN en analytics.html)
 *  - ChartsModule.getSnapshot()  (charts.js)
 *  - AlertsModule.showToast()    (alerts.js)
 *
 * API pública:
 *  ReportsModule.download()   → genera y descarga el PDF
 *  ReportsModule.getPayload() → devuelve objeto JSON para envío por correo (backend)
 *
 * Preparado para envío automático desde Python:
 *   El payload que devuelve getPayload() puede enviarse al endpoint
 *   POST /api/reports/send-email con los campos:
 *     { period, domain, kpis, generatedAt, charts: { trend, bar, donut, opens } }
 */
const ReportsModule = (() => {

    /* ── Constantes de diseño del PDF ─────────────────── */
    const PDF = {
        W: 210,    // mm A4 ancho
        H: 297,    // mm A4 alto
        ML: 18,     // margin left
        MR: 18,     // margin right
        MT: 20,     // margin top
        CONTENT: 210 - 18 - 18,   // ancho útil
        // Colores (RGB)
        C_BG: [7, 8, 10],
        C_SURF: [13, 15, 18],
        C_SURF2: [25, 28, 33],
        C_ACCENT: [74, 222, 128],
        C_TEXT: [240, 242, 245],
        C_TEXT2: [139, 149, 166],
        C_TEXT3: [63, 72, 85],
        C_RED: [248, 113, 113],
        C_YELLOW: [251, 191, 36],
        C_BLUE: [96, 165, 250],
        C_ORANGE: [251, 146, 60],
    };

    /* ── Helpers de dibujo ───────────────────────────── */
    function _rgb(doc, color) { doc.setTextColor(...color); }
    function _fill(doc, color) { doc.setFillColor(...color); }
    function _draw(doc, color) { doc.setDrawColor(...color); }

    function _rect(doc, x, y, w, h, color, r = 0) {
        _fill(doc, color);
        if (r > 0) doc.roundedRect(x, y, w, h, r, r, 'F');
        else doc.rect(x, y, w, h, 'F');
    }

    function _line(doc, x1, y1, x2, y2, color = PDF.C_SURF2, lw = 0.3) {
        _draw(doc, color);
        doc.setLineWidth(lw);
        doc.line(x1, y1, x2, y2);
    }

    function _text(doc, text, x, y, opts = {}) {
        const { color = PDF.C_TEXT, size = 10, font = 'helvetica', style = 'normal', align = 'left' } = opts;
        doc.setFont(font, style);
        doc.setFontSize(size);
        _rgb(doc, color);
        doc.text(String(text ?? ''), x, y, { align });
    }

    /* ── Captura de canvas Chart.js → base64 PNG ─────── */
    function _captureChart(chartId, w, h) {
        return new Promise(resolve => {
            const canvas = document.getElementById(chartId);
            if (!canvas) { resolve(null); return; }
            try {
                // Crea un canvas temporal con fondo oscuro
                const tmp = document.createElement('canvas');
                tmp.width = w || canvas.width || 600;
                tmp.height = h || canvas.height || 300;
                const ctx = tmp.getContext('2d');
                ctx.fillStyle = '#0d0f12';
                ctx.fillRect(0, 0, tmp.width, tmp.height);
                ctx.drawImage(canvas, 0, 0, tmp.width, tmp.height);
                resolve(tmp.toDataURL('image/png'));
            } catch { resolve(null); }
        });
    }

    /* ── Construye el payload de datos ──────────────────
       Útil también para el endpoint de envío por correo  */
    async function getPayload() {
        const snap = ChartsModule?.getSnapshot?.();
        if (!snap) throw new Error('ChartsModule.getSnapshot no disponible');

        const { period, domain, dateFrom, dateTo, kpis, stats, filtered } = snap;

        // Captura asíncrona de los 4 canvas
        const [imgTrend, imgBar, imgDonut, imgOpens] = await Promise.all([
            _captureChart('chart-trend', 900, 350),
            _captureChart('chart-bar', 900, 300),
            _captureChart('chart-donut', 260, 260),
            _captureChart('chart-opens', 900, 260),
        ]);

        // Top dominios desde filtered
        const domMap = {};
        filtered.forEach(e => {
            const m = (e.email_to || '').match(/@([^\s>]+)/);
            if (m) domMap[m[1]] = (domMap[m[1]] || 0) + 1;
        });
        const topDomains = Object.entries(domMap).sort((a, b) => b[1] - a[1]).slice(0, 8);

        const periodLabel = period > 0
            ? `Últimos ${period} días`
            : (dateFrom && dateTo)
                ? `${_fmtDate(dateFrom)} — ${_fmtDate(dateTo)}`
                : 'Período personalizado';

        return {
            generatedAt: new Date().toISOString(),
            period, domain, periodLabel,
            kpis, stats,
            topDomains,
            charts: { trend: imgTrend, bar: imgBar, donut: imgDonut, opens: imgOpens },
        };
    }

    /* ── Función principal: genera y descarga el PDF ──── */
    async function download() {
        if (!window.jspdf?.jsPDF) {
            AlertsModule?.showToast('❌ jsPDF no cargado aún, intenta de nuevo', 'error');
            return;
        }

        _showProgress(10, 'Capturando gráficas…');

        let payload;
        try {
            payload = await getPayload();
        } catch (err) {
            _hideProgress();
            AlertsModule?.showToast('❌ Error al generar datos: ' + err.message, 'error');
            console.error('[ReportsModule]', err);
            return;
        }

        _showProgress(40, 'Construyendo PDF…');

        const { jsPDF } = window.jspdf;
        const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
        let y = 0;

        try {
            y = _drawCover(doc, payload);
            _showProgress(55, 'Añadiendo métricas…');
            y = _drawKPIs(doc, y, payload.kpis);
            _showProgress(65, 'Insertando gráfica de tendencia…');
            y = _drawChartSection(doc, y, 'Tendencia de envíos', payload.charts.trend, 55);
            _showProgress(75, 'Insertando gráfica de rebotes…');
            y = _drawChartSection(doc, y, 'Envíos vs Rebotes', payload.charts.bar, 50);
            _showProgress(82, 'Insertando donut…');
            y = _drawDonutSection(doc, y, payload.charts.donut);
            _showProgress(88, 'Insertando aperturas…');
            y = _drawChartSection(doc, y, 'Aperturas por día', payload.charts.opens, 45);
            _showProgress(93, 'Tabla de dominios…');
            y = _drawDomainsTable(doc, y, payload.topDomains, payload.kpis.total);
            _showProgress(98, 'Finalizando…');
            _drawFooters(doc);
        } catch (err) {
            _hideProgress();
            AlertsModule?.showToast('❌ Error al generar PDF: ' + err.message, 'error');
            console.error('[ReportsModule]', err);
            return;
        }

        const filename = `mailtrack-reporte-${_dateTag()}.pdf`;
        doc.save(filename);
        _hideProgress();
        AlertsModule?.showToast('✅ Reporte PDF descargado', 'ok', 3000);
    }

    /* ══════════════════════════════════════════════════
       SECCIONES DEL PDF
    ══════════════════════════════════════════════════ */

    /* ── Portada ── */
    function _drawCover(doc, { periodLabel, domain, generatedAt }) {
        const W = PDF.W, ML = PDF.ML;

        // Fondo completo oscuro
        _rect(doc, 0, 0, W, 60, PDF.C_BG);

        // Barra de acento en la parte superior
        _rect(doc, 0, 0, W, 3, PDF.C_ACCENT);

        // Logo cuadrado verde
        _rect(doc, ML, 14, 10, 10, PDF.C_ACCENT, 2);
        _text(doc, '✦', ML + 5, 21, { color: PDF.C_BG, size: 8, align: 'center' });

        // Nombre de la app
        _text(doc, 'Mail', ML + 14, 21, { color: PDF.C_TEXT, size: 16, style: 'bold' });
        _text(doc, 'Track', ML + 31, 21, { color: PDF.C_ACCENT, size: 16, style: 'bold' });

        // Subtítulo del reporte
        _text(doc, 'Reporte de Entregabilidad SES', ML, 32, { color: PDF.C_TEXT2, size: 10 });

        // Período y dominio (derecha)
        _text(doc, periodLabel, W - ML, 18, { color: PDF.C_TEXT, size: 10, style: 'bold', align: 'right' });
        _text(doc, domain ? `Dominio: ${domain}` : 'Todos los dominios', W - ML, 24, { color: PDF.C_TEXT2, size: 8, align: 'right' });
        _text(doc, `Generado: ${_fmtDateTime(new Date(generatedAt))}`, W - ML, 30, { color: PDF.C_TEXT3, size: 8, align: 'right' });

        // Línea divisoria
        _line(doc, ML, 42, W - ML, 42, PDF.C_SURF2, 0.4);

        return 50; // y después de la portada
    }

    /* ── KPI Cards (2×2) ── */
    function _drawKPIs(doc, y, kpis) {
        const ML = PDF.ML, CW = PDF.CONTENT;
        const cw = (CW - 6) / 2;  // 2 columnas
        const ch = 22;

        _text(doc, 'RESUMEN EJECUTIVO', ML, y, { color: PDF.C_TEXT3, size: 7, style: 'bold' });
        y += 5;

        const cards = [
            { label: 'ENVIADOS', value: _fmtNum(kpis.total), sub: 'total en período', color: PDF.C_BLUE },
            { label: 'ENTREGADOS', value: kpis.delivRate + '%', sub: _fmtNum(kpis.delivered) + ' correos', color: PDF.C_ACCENT },
            { label: 'TASA DE APERTURA', value: kpis.openRate + '%', sub: _fmtNum(kpis.open) + ' abiertos', color: PDF.C_YELLOW },
            { label: 'BOUNCE RATE', value: kpis.bounceRate + '%', sub: _fmtNum(kpis.bounce) + ' rebotes', color: +kpis.bounceRate >= 2 ? PDF.C_RED : PDF.C_ORANGE },
        ];

        cards.forEach((card, i) => {
            const col = i % 2;
            const row = Math.floor(i / 2);
            const cx = ML + col * (cw + 6);
            const cy = y + row * (ch + 4);

            // Card background
            _rect(doc, cx, cy, cw, ch, PDF.C_SURF, 2);

            // Color stripe top
            _rect(doc, cx, cy, cw, 1.5, card.color, 0);

            // Label
            _text(doc, card.label, cx + 5, cy + 7, { color: PDF.C_TEXT3, size: 6, style: 'bold' });

            // Big value
            _text(doc, card.value, cx + 5, cy + 15, { color: PDF.C_TEXT, size: 14, style: 'bold' });

            // Sub
            _text(doc, card.sub, cx + cw - 5, cy + 18, { color: PDF.C_TEXT3, size: 7, align: 'right' });
        });

        return y + 2 * ch + 4 * 4 + 6; // 2 rows + gaps + padding
    }

    /* ── Sección de gráfica genérica ── */
    function _drawChartSection(doc, y, title, imgData, imgH) {
        const ML = PDF.ML, CW = PDF.CONTENT;
        y = _ensureSpace(doc, y, imgH + 20);

        _text(doc, title, ML, y, { color: PDF.C_TEXT2, size: 7, style: 'bold' });
        y += 4;

        if (imgData) {
            // Card de fondo
            _rect(doc, ML, y, CW, imgH + 4, PDF.C_SURF, 2);
            try {
                doc.addImage(imgData, 'PNG', ML + 2, y + 2, CW - 4, imgH, undefined, 'FAST');
            } catch { /* si falla la imagen, la omitimos silenciosamente */ }
        } else {
            _rect(doc, ML, y, CW, imgH, PDF.C_SURF, 2);
            _text(doc, 'Gráfica no disponible', ML + CW / 2, y + imgH / 2, { color: PDF.C_TEXT3, size: 8, align: 'center' });
        }

        return y + imgH + 10;
    }

    /* ── Sección de donut (imagen cuadrada + stats al lado) ── */
    function _drawDonutSection(doc, y, imgData) {
        const ML = PDF.ML, CW = PDF.CONTENT;
        const dh = 46;
        y = _ensureSpace(doc, y, dh + 14);

        _text(doc, 'DISTRIBUCIÓN POR ESTADO', ML, y, { color: PDF.C_TEXT3, size: 7, style: 'bold' });
        y += 4;

        _rect(doc, ML, y, CW, dh + 4, PDF.C_SURF, 2);

        if (imgData) {
            try {
                doc.addImage(imgData, 'PNG', ML + 2, y + 2, dh, dh, undefined, 'FAST');
            } catch { /* ignore */ }
        }

        // Stats mini junto al donut
        const snap = ChartsModule?.getSnapshot?.();
        if (snap) {
            const { total, delivered, open, bounce, complaint } = snap.kpis;
            const tot = total || 1;
            const statsX = ML + dh + 8;
            const items = [
                { label: 'Entregados', val: delivered, pct: (delivered / tot * 100).toFixed(1), color: PDF.C_ACCENT },
                { label: 'Abiertos', val: open, pct: (open / tot * 100).toFixed(1), color: PDF.C_YELLOW },
                { label: 'Bounce', val: bounce, pct: (bounce / tot * 100).toFixed(1), color: PDF.C_RED },
                { label: 'Complaint', val: complaint, pct: (complaint / tot * 100).toFixed(1), color: PDF.C_ORANGE },
            ];
            let sy = y + 8;
            items.forEach(item => {
                _rect(doc, statsX, sy - 1.5, 2.5, 2.5, item.color, 1);
                _text(doc, item.label, statsX + 5, sy, { color: PDF.C_TEXT2, size: 8 });
                _text(doc, _fmtNum(item.val), statsX + 40, sy, { color: PDF.C_TEXT, size: 8, style: 'bold' });
                _text(doc, item.pct + '%', statsX + 62, sy, { color: PDF.C_TEXT3, size: 7, align: 'right' });
                sy += 9;
            });
        }

        return y + dh + 14;
    }

    /* ── Tabla de top dominios ── */
    function _drawDomainsTable(doc, y, entries, total) {
        const ML = PDF.ML, CW = PDF.CONTENT;
        if (!entries.length) return y;
        y = _ensureSpace(doc, y, 15 + entries.length * 7 + 5);

        _text(doc, 'TOP DOMINIOS DESTINATARIOS', ML, y, { color: PDF.C_TEXT3, size: 7, style: 'bold' });
        y += 5;

        // Header
        _rect(doc, ML, y, CW, 7, PDF.C_SURF2, 2);
        ['#', 'Dominio', 'Envíos', '%'].forEach((h, i) => {
            const xs = [ML + 3, ML + 12, ML + CW - 30, ML + CW - 12];
            const al = i >= 2 ? 'right' : 'left';
            _text(doc, h, xs[i], y + 4.5, { color: PDF.C_TEXT3, size: 6.5, style: 'bold', align: al });
        });
        y += 8;

        entries.forEach(([dom, cnt], i) => {
            const rowColor = i % 2 === 0 ? PDF.C_SURF : PDF.C_BG;
            _rect(doc, ML, y, CW, 6.5, rowColor);
            _text(doc, String(i + 1), ML + 3, y + 4.2, { color: PDF.C_TEXT3, size: 7 });
            _text(doc, '@' + dom, ML + 12, y + 4.2, { color: PDF.C_TEXT, size: 7 });
            _text(doc, _fmtNum(cnt), ML + CW - 30, y + 4.2, { color: PDF.C_TEXT, size: 7, align: 'right' });
            _text(doc, (total ? cnt / total * 100 : 0).toFixed(1) + '%', ML + CW - 12, y + 4.2, { color: PDF.C_TEXT3, size: 7, align: 'right' });

            // Mini progress bar
            const barX = ML + CW - 28;
            const barW = 14;
            const maxCnt = entries[0][1] || 1;
            _rect(doc, barX, y + 3.5, barW, 1.5, PDF.C_SURF2);
            _rect(doc, barX, y + 3.5, Math.max(0.5, barW * (cnt / maxCnt)), 1.5, PDF.C_ACCENT);
            y += 6.5;
        });

        return y + 6;
    }

    /* ── Pie de página en todas las páginas ── */
    function _drawFooters(doc) {
        const totalPages = doc.getNumberOfPages();
        for (let i = 1; i <= totalPages; i++) {
            doc.setPage(i);
            _line(doc, PDF.ML, PDF.H - 12, PDF.W - PDF.ML, PDF.H - 12, PDF.C_SURF2, 0.3);
            _text(doc, 'MailTrack SES Dashboard', PDF.ML, PDF.H - 7, { color: PDF.C_TEXT3, size: 7 });
            _text(doc, `Pág. ${i} / ${totalPages}`, PDF.W - PDF.ML, PDF.H - 7, { color: PDF.C_TEXT3, size: 7, align: 'right' });
            _text(doc, 'Generado automáticamente · Datos de producción', PDF.W / 2, PDF.H - 7, { color: PDF.C_TEXT3, size: 7, align: 'center' });
        }
    }

    /* ── Salto de página si no hay espacio ── */
    function _ensureSpace(doc, y, needed) {
        if (y + needed > PDF.H - 20) {
            doc.addPage();
            _rect(doc, 0, 0, PDF.W, 10, PDF.C_BG);
            _rect(doc, 0, 0, PDF.W, 1.5, PDF.C_ACCENT);
            return 16;
        }
        return y;
    }

    /* ── Progress overlay ── */
    function _showProgress(pct, msg) {
        let box = document.getElementById('pdf-progress-overlay');
        if (!box) {
            box = document.createElement('div');
            box.id = 'pdf-progress-overlay';
            box.className = 'pdf-progress-overlay';
            box.innerHTML = `
        <div class="pdf-progress-box">
          <div class="pdf-progress-title">🖨 Generando reporte PDF…</div>
          <div class="pdf-progress-sub" id="pdf-progress-msg">Iniciando…</div>
          <div class="pdf-progress-bar-track">
            <div class="pdf-progress-bar-fill" id="pdf-progress-fill"></div>
          </div>
        </div>`;
            document.body.appendChild(box);
        }
        box.classList.add('show');
        const msg_el = document.getElementById('pdf-progress-msg');
        const fill = document.getElementById('pdf-progress-fill');
        if (msg_el) msg_el.textContent = msg || '';
        if (fill) fill.style.width = pct + '%';
    }

    function _hideProgress() {
        const box = document.getElementById('pdf-progress-overlay');
        if (box) {
            setTimeout(() => box.classList.remove('show'), 400);
        }
        const btn = document.getElementById('btn-pdf');
        if (btn) btn.classList.remove('loading');
    }

    /* ── Utilidades de formato ── */
    function _fmtNum(n) { return Number(n ?? 0).toLocaleString('es-CO'); }
    function _dateTag() { return new Date().toISOString().slice(0, 10); }
    function _fmtDate(d) { return d instanceof Date ? d.toLocaleDateString('es-CO') : String(d).slice(0, 10); }
    function _fmtDateTime(d) {
        return d.toLocaleString('es-CO', {
            timeZone: 'America/Bogota', day: '2-digit', month: 'short',
            year: 'numeric', hour: '2-digit', minute: '2-digit',
        });
    }

    /* ── Trigger desde el botón ── */
    function triggerDownload() {
        const btn = document.getElementById('btn-pdf');
        if (btn) btn.classList.add('loading');
        download().catch(err => {
            console.error('[ReportsModule] download failed', err);
            AlertsModule?.showToast('❌ Error al generar PDF', 'error');
            _hideProgress();
        });
    }

    return { download, triggerDownload, getPayload };
})();
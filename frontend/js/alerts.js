/**
 * MailTrack — SES Dashboard
 * js/alerts.js
 *
 * Lógica de alertas para métricas de email deliverability.
 * Migración futura → React: cada función es un hook o componente.
 *
 * Exports (uso global en HTML, namespace en módulo ES):
 *   AlertsModule.evaluate(stats)      → calcula niveles de alerta
 *   AlertsModule.render(el, stats)    → renderiza banner en DOM
 *   AlertsModule.showToast(msg)       → muestra notificación flotante
 *   AlertsModule.THRESHOLDS           → umbrales configurables
 *   AlertsModule.DEMO_STATS           → datos de prueba
 */

const AlertsModule = (() => {

    /* ─────────────────────────────────────────────────
        CONFIGURACIÓN — umbrales de AWS SES
        → React: exportar como constantes / config file
       ───────────────────────────────────────────────── */
    const THRESHOLDS = {
        bounce: {
            ok: 2.0,   // < 2%   → verde, todo bien
            warning: 5.0,   // 2–5%   → amarillo, revisar lista
            critical: 5.0,   // ≥ 5%   → rojo, riesgo de suspensión SES
        },
        complaint: {
            ok: 0.08,  // < 0.08% → verde
            warning: 0.10,  // 0.08–0.10% → amarillo
            critical: 0.10,  // ≥ 0.10%  → rojo
        },
        delivery: {
            healthy: 95,    // ≥ 95% → tasa de entrega saludable
            warning: 85,    // 85–95% → revisar
        },
    };

    /* ─────────────────────────────────────────────────
    DATOS DE PRUEBA
    → En producción: reemplazar con apiFetch('/emails/stats')
    → React: pasar como prop <AlertBanner stats={stats} />
       ───────────────────────────────────────────────── */
    const DEMO_STATS = {
        total_sent: 540,
        total_delivered: 520,
        total_bounce: 11,    // ← 2.03% → dispara alerta amarilla
        total_open: 210,
        total_complaint: 1,
        delivery_rate: 96.3,
        bounce_rate: 2.03,
        complaint_rate: 0.18,
    };

    /* ─────────────────────────────────────────────────
    evaluate(stats) → AlertLevel
    → React: custom hook useBounceAlert(stats)
    ───────────────────────────────────────────────── */
    function evaluate(stats) {
        const br = parseFloat(stats.bounce_rate) || 0;
        const cr = parseFloat(stats.complaint_rate) || 0;
        const dr = parseFloat(stats.delivery_rate) || 0;

        const alerts = [];

        // ── Bounce rate ──────────────────────────────
        if (br >= THRESHOLDS.bounce.critical) {
            alerts.push({
                type: 'critical',
                metric: 'Bounce Rate',
                value: br + '%',
                title: 'Alerta crítica — Bounce rate elevado',
                desc: `Tasa actual ${br}% supera el límite de AWS SES (${THRESHOLDS.bounce.critical}%). Tu cuenta puede ser suspendida.`,
                action: 'Limpia tu lista de contactos inmediatamente.',
                cssClass: '',         // default rojo
            });
        } else if (br >= THRESHOLDS.bounce.ok) {
            alerts.push({
                type: 'warning',
                metric: 'Bounce Rate',
                value: br + '%',
                title: 'Advertencia — Bounce rate por encima del umbral',
                desc: `Tasa actual ${br}% · Umbral recomendado <${THRESHOLDS.bounce.ok}% · Revisa tu lista de contactos.`,
                action: 'Considera una limpieza de lista o doble opt-in.',
                cssClass: 'is-warning',
            });
        }

        // ── Complaint rate ───────────────────────────
        if (cr >= THRESHOLDS.complaint.critical) {
            alerts.push({
                type: 'critical',
                metric: 'Complaint Rate',
                value: cr + '%',
                title: 'Tasa de quejas crítica',
                desc: `${cr}% de quejas supera el límite de AWS SES (${THRESHOLDS.complaint.critical}%).`,
                action: 'Revisa el contenido de tus correos y opciones de unsubscribe.',
                cssClass: '',
            });
        } else if (cr >= THRESHOLDS.complaint.ok) {
            alerts.push({
                type: 'warning',
                metric: 'Complaint Rate',
                value: cr + '%',
                title: 'Tasa de quejas elevada',
                desc: `${cr}% de quejas · Umbral seguro <${THRESHOLDS.complaint.ok}%.`,
                action: 'Verifica que tus correos tengan link de unsubscribe visible.',
                cssClass: 'is-warning',
            });
        }

        // ── Delivery rate ────────────────────────────
        if (dr < THRESHOLDS.delivery.warning) {
            alerts.push({
                type: 'warning',
                metric: 'Delivery Rate',
                value: dr + '%',
                title: 'Tasa de entrega baja',
                desc: `Solo el ${dr}% de correos fueron entregados · Mínimo recomendado: ${THRESHOLDS.delivery.warning}%.`,
                action: 'Revisa configuración SPF, DKIM y DMARC.',
                cssClass: 'is-warning',
            });
        }

        // ── Todo en orden ────────────────────────────
        if (alerts.length === 0) {
            alerts.push({
                type: 'ok',
                metric: 'All',
                value: br + '%',
                title: 'Reputación saludable',
                desc: `Bounce ${br}% · Quejas ${cr}% · Entrega ${dr}% — Todos los indicadores dentro de los límites seguros de AWS SES.`,
                action: null,
                cssClass: 'is-ok',   // CSS: .an-alert.is-ok (verde)
                // Otras clases disponibles: is-warning (amarillo), is-hidden (oculto)
            });
        }

        return alerts;
    }

    /* ─────────────────────────────────────────────────
    render(containerEl, stats)
    Renderiza el banner de alerta más prioritario en el DOM.
    → React: componente <AlertBanner /> con props
    ───────────────────────────────────────────────── */
    function render(containerEl, stats) {
        if (!containerEl) return;

        const alerts = evaluate(stats);

        // Mostrar solo la alerta más prioritaria (crítica > warning > ok)
        const priority = ['critical', 'warning', 'ok'];
        const top = priority.reduce((found, type) => {
            return found || alerts.find(a => a.type === type);
        }, null);

        if (!top) { containerEl.innerHTML = ''; return; }

        containerEl.innerHTML = `
        <div class="an-alert ${top.cssClass}" role="alert" aria-live="polite">
        <span class="an-alert-icon" aria-hidden="true">${_icon(top.type)}</span>
        <div class="an-alert-body">
            <div class="an-alert-title">${top.title}</div>
            <div class="an-alert-desc">${top.desc}${top.action ? ' <strong>' + top.action + '</strong>' : ''}</div>
        </div>
        <span class="an-alert-badge">${top.value}</span>
        </div>`;

        // Si hay múltiples alertas, añade contador
        if (alerts.length > 1 && top.type !== 'ok') {
            const extra = alerts.length - 1;
            containerEl.innerHTML += `
        <p style="font-size:11px;color:var(--text3);font-family:var(--font-mono);margin-top:-8px;padding-left:4px">
            +${extra} alerta${extra > 1 ? 's' : ''} adicional${extra > 1 ? 'es' : ''} — revisa el panel de métricas
        </p>`;
        }
    }

    /* ─────────────────────────────────────────────────
    showToast(message, duration)
    → React: componente <Toast /> con useEffect + timeout
    ───────────────────────────────────────────────── */
    function showToast(message = '✓ Actualizado', duration = 2800) {
        let toast = document.getElementById('an-toast');
        if (!toast) {
            toast = document.createElement('div');
            toast.id = 'an-toast';
            toast.className = 'toast';
            document.body.appendChild(toast);
        }
        toast.textContent = message;
        toast.classList.add('show');
        setTimeout(() => toast.classList.remove('show'), duration);
    }

    /* ─────────────────────────────────────────────────
    PRIVATE HELPERS
    ───────────────────────────────────────────────── */
    function _icon(type) {
        return { critical: '🚨', warning: '⚠️', ok: '✅' }[type] || '📊';
    }

    /* ─────────────────────────────────────────────────
    PUBLIC API
    ───────────────────────────────────────────────── */
    return { evaluate, render, showToast, THRESHOLDS, DEMO_STATS };

})();


/* ═══════════════════════════════════════════════════
    DEMO MODE — se activa automáticamente si no hay API
    Eliminar en producción o reemplazar con fetch real.
   ═══════════════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {
    const alertContainer = document.getElementById('alert-container');
    if (!alertContainer) return;

    // Si la página tiene datos reales (inyectados por charts.js), no hacer nada.
    // Si no, renderizar con datos de prueba después de 300ms.
    setTimeout(() => {
        if (alertContainer.dataset.loaded !== 'true') {
            AlertsModule.render(alertContainer, AlertsModule.DEMO_STATS);
        }
    }, 300);
});
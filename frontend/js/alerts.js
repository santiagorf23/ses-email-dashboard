/**
 * MailTrack — SES Dashboard
 * js/alerts.js  v3
 *
 * Lógica de alertas con umbrales configurables.
 * Los umbrales se persisten en localStorage ('mt_thresholds').
 *
 * API pública:
 *   AlertsModule.evaluate(stats)    → array de alertas activas
 *   AlertsModule.render(el, stats)  → pinta banner en #alert-container
 *   AlertsModule.showToast(msg, type)
 *   AlertsModule.openSettings()     → modal de umbrales
 *   AlertsModule.getThresholds()
 *   AlertsModule._saveFromModal()   → llamado desde el modal
 */
const AlertsModule = (() => {

    /* ── Umbrales por defecto (AWS SES guidelines) ── */
    const DEFAULTS = {
        bounce_warning: 2.0,
        bounce_critical: 5.0,
        complaint_warning: 0.08,
        complaint_critical: 0.10,
        delivery_warning: 95,
    };
    const STORAGE_KEY = 'mt_thresholds';

    function getThresholds() {
        try {
            const s = JSON.parse(localStorage.getItem(STORAGE_KEY));
            return s ? { ...DEFAULTS, ...s } : { ...DEFAULTS };
        } catch { return { ...DEFAULTS }; }
    }
    function saveThresholds(t) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(t));
    }

    /* ── evaluate(stats) ── */
    function evaluate(stats) {
        const T = getThresholds();
        const br = parseFloat(stats.bounce_rate) || 0;
        const cr = parseFloat(stats.complaint_rate)
            || (stats.total_sent > 0 ? (stats.total_complaint / stats.total_sent) * 100 : 0);
        const dr = parseFloat(stats.delivery_rate) || 0;
        const list = [];

        if (br >= T.bounce_critical) {
            list.push({
                type: 'critical', value: br.toFixed(2) + '%', cssClass: '',
                title: 'Bounce rate crítico',
                desc: `Tasa actual ${br.toFixed(2)}% supera el límite crítico (${T.bounce_critical}%). AWS SES puede suspender tu cuenta.`,
                action: 'Limpia tu lista de contactos inmediatamente.'
            });
        } else if (br >= T.bounce_warning) {
            list.push({
                type: 'warning', value: br.toFixed(2) + '%', cssClass: 'is-warning',
                title: 'Bounce rate elevado',
                desc: `Tasa actual ${br.toFixed(2)}% · umbral: <${T.bounce_warning}% · Revisa tu lista.`,
                action: 'Considera limpieza de lista o doble opt-in.'
            });
        }

        if (cr >= T.complaint_critical) {
            list.push({
                type: 'critical', value: cr.toFixed(3) + '%', cssClass: '',
                title: 'Tasa de quejas crítica',
                desc: `${cr.toFixed(3)}% supera el límite crítico (${T.complaint_critical}%).`,
                action: 'Revisa el contenido y las opciones de unsubscribe.'
            });
        } else if (cr >= T.complaint_warning) {
            list.push({
                type: 'warning', value: cr.toFixed(3) + '%', cssClass: 'is-warning',
                title: 'Tasa de quejas elevada',
                desc: `${cr.toFixed(3)}% · umbral: <${T.complaint_warning}%.`,
                action: 'Verifica que tus correos tengan link de unsubscribe visible.'
            });
        }

        if (dr > 0 && dr < T.delivery_warning) {
            list.push({
                type: 'warning', value: dr + '%', cssClass: 'is-warning',
                title: 'Tasa de entrega baja',
                desc: `Solo el ${dr}% de correos fueron entregados · mínimo: ${T.delivery_warning}%.`,
                action: 'Revisa configuración SPF, DKIM y DMARC.'
            });
        }

        if (list.length === 0) {
            list.push({
                type: 'ok', value: br.toFixed(2) + '%', cssClass: 'is-ok',
                title: 'Reputación saludable',
                desc: `Bounce ${br.toFixed(2)}% · Quejas ${cr.toFixed(3)}% · Entrega ${dr}% — todos los indicadores dentro de límites.`,
                action: null
            });
        }
        return list;
    }

    /* ── render(el, stats) ── */
    function render(containerEl, stats) {
        if (!containerEl) return;
        const list = evaluate(stats);
        const priority = ['critical', 'warning', 'ok'];
        const top = priority.reduce((f, t) => f || list.find(a => a.type === t), null);
        if (!top) { containerEl.innerHTML = ''; return; }

        containerEl.innerHTML = `
        <div class="an-alert ${top.cssClass}" role="alert">
            <span class="an-alert-icon">${_icon(top.type)}</span>
            <div class="an-alert-body">
            <div class="an-alert-title">${top.title}</div>
            <div class="an-alert-desc">${top.desc}${top.action ? ' <strong>' + top.action + '</strong>' : ''}</div>
            </div>
            <div style="display:flex;align-items:center;gap:8px;flex-shrink:0">
            <span class="an-alert-badge">${top.value}</span>
            <button onclick="AlertsModule.openSettings()"
                style="background:none;border:1px solid currentColor;border-radius:5px;
                    padding:3px 8px;font-size:10px;cursor:pointer;color:inherit;
                    opacity:.75;font-family:var(--font-mono);white-space:nowrap"
                title="Configurar umbrales">⚙ Config</button>
            </div>
        </div>
        ${list.length > 1 && top.type !== 'ok'
        ? `<p style="font-size:11px;color:var(--text3);font-family:var(--font-mono); margin-top:-4px; padding-left:4px">
            +${list.length - 1} alerta${list.length > 2 ? 's' : ''} adicional${list.length > 2 ? 'es' : ''}
        </p>` : ''}`;

        containerEl.dataset.loaded = 'true';
    }

    /* ── showToast(msg, type) ── */
    function showToast(message = '✓ Actualizado', type = 'ok', duration = 2800) {
        let el = document.getElementById('an-toast');
        if (!el) {
            el = document.createElement('div');
            el.id = 'an-toast'; el.className = 'toast';
            document.body.appendChild(el);
        }
        el.style.color = { ok: 'var(--accent)', error: 'var(--red)', warn: 'var(--yellow)' }[type] || 'var(--accent)';
        el.textContent = message;
        el.classList.add('show');
        clearTimeout(el._tid);
        el._tid = setTimeout(() => el.classList.remove('show'), duration);
    }

    /* ── Modal de configuración ── */
    function openSettings() {
        let overlay = document.getElementById('alert-settings-modal');
        if (!overlay) { overlay = _buildModal(); document.body.appendChild(overlay); }
        _populateModal(overlay);
        overlay.classList.add('open');
    }

    function _buildModal() {
        const o = document.createElement('div');
        o.id = 'alert-settings-modal';
        o.className = 'modal-overlay';
        o.innerHTML = `
        <div class="modal" role="dialog" aria-modal="true">
            <div class="modal-header">
            <span class="modal-header-icon">🔔</span>
            <span class="modal-title">Configurar umbrales de alerta</span>
            <button class="modal-close" onclick="document.getElementById('alert-settings-modal').classList.remove('open')">✕</button>
            </div>
            <div class="modal-body">

            <div class="form-field">
                <label class="form-label">Bounce rate — advertencia (%)</label>
                <div class="form-slider-wrap">
                <input type="range" class="form-slider" id="thr-bounce-warn" min="0.5" max="10" step="0.1" />
                <span class="form-slider-val" id="thr-bounce-warn-val">2.0%</span>
                </div>
                <span class="form-hint">Alerta amarilla cuando la tasa supere este valor.</span>
            </div>

            <div class="form-field">
                <label class="form-label">Bounce rate — crítico (%)</label>
                <div class="form-slider-wrap">
                <input type="range" class="form-slider" id="thr-bounce-crit" min="1" max="15" step="0.1" />
                <span class="form-slider-val" id="thr-bounce-crit-val">5.0%</span>
                </div>
                <span class="form-hint">Alerta roja pulsante. AWS SES suspende sobre el 10%.</span>
            </div>

            <div class="form-field">
                <label class="form-label">Tasa de quejas — advertencia (%)</label>
                <div class="form-slider-wrap">
                <input type="range" class="form-slider" id="thr-complaint-warn" min="0.01" max="0.5" step="0.01" />
                <span class="form-slider-val" id="thr-complaint-warn-val">0.08%</span>
                </div>
            </div>

            <div class="form-field">
                <label class="form-label">Tasa de entrega mínima (%)</label>
                <div class="form-slider-wrap">
                <input type="range" class="form-slider" id="thr-delivery" min="50" max="99" step="1" />
                <span class="form-slider-val" id="thr-delivery-val">95%</span>
                </div>
                <span class="form-hint">Alerta si la entrega cae por debajo de este valor.</span>
            </div>

            <div class="threshold-preview">
                <div class="tp-item"><div class="tp-label">Bounce warn</div><div class="tp-val warn" id="tp-bw">—</div></div>
                <div class="tp-item"><div class="tp-label">Bounce crit</div><div class="tp-val bad"  id="tp-bc">—</div></div>
                <div class="tp-item"><div class="tp-label">Complaint</div> <div class="tp-val warn" id="tp-cw">—</div></div>
                <div class="tp-item"><div class="tp-label">Entrega mín</div><div class="tp-val good" id="tp-dr">—</div></div>
            </div>

            </div>
            <div class="modal-footer">
            <button class="btn-modal-cancel" onclick="document.getElementById('alert-settings-modal').classList.remove('open')">Cancelar</button>
            <button class="btn-modal-save"   onclick="AlertsModule._saveFromModal()">Guardar umbrales</button>
            </div>
        </div>`;

        o.addEventListener('click', e => { if (e.target === o) o.classList.remove('open'); });

        // Bind sliders → live preview
        [
            ['thr-bounce-warn', 'thr-bounce-warn-val', 'tp-bw', v => v + '%'],
            ['thr-bounce-crit', 'thr-bounce-crit-val', 'tp-bc', v => v + '%'],
            ['thr-complaint-warn', 'thr-complaint-warn-val', 'tp-cw', v => v + '%'],
            ['thr-delivery', 'thr-delivery-val', 'tp-dr', v => v + '%'],
        ].forEach(([sid, vid, pid, fmt]) => {
            const sl = o.querySelector('#' + sid);
            const vl = o.querySelector('#' + vid);
            const pv = o.querySelector('#' + pid);
            sl.addEventListener('input', () => {
                vl.textContent = fmt(sl.value);
                if (pv) pv.textContent = fmt(sl.value);
            });
        });

        return o;
    }

    function _populateModal(o) {
        const T = getThresholds();
        const set = (sid, vid, val, fmt) => {
            const sl = o.querySelector('#' + sid); if (!sl) return;
            sl.value = val;
            const vl = o.querySelector('#' + vid); if (vl) vl.textContent = fmt(val);
        };
        set('thr-bounce-warn', 'thr-bounce-warn-val', T.bounce_warning, v => v + '%');
        set('thr-bounce-crit', 'thr-bounce-crit-val', T.bounce_critical, v => v + '%');
        set('thr-complaint-warn', 'thr-complaint-warn-val', T.complaint_warning, v => v + '%');
        set('thr-delivery', 'thr-delivery-val', T.delivery_warning, v => v + '%');
        const bw = o.querySelector('#tp-bw'); if (bw) bw.textContent = T.bounce_warning + '%';
        const bc = o.querySelector('#tp-bc'); if (bc) bc.textContent = T.bounce_critical + '%';
        const cw = o.querySelector('#tp-cw'); if (cw) cw.textContent = T.complaint_warning + '%';
        const dr = o.querySelector('#tp-dr'); if (dr) dr.textContent = T.delivery_warning + '%';
    }

    function _saveFromModal() {
        const o = document.getElementById('alert-settings-modal'); if (!o) return;
        const g = id => parseFloat(o.querySelector('#' + id)?.value);
        saveThresholds({
            bounce_warning: g('thr-bounce-warn'),
            bounce_critical: g('thr-bounce-crit'),
            complaint_warning: g('thr-complaint-warn'),
            delivery_warning: g('thr-delivery'),
        });
        o.classList.remove('open');
        showToast('✓ Umbrales guardados', 'ok');
        if (window._lastStats) {
            render(document.getElementById('alert-container'), window._lastStats);
        }
    }

    function _icon(t) { return { critical: '🚨', warning: '⚠️', ok: '✅' }[t] || '📊'; }

    return { evaluate, render, showToast, openSettings, getThresholds, _saveFromModal };
})();
/**
 * MailPulse — SES Dashboard
 * js/alerts.js  v4
 *
 * Alert system with backend-synced thresholds and notification config.
 * Thresholds sync with /api/alerts/config (DB) + localStorage fallback.
 * Notifications sync with /api/alerts/notifications (DB).
 */
const AlertsModule = (() => {

    const DEFAULTS = {
        bounce_warning: 2.0,
        bounce_critical: 5.0,
        complaint_warning: 0.08,
        complaint_critical: 0.10,
        delivery_warning: 95,
    };
    const STORAGE_KEY = 'mt_thresholds';
    let _loaded = false;

    /* ── Thresholds (synced with backend) ── */
    async function getThresholds() {
        if (typeof ApiModule !== 'undefined' && ApiModule.getToken()) {
            try {
                const cfg = await ApiModule.get('/alerts/config');
                const mapped = {
                    bounce_warning: parseFloat(cfg.bounce_rate_threshold) || DEFAULTS.bounce_warning,
                    bounce_critical: parseFloat(cfg.bounce_rate_threshold) ? parseFloat(cfg.bounce_rate_threshold) : DEFAULTS.bounce_critical,
                    complaint_warning: parseFloat(cfg.complaint_rate_threshold) || DEFAULTS.complaint_warning,
                    complaint_critical: parseFloat(cfg.complaint_rate_threshold) ? parseFloat(cfg.complaint_rate_threshold) * 1.25 : DEFAULTS.complaint_critical,
                    delivery_warning: DEFAULTS.delivery_warning,
                };
                _loaded = true;
                return mapped;
            } catch (e) {
                logger.warn('Failed to fetch alert config from backend:', e.message);
            }
        }
        return getThresholdsLocal();
    }

    function getThresholdsLocal() {
        try {
            const s = JSON.parse(localStorage.getItem(STORAGE_KEY));
            return s ? { ...DEFAULTS, ...s } : { ...DEFAULTS };
        } catch { return { ...DEFAULTS }; }
    }

    function saveThresholdsLocal(t) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(t));
    }

    async function saveThresholds(t) {
        saveThresholdsLocal(t);
        if (typeof ApiModule !== 'undefined' && ApiModule.getToken()) {
            try {
                await ApiModule.put('/alerts/config', {
                    bounce_rate_threshold: t.bounce_critical,
                    complaint_rate_threshold: t.complaint_critical,
                });
            } catch (e) {
                logger.warn('Failed to save alert config to backend:', e.message);
            }
        }
    }

    /* ── Notifications (synced with backend) ── */
    async function getNotifications() {
        if (typeof ApiModule !== 'undefined' && ApiModule.getToken()) {
            try {
                return await ApiModule.get('/alerts/notifications');
            } catch (e) {
                logger.warn('Failed to fetch notifications:', e.message);
            }
        }
        try {
            return JSON.parse(localStorage.getItem('mt_notifications') || '{}');
        } catch { return {}; }
    }

    async function saveNotifications(cfg) {
        localStorage.setItem('mt_notifications', JSON.stringify(cfg));
        if (typeof ApiModule !== 'undefined' && ApiModule.getToken()) {
            try {
                await ApiModule.put('/alerts/notifications', cfg);
            } catch (e) {
                logger.warn('Failed to save notifications:', e.message);
                throw e;
            }
        }
    }

    /* ── evaluate(stats) ── */
    async function evaluate(stats) {
        const T = await getThresholds();
        const br = parseFloat(stats.bounce_rate) || 0;
        const cr = parseFloat(stats.complaint_rate)
            || (stats.total_sent > 0 ? (stats.total_complaint / stats.total_sent) * 100 : 0);
        const dr = parseFloat(stats.delivery_rate) || 0;
        const list = [];

        if (br >= T.bounce_critical) {
            list.push({
                type: 'critical', value: br.toFixed(2) + '%', cssClass: '',
                title: 'Bounce rate critico',
                desc: `Tasa actual ${br.toFixed(2)}% supera el limite critico (${T.bounce_critical}%). AWS SES puede suspender tu cuenta.`,
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
                title: 'Tasa de quejas critica',
                desc: `${cr.toFixed(3)}% supera el limite critico (${T.complaint_critical}%).`,
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
                desc: `Solo el ${dr}% de correos fueron entregados · minimo: ${T.delivery_warning}%.`,
                action: 'Revisa configuracion SPF, DKIM y DMARC.'
            });
        }

        if (list.length === 0) {
            list.push({
                type: 'ok', value: br.toFixed(2) + '%', cssClass: 'is-ok',
                title: 'Reputacion saludable',
                desc: `Bounce ${br.toFixed(2)}% · Quejas ${cr.toFixed(3)}% · Entrega ${dr}% — todos los indicadores dentro de limites.`,
                action: null
            });
        }
        return list;
    }

    /* ── render(el, stats) ── */
    async function render(containerEl, stats) {
        if (!containerEl) return;
        const list = await evaluate(stats);
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
                title="Configurar alertas">⚙ Config</button>
            </div>
        </div>
        ${list.length > 1 && top.type !== 'ok'
        ? `<p style="font-size:11px;color:var(--text3);font-family:var(--font-mono); margin-top:-4px; padding-left:4px">
            +${list.length - 1} alerta${list.length > 2 ? 's' : ''} adicional${list.length > 2 ? 'es' : ''}
        </p>` : ''}`;

        containerEl.dataset.loaded = 'true';
    }

    /* ── showToast ── */
    function showToast(message = 'Actualizado', type = 'ok', duration = 2800) {
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

    /* ── Modal: Thresholds + Notifications tabs ── */
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
        <div class="modal modal--wide" role="dialog" aria-modal="true">
            <div class="modal-header">
            <span class="modal-header-icon">🔔</span>
            <span class="modal-title">Configuracion de alertas</span>
            <button class="modal-close" onclick="document.getElementById('alert-settings-modal').classList.remove('open')">✕</button>
            </div>
            <div class="modal-tabs">
                <button class="modal-tab active" onclick="AlertsModule._switchTab('thresholds')">Umbrales</button>
                <button class="modal-tab" onclick="AlertsModule._switchTab('notifications')">Notificaciones</button>
                <button class="modal-tab" onclick="AlertsModule._switchTab('webhooks')">Webhooks</button>
            </div>
            <div class="modal-body">
                <!-- Tab: Umbrales -->
                <div class="modal-tab-content active" id="tab-thresholds">
                    <div class="form-field">
                        <label class="form-label">Bounce rate — advertencia (%)</label>
                        <div class="form-slider-wrap">
                        <input type="range" class="form-slider" id="thr-bounce-warn" min="0.5" max="10" step="0.1" />
                        <span class="form-slider-val" id="thr-bounce-warn-val">2.0%</span>
                        </div>
                    </div>
                    <div class="form-field">
                        <label class="form-label">Bounce rate — critico (%)</label>
                        <div class="form-slider-wrap">
                        <input type="range" class="form-slider" id="thr-bounce-crit" min="1" max="15" step="0.1" />
                        <span class="form-slider-val" id="thr-bounce-crit-val">5.0%</span>
                        </div>
                        <span class="form-hint">AWS SES suspende cuentas sobre 10%.</span>
                    </div>
                    <div class="form-field">
                        <label class="form-label">Tasa de quejas — advertencia (%)</label>
                        <div class="form-slider-wrap">
                        <input type="range" class="form-slider" id="thr-complaint-warn" min="0.01" max="0.5" step="0.01" />
                        <span class="form-slider-val" id="thr-complaint-warn-val">0.08%</span>
                        </div>
                    </div>
                    <div class="form-field">
                        <label class="form-label">Tasa de entrega minima (%)</label>
                        <div class="form-slider-wrap">
                        <input type="range" class="form-slider" id="thr-delivery" min="50" max="99" step="1" />
                        <span class="form-slider-val" id="thr-delivery-val">95%</span>
                        </div>
                    </div>
                    <div class="threshold-preview">
                        <div class="tp-item"><div class="tp-label">Bounce warn</div><div class="tp-val warn" id="tp-bw">—</div></div>
                        <div class="tp-item"><div class="tp-label">Bounce crit</div><div class="tp-val bad"  id="tp-bc">—</div></div>
                        <div class="tp-item"><div class="tp-label">Complaint</div> <div class="tp-val warn" id="tp-cw">—</div></div>
                        <div class="tp-item"><div class="tp-label">Entrega min</div><div class="tp-val good" id="tp-dr">—</div></div>
                    </div>
                </div>
                <!-- Tab: Notificaciones -->
                <div class="modal-tab-content" id="tab-notifications">
                    <div class="form-field">
                        <label class="form-label">Email de notificaciones</label>
                        <input type="email" class="form-input" id="noti-email" placeholder="admin@empresa.com" />
                        <span class="form-hint">Recibe alertas criticas por email.</span>
                    </div>
                    <div class="form-field">
                        <label class="form-label">Slack Webhook URL</label>
                        <input type="url" class="form-input" id="noti-slack" placeholder="https://hooks.slack.com/services/..." />
                        <span class="form-hint">Notificaciones en canal de Slack.</span>
                    </div>
                    <div class="form-field" style="display:flex;align-items:center;gap:10px;">
                        <input type="checkbox" id="noti-enabled" checked />
                        <label class="form-label" style="margin:0">Notificaciones activadas</label>
                    </div>
                </div>
                <!-- Tab: Webhooks -->
                <div class="modal-tab-content" id="tab-webhooks">
                    <div id="webhooks-list" style="margin-bottom:12px;"></div>
                    <div style="border-top:1px solid var(--border);padding-top:12px;">
                        <div class="form-field">
                            <label class="form-label">URL del webhook</label>
                            <input type="url" class="form-input" id="wh-url" placeholder="https://tu-servidor.com/webhook" />
                        </div>
                        <div class="form-field">
                            <label class="form-label">Secret (opcional, para HMAC)</label>
                            <input type="text" class="form-input" id="wh-secret" placeholder="sha256 secret" />
                        </div>
                        <div class="form-field">
                            <label class="form-label">Eventos</label>
                            <div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:4px;">
                                <label style="font-size:11px;display:flex;align-items:center;gap:4px;">
                                    <input type="checkbox" class="wh-event" value="alert.created" checked /> alert.created
                                </label>
                                <label style="font-size:11px;display:flex;align-items:center;gap:4px;">
                                    <input type="checkbox" class="wh-event" value="report.generated" /> report.generated
                                </label>
                                <label style="font-size:11px;display:flex;align-items:center;gap:4px;">
                                    <input type="checkbox" class="wh-event" value="email.bounce" /> email.bounce
                                </label>
                                <label style="font-size:11px;display:flex;align-items:center;gap:4px;">
                                    <input type="checkbox" class="wh-event" value="email.complaint" /> email.complaint
                                </label>
                            </div>
                        </div>
                        <button class="btn-modal-save" style="width:100%;margin-top:8px;" onclick="AlertsModule._addWebhook()">
                            + Agregar Webhook
                        </button>
                    </div>
                </div>
            </div>
            <div class="modal-footer">
            <button class="btn-modal-cancel" onclick="document.getElementById('alert-settings-modal').classList.remove('open')">Cancelar</button>
            <button class="btn-modal-save" onclick="AlertsModule._saveFromModal()">Guardar</button>
            </div>
        </div>`;

        o.addEventListener('click', e => { if (e.target === o) o.classList.remove('open'); });

        // Bind threshold sliders
        [
            ['thr-bounce-warn', 'thr-bounce-warn-val', 'tp-bw', v => v + '%'],
            ['thr-bounce-crit', 'thr-bounce-crit-val', 'tp-bc', v => v + '%'],
            ['thr-complaint-warn', 'thr-complaint-warn-val', 'tp-cw', v => v + '%'],
            ['thr-delivery', 'thr-delivery-val', 'tp-dr', v => v + '%'],
        ].forEach(([sid, vid, pid, fmt]) => {
            const sl = o.querySelector('#' + sid);
            const vl = o.querySelector('#' + vid);
            const pv = o.querySelector('#' + pid);
            if (sl) sl.addEventListener('input', () => {
                if (vl) vl.textContent = fmt(sl.value);
                if (pv) pv.textContent = fmt(sl.value);
            });
        });

        return o;
    }

    function _switchTab(tab) {
        const overlay = document.getElementById('alert-settings-modal');
        if (!overlay) return;
        overlay.querySelectorAll('.modal-tab').forEach((t, i) => {
            t.classList.toggle('active', (tab === 'thresholds' && i === 0) || (tab === 'notifications' && i === 1));
        });
        overlay.querySelector('#tab-thresholds').classList.toggle('active', tab === 'thresholds');
        overlay.querySelector('#tab-notifications').classList.toggle('active', tab === 'notifications');
    }

    async function _populateModal(o) {
        const T = await getThresholds();
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

        // Populate notifications
        try {
            const n = await getNotifications();
            const em = o.querySelector('#noti-email');
            const sl = o.querySelector('#noti-slack');
            const en = o.querySelector('#noti-enabled');
            if (em) em.value = n.notify_email || n.email_to || '';
            if (sl) sl.value = n.notify_slack_webhook || n.slack_webhook_url || '';
            if (en) en.checked = n.is_enabled !== false && n.email_enabled !== false;
        } catch {}

        // Load webhooks
        _loadWebhooks();
    }

    async function _saveFromModal() {
        const o = document.getElementById('alert-settings-modal'); if (!o) return;
        const g = id => parseFloat(o.querySelector('#' + id)?.value);

        // Save thresholds
        await saveThresholds({
            bounce_warning: g('thr-bounce-warn'),
            bounce_critical: g('thr-bounce-crit'),
            complaint_warning: g('thr-complaint-warn'),
            delivery_warning: g('thr-delivery'),
        });

        // Save notifications
        const email = o.querySelector('#noti-email')?.value || '';
        const slack = o.querySelector('#noti-slack')?.value || '';
        const enabled = o.querySelector('#noti-enabled')?.checked || false;
        try {
            await saveNotifications({
                notify_email: email,
                email_to: email,
                notify_slack_webhook: slack,
                slack_webhook_url: slack,
                is_enabled: enabled,
                email_enabled: enabled,
            });
        } catch (e) {
            showToast('Error guardando notificaciones', 'error');
            return;
        }

        o.classList.remove('open');
        showToast('Configuracion guardada', 'ok');
        if (window._lastStats) {
            render(document.getElementById('alert-container'), window._lastStats);
        }
    }

    function _icon(t) { return { critical: '🚨', warning: '⚠️', ok: '✅' }[t] || '📊'; }

    /* ── Webhooks CRUD ── */
    async function _loadWebhooks() {
        const list = document.getElementById('webhooks-list');
        if (!list) return;
        try {
            const res = await ApiModule.get('/webhooks/outbound');
            const hooks = res.webhooks || [];
            if (!hooks.length) {
                list.innerHTML = '<p style="font-size:11px;color:var(--text3);">No hay webhooks configurados.</p>';
                return;
            }
            list.innerHTML = hooks.map(h => `
                <div style="display:flex;align-items:center;gap:8px;padding:8px;border:1px solid var(--border);border-radius:6px;margin-bottom:6px;font-size:11px;">
                    <span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${h.url}">${h.url}</span>
                    <span style="color:${h.is_enabled ? 'var(--accent)' : 'var(--text3)'};">${h.is_enabled ? 'ON' : 'OFF'}</span>
                    <span style="color:var(--text3);font-size:10px;">${(h.events || []).join(', ')}</span>
                    <button onclick="AlertsModule._testWebhook(${h.id})" style="background:none;border:1px solid var(--border);border-radius:3px;padding:2px 6px;font-size:9px;cursor:pointer;">Test</button>
                    <button onclick="AlertsModule._deleteWebhook(${h.id})" style="background:none;border:1px solid var(--red,#f87171);color:var(--red,#f87171);border-radius:3px;padding:2px 6px;font-size:9px;cursor:pointer;">Del</button>
                </div>
            `).join('');
        } catch { list.innerHTML = '<p style="font-size:11px;color:var(--text3);">Error cargando webhooks.</p>'; }
    }

    async function _addWebhook() {
        const url = document.getElementById('wh-url')?.value?.trim();
        if (!url) { showToast('URL requerida', 'error'); return; }
        const secret = document.getElementById('wh-secret')?.value?.trim() || null;
        const events = [...document.querySelectorAll('.wh-event:checked')].map(c => c.value);
        if (!events.length) { showToast('Selecciona al menos 1 evento', 'error'); return; }
        try {
            await ApiModule.post('/webhooks/outbound', { url, secret, events });
            showToast('Webhook agregado', 'ok');
            document.getElementById('wh-url').value = '';
            document.getElementById('wh-secret').value = '';
            _loadWebhooks();
        } catch (e) { showToast('Error: ' + e.message, 'error'); }
    }

    async function _deleteWebhook(id) {
        if (!confirm('Eliminar este webhook?')) return;
        try {
            await ApiModule.del('/webhooks/outbound/' + id);
            showToast('Webhook eliminado', 'ok');
            _loadWebhooks();
        } catch (e) { showToast('Error: ' + e.message, 'error'); }
    }

    async function _testWebhook(id) {
        try {
            await ApiModule.post('/webhooks/outbound/' + id + '/test');
            showToast('Ping enviado', 'ok');
        } catch (e) { showToast('Error: ' + e.message, 'error'); }
    }

    return { evaluate, render, showToast, openSettings, getThresholds, _saveFromModal, _switchTab, getNotifications, saveNotifications, _loadWebhooks, _addWebhook, _deleteWebhook, _testWebhook };
})();

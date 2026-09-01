/**
 * MailTrack — SES Dashboard
 * js/actions.js  v1
 *
 * Gestiona las acciones sobre correos individuales:
 *   · Reenviar (resend)
 *   · Eliminar (delete)
 *   · Bloquear destinatario / enviar a bounced (block)
 *
 * ─ Cada acción hace una llamada fetch() al backend.
 * ─ Los endpoints están preparados; si responden 404/error
 *   se simula éxito en desarrollo para poder probar la UI.
 * ─ Muestra modales de confirmación para acciones destructivas.
 * ─ UI optimista: la fila reacciona inmediatamente con animación.
 *
 * API pública (namespace global ActionsModule):
 *   ActionsModule.resend(id, email, btnEl)
 *   ActionsModule.confirmDelete(id, email, btnEl)
 *   ActionsModule.confirmBlock(id, email, btnEl)
 *
 * Integración con backend Python (FastAPI):
 *   POST /api/emails/{id}/resend
 *   DELETE /api/emails/{id}
 *   POST /api/emails/block  { email_to: string }
 *
 * Para activar el modo producción real:
 *   Cambiar DEV_MODE = false
 */
const ActionsModule = (() => {

    /* ── Configuración ───────────────────────────────── */
    const API_BASE = 'http://localhost:8000/api';
    const DEV_MODE = true;   // true → simula éxito si el endpoint no existe
    const TZ = 'America/Bogota';

    /* ── Helpers de fetch ────────────────────────────── */
    function _token() {
        return localStorage.getItem('ses_token') || '';
    }

    function _headers() {
        const h = { 'Content-Type': 'application/json' };
        const t = _token();
        if (t) h['Authorization'] = 'Bearer ' + t;
        return h;
    }

    async function _call(method, path, body) {
        const opts = { method, headers: _headers() };
        if (body) opts.body = JSON.stringify(body);
        const res = await fetch(API_BASE + path, opts);

        // En DEV_MODE aceptamos 404/405/422 como "no implementado aún" → OK simulado
        if (DEV_MODE && (res.status === 404 || res.status === 405 || res.status === 422)) {
            return { ok: true, simulated: true };
        }
        if (!res.ok) {
            let msg = `HTTP ${res.status}`;
            try { const j = await res.json(); msg = j.detail || j.message || msg; } catch { /* ok */ }
            throw new Error(msg);
        }
        try { return await res.json(); } catch { return { ok: true }; }
    }

    /* ── Manipulación de filas ───────────────────────── */
    function _getRow(id) {
        return document.getElementById('email-row-' + id);
    }

    function _setRowPending(row, pending) {
        if (!row) return;
        row.classList.toggle('row-pending', pending);
    }

    function _flashRow(row, type) {
        if (!row) return;
        row.classList.remove('row-flash-success', 'row-flash-error');
        void row.offsetWidth; // reflow
        row.classList.add(type === 'success' ? 'row-flash-success' : 'row-flash-error');
        setTimeout(() => row.classList.remove('row-flash-success', 'row-flash-error'), 900);
    }

    function _setBtnSpinner(btn, on) {
        if (!btn) return;
        btn.classList.toggle('spinning', on);
        btn.disabled = on;
    }

    /* ══════════════════════════════════════════════════
       ACCIÓN 1 — REENVIAR
       POST /api/emails/{id}/resend
    ══════════════════════════════════════════════════ */
    async function resend(id, email, btnEl) {
        const row = _getRow(id);
        _setBtnSpinner(btnEl, true);
        _setRowPending(row, true);

        try {
            const result = await _call('POST', `/emails/${id}/resend`);
            _setBtnSpinner(btnEl, false);
            _setRowPending(row, false);
            _flashRow(row, 'success');

            const msg = result.simulated
                ? `↺ Reenvío simulado — ${email}`
                : `✓ Correo reenviado a ${email}`;
            AlertsModule?.showToast(msg, 'ok', 3000);

        } catch (err) {
            _setBtnSpinner(btnEl, false);
            _setRowPending(row, false);
            _flashRow(row, 'error');
            AlertsModule?.showToast('❌ No se pudo reenviar: ' + err.message, 'error', 4000);
            console.error('[ActionsModule.resend]', err);
        }
    }

    /* ══════════════════════════════════════════════════
       ACCIÓN 2 — ELIMINAR
       DELETE /api/emails/{id}
       Requiere confirmación modal.
    ══════════════════════════════════════════════════ */
    function confirmDelete(id, email, btnEl) {
        _openConfirmModal({
            icon: '🗑',
            title: 'Eliminar correo',
            body: 'Esta acción eliminará permanentemente el registro de este correo del sistema. No se puede deshacer.',
            emailLine: email,
            actionLabel: 'Eliminar',
            actionClass: 'danger',
            onConfirm: () => _executeDelete(id, email, btnEl),
        });
    }

    async function _executeDelete(id, email, btnEl) {
        const row = _getRow(id);
        _setBtnSpinner(btnEl, true);
        _setRowPending(row, true);

        try {
            const result = await _call('DELETE', `/emails/${id}`);

            // Animación de salida
            if (row) {
                row.style.transition = 'opacity .35s, transform .35s';
                row.style.opacity = '0';
                row.style.transform = 'translateX(12px)';
                await new Promise(r => setTimeout(r, 360));
                row.remove();
            }

            // Quitar del estado interno de charts.js → rerenderiza sin el item
            ChartsModule?.removeItem?.(id);

            const msg = result.simulated
                ? `🗑 Eliminación simulada — ${email}`
                : `✓ Correo de ${email} eliminado`;
            AlertsModule?.showToast(msg, 'ok', 3000);

        } catch (err) {
            _setBtnSpinner(btnEl, false);
            _setRowPending(row, false);
            _flashRow(row, 'error');
            AlertsModule?.showToast('❌ No se pudo eliminar: ' + err.message, 'error', 4000);
            console.error('[ActionsModule.delete]', err);
        }
    }

    /* ══════════════════════════════════════════════════
       ACCIÓN 3 — BLOQUEAR / BOUNCE
       POST /api/emails/block  { email_to: email }
       Requiere confirmación modal.
    ══════════════════════════════════════════════════ */
    function confirmBlock(id, email, btnEl) {
        _openConfirmModal({
            icon: '⊘',
            title: 'Bloquear destinatario',
            body: 'El correo del destinatario se añadirá a la lista de bloqueados. Los futuros envíos a esta dirección serán rechazados automáticamente.',
            emailLine: email,
            actionLabel: 'Bloquear',
            actionClass: 'warning',
            onConfirm: () => _executeBlock(id, email, btnEl),
        });
    }

    async function _executeBlock(id, email, btnEl) {
        const row = _getRow(id);
        _setBtnSpinner(btnEl, true);
        _setRowPending(row, true);

        try {
            const result = await _call('POST', '/emails/block', { email_to: email });
            _setBtnSpinner(btnEl, false);
            _setRowPending(row, false);
            _flashRow(row, 'success');

            // Actualizar el badge del botón a "activo"
            if (btnEl) {
                btnEl.classList.add('active');
                btnEl.title = 'Bloqueado — ya en lista de rebotes';
                btnEl.style.color = 'var(--orange)';
                btnEl.style.borderColor = 'var(--orange)';
                btnEl.style.background = 'var(--orange-dim)';
            }

            const msg = result.simulated
                ? `⊘ Bloqueo simulado — ${email}`
                : `✓ ${email} añadido a lista de bloqueados`;
            AlertsModule?.showToast(msg, 'ok', 3000);

        } catch (err) {
            _setBtnSpinner(btnEl, false);
            _setRowPending(row, false);
            _flashRow(row, 'error');
            AlertsModule?.showToast('❌ No se pudo bloquear: ' + err.message, 'error', 4000);
            console.error('[ActionsModule.block]', err);
        }
    }

    /* ══════════════════════════════════════════════════
       MODAL DE CONFIRMACIÓN
    ══════════════════════════════════════════════════ */
    function _openConfirmModal({ icon, title, body, emailLine, actionLabel, actionClass, onConfirm }) {
        let overlay = document.getElementById('action-confirm-overlay');
        if (!overlay) {
            overlay = _buildConfirmModal();
            document.body.appendChild(overlay);
        }

        // Populate
        overlay.querySelector('.action-confirm-icon').textContent = icon;
        overlay.querySelector('.action-confirm-title').textContent = title;
        overlay.querySelector('.action-confirm-body-text').textContent = body;
        overlay.querySelector('.action-confirm-email').textContent = emailLine;

        const okBtn = overlay.querySelector('.btn-confirm-action');
        okBtn.textContent = actionLabel;
        okBtn.className = 'btn-confirm-action ' + actionClass;

        // Replace onclick cleanly
        const newOkBtn = okBtn.cloneNode(true);
        newOkBtn.addEventListener('click', () => {
            _closeConfirmModal();
            onConfirm();
        });
        okBtn.replaceWith(newOkBtn);

        overlay.classList.add('open');
    }

    function _buildConfirmModal() {
        const o = document.createElement('div');
        o.id = 'action-confirm-overlay';
        o.className = 'action-confirm-overlay';
        o.innerHTML = `
      <div class="action-confirm-box" role="dialog" aria-modal="true">
        <div class="action-confirm-header">
          <span class="action-confirm-icon">⚠</span>
          <span class="action-confirm-title">Confirmar acción</span>
        </div>
        <div class="action-confirm-body">
          <p class="action-confirm-body-text"></p>
          <div class="action-confirm-email"></div>
        </div>
        <div class="action-confirm-footer">
          <button class="btn-confirm-cancel" id="action-cancel-btn">Cancelar</button>
          <button class="btn-confirm-action danger">Confirmar</button>
        </div>
      </div>`;

        o.addEventListener('click', e => { if (e.target === o) _closeConfirmModal(); });
        o.querySelector('#action-cancel-btn').addEventListener('click', _closeConfirmModal);
        document.addEventListener('keydown', e => { if (e.key === 'Escape') _closeConfirmModal(); });
        return o;
    }

    function _closeConfirmModal() {
        document.getElementById('action-confirm-overlay')?.classList.remove('open');
    }

    /* ══════════════════════════════════════════════════
       API pública
    ══════════════════════════════════════════════════ */
    return {
        resend,
        confirmDelete,
        confirmBlock,
        /* Expuesto para testing desde consola */
        _call,
    };

})();
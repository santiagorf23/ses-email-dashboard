/**
 * MailPulse — SES Dashboard
 * js/scheduler.js  v1
 *
 * Auto-alert checker: polls /api/alerts/check every 5 minutes.
 * Runs silently in background when user is logged in.
 */
const SchedulerModule = (() => {

    const CHECK_INTERVAL = 5 * 60 * 1000; // 5 minutes
    let _timer = null;
    let _running = false;

    async function checkNow() {
        if (_running) return;
        if (typeof ApiModule === 'undefined' || !ApiModule.getToken()) return;
        _running = true;
        try {
            const res = await ApiModule.post('/alerts/check');
            if (res && res.alerts_created > 0 && typeof AlertsModule !== 'undefined') {
                AlertsModule.showToast(`${res.alerts_created} nueva(s) alerta(s)`, 'warn');
            }
        } catch (e) {
            logger.warn('Alert check failed:', e.message);
        } finally {
            _running = false;
        }
    }

    function start() {
        if (_timer) return;
        checkNow(); // immediate first check
        _timer = setInterval(checkNow, CHECK_INTERVAL);
    }

    function stop() {
        if (_timer) { clearInterval(_timer); _timer = null; }
    }

    return { start, stop, checkNow };
})();

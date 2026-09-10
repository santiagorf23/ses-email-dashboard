/**
 * MailPulse — SES Dashboard
 * js/api.js  v1
 *
 * Shared API helper module.
 * Centralizes auth token, headers, and fetch calls.
 */
const ApiModule = (() => {

    function getToken() {
        return localStorage.getItem(CONFIG.TOKEN_KEY) || '';
    }

    function getHeaders(includeContentType = true) {
        const h = {};
        if (includeContentType) h['Content-Type'] = 'application/json';
        const t = getToken();
        if (t) h['Authorization'] = 'Bearer ' + t;
        return h;
    }

    async function request(method, path, body) {
        const opts = { method, headers: getHeaders() };
        if (body) opts.body = JSON.stringify(body);
        const res = await fetch(CONFIG.API_BASE_URL + path, opts);
        if (!res.ok) {
            let msg = `HTTP ${res.status}`;
            try { const j = await res.json(); msg = j.detail || j.message || msg; } catch { /* ok */ }
            throw new Error(msg);
        }
        try { return await res.json(); } catch { return { ok: true }; }
    }

    function get(path) { return request('GET', path); }
    function post(path, body) { return request('POST', path, body); }
    function put(path, body) { return request('PUT', path, body); }
    function del(path) { return request('DELETE', path); }

    return { getToken, getHeaders, request, get, post, put, del };

})();

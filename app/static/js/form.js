/**
 * NIELIT Smart Entry — Shared Form Utilities
 * Provides reusable helpers for all registration/visitor forms.
 */

/**
 * Show field-level validation errors returned from the API.
 * @param {Object} errors - Map of field name -> error message
 */
function showFieldErrors(errors) {
    // Clear previous errors
    document.querySelectorAll('.field-error').forEach(el => {
        el.classList.add('hidden');
        el.textContent = '';
    });
    document.querySelectorAll('.field').forEach(el => {
        el.classList.remove('border-red-400');
    });

    for (const [field, msg] of Object.entries(errors)) {
        const input = document.getElementById(field);
        if (input) {
            input.classList.add('border-red-400');
            // Look for sibling error element
            const errEl = input.closest('div')?.querySelector('.field-error');
            if (errEl) {
                errEl.textContent = msg;
                errEl.classList.remove('hidden');
            }
        }
    }
}

/**
 * Set button into loading or normal state.
 * @param {HTMLButtonElement} btn
 * @param {boolean} loading
 * @param {string} normalHTML - HTML to restore when not loading
 */
function setButtonLoading(btn, loading, normalHTML) {
    btn.disabled = loading;
    btn.innerHTML = loading
        ? '<i class="fa-solid fa-spinner fa-spin mr-2"></i>Processing...'
        : normalHTML;
}

/**
 * Format an ISO datetime string into local time + date strings.
 * @param {string} isoString
 * @returns {{ time: string, date: string }}
 */
function formatDateTime(isoString) {
    const d = new Date(isoString);
    return {
        time: d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true }),
        date: d.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' }),
    };
}

/**
 * Escape HTML special characters to prevent XSS in dynamically inserted text.
 * @param {string} str
 * @returns {string}
 */
function escapeHTML(str) {
    return String(str).replace(/[&<>"']/g, c => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
}

/**
 * Extract UUID from a raw QR scan payload (plain UUID or URL containing UUID).
 * @param {string} raw
 * @returns {string}
 */
function extractUUID(raw) {
    const s = (raw || '').trim();
    const match = s.match(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i);
    return match ? match[0].toLowerCase() : s;
}

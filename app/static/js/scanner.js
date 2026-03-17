/**
 * NIELIT Smart Entry — QR Scanner Utility Functions
 *
 * Shared helpers used by scanner.html.
 * Core scanning logic lives inline in scanner.html for simplicity,
 * but these utilities are available globally once this file is loaded.
 */

/**
 * Extract a UUID from a raw QR scan payload.
 * Handles plain UUIDs, URLs containing a UUID, or padded whitespace.
 *
 * @param {string} raw - Raw text decoded from the QR code.
 * @returns {string} - Lowercase UUID string, or the raw value if no UUID found.
 */
function extractUUID(raw) {
    const s = (raw || '').trim();
    const match = s.match(
        /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i
    );
    return match ? match[0].toLowerCase() : s;
}

/**
 * Validate that a string is a well-formed UUID v4.
 *
 * @param {string} uuid
 * @returns {boolean}
 */
function isValidUUID(uuid) {
    return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(uuid);
}

/**
 * Format an ISO 8601 datetime string into human-readable time and date parts.
 *
 * @param {string} isoString
 * @returns {{ time: string, date: string }}
 */
function formatDateTime(isoString) {
    const d = new Date(isoString);
    return {
        time: d.toLocaleTimeString('en-US', {
            hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true,
        }),
        date: d.toLocaleDateString('en-US', {
            weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
        }),
    };
}

/**
 * Escape HTML special characters to prevent XSS when inserting dynamic text.
 *
 * @param {*} value
 * @returns {string}
 */
function escapeHTML(value) {
    return String(value).replace(/[&<>"']/g, c => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }[c]));
}

/**
 * Zero-Knowledge Encryption Module (MEGA.nz-style)
 *
 * - PBKDF2 (100,000 iterations, SHA-256) for key derivation
 * - AES-256-GCM for encryption/decryption
 * - All crypto happens in browser via Web Crypto API
 * - Server NEVER sees plaintext keys or encryption key
 */

const CRYPTO_PBKDF2_ITERATIONS = 100000;
const CRYPTO_KEY_SESSION_KEY = "tr_ek";

/**
 * Derive an AES-256 encryption key from password + email.
 * Salt = "tokenrouter:zk:" + email (deterministic per user).
 */
async function deriveEncryptionKey(password, email) {
    const enc = new TextEncoder();
    const salt = enc.encode("tokenrouter:zk:" + email.toLowerCase().trim());
    const keyMaterial = await crypto.subtle.importKey(
        "raw", enc.encode(password), "PBKDF2", false, ["deriveKey"]
    );
    return crypto.subtle.deriveKey(
        { name: "PBKDF2", salt, iterations: CRYPTO_PBKDF2_ITERATIONS, hash: "SHA-256" },
        keyMaterial,
        { name: "AES-GCM", length: 256 },
        true,  // extractable for sessionStorage serialization
        ["encrypt", "decrypt"]
    );
}

/**
 * Encrypt plaintext with AES-256-GCM.
 * Returns base64 string: [12-byte IV] + [ciphertext + 16-byte tag]
 */
async function encryptString(plaintext, cryptoKey) {
    const enc = new TextEncoder();
    const iv = crypto.getRandomValues(new Uint8Array(12));
    const ciphertext = await crypto.subtle.encrypt(
        { name: "AES-GCM", iv },
        cryptoKey,
        enc.encode(plaintext)
    );
    // Concat IV + ciphertext
    const result = new Uint8Array(iv.length + ciphertext.byteLength);
    result.set(iv, 0);
    result.set(new Uint8Array(ciphertext), iv.length);
    return btoa(String.fromCharCode(...result));
}

/**
 * Decrypt base64 AES-256-GCM ciphertext.
 * Input format: base64([12-byte IV] + [ciphertext + tag])
 */
async function decryptString(base64Data, cryptoKey) {
    const raw = Uint8Array.from(atob(base64Data), c => c.charCodeAt(0));
    const iv = raw.slice(0, 12);
    const ciphertext = raw.slice(12);
    const decrypted = await crypto.subtle.decrypt(
        { name: "AES-GCM", iv },
        cryptoKey,
        ciphertext
    );
    return new TextDecoder().decode(decrypted);
}

/**
 * Store derived key in sessionStorage (tab-scoped, cleared on close).
 */
async function storeEncryptionKey(cryptoKey) {
    const exported = await crypto.subtle.exportKey("jwk", cryptoKey);
    sessionStorage.setItem(CRYPTO_KEY_SESSION_KEY, JSON.stringify(exported));
}

/**
 * Load derived key from sessionStorage.
 * Returns CryptoKey or null.
 */
async function loadEncryptionKey() {
    const raw = sessionStorage.getItem(CRYPTO_KEY_SESSION_KEY);
    if (!raw) return null;
    try {
        const jwk = JSON.parse(raw);
        return crypto.subtle.importKey(
            "jwk", jwk, { name: "AES-GCM" }, true, ["encrypt", "decrypt"]
        );
    } catch {
        return null;
    }
}

/**
 * Check if encryption key is available.
 */
function hasEncryptionKey() {
    return sessionStorage.getItem(CRYPTO_KEY_SESSION_KEY) !== null;
}

/**
 * Clear encryption key (on logout).
 */
function clearEncryptionKey() {
    sessionStorage.removeItem(CRYPTO_KEY_SESSION_KEY);
}

/**
 * Mask a decrypted key for display (first 8 + last 4 chars).
 */
function maskKey(key) {
    if (!key || key.length <= 12) return key ? key.slice(0, 4) + "..." + key.slice(-2) : "";
    return key.slice(0, 8) + "..." + key.slice(-4);
}

/**
 * Secure credential storage for Studio
 * 
 * Uses Web Crypto API to encrypt credentials before storing in localStorage.
 * Encryption key is derived from a device-specific identifier.
 * 
 * Security model:
 * - Credentials encrypted with AES-GCM
 * - Key derived from browser fingerprint + random salt
 * - Salt stored separately to prevent rainbow table attacks
 * - Cleared on explicit logout
 */

const STORAGE_KEY_PREFIX = 'aico_studio_secure_';
const CREDENTIALS_KEY = `${STORAGE_KEY_PREFIX}credentials`;
const SALT_KEY = `${STORAGE_KEY_PREFIX}salt`;

interface StoredCredentials {
  userUuid: string;
  pin: string;
}

/**
 * Generate a device-specific fingerprint for key derivation
 */
async function getDeviceFingerprint(): Promise<string> {
  // Combine multiple browser/device properties for fingerprinting
  const components = [
    navigator.userAgent,
    navigator.language,
    new Date().getTimezoneOffset().toString(),
    window.screen.colorDepth.toString(),
    window.screen.width.toString() + 'x' + window.screen.height.toString(),
  ];
  
  // Hash the fingerprint components
  const encoder = new TextEncoder();
  const data = encoder.encode(components.join('|'));
  const hashBuffer = await crypto.subtle.digest('SHA-256', data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

/**
 * Get or generate a random salt for key derivation
 */
async function getSalt(): Promise<Uint8Array> {
  try {
    const stored = localStorage.getItem(SALT_KEY);
    if (stored) {
      return Uint8Array.from(atob(stored), c => c.charCodeAt(0));
    }
  } catch {
    // Ignore errors, generate new salt
  }
  
  // Generate new salt
  const salt = crypto.getRandomValues(new Uint8Array(16));
  try {
    localStorage.setItem(SALT_KEY, btoa(String.fromCharCode.apply(null, Array.from(salt))));
  } catch {
    // Ignore storage errors
  }
  return salt;
}

/**
 * Derive encryption key from device fingerprint and salt
 */
async function deriveKey(salt: Uint8Array): Promise<CryptoKey> {
  const fingerprint = await getDeviceFingerprint();
  const encoder = new TextEncoder();
  const keyMaterial = await crypto.subtle.importKey(
    'raw',
    encoder.encode(fingerprint),
    'PBKDF2',
    false,
    ['deriveBits', 'deriveKey']
  );
  
  // @ts-ignore - TypeScript strict mode issue with Uint8Array/ArrayBuffer compatibility
  return crypto.subtle.deriveKey(
    {
      name: 'PBKDF2',
      salt: salt,
      iterations: 100000,
      hash: 'SHA-256',
    },
    keyMaterial,
    { name: 'AES-GCM', length: 256 },
    false,
    ['encrypt', 'decrypt']
  );
}

/**
 * Encrypt and store credentials
 * Overwrites any existing credentials (updates on PIN/password changes)
 */
export async function storeCredentials(userUuid: string, pin: string): Promise<void> {
  try {
    const salt = await getSalt();
    const key = await deriveKey(salt);
    
    const credentials: StoredCredentials = { userUuid, pin };
    const encoder = new TextEncoder();
    const data = encoder.encode(JSON.stringify(credentials));
    
    // Generate random IV
    const iv = crypto.getRandomValues(new Uint8Array(12));
    
    // Encrypt
    const encrypted = await crypto.subtle.encrypt(
      { name: 'AES-GCM', iv: iv },
      key,
      data
    );
    
    // Store IV + encrypted data (overwrites existing)
    const combined = new Uint8Array(iv.length + encrypted.byteLength);
    combined.set(iv, 0);
    combined.set(new Uint8Array(encrypted), iv.length);
    
    localStorage.setItem(CREDENTIALS_KEY, btoa(String.fromCharCode.apply(null, Array.from(combined))));
    console.log('[CredentialStorage] Credentials updated successfully');
  } catch (error) {
    console.error('[CredentialStorage] Failed to store credentials:', error);
    throw error;
  }
}

/**
 * Retrieve and decrypt stored credentials
 */
export async function getStoredCredentials(): Promise<StoredCredentials | null> {
  try {
    const stored = localStorage.getItem(CREDENTIALS_KEY);
    if (!stored) {
      return null;
    }
    
    const salt = await getSalt();
    const key = await deriveKey(salt);
    
    // Decode stored data
    const combined = Uint8Array.from(atob(stored), c => c.charCodeAt(0));
    
    // Extract IV and encrypted data
    const iv = combined.slice(0, 12);
    const encrypted = combined.slice(12);
    
    // Decrypt
    const decrypted = await crypto.subtle.decrypt(
      { name: 'AES-GCM', iv: iv },
      key,
      encrypted
    );
    
    const decoder = new TextDecoder();
    const json = decoder.decode(decrypted);
    return JSON.parse(json) as StoredCredentials;
  } catch (error) {
    console.error('[CredentialStorage] Failed to retrieve credentials:', error);
    return null;
  }
}

/**
 * Clear stored credentials (on logout)
 */
export function clearStoredCredentials(): void {
  try {
    localStorage.removeItem(CREDENTIALS_KEY);
    localStorage.removeItem(SALT_KEY);
  } catch (error) {
    console.error('[CredentialStorage] Failed to clear credentials:', error);
  }
}

/**
 * Check if credentials are stored
 */
export function hasStoredCredentials(): boolean {
  try {
    return localStorage.getItem(CREDENTIALS_KEY) !== null;
  } catch {
    return false;
  }
}

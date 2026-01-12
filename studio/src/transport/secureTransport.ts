import nacl from 'tweetnacl';
import { API_BASE_URL } from '../api/config';

const encoder = new TextEncoder();
const decoder = new TextDecoder();

let sharedKey: Uint8Array | null = null;
let clientId: string | null = null;
let sessionEstablishedAt = 0;
const SESSION_TIMEOUT_MS = 60 * 60 * 1000; // 1 hour

// Use the runtime-return types from tweetnacl without referencing
// non-existent TS type exports.
let identityKeyPair: ReturnType<typeof nacl.sign.keyPair> | null = null;
let sessionKeyPair: ReturnType<typeof nacl.box.keyPair> | null = null;

function toBase64(bytes: Uint8Array): string {
  let binary = '';
  for (let i = 0; i < bytes.length; i += 1) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

function fromBase64(b64: string): Uint8Array {
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

function computeClientId(publicKey: Uint8Array): string {
  // Same scheme as TransportIdentityManager: hex(identity_key)[:16]
  const hex = Array.from(publicKey)
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
  return hex.slice(0, 16);
}

function hasValidSession(): boolean {
  if (!sharedKey) return false;
  if (!sessionEstablishedAt) return false;
  return Date.now() - sessionEstablishedAt < SESSION_TIMEOUT_MS;
}

async function performHandshake(): Promise<void> {
  identityKeyPair = nacl.sign.keyPair();
  sessionKeyPair = nacl.box.keyPair();

  const challenge = nacl.randomBytes(32);
  const timestamp = Date.now() / 1000;

  const handshakeRequest = {
    component: 'studio',
    public_key: toBase64(sessionKeyPair.publicKey),
    identity_key: toBase64(identityKeyPair.publicKey),
    timestamp,
    challenge: toBase64(challenge),
    signature: toBase64(nacl.sign.detached(challenge, identityKeyPair.secretKey)),
  };

  const response = await fetch(`${API_BASE_URL}/handshake`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ handshake_request: handshakeRequest }),
  });

  if (!response.ok) {
    const text = await response.text().catch(() => '');
    throw new Error(
      `Handshake failed with HTTP ${response.status} ${response.statusText}` + (text ? `: ${text}` : ''),
    );
  }

  const data = await response.json();
  if (!data || data.status !== 'session_established' || !data.handshake_response) {
    throw new Error('Invalid handshake response format');
  }

  const handshakeResponse = data.handshake_response as {
    public_key: string;
    identity_key?: string;
    timestamp: number;
    challenge: string;
    signature: string;
  };

  const serverPublicKey = fromBase64(handshakeResponse.public_key);

  if (!sessionKeyPair) {
    throw new Error('Missing local session keypair');
  }

  // Derive shared session key using X25519 + XSalsa20-Poly1305 (libsodium Box compatible)
  sharedKey = nacl.box.before(serverPublicKey, sessionKeyPair.secretKey);
  sessionEstablishedAt = Date.now();

  clientId = computeClientId(identityKeyPair.publicKey);
}

export async function ensureSecureSession(): Promise<{ clientId: string | null }> {
  if (!hasValidSession()) {
    await performHandshake();
  }
  return { clientId };
}

export function wrapEncryptedRequestBody(body: unknown): { encrypted: true; payload: string } {
  if (!sharedKey) {
    throw new Error('No active transport session');
  }
  const json = JSON.stringify(body ?? {});
  const message = encoder.encode(json);
  const nonce = nacl.randomBytes(nacl.box.nonceLength);
  const box = nacl.box.after(message, nonce, sharedKey);
  const combined = new Uint8Array(nonce.length + box.length);
  combined.set(nonce, 0);
  combined.set(box, nonce.length);
  const payload = toBase64(combined);
  return { encrypted: true, payload };
}

export function unwrapEncryptedResponse<T = unknown>(data: any): T {
  if (!data || typeof data !== 'object') {
    return data as T;
  }
  if (!data.encrypted || typeof data.payload !== 'string') {
    return data as T;
  }
  if (!sharedKey) {
    throw new Error('No active transport session for decrypting response');
  }
  const combined = fromBase64(data.payload);
  const nonce = combined.slice(0, nacl.box.nonceLength);
  const box = combined.slice(nonce.length);
  const plain = nacl.box.open.after(box, nonce, sharedKey);
  if (!plain) {
    throw new Error('Failed to decrypt response payload');
  }
  const json = decoder.decode(plain);
  return JSON.parse(json) as T;
}

export function getClientId(): string | null {
  return clientId;
}

export function forceNewHandshake(): void {
  // Invalidate current session to force a new handshake
  sharedKey = null;
  clientId = null;
  sessionEstablishedAt = 0;
  identityKeyPair = null;
  sessionKeyPair = null;
}

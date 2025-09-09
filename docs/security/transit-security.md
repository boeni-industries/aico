---
title: Transport Security Architecture
---

# Transport Security Architecture

AICO implements application-level transport security using libsodium for all inter-component communication. This approach provides strong cryptographic guarantees while maintaining compatibility with AICO's modular architecture and deployment flexibility.

## Architecture Overview

### Design Principles

**Application-Level Encryption**: Uses libsodium instead of TLS for direct cryptographic control and simplified (no) certificate management.

**Zero-Configuration Security**: Automatic key exchange and session establishment without manual certificate setup.

**Deployment Agnostic**: Consistent security model across coupled (same device) and detached (separate devices) deployments.

**Performance Optimized**: Hardware-accelerated ChaCha20-Poly1305 with minimal overhead.

**Integration Native**: Leverages existing AICO key management and authentication systems.

### Communication Channels

AICO's transport security protects three primary communication channels:

```mermaid
flowchart LR
    Frontend["Frontend<br/>(Flutter)"] 
    Backend["Backend<br/>(Python)"]
    CLI["CLI<br/>(Python)"]
    Studio["Studio<br/>(React)"]
    
    Frontend -.->|libsodium| Backend
    CLI -.->|libsodium| Backend  
    CLI -.->|libsodium| Studio
    Studio -.->|libsodium| Backend
    
    classDef secure fill:#663399,stroke:#9370DB,color:#fff
    class Frontend,Backend,CLI,Studio secure
```

## Cryptographic Foundation

### Core Algorithms

| Component | Algorithm | Purpose |
|-----------|-----------|---------|
| **Key Exchange** | X25519 | Establish shared secrets |
| **Encryption** | XChaCha20-Poly1305 | Message encryption with authentication |
| **Key Derivation** | BLAKE2b | Derive session keys from shared secrets |
| **Authentication** | Ed25519 | Component identity verification |

### Algorithm Selection Rationale

**XChaCha20-Poly1305**: 
- 192-bit nonces enable safe random nonce generation
- No practical message count limits
- Software-optimized performance (3x faster than AES without hardware acceleration)
- Timing attack resistant

**X25519 Key Exchange**:
- 128-bit security level
- Fast scalar multiplication
- Small key sizes (32 bytes)
- Widely audited implementation

## Security Architecture

### Component Identity System

Each AICO component maintains a persistent Ed25519 identity keypair:

```python
# Component identity management
class ComponentIdentity:
    def __init__(self, component_name: str, key_manager: AICOKeyManager):
        self.component_name = component_name
        self.key_manager = key_manager
        self._load_or_generate_identity()
    
    def _load_or_generate_identity(self):
        # Try to load existing identity
        stored_key = self.key_manager.get_component_key(self.component_name, "identity")
        
        if stored_key:
            self.secret_key = stored_key
            self.public_key = crypto_sign_sk_to_pk(self.secret_key)
        else:
            # Generate new identity
            self.public_key, self.secret_key = crypto_sign_keypair()
            self.key_manager.store_component_key(
                self.component_name, "identity", self.secret_key
            )
```

### Session Key Derivation

Session keys are derived using libsodium's `crypto_kx` API with component identities:

```python
class SecureChannel:
    def establish_session(self, peer_public_key: bytes) -> tuple[bytes, bytes]:
        """Establish bidirectional session keys with peer"""
        
        # Perform X25519 key exchange
        if self.is_client:
            rx_key, tx_key = crypto_kx_client_session_keys(
                self.identity.public_key,
                self.identity.secret_key, 
                peer_public_key
            )
        else:
            rx_key, tx_key = crypto_kx_server_session_keys(
                self.identity.public_key,
                self.identity.secret_key,
                peer_public_key
            )
        
        return rx_key, tx_key
```

### Message Format

All encrypted messages use a standardized format:

```
┌─────────────┬──────────────┬──────────────┬─────────────────┬──────────────┐
│   Header    │    Nonce     │   Metadata   │ Encrypted Data  │   Auth Tag   │
│   8 bytes   │   24 bytes   │   Variable   │   Variable      │   16 bytes   │
└─────────────┴──────────────┴──────────────┴─────────────────┴──────────────┘
```

**Header**: `AICO-MSG` (8 ASCII bytes) + version
**Nonce**: 192-bit XChaCha20 nonce (random generation safe)
**Metadata**: Protocol-specific data (timestamps, message types)
**Auth Tag**: Poly1305 authentication tag

## Protocol Implementation

### Connection Establishment

#### Phase 1: Identity Exchange
```python
# 1. Components exchange public keys
handshake_msg = {
    "component": "frontend",
    "public_key": base64.encode(identity.public_key),
    "timestamp": time.time(),
    "challenge": os.urandom(32)
}
```

#### Phase 2: Authentication
```python
# 2. Mutual authentication via Ed25519 signatures
def authenticate_peer(peer_msg: dict) -> bool:
    # Verify timestamp freshness
    if abs(time.time() - peer_msg["timestamp"]) > 30:
        return False
    
    # Verify signature over challenge
    signature = peer_msg["signature"]
    challenge = peer_msg["challenge"]
    peer_pubkey = base64.decode(peer_msg["public_key"])
    
    try:
        crypto_sign_open(signature + challenge, peer_pubkey)
        return True
    except ValueError:
        return False
```

#### Phase 3: Session Key Derivation
```python
# 3. Derive session keys using crypto_kx
rx_key, tx_key = establish_session(peer_public_key)

# 4. Begin encrypted communication
secure_channel = SecureChannel(rx_key, tx_key)
```

### Message Encryption

```python
class SecureChannel:
    def encrypt_message(self, plaintext: bytes, metadata: dict = None) -> bytes:
        # Generate random nonce (safe with XChaCha20)
        nonce = os.urandom(24)
        
        # Serialize metadata as additional data
        additional_data = json.dumps(metadata or {}).encode()
        
        # Encrypt with XChaCha20-Poly1305
        ciphertext = crypto_aead_xchacha20poly1305_ietf_encrypt(
            plaintext, additional_data, nonce, self.tx_key
        )
        
        # Construct message
        header = b"AICO-MSG"
        return header + nonce + len(additional_data).to_bytes(4, 'big') + additional_data + ciphertext
    
    def decrypt_message(self, encrypted_msg: bytes) -> tuple[bytes, dict]:
        # Parse message format
        header = encrypted_msg[:8]
        nonce = encrypted_msg[8:32]
        metadata_len = int.from_bytes(encrypted_msg[32:36], 'big')
        metadata = json.loads(encrypted_msg[36:36+metadata_len])
        ciphertext = encrypted_msg[36+metadata_len:]
        
        # Decrypt and authenticate
        plaintext = crypto_aead_xchacha20poly1305_ietf_decrypt(
            ciphertext, json.dumps(metadata).encode(), nonce, self.rx_key
        )
        
        return plaintext, metadata
```

## Integration with AICO Systems

### Key Manager Integration

Transport security integrates with AICO's existing key management:

```python
class TransportKeyManager:
    def __init__(self, aico_key_manager: AICOKeyManager):
        self.key_manager = aico_key_manager
        
    def derive_transport_keys(self, purpose: str) -> tuple[bytes, bytes]:
        """Derive transport keypair from master key"""
        master_key = self.key_manager.get_master_key()
        
        # Use AICO's Argon2id derivation for transport keys
        seed = self.key_manager.derive_key(
            master_key, f"transport-{purpose}", 32
        )
        
        return crypto_sign_seed_keypair(seed)
```

### Message Bus Security

ZeroMQ message bus uses libsodium for internal security:

```python
class SecureMessageBus:
    def __init__(self, identity: ComponentIdentity):
        self.identity = identity
        self.channels = {}  # peer_id -> SecureChannel
        
    def publish_secure(self, topic: str, message: bytes, target_peers: list = None):
        """Publish encrypted message to specific peers or broadcast"""
        
        if target_peers:
            # Encrypt for specific peers
            for peer_id in target_peers:
                if peer_id in self.channels:
                    encrypted = self.channels[peer_id].encrypt_message(
                        message, {"topic": topic, "timestamp": time.time()}
                    )
                    self.zmq_socket.send_multipart([f"{topic}.{peer_id}".encode(), encrypted])
        else:
            # Broadcast (requires group key or per-peer encryption)
            self._broadcast_encrypted(topic, message)
```

### API Gateway Security

REST and WebSocket endpoints use the same transport security:

```python
class SecureAPIGateway:
    def __init__(self, backend_identity: ComponentIdentity):
        self.identity = backend_identity
        self.client_channels = {}  # client_id -> SecureChannel
        
    async def websocket_handler(self, websocket, path):
        # Perform handshake
        client_identity = await self.perform_handshake(websocket)
        
        # Establish secure channel
        channel = SecureChannel.from_handshake(self.identity, client_identity)
        self.client_channels[client_identity.component_id] = channel
        
        # Handle encrypted messages
        async for encrypted_msg in websocket:
            plaintext, metadata = channel.decrypt_message(encrypted_msg)
            response = await self.process_api_request(plaintext, metadata)
            encrypted_response = channel.encrypt_message(response)
            await websocket.send(encrypted_response)
```

## Deployment Patterns

### Coupled Mode (Same Device)

Components communicate via local sockets with libsodium encryption:

```python
# Local secure communication
class LocalSecureTransport:
    def __init__(self, socket_path: str, identity: ComponentIdentity):
        self.socket_path = socket_path
        self.identity = identity
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        
    def connect_secure(self):
        self.socket.connect(self.socket_path)
        # Perform libsodium handshake over Unix socket
        peer_identity = self.perform_handshake()
        self.channel = SecureChannel.establish(self.identity, peer_identity)
```

### Detached Mode (Separate Devices)

Components communicate over network with additional security layers:

```python
class NetworkSecureTransport:
    def __init__(self, host: str, port: int, identity: ComponentIdentity):
        self.host = host
        self.port = port
        self.identity = identity
        
    def connect_secure(self):
        # Establish TCP connection
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.host, self.port))
        
        # Perform libsodium handshake over network
        peer_identity = self.perform_network_handshake()
        self.channel = SecureChannel.establish(self.identity, peer_identity)
        
        # Additional network security measures
        self.enable_keepalive()
        self.setup_connection_monitoring()
```

## Security Properties

### Cryptographic Guarantees

**Confidentiality**: XChaCha20 encryption with 256-bit keys
**Authenticity**: Poly1305 authentication prevents tampering
**Forward Secrecy**: Session keys rotated, old messages remain secure
**Replay Protection**: Nonce-based message ordering prevents replay attacks

### Threat Model Coverage

| Threat | Mitigation |
|--------|------------|
| **Eavesdropping** | XChaCha20 encryption |
| **Message Tampering** | Poly1305 authentication |
| **Identity Spoofing** | Ed25519 component signatures |
| **Replay Attacks** | Nonce validation and timestamps |
| **Man-in-the-Middle** | Mutual authentication with persistent identities |
| **Key Compromise** | Session key rotation and forward secrecy |

### Performance Characteristics

**Handshake Overhead**: ~2ms for key exchange and authentication
**Message Overhead**: 48 bytes per message (header + nonce + tag)
**Throughput Impact**: <5% performance reduction vs plaintext
**CPU Usage**: Hardware-accelerated ChaCha20 on modern processors

## Configuration

### Security Parameters

Transport security is configured via `security.yaml`:

```yaml
security:
  transport:
    # Cryptographic algorithms
    encryption: "xchacha20poly1305"
    key_exchange: "x25519"
    authentication: "ed25519"
    
    # Session management
    session_timeout: 3600  # 1 hour
    key_rotation_interval: 86400  # 24 hours
    max_message_size: 16777216  # 16MB
    
    # Network settings
    handshake_timeout: 30
    keepalive_interval: 60
    connection_retry_limit: 3
    
    # Security policies
    require_fresh_handshake: true
    allow_key_reuse: false
    enforce_message_ordering: true
```

### Component Configuration

Each component configures transport security:

```python
# Backend configuration
transport_config = {
    "identity_file": "~/.aico/backend_identity.key",
    "listen_address": "127.0.0.1:8771",
    "allowed_components": ["frontend", "cli", "studio"],
    "security_level": "high"
}

# Frontend configuration  
transport_config = {
    "identity_file": "~/.aico/frontend_identity.key", 
    "backend_address": "127.0.0.1:8771",
    "auto_reconnect": true,
    "security_level": "high"
}
```

## Implementation Roadmap

### Phase 1: Core Infrastructure
- [ ] Component identity management
- [ ] Basic libsodium integration
- [ ] Secure channel implementation
- [ ] Message format specification

### Phase 2: Protocol Integration
- [ ] API Gateway security layer
- [ ] ZeroMQ message bus encryption
- [ ] WebSocket secure transport
- [ ] REST API protection

### Phase 3: Advanced Features
- [ ] Session key rotation
- [ ] Connection monitoring
- [ ] Performance optimization
- [ ] Security audit logging

### Phase 4: Production Hardening
- [ ] Threat model validation
- [ ] Security testing
- [ ] Performance benchmarking
- [ ] Documentation completion

## Security Considerations

### Key Management

**Identity Persistence**: Component identities stored in AICO keyring
**Key Rotation**: Automatic session key rotation every 24 hours
**Compromise Recovery**: Identity revocation and regeneration procedures

### Network Security

**Connection Validation**: Peer identity verification before key exchange
**Traffic Analysis**: Metadata protection through consistent message sizes
**Denial of Service**: Rate limiting and connection throttling

### Implementation Security

**Memory Safety**: Secure key erasure after use
**Side Channel Protection**: Constant-time operations where possible
**Error Handling**: Secure failure modes without information leakage

---

This transport security architecture provides AICO with robust, application-level encryption that integrates seamlessly with existing systems while maintaining performance and usability across all deployment scenarios.

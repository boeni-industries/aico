# AICO Authentication Architecture

AICO's authentication system provides secure, user-friendly access control across all system components with support for multiple authentication methods.

**Current Status**: ✅ Core JWT authentication operational, biometric and ambient authentication planned.

## Vision: Natural Family Recognition

AICO's long-term vision includes a **natural family recognition system** that identifies family members through voice, behavior, and conversation patterns. This would enable personalized relationships while maintaining AICO's core personality.

**Current Reality**: Traditional JWT-based authentication with planned enhancements.

## Current Implementation

### JWT Authentication ✅ Operational
- **Token-Based**: Secure JWT tokens for session management
- **Platform Keyring**: OS-native secure credential storage via AICOKeyManager
- **Session Management**: Automatic token renewal and timeout handling
- **Admin Access**: CLI and backend admin operations protected

### Security Features ✅ Implemented
- **Argon2id Hashing**: Secure password storage with configurable parameters
- **Breach Protection**: HaveIBeenPwned API integration
- **Account Lockout**: Progressive delays after failed attempts
- **Audit Logging**: All authentication attempts logged

## Recognition Architecture

### Family Recognition System
**Core Concept:**
- AICO maintains consistent personality across all family members
- Develops unique relationship dynamics with each person
- Recognizes individuals through natural interaction patterns
- Builds relationship memory and context over time

**Multi-Modal Recognition:**
- **Voice Biometrics**: Primary identifier - natural, passive, always-on
- **Behavioral Patterns**: Conversation style, topic preferences, interaction timing
- **Context Clues**: Device usage patterns, location, time of day
- **Gradual Learning**: Recognition confidence improves over time

### Confidence-Based Verification
**Recognition Threshold: 95%+**
- **High Confidence (95%+)**: Natural interaction proceeds immediately
- **Medium Confidence (80-94%)**: Gentle verification: "Is this Sarah?"
- **Low Confidence (<80%)**: Friendly identification: "Who am I speaking with?"
- **Verification Methods**: Simple PIN, biometric, or family member confirmation

**Protection Against Profile Pollution:**
- Siblings attempting to access each other's profiles
- Accidental misidentification scenarios
- Intentional impersonation attempts
- Maintaining individual privacy boundaries

## Recognition Flow

### Family Introduction Process
1. **Initial Setup**: 
   - Primary user introduces AICO to family
   - Voice pattern collection during natural conversation
   - Relationship context establishment ("This is my daughter Sarah")
   - Privacy preferences setup per family member

2. **Recognition Training**:
   - Gradual learning through daily interactions
   - Behavioral pattern recognition development
   - Conversation style and preference mapping
   - Confidence threshold calibration

3. **Daily Recognition**:
   - Passive voice identification during conversation
   - Contextual greeting based on recognized individual
   - Automatic relationship context switching
   - Privacy boundary enforcement

4. **Verification Handling**:
   - Gentle verification when confidence < 95%
   - Multiple verification options (PIN, biometric, family confirmation)
   - Graceful uncertainty handling
   - Learning from verification outcomes

## Security Features

### Core Security Mechanisms
- **No Passwords**: Device biometrics + platform security only
- **Automatic Key Rotation**: Background certificate renewal
- **Graceful Degradation**: Fallback to PIN if biometrics unavailable
- **Privacy-First**: No user accounts, no cloud authentication
- **Zero Trust**: Every request authenticated and authorized

### Biometric Authentication 
- **Platform Integration**: TouchID, FaceID, Windows Hello
- **Voice Recognition**: Speaker verification for hands-free access
- **Behavioral Patterns**: Typing and interaction analysis (future)
- **Privacy Protection**: Biometric templates never leave secure hardware
- **Selective Use**: Only for sensitive operations, not routine access

### Certificate Management
- **Device Certificates**: Unique per-device identity certificates
- **Automatic Renewal**: Background certificate rotation
- **Revocation Support**: Ability to revoke compromised device certificates
- **Cross-Platform**: Consistent certificate format across platforms

## Authentication Methods

### Password Authentication ✅ Implemented
- **Secure Hashing**: Argon2id with configurable parameters
- **Breach Protection**: HaveIBeenPwned API integration
- **Account Security**: Progressive lockout after failed attempts
- **Password Policy**: Configurable complexity requirements

### Multi-Factor Authentication 🚧 Planned
- **TOTP**: Time-based one-time passwords (Google Authenticator, Authy)
- **Hardware Keys**: FIDO2/WebAuthn security key support
- **Push Notifications**: Mobile app approval with context
- **Backup Methods**: SMS/Email with fraud detection

## Technical Implementation

### MVP Foundation: Smart PIN Authentication

**Architecture Overview:**
- **Device-Level Security**: Master password encrypts database (user-agnostic)
- **User-Level Identity**: Smart PIN system for individual family member identification
- **Progressive Enhancement**: Start with PINs, evolve to voice recognition

**Smart PIN System Design:**
```
Authentication Flow:
1. Device unlocks database with master password (keyring-stored)
2. User enters PIN for individual identification
3. System creates JWT session with family member context
4. Conversation proceeds with personalized relationship context
```

**Family-Aware PIN Logic:**
- **PIN Length = User Type**: No need to select user category first
- **4-digit PINs**: Parents/primary users (1234-9999)
- **3-digit PINs**: Children/secondary users (100-999)  
- **2-digit PINs**: Guests/temporary users (10-99)
- **Collision Detection**: System prevents duplicate PINs automatically
- **Quick Switching**: Enter different PIN to switch users mid-conversation

**User Experience Benefits:**
- Natural conversation flow: "Hey AICO" → "Hi! What's your PIN?" → "123" → "Hi Sarah!"
- Age-appropriate complexity: Even 5-year-olds can remember 3 digits
- Zero friction user switching during family conversations
- Emergency override: Master password can access any profile

**Security Features:**
- Database encryption provides device-level security
- PINs only work after database is unlocked
- Individual privacy maintained per PIN
- Brute force protection with lockout after failed attempts
- Audit logging of all authentication attempts

### Implementation Status

**✅ Currently Implemented:**
- JWT token creation and validation
- Platform keyring integration via AICOKeyManager
- Session management with timeout and renewal
- Encrypted database storage with master password
- Admin authentication for CLI and backend services

**🚧 Planned Implementation:**
- **Smart PIN System**: Family member identification via PIN length
- **Voice Recognition**: Multi-modal biometric authentication
- **Family Management**: User profiles with individual privacy boundaries
- **Confidence-Based Verification**: Risk-adaptive authentication levels

### Required Endpoints

**Recognition Endpoints:**
- `POST /api/v1/recognition/introduce` - Introduce new family member
- `GET /api/v1/recognition/identify` - Identify current speaker
- `POST /api/v1/recognition/verify` - Verify identity when confidence low
- `GET /api/v1/recognition/family` - List family members
- `DELETE /api/v1/recognition/family/{id}` - Remove family member

**Current Status:**
- ✅ JWT token creation and validation implemented
- ✅ Platform keyring integration (AICOKeyManager) working
- ✅ Session management infrastructure operational
- ✅ Encrypted database with master password system functional
- 🚧 Voice recognition system planned for future implementation
- 🚧 Family member management with PIN system in development

### Implementation Priorities

**Phase 1: Basic Recognition System**
1. Replace fake login with voice recognition foundation
2. Implement family member introduction workflow
3. Add basic voice pattern storage and matching
4. Create confidence scoring system

**Phase 2: Multi-Modal Recognition**
1. Voice biometric engine integration
2. Behavioral pattern analysis
3. Conversation style recognition
4. Context-aware identification

**Phase 3: Advanced Features**
1. Confidence-based verification system
2. Privacy boundary enforcement
3. Relationship context management
4. Family member management UI

## Security Considerations

### Threat Model
- **Voice Spoofing**: Mitigated by multi-modal recognition and confidence thresholds
- **Profile Pollution**: Mitigated by 95% confidence requirement and verification
- **Privacy Breach**: Mitigated by individual privacy boundaries and data isolation
- **Impersonation**: Mitigated by behavioral pattern analysis and verification fallbacks
- **Family Conflicts**: Mitigated by clear privacy boundaries and verification systems

### Compliance & Standards
- **Zero Trust Architecture**: All requests authenticated and authorized
- **OWASP Guidelines**: Following modern authentication best practices
- **Platform Security**: Leveraging OS-native security capabilities
- **Privacy Regulations**: Minimal data collection and local processing

## Integration with AICO Architecture

### Message Bus Security
- **Topic-Level Authorization**: Fine-grained access control per message topic
- **Authentication Context**: Family member UUID propagated through message metadata
- **Plugin Isolation**: Strict permission boundaries for plugin access

### Database Security
- **Encrypted Storage**: All data encrypted at rest with user-derived keys
- **Access Control**: Database access tied to authenticated sessions
- **Audit Logging**: All access attempts logged for security monitoring

### Frontend Integration
- **WebSocket Authentication**: Secure real-time communication
- **API Security**: All REST endpoints protected with JWT validation
- **UI Security Controls**: Permission dialogs and security status indicators

---

*This authentication architecture aligns with AICO's core principles of privacy-first, local-first, and zero-effort security while providing robust protection for a single-user AI companion system.*

---
title: AICO Namespace Strategy
---

# AICO Global Namespace Strategy

This document outlines the comprehensive namespace strategy for the entire AICO system, ensuring consistency across all languages, platforms, and components.

## Overview

All AICO components use the `aico.*` namespace hierarchy to provide:
- **Brand consistency**: Everything clearly belongs to AICO
- **Collision avoidance**: No conflicts with system or third-party packages
- **Professional appearance**: Shows mature, well-organized project
- **Scalability**: Easy to add new components without naming conflicts
- **Cross-platform clarity**: Same logical structure across all languages

## Top-Level Namespace Hierarchy

```
aico.                       # Root namespace
├── core.*                  # Core system components
├── security.*              # Security & encryption
├── data.*                  # Data layer & models
├── ai.*                    # AI/ML components
├── ui.*                    # UI/Frontend components
├── plugins.*               # Plugin system
├── federation.*            # Device federation
├── tools.*                 # Development tools
├── integrations.*          # Third-party integrations
└── experimental.*          # Experimental features
```

## Language-Specific Implementation

### Python (Backend, CLI, Tools)

**Package Structure**:
```python
# Shared libraries use aico.* namespace
from aico.security import AICOKeyManager
from aico.data.models import Conversation
from aico.ai.llm import LLMProvider
from aico.core.bus import MessageBus
from aico.core.config import Config
from aico.tools.cli import AICOCli
```

**Setup Configuration**:
```python
# setup.py for shared libraries
setup(
    name="aico-security",
    packages=["aico.security"],
    namespace_packages=["aico"]
)
```

### Dart/Flutter (Frontend)

**Package Structure**:
```dart
// Dart packages use aico_ prefix
import 'package:aico_ui/widgets.dart';
import 'package:aico_data/models.dart';
import 'package:aico_core/api_client.dart';
import 'package:aico_security/auth.dart';
```

**pubspec.yaml**:
```yaml
name: aico_ui
dependencies:
  aico_core: ^1.0.0
  aico_data: ^1.0.0
  aico_security: ^1.0.0
```

### JavaScript/TypeScript (Web UI, if needed)

**Package Structure**:
```typescript
// NPM packages use @aico/ scope
import { AicoApiClient } from '@aico/core';
import { ConversationModel } from '@aico/data';
import { SecurityManager } from '@aico/security';
```

**package.json**:
```json
{
  "name": "@aico/frontend",
  "dependencies": {
    "@aico/core": "^1.0.0",
    "@aico/data": "^1.0.0"
  }
}
```

## System-Level Namespacing

### Environment Variables
All AICO environment variables use the `AICO_` prefix:
```bash
AICO_CONFIG_PATH=/path/to/config
AICO_DATA_DIR=/path/to/data
AICO_LOG_LEVEL=info
AICO_BACKEND_PORT=8080
AICO_FRONTEND_PORT=3000
```

### File System Structure
```
/opt/aico/                  # System installation directory
~/.aico/                    # User data directory
/var/log/aico/              # System logs
/etc/aico/                  # System configuration
```

### Network & URLs
```
aico://                     # Custom protocol for device federation
api.aico.local              # Local API endpoint
*.aico.internal             # Internal service discovery
ws.aico.local               # WebSocket endpoint
```

## Data Layer Namespacing

### Database Tables
All database tables use the `aico_` prefix:
```sql
aico_conversations
aico_users
aico_plugins
aico_system_config
aico_audit_logs
aico_device_registry
```

### Message Bus Topics
Message bus topics follow the `aico.` hierarchy:
```
aico.system.startup
aico.system.shutdown
aico.ai.request
aico.ai.response
aico.ui.interaction
aico.security.auth
aico.plugins.loaded
aico.federation.sync
```

## Reserved Namespace Definitions

### Core System (`aico.core.*`)
- `aico.core.bus` - Message bus implementation
- `aico.core.config` - Configuration management
- `aico.core.logging` - Logging framework
- `aico.core.health` - Health monitoring
- `aico.core.api` - API gateway

### Security (`aico.security.*`)
- `aico.security.auth` - Authentication
- `aico.security.crypto` - Cryptographic operations
- `aico.security.keys` - Key management
- `aico.security.access` - Access control
- `aico.security.audit` - Security auditing

### Data Layer (`aico.data.*`)
- `aico.data.models` - Data models
- `aico.data.schemas` - Database schemas
- `aico.data.migrations` - Database migrations
- `aico.data.repositories` - Data access layer
- `aico.data.sync` - Data synchronization

### AI Components (`aico.ai.*`)
- `aico.ai.llm` - Large Language Model providers
- `aico.ai.embeddings` - Vector embeddings
- `aico.ai.memory` - AI memory systems
- `aico.ai.personality` - Personality engine
- `aico.ai.emotion` - Emotion processing

### User Interface (`aico.ui.*`)
- `aico.ui.widgets` - UI components
- `aico.ui.themes` - Theme system
- `aico.ui.navigation` - Navigation
- `aico.ui.state` - State management
- `aico.ui.animations` - Animations

### Plugin System (`aico.plugins.*`)
- `aico.plugins.manager` - Plugin management
- `aico.plugins.loader` - Plugin loading
- `aico.plugins.sandbox` - Plugin sandboxing
- `aico.plugins.api` - Plugin API
- `aico.plugins.registry` - Plugin registry

### Federation (`aico.federation.*`)
- `aico.federation.sync` - Device synchronization
- `aico.federation.discovery` - Device discovery
- `aico.federation.pairing` - Device pairing
- `aico.federation.conflict` - Conflict resolution
- `aico.federation.security` - Federation security

### Development Tools (`aico.tools.*`)
- `aico.tools.cli` - Command-line interface
- `aico.tools.dev` - Development utilities
- `aico.tools.test` - Testing utilities
- `aico.tools.deploy` - Deployment tools
- `aico.tools.debug` - Debugging tools

## Implementation Guidelines

### For Developers

1. **Always use the namespace**: Never create packages outside the `aico.*` hierarchy
2. **Follow the hierarchy**: Place components in the appropriate namespace category
3. **Be consistent**: Use the same naming patterns across languages
4. **Document new namespaces**: Update this document when adding new namespace areas

### For New Components

1. **Choose appropriate namespace**: Select the most fitting top-level category
2. **Check for conflicts**: Ensure the namespace doesn't already exist
3. **Follow naming conventions**: Use clear, descriptive names
4. **Update documentation**: Add new namespaces to this document

### For Cross-Language Development

1. **Maintain logical consistency**: Same concepts should have similar namespace paths
2. **Adapt to language conventions**: Use language-appropriate naming (snake_case vs camelCase)
3. **Document mappings**: Clearly document how namespaces map across languages

## Migration Strategy

### Phase 1: Python Implementation
- Implement namespace structure for all Python shared libraries
- Update existing code to use namespaced imports
- Establish namespace package structure

### Phase 2: Cross-Language Extension
- Extend namespace strategy to Dart/Flutter packages
- Implement JavaScript/TypeScript namespaces if needed
- Update build and deployment scripts

### Phase 3: System-Wide Consistency
- Apply namespace strategy to environment variables
- Update configuration files and system paths
- Implement namespace-aware service discovery

## Benefits

- **Professional Organization**: Clear, hierarchical structure shows mature project
- **Collision Prevention**: No conflicts with system or third-party packages
- **Scalability**: Easy to add new components without naming issues
- **Brand Consistency**: Everything clearly identified as part of AICO
- **Cross-Platform Clarity**: Same logical structure across all technologies
- **Maintenance Efficiency**: Easy to locate and organize code components

## Conclusion

The AICO namespace strategy provides a comprehensive, scalable approach to organizing all system components. By following these guidelines, developers ensure consistency, prevent conflicts, and maintain a professional, organized codebase across all languages and platforms.

For questions or suggestions about the namespace strategy, please refer to the development team or update this document through the standard review process.

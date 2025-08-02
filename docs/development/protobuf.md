# Protocol Buffers in AICO

This document provides guidance for developers working with Protocol Buffers (protobuf) in the AICO system.

## Overview

AICO uses Protocol Buffers as the unified message format for all communication between components. Protocol Buffers provide:

- **High Performance**: Binary serialization is faster and more compact than JSON
- **Strong Typing**: Compile-time type checking reduces errors
- **Cross-Platform**: Consistent message format across all platforms and languages
- **Schema Evolution**: Built-in versioning and backward compatibility
- **Code Generation**: Automatic generation of serialization/deserialization code

## Directory Structure

All Protocol Buffer definitions are located in the `/proto/` directory with the following structure:

```
/proto/
  ├── core/           # Core message envelope and common types
  │   ├── envelope.proto
  │   ├── common.proto
  │   └── api_gateway.proto
  ├── conversation/   # Conversation and chat-related messages
  │   └── conversation.proto
  ├── emotion/        # Emotion simulation and recognition messages
  │   └── emotion.proto
  ├── integration/    # Cross-module integration messages
  │   └── integration.proto
  └── personality/    # Personality simulation messages
      └── personality.proto
```

## Code Generation

### Prerequisites

1. Install the Protocol Buffers compiler (`protoc`):
   ```bash
   # macOS
   brew install protobuf
   
   # Ubuntu/Debian
   sudo apt-get install protobuf-compiler
   
   # Windows (via chocolatey)
   choco install protoc
   ```

2. Install language-specific plugins:
   ```bash
   # Python
   pip install protobuf mypy-protobuf

   # Dart
   dart pub global activate protoc_plugin
   
   # JavaScript/TypeScript
   npm install -g protoc-gen-js protoc-gen-grpc-web
   ```

### Generating Code

#### Python

```bash
cd /path/to/aico/proto
protoc -I=. --python_out=../aico/generated --mypy_out=../aico/generated ./core/*.proto ./emotion/*.proto ./conversation/*.proto ./personality/*.proto ./integration/*.proto
```

#### Dart (Flutter Frontend)

```bash
cd /path/to/aico/proto
protoc -I=. --dart_out=../frontend/lib/generated ./core/*.proto ./emotion/*.proto ./conversation/*.proto ./personality/*.proto ./integration/*.proto
```

#### JavaScript/TypeScript (Avatar System)

```bash
cd /path/to/aico/proto
protoc -I=. --js_out=import_style=commonjs,binary:../avatar/generated --grpc-web_out=import_style=commonjs,mode=grpcwebtext:../avatar/generated ./core/*.proto ./emotion/*.proto ./conversation/*.proto ./personality/*.proto ./integration/*.proto
```

## Development Guidelines

### Message Format Evolution

When updating message formats:

1. Follow Protocol Buffers best practices for backward compatibility:
   - Never remove or renumber fields, only add new ones
   - Use the `reserved` keyword for deprecated fields
   - Keep field numbers consistent across versions

2. Update version numbers in the message metadata when making changes

3. Document changes in commit messages and update relevant architecture documentation

### Common Patterns

#### Message Envelope

All messages should use the common envelope structure defined in `core/envelope.proto`:

```protobuf
message Envelope {
  Metadata metadata = 1;
  google.protobuf.Any payload = 2;
}

message Metadata {
  string message_id = 1;
  google.protobuf.Timestamp timestamp = 2;
  string source = 3;
  string message_type = 4;
  string version = 5;
}
```

#### Timestamps

Always use `google.protobuf.Timestamp` for timestamp fields:

```protobuf
import "google/protobuf/timestamp.proto";

message YourMessage {
  google.protobuf.Timestamp created_at = 1;
}
```

#### Enumerations

Define enumerations with an `UNKNOWN = 0` default value:

```protobuf
enum Priority {
  UNKNOWN = 0;
  LOW = 1;
  MEDIUM = 2;
  HIGH = 3;
}
```

#### Extensibility

Use `oneof` for fields that can have multiple types:

```protobuf
message Result {
  oneof value {
    string text_value = 1;
    int32 numeric_value = 2;
    bool boolean_value = 3;
  }
}
```

### Testing

1. **Unit Testing**: Test serialization/deserialization of messages
2. **Integration Testing**: Test message passing between different components
3. **Cross-Language Testing**: Verify compatibility between Python, Dart, and JavaScript implementations

## Integration with Message Bus

The ZeroMQ message bus uses these Protocol Buffer definitions for serialization and deserialization of all messages. See the [Message Bus Architecture](/docs/architecture/message_bus.md) document for more details.

## Integration with API Gateway

The API Gateway performs minimal transformation between external formats (JSON, gRPC) and internal Protocol Buffer messages. See the [API Gateway Architecture](/docs/architecture/api_gateway.md) document for more details.

## Local-First and Federated Architecture Considerations

Protocol Buffers support AICO's local-first, federated architecture by:

1. **Efficiency**: Compact binary format reduces network bandwidth for device synchronization
2. **Consistency**: Same message format used across all devices and platforms
3. **Versioning**: Built-in schema evolution supports gradual updates across federated devices
4. **Security**: Binary format with clear structure reduces attack surface compared to text-based formats

## References

- [Protocol Buffers Developer Guide](https://developers.google.com/protocol-buffers/docs/overview)
- [Protocol Buffer Basics: Python](https://developers.google.com/protocol-buffers/docs/pythontutorial)
- [Protocol Buffer Basics: Dart](https://developers.google.com/protocol-buffers/docs/darttutorial)
- [Protocol Buffer Style Guide](https://developers.google.com/protocol-buffers/docs/style)

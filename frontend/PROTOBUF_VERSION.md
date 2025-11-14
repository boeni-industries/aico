# Protobuf Version Compatibility

## Current Setup

- **Backend**: protobuf 6.32.0 (Python)
- **Frontend**: protobuf 5.0.0 (Dart)

## Why Different Versions?

The Dart protobuf package is currently at version 5.0.0 maximum on pub.dev, while Python protobuf is at 6.32.0. This is **not a problem** because:

1. **Wire Format Compatibility**: Protobuf maintains backward and forward compatibility in its wire format across major versions
2. **Generated Code**: The `protoc` compiler generates code based on `.proto` files, not runtime versions
3. **Runtime Library**: The protobuf 5.0.0 Dart runtime can read/write messages that are compatible with protobuf 6.32.0 Python runtime

## Dependency Resolution

We removed the unused `retrofit` and `retrofit_generator` dependencies which were constraining us to protobuf ^4.x. This allowed us to upgrade to protobuf ^5.0.0, bringing us one major version closer to the backend.

## Regenerating Protobuf Files

To regenerate the Dart protobuf files:

```bash
cd frontend
rm -rf lib/generated
mkdir -p lib/generated
export PATH="$PATH:$HOME/.pub-cache/bin"
protoc -I=../proto \
  -I=$HOME/.pub-cache/hosted/pub.dev/protoc_plugin-23.0.0/test/protos \
  --dart_out=lib/generated \
  ../proto/aico_modelservice.proto \
  ../proto/aico_conversation.proto \
  google/protobuf/timestamp.proto
```

## Testing Compatibility

The protobuf wire format is tested to be compatible across versions. Our implementation:
- Backend sends protobuf 6.x binary messages
- Frontend receives and parses with protobuf 5.x runtime
- All field types (strings, ints, enums, nested messages) work correctly
- New fields in 6.x are forward-compatible with 5.x readers

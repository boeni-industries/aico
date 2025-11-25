---
title: Text-to-Speech Architecture
---

# Text-to-Speech (TTS) Architecture

## Overview

AICO implements a **single-tier, frontend-native TTS architecture** that prioritizes local-first operation, privacy, and cross-platform consistency. The system uses platform-native TTS engines as the foundation with optional on-device neural TTS for premium voice quality.

## Design Principles

### Local-First Operation
All TTS processing occurs on-device without backend dependencies. Text never leaves the user's device, preserving privacy and enabling offline functionality.

### Thin Client Alignment
TTS is presentation layer functionality—audio output for the UI. No business logic or backend orchestration required. Audio playback is inherently client-side.

### Zero Latency
On-device processing eliminates network round-trips, providing instant audio response with no buffering or streaming delays.

### Cross-Platform Consistency
While platform engines vary, the architecture supports optional neural TTS (Kokoro-82M via ONNX) for consistent voice quality across all platforms when needed.

## Architecture Components

### Primary: Platform Native TTS (flutter_tts)

**Technology**: `flutter_tts` package (MIT License)

**Platform Engines**:
- **iOS/macOS**: AVSpeechSynthesizer
- **Android**: TextToSpeech API  
- **Windows**: SpeechSynthesizer
- **Web**: Web Speech API
- **Linux**: espeak/festival

**Characteristics**:
- Zero setup complexity
- Excellent quality on iOS/macOS
- Minimal battery impact
- Instant availability
- No model downloads required

**Use Cases**:
- MVP implementation
- Default voice output
- Fallback when neural TTS unavailable
- Low-latency requirements

### Optional: Neural TTS (kokoro_tts_flutter)

**Technology**: Kokoro-82M via ONNX Runtime (Apache 2.0 License)

**Characteristics**:
- 82M parameter model
- On-device inference (<300ms latency)
- Consistent voice across platforms
- ~100MB model download
- Multi-language support
- Emotional prosody control

**Use Cases**:
- Premium voice quality
- Character voice consistency (Eve personality)
- Emotional expressiveness
- Cross-platform voice uniformity

## Implementation Strategy

### Phase 1: MVP (Platform Native)

Use `flutter_tts` for immediate functionality:
- Rapid implementation
- Zero configuration
- Good quality baseline
- Works everywhere

### Phase 2: Neural Enhancement (Optional)

Add `kokoro_tts_flutter` for premium experiences:
- User preference toggle (native vs neural)
- Model download on first use
- Cached for offline use
- Graceful fallback to native

### Phase 3: Character Voices

Implement custom voice models for AI personalities:
- Fine-tuned Kokoro models per character
- Emotional tone variations
- Consistent character identity
- Voice cloning for brand consistency

## Custom Voice Creation

### Training Custom Character Voices

For consistent cross-platform character voices (e.g., Eve personality), AICO supports custom voice model training:

**Approach**: Fine-tune Kokoro-82M on character-specific voice samples

**Requirements**:
- 10-30 minutes of clean audio samples
- Consistent recording environment
- Single speaker (target character voice)
- Diverse emotional range samples

**Training Process**:

1. **Data Preparation**
   - Record or source voice samples
   - Clean audio (noise reduction, normalization)
   - Segment into 5-15 second clips
   - Transcribe all audio accurately

2. **Model Fine-Tuning**
   - Use Kokoro training scripts
   - Fine-tune on character voice dataset
   - Validate emotional range
   - Export ONNX model for mobile deployment

3. **Model Distribution**
   - Package ONNX model (~100MB)
   - Distribute via app assets or download
   - Cache locally on device
   - Version control for updates

**Tools & Resources**:
- Kokoro training repository: `github.com/hexgrad/kokoro`
- ONNX Runtime for mobile deployment
- Audio preprocessing: Audacity, Adobe Audition
- Dataset curation: Coqui dataset tools

### Voice Consistency Strategy

**Single Source of Truth**: One trained model deployed across all platforms via ONNX ensures identical voice output regardless of device.

**Fallback Hierarchy**:
1. Custom neural voice (Kokoro fine-tuned)
2. Generic neural voice (Kokoro base model)
3. Platform native TTS

**Model Management**:
- Models stored in app assets or downloaded on-demand
- Versioned model files for updates
- Automatic fallback if model unavailable
- User preference persistence

## Technical Integration

### Repository Pattern

```dart
abstract class TtsRepository {
  Future<void> speak(String text, {TtsVoiceType? voiceType});
  Future<void> stop();
  Future<void> pause();
  Stream<TtsState> get stateStream;
}
```

### Voice Type Enumeration

```dart
enum TtsVoiceType {
  platformNative,    // flutter_tts
  neuralGeneric,     // Kokoro base
  characterEve,      // Custom Eve voice
  characterCustom,   // User-trained voice
}
```

### State Management (Riverpod)

```dart
final ttsRepositoryProvider = Provider<TtsRepository>((ref) {
  return TtsRepositoryImpl(
    nativeTts: FlutterTts(),
    neuralTts: KokoroTts(),
    preferences: ref.read(userPreferencesProvider),
  );
});

final ttsProvider = StateNotifierProvider<TtsNotifier, TtsState>((ref) {
  return TtsNotifier(ref.read(ttsRepositoryProvider));
});
```

## Performance Characteristics

| Metric | Platform Native | Neural (Kokoro) |
|--------|----------------|-----------------|
| Latency | <100ms | ~300ms |
| Quality | Good | Excellent |
| Memory | <10MB | ~150MB |
| Battery Impact | Minimal | Low |
| Offline | ✅ | ✅ |
| Consistency | Platform-dependent | Uniform |

## Privacy & Security

### Data Flow
- Text input → On-device TTS → Audio output
- No network transmission
- No backend logging
- No cloud dependencies

### Model Security
- ONNX models stored in encrypted app storage
- Model integrity verification via checksums
- Secure model download over HTTPS
- No telemetry or usage tracking

## Future Enhancements

### Emotional Prosody Control
- Dynamic pitch/rate adjustment based on emotion state
- Integration with emotion simulation system
- Real-time prosody modulation
- SSML support for fine-grained control

### Voice Cloning
- User-provided voice samples
- Personal voice model training
- Privacy-preserving on-device training
- Custom voice library management

### Multi-Speaker Conversations
- Different voices for different characters
- Conversation mode with speaker switching
- Voice mixing for group scenarios

### Streaming Synthesis
- Sentence-by-sentence generation
- Reduced perceived latency
- Interrupt and resume support
- Background audio processing

## Dependencies

### Flutter Packages
- `flutter_tts: ^4.2.3` (MIT) - Platform native TTS
- `kokoro_tts_flutter: ^0.2.0+1` (Apache 2.0) - Neural TTS (optional)
- `audioplayers` - Audio playback control (if needed)

### Platform Requirements
- **iOS**: iOS 13+ for AVSpeechSynthesizer features
- **Android**: API 21+ for TextToSpeech API
- **macOS**: macOS 10.15+ for AVSpeechSynthesizer
- **Windows**: Windows 10+ for SpeechSynthesizer
- **Linux**: espeak-ng installed

### Model Assets
- Kokoro base model: ~100MB (optional download)
- Custom character voices: ~100MB each
- Cached locally after first download

## Testing Strategy

### Unit Tests
- TTS repository implementations
- Voice type selection logic
- Fallback mechanism validation
- State management transitions

### Integration Tests
- Platform TTS engine integration
- Neural TTS model loading
- Audio output verification
- Error handling and recovery

### Platform Tests
- iOS/macOS AVSpeechSynthesizer
- Android TextToSpeech API
- Windows SpeechSynthesizer
- Web Speech API
- Linux espeak integration

## Monitoring & Observability

### Metrics
- TTS invocation count
- Voice type usage distribution
- Latency measurements
- Error rates by platform
- Model download success rate

### Error Handling
- Graceful fallback to platform native
- Model loading failure recovery
- Audio output device errors
- Network timeout (model download)

## Conclusion

AICO's single-tier TTS architecture provides immediate, private, and high-quality voice synthesis without backend dependencies. The optional neural TTS tier enables premium experiences and character voice consistency while maintaining the core local-first principle. Custom voice training ensures brand consistency and emotional expressiveness for AI companion personalities.

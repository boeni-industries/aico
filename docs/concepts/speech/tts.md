---
title: Text-to-Speech Architecture
---

# Text-to-Speech (TTS) Architecture

## Overview

**Current implementation:** AICO uses a backend TTS service in the modelservice (Piper TTS and Coqui XTTS v2) and streams ready-to-play audio to the Flutter frontend, which plays it via `just_audio`.

## Design Principles

### Local-First Operation
TTS synthesis runs in the local backend modelservice; audio is then streamed to the frontend. Text and audio remain on the user's device.

### Thin Client Alignment
Synthesis is handled by the backend modelservice; audio playback is client-side.

### Zero Latency
Local backend processing eliminates external network round-trips, providing fast audio response with minimal buffering or streaming delays.

### Cross-Platform Consistency
Using a centralized backend TTS engine (Piper/XTTS and potentially Kokoro) ensures consistent voice quality and behavior across all frontend platforms.

## Architecture Components

### Primary (Current): Backend TTS (Modelservice)

The primary, production implementation for TTS is the backend modelservice, using Piper TTS (recommended) and Coqui XTTS v2, with the Flutter app receiving only the audio stream and playing it via `just_audio`.

### Future Backend Engine (Planned): Kokoro TTS

**Status**: Under evaluation as a potential **third backend engine** (alongside Piper and XTTS). Not implemented yet.

**Conceptual Technology**: Kokoro-82M via ONNX Runtime (Apache 2.0 License)

**Target Characteristics** (if adopted):
- 82M parameter model
- Fast inference on local backend
- Consistent voice across platforms
- ~100MB model download
- Multi-language support
- Emotional prosody control

**Use Cases**:
- Premium voice quality
- Character voice consistency (Eve personality)
- Emotional expressiveness
- Cross-platform voice uniformity

## Custom Voice Creation (Planned Backend Models)

## Custom Voice Creation

### Training Custom Character Voices

For consistent cross-platform character voices (e.g., Eve personality), AICO envisions custom backend voice model training:

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

**Single Source of Truth**: One trained backend model deployed across all platforms via ONNX ensures identical voice output regardless of device.

**Model Management (Planned):**
- Models stored on the local backend or downloaded on-demand
- Versioned model files for updates
- Automatic backend-side fallback if a model is unavailable

## Future Enhancements (Planned Backend Capabilities)

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

### Flutter Packages (Current)
- `just_audio` - Audio playback for streamed WAV from backend modelservice TTS

## Testing Strategy

### Unit Tests
- TTS repository implementations
- Voice type selection logic
- Fallback mechanism validation
- State management transitions

### Integration Tests
- Backend TTS request/response
- Audio streaming over network (ZeroMQ/WebSocket)
- Audio output verification on client (via `just_audio`)
- Error handling and recovery

## Monitoring & Observability

### Metrics
- TTS invocation count
- Voice type usage distribution
- Latency measurements
- Error rates by platform
- Model download success rate

### Error Handling
- Graceful fallback between TTS engines (e.g., XTTS → Piper)
- Model loading failure recovery
- Audio output device errors (client-side)
- Network errors (model download or audio streaming)

## Backend TTS (Modelservice)

AICO's backend supports two TTS engines: **Piper TTS** (ultra-fast, local) and **Coqui XTTS v2** (high-quality, voice cloning). The system automatically detects language and applies appropriate text preprocessing.

### Piper TTS (Recommended)

**Technology**: Piper - Fast, local neural TTS via ONNX Runtime

**Features**:
- Ultra-fast synthesis (~300ms for full sentences)
- 15-24x faster than XTTS
- Multiple quality levels (x_low, low, medium, high)
- 100+ voices across 40+ languages
- On-device processing, no cloud dependencies
- Automatic voice model download

**Performance**:
- Synthesis: ~300ms per sentence
- Model size: 5-30MB per voice (quality dependent)
- Sample rates: 16kHz (low quality) or 22.05kHz (medium/high)
- Memory: ~100MB RAM per loaded voice

**Voice Quality Levels**:
- `x_low`: 16kHz, 5-7M params (fastest, lowest quality)
- `low`: 16kHz, 15-20M params (fast, good quality)
- `medium`: 22.05kHz, 15-20M params (balanced)
- `high`: 22.05kHz, 28-32M params (best quality, slower)

### Coqui XTTS v2 (High-Quality Alternative)

**Technology**: Coqui XTTS v2 - Neural TTS with voice cloning

**Features**:
- 58 built-in multilingual speakers
- 17 language support
- Voice cloning from 6-second samples
- Streaming audio synthesis
- WAV format output
- Excellent quality, natural prosody

**Performance**:
- Synthesis: ~500ms per chunk
- Model size: 1.8GB (auto-downloaded)
- Sample rate: 22.05kHz
- Memory: ~2GB RAM

### Configuration

Both engines are configured in `config/defaults/core.yaml` under the `core.modelservice.tts` section:

```yaml
core:
  modelservice:
    tts:
      enabled: true
      engine: "piper"  # or "xtts"
      auto_detect_language: true
      
      # XTTS Configuration
      xtts:
        voices:
          en: "Daisy Studious"
          de: "Daisy Studious"
        custom_voice_path: null
      
      # Piper Configuration
      piper:
        voices:
          en: "en_US-amy-medium"
          de: "de_DE-kerstin-low"
        quality: "medium"
      
      speed: 1.0
```

### Piper Available Voices

#### German Female Voices
- **`de_DE-kerstin-low`** - Clear, professional (recommended, sped up 10%)
- **`de_DE-ramona-low`** - Younger-sounding, natural
- **`de_DE-pavoque-low`** - Alternative option

#### English Voices
- **`en_US-amy-medium`** - Clear, professional (default)
- **`en_US-lessac-medium`** - Warm, friendly
- **`en_US-libritts-high`** - Highest quality, slower
- **`en_GB-alan-medium`** - British male
- Many more available in [Piper voice samples](https://rhasspy.github.io/piper-samples/)

### Audio Processing & Optimizations

**Text Preprocessing**:
- Automatic markdown removal (bold, italic, links)
- Emoji removal (comprehensive Unicode ranges)
- Em-dash/en-dash conversion to periods (for proper pauses)
- Abbreviation expansion (P.S. → Postscript, e.g. → for example)
- Ensures space after punctuation (critical for Piper pause detection)

**Audio Post-Processing**:
- **German voice speed-up**: 10% faster using scipy polyphase resampling
  - Prevents "Mickey Mouse" effect while improving pace
  - High-quality interpolation maintains audio fidelity
- **Trailing artifact removal**: 300ms fade-out + 500 samples forced to zero
  - Eliminates pop/click sounds at end of playback
  - Ensures smooth audio termination at zero crossing

**Sample Rate Handling**:
- Automatic detection from voice model (16kHz or 22.05kHz)
- Proper WAV header construction with correct sample rate
- Backend buffers all audio before sending complete WAV file
- Frontend receives ready-to-play WAV with no additional processing

**Known Limitations**:
- Piper doesn't respect comma pauses (only periods create pauses)
- Voice synthesis is non-deterministic (slight variations between runs)
- Low-quality German voices have inherent noise characteristics
- No medium/high quality female German voices available in Piper

### XTTS Available Voices by Language

#### Female Voices
- **Claribel Dervla** - Clear, professional
- **Daisy Studious** - Warm, friendly (default)
- **Gracie Wise** - Mature, authoritative
- **Tammie Ema** - Energetic, young
- **Alison Dietlinde** - Soft, gentle
- **Ana Florence** - Elegant, refined
- **Annmarie Nele** - Casual, approachable
- **Asya Anara** - Exotic, mysterious
- **Brenda Stern** - Strong, confident
- **Gitta Nikolina** - Playful, cheerful
- **Henriette Usha** - Sophisticated, calm
- **Sofia Hellen** - Smooth, melodic
- **Tammy Grit** - Determined, bold
- **Tanja Adelina** - Sweet, caring
- **Vjollca Johnnie** - Unique, distinctive

#### Male Voices
- **Andrew Chipper** - Upbeat, friendly
- **Badr Odhiambo** - Deep, resonant
- **Dionisio Schuyler** - Theatrical, expressive
- **Royston Min** - Calm, measured
- **Viktor Eka** - Strong, commanding
- **Abrahan Mack** - Warm, trustworthy
- **Adde Michal** - Young, energetic
- **Baldur Sanjin** - Mature, wise
- **Craig Gutsy** - Bold, adventurous
- **Damien Black** - Mysterious, dark
- **Gilberto Mathias** - Friendly, approachable
- **Ilkin Urbano** - Urban, modern
- **Kazuhiko Atallah** - Precise, technical
- **Ludvig Milivoj** - Noble, refined
- **Suad Qasim** - Authoritative, serious
- **Torcull Diarmuid** - Rugged, strong
- **Viktor Menelaos** - Heroic, brave
- **Zacharie Aimilios** - Gentle, kind

#### Neutral/Androgynous Voices
- **Nova Hogarth** - Futuristic, neutral
- **Maja Ruoho** - Balanced, clear
- **Uta Obando** - Versatile, adaptable

### Supported Languages

All voices work across all languages:
- **en** - English
- **de** - German  
- **es** - Spanish
- **fr** - French
- **it** - Italian
- **pt** - Portuguese
- **pl** - Polish
- **tr** - Turkish
- **ru** - Russian
- **nl** - Dutch
- **cs** - Czech
- **ar** - Arabic
- **zh-cn** - Chinese (Simplified)
- **hu** - Hungarian
- **ko** - Korean
- **ja** - Japanese
- **hi** - Hindi

### Voice Cloning

For custom voices, provide a 6-30 second WAV file:

1. Place WAV file in `modelservice/assets/voices/`
2. Set `custom_voice_path` in config
3. Restart modelservice

Custom voice overrides built-in speakers for all languages.

### Performance Comparison

| Metric | Piper TTS | XTTS v2 |
|--------|-----------|---------|
| Model Size | 5-30MB per voice | 1.8GB |
| Synthesis Time | ~300ms | ~500ms per chunk |
| Speed vs XTTS | 15-24x faster | Baseline |
| Quality | Good to Excellent | Excellent |
| Memory | ~100MB | ~2GB RAM |
| Languages | 40+ | 17 |
| Voices | 100+ | 58 built-in |
| Voice Cloning | No | Yes (6s samples) |
| Sample Rate | 16-22.05kHz | 22.05kHz |

## Conclusion

AICO's TTS system focuses on a single, consistent architecture:

**Current Backend (Modelservice)**:
- **Piper TTS** (recommended): Ultra-fast synthesis (15-24x faster than XTTS) with 100+ voices across 40+ languages
- **XTTS v2** (alternative): High-quality synthesis with voice cloning capabilities
- Automatic language detection and text preprocessing
- Optimized audio processing with speed adjustments and artifact removal
- Audio is streamed as WAV to the Flutter client and played via `just_audio`.

**Planned Backend Extension**:
- **Kokoro TTS** considered as a potential third engine for the modelservice and for custom character voices.

The system prioritizes speed and quality while maintaining privacy and local-first operation on the user's machine. Piper TTS currently provides the best balance of performance and quality for most use cases, with XTTS available for scenarios requiring voice cloning or maximum quality, and Kokoro evaluated as a future backend option.

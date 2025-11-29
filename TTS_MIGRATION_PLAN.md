# TTS Migration Plan: Frontend → Backend

## Overview
Migrating TTS from Flutter frontend (Piper/sherpa-onnx) to Python backend (Coqui XTTS) for zero UI blocking and better quality.

---

## ✅ Phase 1: Frontend Cleanup (COMPLETED)

**Removed:**
- `sherpa_onnx` dependency
- `/lib/core/services/piper_tts_service.dart`
- `/lib/core/config/tts_voices.dart`
- `assets/tts/` directory (models, espeak-ng-data)
- All Piper synthesis code from `tts_repository_impl.dart`

**Kept:**
- `just_audio` for audio playback
- TTS state management (`TtsState`, `TtsStatus`)
- TTS repository interface
- TTS provider (Riverpod)

**Result:** Clean 125-line stub ready for backend integration

---

## ✅ Phase 2: API Contract Definition (COMPLETED)

### Protobuf Messages

**File:** `/proto/aico_modelservice.proto`

```protobuf
// TTS request
message TtsRequest {
  string text = 1;
  string language = 2;  // ISO 639-1 code (e.g., "en", "de")
  optional float speed = 3;  // Speech speed multiplier (default: 1.0)
  optional string voice = 4;  // Voice identifier (optional)
}

// TTS streaming chunk
message TtsStreamChunk {
  bytes audio_data = 1;  // Raw audio bytes (WAV format)
  int32 sample_rate = 2;  // Sample rate (e.g., 22050)
  bool is_final = 3;  // True if this is the last chunk
  optional string error = 4;  // Error message if synthesis failed
}
```

### ZMQ Topics

**File:** `/shared/aico/core/topics.py`

```python
MODELSERVICE_TTS_REQUEST = "modelservice/tts/request/v1"
MODELSERVICE_TTS_STREAM = "modelservice/tts/stream/v1"
```

**Communication Flow:**
```
Frontend → Gateway → Modelservice (TTS Request)
Modelservice → Gateway → Frontend (TTS Stream Chunks)
```

---

## 🔄 Phase 3: Backend Implementation (TODO)

### 3.1 Add Coqui TTS Dependency

**File:** `/modelservice/pyproject.toml`

```toml
[tool.poetry.dependencies]
TTS = "^0.22.0"  # Coqui TTS
```

### 3.2 Create TTS Handler

**File:** `/modelservice/core/tts_handler.py`

```python
from TTS.api import TTS
import asyncio
from typing import AsyncGenerator

class TtsHandler:
    def __init__(self):
        self._tts = None
        self._voice_path = Path(__file__).parent / "assets/voices/aico_default.wav"
    
    async def initialize(self):
        """Load Coqui XTTS model on startup"""
        self._tts = await asyncio.to_thread(
            TTS, "tts_models/multilingual/multi-dataset/xtts_v2"
        )
        # Warm-up synthesis
        await asyncio.to_thread(self._tts.tts, "ready", language="en")
    
    async def synthesize_stream(
        self, 
        text: str, 
        language: str, 
        speed: float = 1.0
    ) -> AsyncGenerator[bytes, None]:
        """Stream audio chunks as they're synthesized"""
        # Chunk text at sentence boundaries
        chunks = self._split_text(text)
        
        for chunk in chunks:
            audio = await asyncio.to_thread(
                self._tts.tts,
                text=chunk,
                language=language,
                speaker_wav=str(self._voice_path)
            )
            # Convert to WAV bytes
            wav_bytes = self._to_wav(audio, sample_rate=22050)
            yield wav_bytes
```

### 3.3 Register TTS Handler

**File:** `/modelservice/core/zmq_handlers.py`

```python
from .tts_handler import TtsHandler

class ModelserviceZMQHandlers:
    def __init__(self):
        # ... existing handlers
        self.tts_handler = TtsHandler()
    
    async def initialize(self):
        # ... existing initialization
        await self.tts_handler.initialize()
    
    async def handle_tts_request(self, request: TtsRequest) -> AsyncGenerator:
        """Handle TTS streaming request"""
        async for audio_chunk in self.tts_handler.synthesize_stream(
            text=request.text,
            language=request.language,
            speed=request.speed or 1.0
        ):
            yield TtsStreamChunk(
                audio_data=audio_chunk,
                sample_rate=22050,
                is_final=False
            )
        
        # Send final chunk
        yield TtsStreamChunk(
            audio_data=b"",
            sample_rate=22050,
            is_final=True
        )
```

### 3.4 Register Topic Mapping

**File:** `/modelservice/core/zmq_service.py`

```python
self.topic_handlers = {
    # ... existing handlers
    AICOTopics.MODELSERVICE_TTS_REQUEST: self.handlers.handle_tts_request,
}
```

### 3.5 Add Voice Assets

**Directory:** `/modelservice/assets/voices/`

```
aico_default.wav  # Reference voice for XTTS
```

---

## 🔄 Phase 4: Frontend Integration (TODO)

### 4.1 Add Gateway API Client

**File:** `/frontend/lib/data/datasources/tts_remote_datasource.dart`

```dart
class TtsRemoteDataSource {
  final GatewayClient _client;
  
  Stream<Uint8List> requestTts({
    required String text,
    required String language,
    double speed = 1.0,
  }) async* {
    // Send TTS request to Gateway
    final response = await _client.sendTtsRequest(
      text: text,
      language: language,
      speed: speed,
    );
    
    // Stream audio chunks
    await for (final chunk in response.stream) {
      if (chunk.isFinal) break;
      yield chunk.audioData;
    }
  }
}
```

### 4.2 Update TTS Repository

**File:** `/frontend/lib/data/repositories/tts_repository_impl.dart`

```dart
Future<void> speak(String text) async {
  if (text.isEmpty || !_isAvailable) return;

  try {
    _updateState(_currentState.copyWith(
      status: TtsStatus.speaking,
      currentText: text,
      progress: 0.0,
    ));
    
    // Request TTS from backend
    final audioStream = _remoteDataSource.requestTts(
      text: text,
      language: 'en',  // TODO: Get from user settings
    );
    
    // Stream audio chunks to player
    await _playAudioStream(audioStream);
    
    _updateState(_currentState.copyWith(
      status: TtsStatus.idle,
      currentText: null,
      progress: 1.0,
    ));
  } catch (e, stackTrace) {
    AICOLog.error('TTS speak failed', error: e, stackTrace: stackTrace);
    _updateState(_currentState.copyWith(
      status: TtsStatus.error,
      errorMessage: 'TTS failed: ${e.toString()}',
    ));
  }
}

Future<void> _playAudioStream(Stream<Uint8List> audioStream) async {
  await _audioPlayer!.setAudioSource(
    _StreamingAudioSource(audioStream),
  );
  await _audioPlayer!.play();
  await _audioPlayer!.playerStateStream.firstWhere(
    (state) => state.processingState == ProcessingState.completed,
  );
}
```

---

## 🔄 Phase 5: Testing & Polish (TODO)

### 5.1 Test Multi-language
- English (en)
- German (de)

### 5.2 Verify Zero UI Blocking
- Button press → immediate animation
- No stuttering during synthesis
- Smooth playback

### 5.3 Optimize Chunk Size
- Balance latency vs. smoothness
- Test with various text lengths

### 5.4 Error Handling
- Network failures
- Backend unavailable
- Synthesis errors

---

## Technical Decisions

### Why Coqui XTTS?
- ✅ High quality (9/10 naturalness)
- ✅ Emotion support (8/10)
- ✅ Voice cloning capability
- ✅ Multi-language (17 languages including EN, DE)
- ✅ Production-ready
- ✅ Runs on consumer hardware (M1/M2)

### Why Backend?
- ✅ Zero UI blocking (synthesis off main thread)
- ✅ Better architecture (modelservice handles all AI)
- ✅ Easier model management (no LFS needed)
- ✅ Scalable (one engine serves all clients)

### Streaming Protocol
- Request: Single `TtsRequest` message
- Response: Stream of `TtsStreamChunk` messages
- Final chunk: `is_final=true` with empty audio_data

---

## Migration Checklist

- [x] Phase 1: Frontend cleanup
- [x] Phase 2: API contract definition
- [x] Phase 3: Backend implementation
  - [x] Add Coqui TTS dependency
  - [x] Create TTS handler
  - [x] Register in ZMQ handlers
  - [x] Add voice assets directory
  - [ ] Test backend synthesis
- [x] Phase 4: Frontend integration (prepared)
  - [x] Create TTS remote datasource stub
  - [x] Clean TTS repository ready
  - [ ] Implement Gateway API endpoint
  - [ ] Complete datasource implementation
  - [ ] Test streaming playback
- [ ] Phase 5: Testing & polish
  - [ ] Multi-language testing
  - [ ] UI responsiveness verification
  - [ ] Error handling
  - [ ] Performance optimization

---

## Next Steps

**Ready to proceed with Phase 3: Backend Implementation**

Start with:
1. Add Coqui TTS to modelservice dependencies
2. Create TTS handler with model loading
3. Test synthesis locally before ZMQ integration

# Kokoro-82M Voice Reference

Complete reference of all available voices in the Kokoro-82M TTS model.

## Voice Naming Convention

Voice IDs follow a consistent pattern:
- **Prefix**: Language + Gender
  - `af` = American English Female
  - `am` = American English Male
  - `bf` = British English Female
  - `bm` = British English Male
  - `jf` = Japanese Female
  - `jm` = Japanese Male
  - `zf` = Mandarin Chinese Female
  - `zm` = Mandarin Chinese Male
  - `ef` = Spanish Female
  - `em` = Spanish Male
  - `ff` = French Female
  - `hf` = Hindi Female
  - `hm` = Hindi Male
  - `if` = Italian Female
  - `im` = Italian Male
  - `pf` = Brazilian Portuguese Female
  - `pm` = Brazilian Portuguese Male

## American English (20 voices)

**Language Code**: `a` (for phonemization: `lang='en-us'`)

### Female Voices (11)
- `af_alloy` - Clear, neutral tone
- `af_aoede` - Expressive, dynamic
- `af_bella` - Smooth, warm, expressive
- `af_heart` - Gentle, empathetic, soft
- `af_jessica` - Professional, clear
- `af_kore` - Balanced, natural
- `af_nicole` - Confident, articulate
- `af_nova` - Bright, energetic
- `af_river` - Calm, flowing
- `af_sarah` - Clear, warm, reliable
- `af_sky` - Light, airy

### Male Voices (9)
- `am_adam` - Deep, authoritative
- `am_echo` - Resonant, clear
- `am_eric` - Friendly, approachable
- `am_fenrir` - Strong, commanding
- `am_liam` - Casual, relatable
- `am_michael` - Professional, steady
- `am_onyx` - Rich, deep
- `am_puck` - Playful, light
- `am_santa` - Warm, jolly (seasonal)

**Recommended for Eve**: `af_sarah` (clear, warm), `af_bella` (smooth, expressive), `af_heart` (gentle, empathetic)

---

## British English (8 voices)

**Language Code**: `b` (for phonemization: `lang='en-gb'`)

### Female Voices (5)
- `bf_alice` - Classic British, refined
- `bf_emma` - Modern British, clear
- `bf_isabella` - Elegant, sophisticated
- `bf_lily` - Soft, gentle

### Male Voices (4)
- `bm_daniel` - Traditional British, authoritative
- `bm_fable` - Storytelling quality, engaging
- `bm_george` - Formal, distinguished
- `bm_lewis` - Contemporary British, friendly

---

## Japanese (5 voices)

**Language Code**: `j` (for phonemization: `lang='ja'`)

### Female Voices (4)
- `jf_alpha` - Standard female voice
- `jf_gongitsune` - Based on "Gongitsune" story narration
- `jf_nezumi` - Based on "Nezumi no Yomeiri" story
- `jf_tebukuro` - Based on "Tebukuro wo Kai ni" story

### Male Voices (1)
- `jm_kumo` - Based on "Kumo no Ito" story narration

**Note**: Japanese voices trained on literary narration, excellent for storytelling.

---

## Mandarin Chinese (8 voices)

**Language Code**: `z` (for phonemization: `lang='zh'`)

### Female Voices (4)
- `zf_xiaobei` - Northern accent, clear
- `zf_xiaoni` - Soft, gentle
- `zf_xiaoxiao` - Bright, cheerful
- `zf_xiaoyi` - Professional, articulate

### Male Voices (4)
- `zm_yunjian` - Deep, authoritative
- `zm_yunxi` - Calm, steady
- `zm_yunxia` - Warm, friendly
- `zm_yunyang` - Energetic, dynamic

---

## Spanish (3 voices)

**Language Code**: `e` (for phonemization: `lang='es'`)

### Female Voices (1)
- `ef_dora` - Clear, expressive

### Male Voices (2)
- `em_alex` - Neutral, professional
- `em_santa` - Warm, festive (seasonal)

---

## French (1 voice)

**Language Code**: `f` (for phonemization: `lang='fr-fr'`)

### Female Voices (1)
- `ff_siwis` - Based on SIWIS dataset, clear French pronunciation

**Note**: Limited French voice selection. Based on CC BY licensed SIWIS dataset.

---

## Hindi (4 voices)

**Language Code**: `h` (for phonemization: `lang='hi'`)

### Female Voices (2)
- `hf_alpha` - Standard female voice
- `hf_beta` - Alternative female voice

### Male Voices (2)
- `hm_omega` - Deep, authoritative
- `hm_psi` - Clear, neutral

---

## Italian (2 voices)

**Language Code**: `i` (for phonemization: `lang='it'`)

### Female Voices (1)
- `if_sara` - Clear, expressive Italian

### Male Voices (1)
- `im_nicola` - Professional, articulate

---

## Brazilian Portuguese (3 voices)

**Language Code**: `p` (for phonemization: `lang='pt-br'`)

### Female Voices (1)
- `pf_dora` - Clear, warm Brazilian accent

### Male Voices (2)
- `pm_alex` - Neutral, professional
- `pm_santa` - Warm, festive (seasonal)

---

## Voice Samples

### Online Demos (Try Voices Live)

**Test all voices online**:
- **Kokoro TTS Demo**: https://kokoroai.org/ - Free online demo with all voices (RECOMMENDED)
- **Unreal Speech Studio**: https://unrealspeech.com/studio - Professional demo with download
- **Kokoro TTS Net**: https://kokorotts.net/ - Alternative demo site

**How to test**:
1. Visit https://kokoroai.org/ (most reliable)
2. Select voice from dropdown (e.g., `af_sarah`, `af_bella`, `af_heart`)
3. Enter test text: "Hello, I'm Eve. It's nice to meet you."
4. Click generate/play to hear the voice

**Note**: Hugging Face Space may be down intermittently. Use kokoroai.org as primary demo.

### Voice Samples Repository

**Download samples**: [Kokoro-82M Voice Samples Repository](https://github.com/KingRabbiTV/Kokoro-82M-samples)
- Clone repo to listen to all 56 voice samples locally
- MP3 files for each voice ID

---

## Voice Selection Guidelines

### For Character Personalities

**Warm & Empathetic** (like Eve):
- American: `af_heart`, `af_sarah`, `af_bella`
- British: `bf_lily`, `bf_emma`
- Mandarin: `zf_xiaoni`, `zf_xiaoyi`

**Professional & Clear**:
- American: `af_jessica`, `af_nicole`, `am_michael`
- British: `bm_daniel`, `bf_isabella`
- Mandarin: `zf_xiaoyi`, `zm_yunxi`

**Energetic & Dynamic**:
- American: `af_nova`, `am_puck`
- Mandarin: `zm_yunyang`, `zf_xiaoxiao`

**Calm & Contemplative**:
- American: `af_river`, `am_echo`
- British: `bf_lily`, `bm_lewis`
- Mandarin: `zm_yunxi`

### Technical Considerations

1. **Language Matching**: Voice prefix must match content language
   - Don't use `af_*` (American) for British English content
   - Don't use `am_*` (Male) for female characters

2. **Phonemization**: Use correct `lang` parameter in `Tokenizer.phonemize()`
   - American English: `lang='en-us'`
   - British English: `lang='en-gb'`
   - Japanese: `lang='ja'`
   - Mandarin: `lang='zh'`
   - Spanish: `lang='es'`
   - French: `lang='fr-fr'`
   - Hindi: `lang='hi'`
   - Italian: `lang='it'`
   - Portuguese: `lang='pt-br'`

3. **Voice Quality**: All voices are high-quality neural TTS
   - Consistent quality across languages
   - Natural prosody and intonation
   - Suitable for production use

4. **Seasonal Voices**: `*_santa` voices are festive/seasonal
   - Use for holiday-themed content
   - May sound out of place in regular conversations

---

## Configuration

### Backend Configuration

Set character voice in `config/defaults/core.yaml`:

```yaml
character:
  name: "Eve"
  voice_id: "af_sarah"  # Choose from available voices above
  description: "Warm, curious, contemplative AI companion"
```

### Frontend Usage

Voice ID is read from character configuration during TTS synthesis:

```dart
// In tts_repository_impl.dart
final voiceId = characterConfig.voiceId;  // e.g., "af_sarah"
final phonemes = await _tokenizer!.phonemize(text, lang: 'en-us');
final ttsResult = await _kokoro!.createTTS(
  text: phonemes,
  voice: voiceId,
  isPhonemes: true,
);
```

### CI/CD Integration

The build process must:
1. Read `character.voice_id` from `core.yaml`
2. Verify voice exists in `voices.json`
3. Configure frontend with correct voice ID
4. Package application with character configuration

---

## Voice Samples

To test voices before selection:

```python
from kokoro import KPipeline

# Initialize pipeline
pipeline = KPipeline(lang_code='a')  # 'a' for American English

# Test different voices
test_text = "Hello, I'm Eve. It's nice to meet you."

for voice in ['af_sarah', 'af_bella', 'af_heart']:
    print(f"Testing voice: {voice}")
    generator = pipeline(test_text, voice=voice)
    for i, (gs, ps, audio) in enumerate(generator):
        # Save or play audio
        pass
```

---

## License & Attribution

All voices are part of the Kokoro-82M model:
- **Model License**: Apache 2.0
- **Training Data**: Permissive/non-copyrighted audio
- **Package License**: MIT (`kokoro_tts_flutter`)

Voices are trained on:
- Public domain audio
- Apache/MIT licensed audio
- Synthetic audio from large providers
- CC BY licensed datasets (SIWIS for French, Koniwa for Japanese)

See [Kokoro-82M model card](https://huggingface.co/hexgrad/Kokoro-82M) for full details.

---

## Total Voice Count: 56

- **American English**: 20 (11 female, 9 male)
- **British English**: 8 (5 female, 4 male)
- **Japanese**: 5 (4 female, 1 male)
- **Mandarin Chinese**: 8 (4 female, 4 male)
- **Spanish**: 3 (1 female, 2 male)
- **French**: 1 (1 female)
- **Hindi**: 4 (2 female, 2 male)
- **Italian**: 2 (1 female, 1 male)
- **Brazilian Portuguese**: 3 (1 female, 2 male)

All voices are included in the bundled `voices.json` file (144MB).

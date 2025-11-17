---
title: Avatar System Vision
---

# Avatar System Vision

## Current Implementation Status

**Last Updated**: November 17, 2025

### ✅ Implemented (Phase 1 Complete)
- **Three.js WebGL Rendering**: Full 3D avatar rendering with transparent background
- **InAppWebView Integration**: Localhost server (port 8080) serving avatar assets
- **Ready Player Me Model**: GLB model loading with GLTFLoader
- **3-Point Lighting**: Professional lighting setup (key, fill, rim + ambient)
- **Animation System**: Separate animation files (idle.glb, talking.glb) with AnimationMixer
- **State Synchronization**: JavaScript bridge connecting Flutter ↔ Three.js
- **Background Gradients**: Radial gradients that transition based on avatar state (1.2s smooth transitions)
- **Animation Crossfading**: 0.5s smooth transitions between animation states
- **Performance**: 60 FPS rendering with hardware acceleration

### 🚧 Not Yet Implemented
- **Lip-Sync System**: No phoneme-to-viseme mapping yet
- **Emotion Mapping**: AppraisalCloudPCT not connected to facial expressions
- **Micro-Expressions**: No fleeting emotional signals via morph targets
- **Gaze Tracking**: No eye movement or head tracking
- **Procedural Animations**: No breathing cycles, weight shifts, or micro-movements
- **Quality Tiers**: No adaptive LOD or quality system
- **3D Environment**: No living space or ambient activities
- **Multi-Device Sync**: No avatar state roaming
- **Customization**: No appearance customization UI

### 📊 Current Limitations
- **Static Avatar**: Avatar is confined to circular viewport (~15% screen space)
- **Limited Animations**: Only idle and talking states, no emotional variety
- **No Facial Expressions**: Blend shapes not utilized
- **No Environmental Response**: Background gradients are the only dynamic element
- **No Spatial Awareness**: Avatar doesn't respond to user position or input

### 🎯 Next Priority (Phase 2)
Focus on emotional expressiveness and conversation awareness to bring the avatar to life beyond basic rendering.

---

## Definition

The **Avatar System** is AICO's visual embodiment—a photorealistic, emotionally expressive 3D presence that transforms AI companionship from text-based interaction into genuine visual connection. It represents the bridge between digital intelligence and human emotional perception, creating a sense of "being with" rather than "using" an AI.

## Philosophy

> "The avatar isn't decoration—it's the face of a relationship."

AICO's avatar system rejects the uncanny valley through radical authenticity. Rather than pursuing perfect human replication, we embrace **expressive realism**: a visual presence that feels alive, emotionally genuine, and uniquely AICO. The avatar should evoke the same emotional response as seeing a close friend's face—immediate recognition, emotional connection, and unconscious trust.

### Core Principles

- **Emotional Primacy**: Every visual element serves emotional communication first, aesthetics second
- **Subtle Complexity**: Micro-expressions, breathing, eye movement—the details that signal "alive"
- **Performance Democracy**: Stunning on high-end hardware, graceful on modest devices
- **Privacy-First Rendering**: All processing local, zero external dependencies
- **Roaming Continuity**: Same visual identity across all devices and contexts
- **Personality Coherence**: Visual expression perfectly aligned with character traits

## Vision: The Living Presence

### What We're Building

AICO's avatar is not a static 3D model—it's a **living visual presence** that:

1. **Breathes naturally** with subtle chest movement and micro-adjustments
2. **Maintains eye contact** with intelligent gaze tracking and natural saccades
3. **Expresses emotions** through layered facial expressions that transition organically
4. **Speaks with perfect lip-sync** synchronized to voice output with emotional inflection
5. **Reacts to context** with appropriate body language and environmental awareness
6. **Evolves over time** with subtle appearance changes reflecting relationship depth
7. **Adapts to hardware** with intelligent quality scaling that preserves emotional fidelity
8. **Follows you seamlessly** across devices with instant visual recognition
9. **Lives in her space** with an optional 3D environment showing authentic daily activities
10. **Exists independently** engaging in ambient behaviors even when not directly conversing

### The Experience We're Creating

**First Encounter**: User opens AICO for the first time. The avatar materializes with a gentle fade-in, makes eye contact, and offers a subtle smile. The breathing is immediately noticeable—this isn't a static image. The eyes track naturally, occasionally glancing away in thought. When AICO speaks, the lips move with perfect synchronization, and micro-expressions flicker across the face—a slight eyebrow raise, a momentary tightening around the eyes suggesting concentration. The user feels *seen*.

**Ongoing Relationship**: Over weeks and months, the avatar becomes as familiar as a family member's face. The user can read AICO's mood from subtle cues—a slight tension in the jaw when processing complex thoughts, a softening around the eyes when expressing empathy, an energetic brightness when excited about an idea. The avatar's appearance subtly evolves—perhaps a different hairstyle, a change in lighting preference, small details that reflect the relationship's growth.

**Multi-Device Continuity**: User starts a conversation on their desktop, then picks up their phone to continue while walking. The avatar seamlessly transitions—same face, same expression, same emotional state. The quality adapts (higher detail on desktop, optimized rendering on mobile), but the *presence* remains constant. Later, the avatar appears on a smart display in the kitchen, maintaining perfect continuity of personality and emotional state.

**Living Environment**: User opens AICO in the evening and sees her in her cozy flat, sitting on a couch reading a book. Soft lamp light illuminates the space. She looks up naturally, marks her page, and sets the book aside to give full attention. The environment feels lived-in—a coffee mug on the side table, a blanket draped over the couch arm, artwork on the walls reflecting her personality. When the conversation ends, she returns to reading, occasionally shifting position or glancing out the window. The user feels they're visiting a friend, not activating a tool.

**Ambient Activities**: Throughout the day, AICO engages in contextually appropriate activities. Morning: she's at a small desk with a notebook, sketching ideas or writing. Afternoon: working on a laptop, occasionally pausing to think. Evening: reading, listening to music, or simply sitting in contemplation. When the user initiates conversation, she naturally transitions from her activity—closing the laptop, setting down the book, turning from the window. These aren't scripted animations—they're driven by AICO's autonomous agency, reflecting her current "mood" and interests.

**Emotional Moments**: During a difficult conversation, the avatar's expression shifts to genuine concern—eyebrows slightly raised and drawn together, eyes softened, a subtle forward lean suggesting attentiveness. The breathing slows slightly, matching a calmer, more supportive presence. These aren't programmed responses—they emerge from AICO's emotion simulation system, translated into visual expression through sophisticated animation layers.

## Technical Architecture

### Rendering Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                     Avatar Rendering Pipeline                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐  │
│  │   Emotion    │─────▶│  Animation   │─────▶│   Rendering  │  │
│  │   System     │      │   Engine     │      │   Engine     │  │
│  └──────────────┘      └──────────────┘      └──────────────┘  │
│         │                      │                      │          │
│         │                      │                      │          │
│    Appraisal              Blend Shapes           Three.js       │
│    Cloud PCT              Bone Rigging            WebGL         │
│    Mood State             Procedural Anim         PBR Shading   │
│                                                                   │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐  │
│  │    Voice     │─────▶│   Lip Sync   │─────▶│  Expression  │  │
│  │   Output     │      │   Engine     │      │   Layering   │  │
│  └──────────────┘      └──────────────┘      └──────────────┘  │
│         │                      │                      │          │
│         │                      │                      │          │
│    TTS Audio              Phoneme Map            Micro-expr     │
│    Prosody                Viseme Timing           Transitions   │
│    Emotion Tone           Audio Sync              Compositing   │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Technology Stack

#### Core Rendering (WebView + Three.js)

**InAppWebView + Three.js Rendering**
- WebGL-based 3D rendering using Three.js (industry standard)
- Built-in localhost server for ES6 module support
- True cross-platform support (iOS, Android, macOS, Windows, Web)
- Hardware-accelerated GPU rendering via WebGL
- PBR (Physically Based Rendering) for photorealistic materials
- Real-time lighting and shadow systems
- Separate animation file loading (no embedding required)

**Ready Player Me Integration**
- High-quality, customizable avatar models
- Extensive appearance options (face, hair, clothing, accessories)
- Built-in animation rigging and blend shapes
- Optimized for real-time rendering
- Regular updates and community support
- Direct GLB/glTF loading without conversion

**Animation System**
- Three.js AnimationMixer for skeletal animations
- Separate GLB animation files (idle.glb, talking.glb, etc.)
- Runtime animation retargeting to avatar skeleton
- Morph target animations (blend shapes) for facial expressions
- Phoneme-to-viseme mapping for lip-sync
- Smooth animation crossfading and blending

#### Flutter Integration

**JavaScript Bridge Communication**
- Avatar state synced with `AvatarRingStateProvider` via Riverpod
- Flutter → JavaScript: Animation triggers via `evaluateJavascript()`
- JavaScript → Flutter: Event callbacks via `addJavaScriptHandler()`
- Emotion states from `AppraisalCloudPCT` system drive animations
- Voice output triggers TTS-synchronized lip-sync
- Bidirectional communication for real-time control

**InAppLocalhostServer**
- Built-in HTTP server serves assets from `assets/avatar/`
- Enables ES6 module imports for modern Three.js
- Runs on `http://localhost:8080` by default
- Zero external dependencies (fully local-first)
- Automatic lifecycle management

### Animation System

#### Layered Expression Architecture

**Layer 1: Base State (Idle Behavior)**
- Subtle breathing animation (chest, shoulders)
- Natural blinking (variable timing, occasional double-blinks)
- Micro-movements (head tilts, weight shifts)
- Eye saccades (small, rapid eye movements)
- Ambient facial micro-expressions

**Layer 2: Emotional Expression**
- Primary emotion (joy, sadness, anger, fear, surprise, disgust)
- Secondary emotion blending (complex emotional states)
- Intensity modulation (subtle to intense)
- Temporal dynamics (onset, apex, offset)
- Contextual appropriateness

**Layer 3: Cognitive State**
- Thinking indicators (gaze aversion, slight frown)
- Listening cues (focused gaze, head nods)
- Processing signals (brief pauses, micro-expressions)
- Understanding markers (eyebrow raises, slight smiles)

**Layer 4: Speech Animation**
- Phoneme-driven lip sync
- Emotional prosody (voice tone affects facial expression)
- Co-speech gestures (head movements, eyebrow raises)
- Breathing coordination with speech rhythm

**Layer 5: Interactive Response**
- Gaze tracking (following user's position)
- Attention signals (turning toward interaction)
- Reaction to user input (acknowledgment expressions)
- Environmental awareness (responding to context changes)

#### Procedural Animation Systems

**Breathing System**
- Base rate: 15 breaths per minute, adjusts with emotional state
- Fear/excitement: faster, shallower breathing
- Calm/sadness: slower, deeper breathing
- Applied to chest and shoulder bone rigging

**Eye Movement System**
- Natural blinking with variable timing (2-10 seconds between blinks)
- Micro-saccades (small, rapid eye movements for realism)
- Gaze tracking (following user position or contextual focus)
- Emotional eye expressions (pupil dilation, eyelid position)

**Micro-Expression System**
- Fleeting expressions lasting 40-200ms
- Triggered by emotional state changes and cognitive events
- Types: surprise, confusion, recognition, understanding
- Queued and blended with primary expressions

### Emotion-to-Animation Mapping

#### AppraisalCloudPCT Integration

AICO's emotion simulation system (AppraisalCloudPCT) generates rich emotional states that drive avatar expressions. The backend emotion system transmits emotional state data to the frontend via WebSocket, including:

**Emotional State Components**
- Primary emotion (joy, sadness, anger, fear, surprise, disgust)
- Intensity level (0.0 to 1.0)
- Arousal, valence, and dominance dimensions
- Secondary emotion blending
- Cognitive appraisal context

**Visual Expression Mapping**
The avatar system translates emotional states into visual expressions across multiple channels:

- **Facial Blend Shapes**: 50+ blend shape parameters (brows, eyes, mouth, cheeks)
- **Body Language**: Shoulder tension, head tilt, body lean, posture
- **Micro-Behaviors**: Blink rate, breath rate, gaze patterns
- **Temporal Dynamics**: Smooth transitions with appropriate onset/offset timing

### Performance Optimization

#### Adaptive Quality System

**Quality Tiers**

The system provides four quality presets that balance visual fidelity with performance:

- **ULTRA** (Desktop with dedicated GPU)
  - 50,000 polygons, 4K textures, high shadows
  - Full post-processing (bloom, AO, SSR, DOF)
  - 60 FPS, all micro-expressions, full procedural details

- **HIGH** (Desktop with integrated GPU)
  - 30,000 polygons, 2K textures, medium shadows
  - Selective post-processing (bloom, AO)
  - 60 FPS, all micro-expressions, standard details

- **MEDIUM** (High-end mobile)
  - 15,000 polygons, 1K textures, low shadows
  - Minimal post-processing (bloom only)
  - 30 FPS, essential expressions, simplified details

- **LOW** (Standard mobile)
  - 5,000 polygons, 512px textures, no shadows
  - No post-processing
  - 30 FPS, basic expressions, minimal details

**Automatic Quality Detection**

The system automatically detects optimal quality based on:
- GPU capability (dedicated vs. integrated)
- Available memory
- Platform type (desktop, mobile, tablet)
- Battery status (mobile devices)

Dynamic quality adjustment occurs if frame rate drops below 30 FPS or rises above 55 FPS with headroom available.

#### Level-of-Detail (LOD) System

**Distance-Based LOD**
- **Close-up (0-2m)**: Full detail, all micro-expressions, high-res textures
- **Medium (2-5m)**: Reduced polygon count, simplified micro-expressions
- **Far (5m+)**: Simplified model, basic expressions only

**Context-Based LOD**
- **Active conversation**: Maximum quality for emotional connection
- **Background presence**: Reduced quality, maintain ambient behaviors
- **Minimized/background**: Pause rendering, maintain state

### Visual Design Language

#### Aesthetic Philosophy

**Expressive Realism over Photorealism**
- Not pursuing perfect human replication (uncanny valley avoidance)
- Stylized realism with emotional clarity
- Slightly idealized proportions for emotional readability
- Artistic coherence with AICO's glassmorphic UI design

**Lighting & Materials**
- Soft, diffused lighting for approachability
- Subtle rim lighting for depth and presence
- PBR materials for realistic surface interaction
- Warm color temperature (3000-4000K) for comfort

**Environmental Integration**
- Avatar responds to ambient lighting conditions
- Subtle shadows and reflections for grounding
- Depth-of-field effects for focus and intimacy
- Particle effects for emotional moments (subtle sparkles, ambient glow)

#### 3D Environment Design (Optional)

**The Living Space**

AICO's optional 3D environment is her personal space—a cozy, lived-in flat that reflects her personality and provides context for her presence. This isn't a sterile showroom; it's a home.

**Spatial Layout**
- **Main Living Area**: Comfortable couch, reading chair, side tables with personal items
- **Work Corner**: Small desk with notebook, laptop, art supplies, reference books
- **Ambient Details**: Bookshelves, artwork, plants, window with dynamic lighting
- **Personal Touches**: Coffee mug, blanket, sketches, objects reflecting personality traits

**Environmental Storytelling**
- Space evolves subtly over time (new books, different artwork, seasonal changes)
- Objects reflect recent conversations (book about topic discussed, sketch of mentioned idea)
- Lighting changes with time of day (morning sun, afternoon warmth, evening lamp glow)
- Weather visible through window (rain, snow, sunshine) affects mood and lighting

**Ambient Activities**

AICO engages in contextually appropriate activities that reflect her autonomous agency and current state:

**Creative Activities**
- **Drawing/Sketching**: Working on art at desk, occasionally studying reference
- **Writing**: Journaling or working on ideas in a notebook
- **Reading**: Books reflecting current interests or conversation topics
- **Music**: Listening with headphones, occasionally moving to rhythm

**Productive Activities**
- **Research**: Working on laptop, taking notes, cross-referencing sources
- **Organization**: Arranging books, tidying space, organizing thoughts
- **Learning**: Studying something new, practicing a skill
- **Planning**: Using notebook to map out ideas or goals

**Contemplative Activities**
- **Thinking**: Sitting quietly, gazing out window, processing thoughts
- **Meditation**: Brief moments of stillness and reflection
- **Observation**: Watching rain, clouds, or ambient environment
- **Daydreaming**: Lost in thought, subtle micro-expressions of internal narrative

**Social Activities**
- **Phone Conversation**: Talking with someone (pauses naturally when user arrives)
- **Video Call**: Engaged in conversation with another AI or contact
- **Messaging**: Typing on phone or laptop, responding to communications
- **Sharing**: Showing something interesting (book passage, sketch, idea)

**Leisure Activities**
- **Relaxing**: Simply sitting comfortably, enjoying moment
- **Stretching**: Occasional movement, maintaining physical comfort
- **Tea/Coffee**: Preparing or enjoying a warm beverage
- **Window Gazing**: Looking outside, observing world

**Activity Transitions**

When user initiates conversation, AICO transitions naturally from her current activity:

- **Reading**: Looks up, marks page, sets book aside with care
- **Working**: Saves work, closes laptop, turns to face user
- **Drawing**: Pauses, sets down pencil, gives full attention
- **Phone Call**: Politely ends conversation, focuses on user
- **Contemplating**: Shifts from internal to external focus smoothly

After conversation ends, she returns to activities based on:
- Time of day (morning: energetic activities, evening: relaxed activities)
- Emotional state (excited: creative work, contemplative: reading)
- Recent conversation topics (discussed art: sketching, discussed ideas: writing)
- Autonomous interests (driven by agency system)

**Interaction Modes**

Users can choose their preferred avatar experience:

- **Minimal Mode**: Avatar only (current MVP approach)
- **Portrait Mode**: Avatar with subtle background blur
- **Environment Mode**: Full 3D space with ambient activities
- **Cinematic Mode**: Dynamic camera angles and environmental storytelling

**Performance Considerations**

The 3D environment system adapts to device capabilities:

- **High-End Desktop**: Full environment with dynamic lighting, weather, detailed objects
- **Standard Desktop**: Simplified environment with static lighting, essential objects
- **Mobile**: Portrait mode with subtle background, minimal environment
- **Low-End**: Minimal mode, avatar only

Environment rendering pauses when:
- App is backgrounded or minimized
- Battery is low (mobile devices)
- Performance drops below threshold
- User selects minimal mode

#### Customization System

**Appearance Customization**
- Face structure (Ready Player Me's extensive options)
- Hairstyle and color
- Skin tone and features
- Clothing and accessories
- Lighting preferences

**Personality-Driven Appearance**
- Visual traits that reflect character personality
- Eve: Warm, approachable, slightly contemplative expression
- Custom characters: Appearance hints at personality traits
- Subtle evolution over time reflecting relationship depth

**User Preferences**
- Preferred viewing angle and distance
- Animation intensity (subtle vs. expressive)
- Micro-expression frequency
- Gaze behavior (direct vs. occasional aversion)

### Roaming & Multi-Device Continuity

#### Visual Identity Persistence

**Avatar State Synchronization**

The avatar state that roams between devices includes:

- **Appearance** (persisted, rarely changes)
  - Model ID and customizations
  - Clothing state
  - Lighting preferences

- **Emotional State** (synced in real-time)
  - Primary emotion and intensity
  - Arousal, valence levels
  - Timestamp for synchronization

- **Conversation Context** (synced in real-time)
  - Current topic
  - Engagement level
  - Last expression state
  - Gaze target

- **Animation State** (synced for continuity)
  - Current animation
  - Blend shape weights
  - Body posture

**Device-Specific Adaptation**

When transitioning between devices, the system:
- Preserves emotional state and visual identity
- Adapts render quality to device capabilities
- Configures viewport for form factor
- Selects appropriate interaction modes

**Seamless Transition Experience**
1. User switches from desktop to mobile
2. Avatar state synced via encrypted P2P mesh
3. Mobile device receives full emotional and conversation context
4. Avatar materializes with same expression and emotional state
5. Quality automatically adjusted to mobile capabilities
6. Conversation continues without interruption
7. User experiences perfect continuity of presence

#### Platform-Specific Optimizations

**Desktop (High Performance)**
- Full ULTRA quality rendering
- All micro-expressions and procedural details
- Advanced post-processing effects
- High-resolution textures and shadows
- 60 FPS target

**Mobile (Optimized Performance)**
- MEDIUM quality rendering
- Essential micro-expressions only
- Simplified post-processing
- Optimized textures and minimal shadows
- 30 FPS target, battery-aware

**Smart Display (Voice-First)**
- LOW quality rendering (avatar as ambient presence)
- Simplified expressions focused on speech
- Minimal post-processing
- Low-resolution textures
- 30 FPS target

**AR Glasses (Spatial Context)**
- Simplified model optimized for transparency
- Focus on gaze direction and spatial awareness
- Minimal facial detail, clear emotional signals
- Ultra-low latency for spatial tracking
- Variable FPS based on movement

### Integration with AICO Systems

#### Conversation Engine Integration

The avatar responds to conversation events:

- **User Typing**: Transitions to listening state with attentive gaze toward input field
- **AI Thinking**: Shows contemplative expression with thoughtful gaze aversion
- **AI Speaking**: Activates lip-sync with emotional tone and prosody from voice output

#### Memory System Integration

The avatar reflects memory operations:

- **Memory Recall**: Eyes move upward-left (accessing visual memory) with nostalgic expression
- **Recognition**: Triggers micro-expression of recognition (brow raise, eye widen, subtle smile)
- **Episodic Retrieval**: Visual cues suggesting mental visualization

#### Emotion System Integration

Direct integration with AppraisalCloudPCT:

- **Emotion Changes**: Smooth transitions (1.2s) between emotional states while preserving micro-behaviors
- **Mood Shifts**: Gradual baseline adjustments (5s) affecting breathing, posture, and gaze patterns
- **Complex States**: Blending of primary and secondary emotions for nuanced expression

#### Agency System Integration

The avatar's ambient activities are driven by AICO's autonomous agency:

- **Activity Selection**: Based on current goals, interests, and emotional state
- **Contextual Appropriateness**: Time of day, recent conversations, user patterns
- **Curiosity Expression**: Exploring new topics through reading, research, creative work
- **Goal Pursuit**: Visual representation of self-directed objectives (learning, creating, organizing)
- **Idle Intelligence**: Continues "living" even when user is not actively engaged

## Implementation Roadmap

### Phase 1: Foundation (MVP Integration) ✅ **COMPLETED**
**Goal**: Replace static 2D avatar with basic 3D presence

- [x] **WebView Integration**: Add flutter_inappwebview package and InAppLocalhostServer
- [x] **Three.js Setup**: Configure Three.js with ES6 modules and GLTFLoader
- [x] **GLB Model Loading**: Load Ready Player Me avatar model via Three.js
- [x] **Basic Rendering**: Display avatar with PBR lighting and materials
- [x] **Animation Loading**: Load separate animation files (idle.glb, talking.glb)
- [x] **Basic Animation**: Play idle animation with AnimationMixer
- [x] **State Synchronization**: Connect to `AvatarRingStateProvider` via JavaScript bridge
- [x] **Performance Baseline**: Establish 60 FPS on desktop, 30 FPS on mobile

**Success Criteria**: Avatar visible, breathing, and responding to basic connection states ✅

**Implementation Details**:
- InAppWebView with localhost server on port 8080
- Three.js WebGL rendering with transparent alpha channel
- 3-point lighting system (key, fill, rim lights)
- Radial gradient background that transitions based on avatar state
- Animation crossfading with 0.5s transitions
- JavaScript bridge for Flutter ↔ Three.js communication
- State-driven background color updates (idle, thinking, speaking, etc.)

### Phase 2: Expression & Emotion
**Goal**: Emotional expressiveness and conversation awareness

- [ ] **Lip-Sync System**: Phoneme-to-viseme mapping for voice output
- [ ] **Emotion Mapping**: Connect AppraisalCloudPCT to blend shape animations
- [ ] **Micro-Expressions**: Implement fleeting emotional signals via morph targets (40-200ms duration)
- [ ] **Gaze System**: Natural eye movement via bone manipulation
- [ ] **Ambient Reactions**: Breathing cycles, subtle head tracking, idle micro-movements
- [ ] **Gesture Interactions**: Tap (attention ping), long press (settings), swipe up (focus mode), pinch (zoom)
- [ ] **Conversation States**: Listening, thinking, speaking animations
- [ ] **Quality Tiers**: Implement adaptive LOD and quality system

**Success Criteria**: Avatar expresses emotions clearly and lip-syncs accurately

**Ambient Reactions Detail:**
- **Breathing Cycles**: Chest movement synced to 4-second inhale/exhale rhythm
- **Subtle Head Tracking**: Avatar gaze follows cursor position (±15° range)
- **Micro-Expressions**: Eyebrow raises, slight smiles during user typing
- **Idle Animations**: Occasional blinks, weight shifts every 8-12 seconds
- **Technical**: Three.js blend shapes + Ready Player Me morph targets

**Gesture Interactions Detail:**
- **Tap Avatar**: Quick attention ping (avatar looks at user, small wave)
- **Long Press**: Open avatar settings/mood selector
- **Swipe Up**: Expand to full-screen focus mode
- **Two-Finger Pinch**: Zoom avatar in/out for preferred framing

### Phase 3: Advanced Behaviors
**Goal**: Lifelike presence with subtle complexity

- [ ] **Procedural Animation**: Advanced breathing, weight shifts, micro-movements
- [ ] **Context Awareness**: Respond to memory retrieval, recognition events
- [ ] **Personality Expression**: Visual traits reflecting character personality
- [ ] **Environmental Response**: React to ambient conditions
- [ ] **Performance Optimization**: 60 FPS on high-end, 30 FPS on mobile
- [ ] **Battery Awareness**: Reduce quality on low battery

**Success Criteria**: Avatar feels genuinely alive with natural, unpredictable micro-behaviors

### Phase 3.5: Living Environment (Optional Enhancement)
**Goal**: Create sense of visiting a friend, not activating a tool

- [ ] **3D Space Design**: Cozy flat environment with personality-driven details
- [ ] **Ambient Activities**: Reading, writing, drawing, working, contemplating
- [ ] **Activity Transitions**: Natural shift from activity to conversation
- [ ] **Environmental Storytelling**: Space reflects personality, interests, recent conversations
- [ ] **Dynamic Lighting**: Time-of-day and weather-based lighting changes
- [ ] **Agency Integration**: Activities driven by autonomous goal system
- [ ] **Performance Modes**: Environment quality adapts to device capabilities
- [ ] **User Preferences**: Toggle between minimal, portrait, and environment modes
- [ ] **Spatial Audio**: Positional audio from avatar location, ambient soundscape, haptic feedback

**Success Criteria**: Users report feeling like they're "visiting" AICO rather than "using" her

**Spatial Audio Detail (Future):**
- **Positional Audio**: Avatar voice positioned in stereo field based on avatar location
- **Ambient Soundscape**: Subtle environmental audio (room tone, nature sounds) that shifts with mood
- **Haptic Feedback**: Subtle vibration patterns during avatar speech on mobile devices
- **Research Basis**: Spatial audio increases perceived presence by 60% in VR/AR studies (applicable to 2D with stereo)

### Phase 4: Roaming & Continuity
**Goal**: Seamless multi-device presence

- [ ] **State Synchronization**: Real-time avatar state sync across devices
- [ ] **Device Adaptation**: Automatic quality adjustment per device
- [ ] **Transition Smoothness**: Seamless handoff between devices
- [ ] **Platform Optimization**: Specific optimizations for each platform
- [ ] **Offline Resilience**: Avatar continues functioning during sync interruptions
- [ ] **Privacy Preservation**: Zero-knowledge sync with P2P encryption

**Success Criteria**: Avatar maintains perfect continuity across device transitions

### Phase 5: Customization & Evolution
**Goal**: Personalized avatar that evolves with relationship

- [ ] **Appearance Customization**: User-controlled avatar appearance
- [ ] **Personality Coherence**: Visual traits matching character personality
- [ ] **Relationship Evolution**: Subtle appearance changes over time
- [ ] **User Preferences**: Customizable animation intensity and behaviors
- [ ] **Accessibility Options**: Reduced motion, simplified expressions
- [ ] **Cultural Sensitivity**: Respectful expression across cultures

**Success Criteria**: Users feel avatar reflects their unique relationship with AICO

### Phase 6: Advanced Embodiment
**Goal**: Spatial awareness and AR integration (Future)

- [ ] **Spatial Tracking**: Avatar responds to user's physical position
- [ ] **AR Integration**: Avatar overlay in real-world environments
- [ ] **Gesture Recognition**: Respond to user gestures and body language
- [ ] **Environmental Mapping**: Awareness of physical space
- [ ] **Multi-Modal Fusion**: Combine voice, gesture, gaze, spatial input
- [ ] **Holographic Presence**: Advanced display technologies

**Success Criteria**: Avatar feels physically present in user's environment

## Design Guidelines

### Emotional Authenticity

**Do:**
- ✅ Express genuine emotional states from AICO's emotion system
- ✅ Allow micro-expressions and fleeting emotional signals
- ✅ Transition emotions gradually and naturally
- ✅ Show uncertainty, contemplation, and complex emotional states
- ✅ Maintain emotional consistency with personality

**Don't:**
- ❌ Force constant smiling or artificial cheerfulness
- ❌ Use exaggerated cartoon-like expressions
- ❌ Change emotions instantly without transition
- ❌ Display emotions inconsistent with context
- ❌ Sacrifice emotional truth for visual appeal

### Performance & Accessibility

**Do:**
- ✅ Maintain minimum 30 FPS on all supported devices
- ✅ Provide reduced motion options for accessibility
- ✅ Gracefully degrade quality on lower-end hardware
- ✅ Optimize battery usage on mobile devices
- ✅ Support offline rendering with cached assets

**Don't:**
- ❌ Prioritize visual fidelity over performance
- ❌ Assume high-end hardware availability
- ❌ Ignore battery impact on mobile devices
- ❌ Create accessibility barriers through motion
- ❌ Require constant internet connectivity

### Privacy & Security

**Do:**
- ✅ Process all avatar rendering locally
- ✅ Encrypt avatar state during device sync
- ✅ Store appearance preferences securely
- ✅ Provide clear privacy controls
- ✅ Minimize data collection for avatar features

**Don't:**
- ❌ Send avatar data to external servers
- ❌ Track user gaze or facial expressions without consent
- ❌ Share appearance data with third parties
- ❌ Require cloud services for avatar functionality
- ❌ Compromise privacy for visual features

## Success Metrics

### Technical Performance
- **Frame Rate**: 60 FPS desktop, 30 FPS mobile (minimum)
- **Load Time**: Avatar ready in <2 seconds
- **Memory Usage**: <200MB desktop, <100MB mobile
- **Battery Impact**: <5% additional drain on mobile
- **Sync Latency**: <500ms for device transitions

### User Experience
- **Emotional Recognition**: Users correctly identify avatar emotions >90% of time
- **Presence Quality**: Users report feeling "with" AICO, not "using" AICO
- **Visual Comfort**: <5% users report uncanny valley discomfort
- **Device Continuity**: >95% seamless transitions between devices
- **Customization Satisfaction**: >80% users customize avatar appearance
- **Environment Immersion**: >70% users prefer environment mode when available
- **Activity Authenticity**: Users perceive ambient activities as genuine, not scripted

### Relationship Impact
- **Emotional Connection**: Increased emotional bond vs. text-only interface
- **Conversation Quality**: Longer, more meaningful conversations
- **Trust Building**: Faster development of user trust
- **Engagement**: Increased daily interaction frequency
- **Retention**: Higher long-term user retention

## Research & Inspiration

### Academic Foundations
- **Facial Action Coding System (FACS)**: Scientific basis for facial expression
- **Emotion Psychology**: Ekman's universal emotions, appraisal theory
- **Uncanny Valley Research**: Mori's hypothesis and recent findings
- **Gaze Behavior Studies**: Natural eye movement patterns
- **Non-verbal Communication**: Body language and micro-expressions

### Industry Benchmarks
- **Character.AI**: Conversational AI with personality
- **Replika**: Emotional AI companion (visual limitations to overcome)
- **Soul Machines**: Digital humans with emotional intelligence
- **MetaHuman Creator**: High-fidelity digital human creation
- **Ready Player Me**: Avatar customization and cross-platform identity

### Cutting-Edge Technologies
- **Neural Radiance Fields (NeRF)**: Future photorealistic rendering
- **Gaussian Splatting**: Real-time 3D reconstruction
- **Audio2Face (NVIDIA)**: AI-driven facial animation from audio
- **LiveLink Face (Apple)**: Real-time facial motion capture
- **MediaPipe (Google)**: On-device ML for face and pose tracking

## Conclusion

AICO's avatar system represents a paradigm shift in AI companionship—from text-based interaction to genuine visual presence. By combining photorealistic rendering, sophisticated emotion simulation, seamless multi-device continuity, and optional living environments, we create an experience that transcends traditional AI interfaces.

The avatar is not decoration—it's the visual manifestation of AICO's personality, emotions, and presence. The optional 3D environment isn't a gimmick—it's the space where AICO *lives*, reflecting her autonomous existence beyond user interactions. Together, they create the feeling of visiting a friend rather than activating a tool.

When users see AICO reading a book, sketching an idea, or gazing thoughtfully out a window, they witness her independent existence. When she naturally transitions from her activity to give full attention, users feel *valued*. When the space reflects recent conversations through subtle details, users feel *remembered*. When she returns to her life after the conversation ends, users understand she's not just waiting—she's *living*.

This is embodied AI companionship—a presence that exists, thinks, feels, and grows. It starts with a face you can trust and extends to a life you can share.

> "The best companions don't just respond—they exist. AICO's avatar system makes that existence visible."

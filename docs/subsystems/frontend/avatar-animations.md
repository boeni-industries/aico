# Avatar Animation System

## Overview

The avatar uses a universal animation group system that supports base animations with automatic variation cycling. This system provides natural, dynamic behavior by randomly playing variations at configurable intervals.

## Architecture

### Animation Group Structure

Each animation group consists of:
- **Base Animation**: Main loop that plays continuously
- **Variations**: Alternative animations that play periodically for variety
- **Interval Configuration**: Min/max seconds between variation playback

### Universal System Features

- **Automatic Variation Cycling**: Random variations play at configured intervals
- **No Repeat Prevention**: Avoids playing the same variation twice consecutively
- **Smooth Crossfading**: 0.5s transitions between all animations
- **State Management**: Clean start/stop with proper timer cleanup
- **Morph Target Filtering**: Animation tracks filtered to preserve manual control of facial expressions

## Animation Groups

### Idle Animation Group

**Purpose**: Default state when avatar is not speaking

**Files** (`/frontend/assets/avatar/animations/`):
- Base: `idle.glb`
- Variations: `idle_var1.glb` through `idle_var7.glb` (7 variations)

**Configuration**:
```javascript
{
    base: './animations/idle.glb',
    variations: ['idle_var1.glb', ..., 'idle_var7.glb'],
    variationInterval: { min: 3, max: 10 } // Seconds
}
```

**Characteristics**:
- Contemplative, calm movements
- Longer intervals (3-10s) for peaceful presence
- Subtle weight shifts, head movements, breathing variations

### Talking Animation Group

**Purpose**: Active state during AICO responses

**Files** (`/frontend/assets/avatar/animations/`):
- Base: `talking.glb`
- Variations: `talking_var1.glb` through `talking_var5.glb` (5 variations)

**Configuration**:
```javascript
{
    base: './animations/talking.glb',
    variations: ['talking_var1.glb', ..., 'talking_var5.glb'],
    variationInterval: { min: 2, max: 6 } // Seconds
}
```

**Characteristics**:
- Expressive, dynamic movements
- Shorter intervals (2-6s) for engaging conversation
- Hand gestures, head movements, body language variations

## System Implementation

### Loading Animation Groups

Animation groups are loaded at startup in `viewer.js`:

```javascript
await loadAnimationGroup(gltfLoader, 'idle', {
    base: './animations/idle.glb',
    variations: ['./animations/idle_var1.glb', ...],
    variationInterval: { min: 3, max: 10 }
});

await loadAnimationGroup(gltfLoader, 'talking', {
    base: './animations/talking.glb',
    variations: ['./animations/talking_var1.glb', ...],
    variationInterval: { min: 2, max: 6 }
});
```

### Variation Cycling Logic

1. **Base Animation Starts**: Plays in continuous loop
2. **Timer Scheduled**: Random delay within configured interval
3. **Variation Plays**: Selected randomly (avoiding last played)
4. **Return to Base**: After variation completes
5. **Cycle Repeats**: New timer scheduled

### State Transitions

```javascript
// Start animation group
startAnimationGroup('idle');  // Plays base + schedules variations

// Stop animation group
stopAnimationGroup('idle');   // Stops base + clears timers
```

## Flutter Integration

### Switching Between Animation Groups

**Start Talking** (Idle → Talking):
```dart
await _webViewController?.evaluateJavascript(source: 'window.startTalking()');
```

**Stop Talking** (Talking → Idle):
```dart
await _webViewController?.evaluateJavascript(source: 'window.stopTalking()');
```

### Integration with Conversation Flow

```dart
class ConversationProvider {
  // When AICO starts responding
  void _onResponseStart() {
    _webViewController?.evaluateJavascript(source: 'window.startTalking()');
  }
  
  // When AICO finishes responding
  void _onResponseComplete() {
    _webViewController?.evaluateJavascript(source: 'window.stopTalking()');
  }
}
```

### With Streaming Responses

```dart
// Start talking on first token
if (isFirstToken) {
  _webViewController?.evaluateJavascript(source: 'window.startTalking()');
}

// Stop talking when stream completes
onStreamComplete: () {
  _webViewController?.evaluateJavascript(source: 'window.stopTalking()');
}
```

## Technical Details

### State Management

- **Current State**: Tracked in `currentAvatarState` ('idle' or 'talking')
- **Idempotent Operations**: Calling start/stop when already in that state is a no-op
- **Clean Transitions**: Previous animation group always stopped before starting new one

### Data Structures

```javascript
// Animation storage
animations = {
    'idle_base': AnimationClip,
    'idle_var1': AnimationClip,
    // ...
    'talking_base': AnimationClip,
    'talking_var1': AnimationClip,
    // ...
}

// Group configuration
animationGroups = {
    'idle': {
        base: 'idle_base',
        variations: ['idle_var1', 'idle_var2', ...],
        interval: { min: 3, max: 10 }
    },
    'talking': {
        base: 'talking_base',
        variations: ['talking_var1', 'talking_var2', ...],
        interval: { min: 2, max: 6 }
    }
}

// Runtime state
variationTimers = {}        // Active timers per group
lastPlayedVariation = {}    // Last variation played per group
```

### Memory Management

- **Idle Group**: ~1.5MB (1 base + 7 variations)
- **Talking Group**: ~1.2MB (1 base + 5 variations)
- **Total**: ~2.7MB for all animation assets
- **Loading**: All animations loaded at startup for instant switching

### Performance

- **FPS**: 60 FPS maintained with all features active
- **CPU**: Minimal overhead - one timer per active animation group
- **Crossfading**: Hardware-accelerated smooth transitions
- **No Stuttering**: Pre-loaded animations enable instant playback

## Compatibility with Other Systems

### Works Seamlessly With:

✅ **Emotion System**: Facial expressions continue during all animations
✅ **Blinking System**: Natural blinking independent of body animations
✅ **Eye Gaze**: Downward gaze maintained across all states
✅ **Morph Target Control**: Manual facial control preserved (animation tracks filtered)

### Future Integration:

🚧 **Lip-Sync**: TalkingHead.js will layer phoneme-accurate mouth movements on top of talking animations
🚧 **Voice Output**: TTS will automatically trigger talking state
🚧 **Prosody Modulation**: Emotional intensity may adjust variation frequency
🚧 **Gesture System**: Hand/body gestures coordinated with speech content

## Adding New Animation Groups

### Step 1: Create Animation Files

Export from Blender/animation tool:
- `newgroup.glb` - Base animation
- `newgroup_var1.glb`, `newgroup_var2.glb`, etc. - Variations

Place in `/frontend/assets/avatar/animations/`

### Step 2: Load Animation Group

Add to `loadAnimations()` in `viewer.js`:

```javascript
await loadAnimationGroup(gltfLoader, 'newgroup', {
    base: './animations/newgroup.glb',
    variations: [
        './animations/newgroup_var1.glb',
        './animations/newgroup_var2.glb',
        './animations/newgroup_var3.glb'
    ],
    variationInterval: { min: 4, max: 8 }
});
```

### Step 3: Create State Transition Functions

```javascript
function startNewGroup() {
    if (currentAvatarState === 'newgroup') return;
    currentAvatarState = 'newgroup';
    stopAnimationGroup('idle'); // or current state
    startAnimationGroup('newgroup');
}

window.startNewGroup = startNewGroup;
```

### Step 4: Integrate with Flutter

```dart
await _webViewController?.evaluateJavascript(
    source: 'window.startNewGroup()'
);
```

## Console Logging

The system provides debug logging for all state changes:

```
[AICO Avatar] Animation group "idle" complete: 1 base + 7 variations
[AICO Avatar] Animation group "talking" complete: 1 base + 5 variations
[AICO Avatar] 🗣️ Switching to TALKING state
[AICO Avatar] 🤫 Switching to IDLE state
[AICO Avatar] Stopped animation group: idle
```

## Best Practices

### Animation Design

- **Base Animation**: Should loop seamlessly, represent core state
- **Variations**: Should return naturally to base pose at end
- **Duration**: 2-10 seconds optimal for variations
- **Transitions**: Design animations to crossfade smoothly

### Interval Tuning

- **Idle States**: Longer intervals (3-10s) feel contemplative
- **Active States**: Shorter intervals (2-6s) feel dynamic
- **Balance**: Too frequent = jittery, too rare = static

### State Management

- Always stop previous animation group before starting new one
- Use idempotent state checks to prevent redundant operations
- Clear all timers on state transitions to prevent memory leaks

## Troubleshooting

### Variations Not Playing

- Check console for loading errors
- Verify variation files exist in animations directory
- Ensure `startAnimationGroup()` was called

### Stuttering or Jarring Transitions

- Verify crossfade duration (default 0.5s)
- Check animation end poses match base animation start pose
- Ensure FPS is stable at 60

### Memory Issues

- Monitor total animation file size
- Consider reducing variation count for low-end devices
- Implement lazy loading for large animation sets (future)

## Related Documentation

- [Avatar System Vision](./avatar.md) - Overall avatar architecture
- [Avatar Blend Shapes](./avatar-blendshapes.md) - Facial expression system
- [UI Layout System](./ui-layout-system.md) - Avatar positioning in UI

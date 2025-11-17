# Avatar Blendshapes (Morph Targets)

## Overview

The AICO avatar uses Ready Player Me with ARKit-compatible blendshapes (morph targets) for facial expressions and eye gaze control. These work independently from skeletal animations, allowing real-time facial control during idle, talking, and other body animations.

## Avatar Configuration

**Current Avatar URL:**
```
https://models.readyplayer.me/6918f89f132e61458ce01a74.glb?morphTargets=ARKit
```

**File Location:**
```
/frontend/assets/avatar/models/avatar.glb
```

**File Size:** ~3x larger than base avatar (ARKit adds 52 morph targets)

## Available Blendshapes (52 Total)

### Eye Gaze Control (8 morph targets)

These control where the avatar looks. Values range from 0.0 (no influence) to 1.0 (full influence).

| Morph Target | Description | Usage Example |
|--------------|-------------|---------------|
| `eyeLookUpLeft` | Left eye looks up | `influences[dict['eyeLookUpLeft']] = 0.5` |
| `eyeLookUpRight` | Right eye looks up | `influences[dict['eyeLookUpRight']] = 0.5` |
| `eyeLookDownLeft` | Left eye looks down | `influences[dict['eyeLookDownLeft']] = 0.4` |
| `eyeLookDownRight` | Right eye looks down | `influences[dict['eyeLookDownRight']] = 0.4` |
| `eyeLookInLeft` | Left eye looks inward (toward nose) | `influences[dict['eyeLookInLeft']] = 0.3` |
| `eyeLookInRight` | Right eye looks inward (toward nose) | `influences[dict['eyeLookInRight']] = 0.3` |
| `eyeLookOutLeft` | Left eye looks outward (away from nose) | `influences[dict['eyeLookOutLeft']] = 0.3` |
| `eyeLookOutRight` | Right eye looks outward (away from nose) | `influences[dict['eyeLookOutRight']] = 0.3` |

**Current Implementation:**
- Camera at Y=0.85m (chest level), eyes at Y=1.6m (eye level)
- Avatar uses `eyeLookDownLeft/Right` at 0.4 influence for natural eye contact with camera
- Applied every frame in `applyEyeGaze()` function

### Eye Expressions (6 morph targets)

| Morph Target | Description | Typical Range |
|--------------|-------------|---------------|
| `eyeBlinkLeft` | Left eye blink | 0.0 - 1.0 |
| `eyeBlinkRight` | Right eye blink | 0.0 - 1.0 |
| `eyeSquintLeft` | Left eye squint | 0.0 - 0.7 |
| `eyeSquintRight` | Right eye squint | 0.0 - 0.7 |
| `eyeWideLeft` | Left eye wide open (surprise) | 0.0 - 0.8 |
| `eyeWideRight` | Right eye wide open (surprise) | 0.0 - 0.8 |

### Eyebrow Control (5 morph targets)

| Morph Target | Description | Typical Range |
|--------------|-------------|---------------|
| `browDownLeft` | Left eyebrow down (frown/concern) | 0.0 - 0.6 |
| `browDownRight` | Right eyebrow down (frown/concern) | 0.0 - 0.6 |
| `browInnerUp` | Inner eyebrows up (sadness/concern) | 0.0 - 0.7 |
| `browOuterUpLeft` | Left outer eyebrow up (surprise) | 0.0 - 0.8 |
| `browOuterUpRight` | Right outer eyebrow up (surprise) | 0.0 - 0.8 |

### Mouth Expressions (24 morph targets)

#### Basic Mouth Shapes
| Morph Target | Description | Typical Range |
|--------------|-------------|---------------|
| `jawOpen` | Open jaw (talking, surprise) | 0.0 - 0.7 |
| `mouthClose` | Close mouth tightly | 0.0 - 0.5 |
| `mouthFunnel` | Mouth funnel shape (O shape) | 0.0 - 0.8 |
| `mouthPucker` | Pucker lips (kiss shape) | 0.0 - 0.7 |

#### Smiles and Frowns
| Morph Target | Description | Typical Range |
|--------------|-------------|---------------|
| `mouthSmileLeft` | Left side smile | 0.0 - 1.0 |
| `mouthSmileRight` | Right side smile | 0.0 - 1.0 |
| `mouthFrownLeft` | Left side frown | 0.0 - 0.7 |
| `mouthFrownRight` | Right side frown | 0.0 - 0.7 |

#### Mouth Movement
| Morph Target | Description | Typical Range |
|--------------|-------------|---------------|
| `mouthLeft` | Mouth moves left | 0.0 - 0.5 |
| `mouthRight` | Mouth moves right | 0.0 - 0.5 |
| `mouthUpperUpLeft` | Left upper lip up | 0.0 - 0.6 |
| `mouthUpperUpRight` | Right upper lip up | 0.0 - 0.6 |
| `mouthLowerDownLeft` | Left lower lip down | 0.0 - 0.6 |
| `mouthLowerDownRight` | Right lower lip down | 0.0 - 0.6 |
| `mouthStretchLeft` | Stretch mouth left | 0.0 - 0.5 |
| `mouthStretchRight` | Stretch mouth right | 0.0 - 0.5 |

#### Lip Control
| Morph Target | Description | Typical Range |
|--------------|-------------|---------------|
| `mouthRollLower` | Roll lower lip inward | 0.0 - 0.6 |
| `mouthRollUpper` | Roll upper lip inward | 0.0 - 0.6 |
| `mouthShrugLower` | Lower lip shrug | 0.0 - 0.5 |
| `mouthShrugUpper` | Upper lip shrug | 0.0 - 0.5 |
| `mouthPressLeft` | Press left side of mouth | 0.0 - 0.5 |
| `mouthPressRight` | Press right side of mouth | 0.0 - 0.5 |
| `mouthDimpleLeft` | Left dimple | 0.0 - 0.7 |
| `mouthDimpleRight` | Right dimple | 0.0 - 0.7 |

### Jaw Control (3 morph targets)

| Morph Target | Description | Typical Range |
|--------------|-------------|---------------|
| `jawForward` | Jaw moves forward | 0.0 - 0.5 |
| `jawLeft` | Jaw moves left | 0.0 - 0.4 |
| `jawRight` | Jaw moves right | 0.0 - 0.4 |

### Cheek Control (3 morph targets)

| Morph Target | Description | Typical Range |
|--------------|-------------|---------------|
| `cheekPuff` | Puff both cheeks | 0.0 - 0.8 |
| `cheekSquintLeft` | Left cheek squint (smile) | 0.0 - 0.6 |
| `cheekSquintRight` | Right cheek squint (smile) | 0.0 - 0.6 |

### Nose Control (2 morph targets)

| Morph Target | Description | Typical Range |
|--------------|-------------|---------------|
| `noseSneerLeft` | Left nostril flare (disgust) | 0.0 - 0.5 |
| `noseSneerRight` | Right nostril flare (disgust) | 0.0 - 0.5 |

### Tongue (1 morph target)

| Morph Target | Description | Typical Range |
|--------------|-------------|---------------|
| `tongueOut` | Stick tongue out | 0.0 - 1.0 |

## Code Usage

### Accessing Morph Targets

```javascript
// Find meshes with morph targets
let eyeMeshes = [];
avatar.traverse((node) => {
    if (node.isMesh && node.morphTargetInfluences) {
        eyeMeshes.push(node);
    }
});

// Apply morph target by name
eyeMeshes.forEach(mesh => {
    const dict = mesh.morphTargetDictionary;
    const influences = mesh.morphTargetInfluences;
    
    // Set specific morph target
    if (dict['mouthSmileLeft'] !== undefined) {
        influences[dict['mouthSmileLeft']] = 0.8; // 80% smile
    }
});
```

### Affected Meshes

The avatar has 4 meshes with morph targets:
1. **EyeLeft** - All 52 morph targets
2. **EyeRight** - All 52 morph targets
3. **Wolf3D_Head** - All 52 morph targets
4. **Wolf3D_Teeth** - All 52 morph targets

**Important:** Apply morph targets to ALL meshes for consistent facial expressions.

### Integration with Animations

Morph targets work **independently** from skeletal animations:
- Skeletal animations (idle, talking) control body and head bones
- Morph targets control facial mesh deformations
- Both can run simultaneously without conflict

**Best Practice:** Apply morph targets **after** animation mixer updates:

```javascript
function animate() {
    requestAnimationFrame(animate);
    
    const delta = clock.getDelta();
    
    // Update skeletal animations first
    if (mixer) {
        mixer.update(delta);
    }
    
    // Apply morph targets after (overrides animation facial expressions)
    applyFacialExpressions();
    
    renderer.render(scene, camera);
}
```

## Common Expression Combinations

### Happiness
```javascript
influences[dict['mouthSmileLeft']] = 0.8;
influences[dict['mouthSmileRight']] = 0.8;
influences[dict['cheekSquintLeft']] = 0.5;
influences[dict['cheekSquintRight']] = 0.5;
influences[dict['browOuterUpLeft']] = 0.3;
influences[dict['browOuterUpRight']] = 0.3;
```

### Sadness
```javascript
influences[dict['mouthFrownLeft']] = 0.6;
influences[dict['mouthFrownRight']] = 0.6;
influences[dict['browInnerUp']] = 0.7;
influences[dict['browDownLeft']] = 0.4;
influences[dict['browDownRight']] = 0.4;
```

### Surprise
```javascript
influences[dict['eyeWideLeft']] = 0.8;
influences[dict['eyeWideRight']] = 0.8;
influences[dict['browOuterUpLeft']] = 0.8;
influences[dict['browOuterUpRight']] = 0.8;
influences[dict['jawOpen']] = 0.5;
influences[dict['mouthFunnel']] = 0.4;
```

### Anger
```javascript
influences[dict['browDownLeft']] = 0.6;
influences[dict['browDownRight']] = 0.6;
influences[dict['eyeSquintLeft']] = 0.5;
influences[dict['eyeSquintRight']] = 0.5;
influences[dict['mouthFrownLeft']] = 0.4;
influences[dict['mouthFrownRight']] = 0.4;
influences[dict['jawForward']] = 0.3;
```

### Thinking/Concentration
```javascript
influences[dict['eyeSquintLeft']] = 0.3;
influences[dict['eyeSquintRight']] = 0.3;
influences[dict['browDownLeft']] = 0.3;
influences[dict['browDownRight']] = 0.3;
influences[dict['mouthPucker']] = 0.2;
```

## Future Use Cases

### Lip Sync for Speech
Use mouth morph targets synchronized with audio phonemes:
- **A/E sounds:** `jawOpen`, `mouthFunnel`
- **O sounds:** `mouthPucker`, `mouthFunnel`
- **M/B/P sounds:** `mouthClose`, `mouthPressLeft/Right`
- **F/V sounds:** `mouthRollLower`, `mouthUpperUpLeft/Right`

### Emotional State Indicators
Map conversation sentiment to facial expressions:
- Positive sentiment → smile blend
- Negative sentiment → frown blend
- Questioning → eyebrow raise
- Listening → subtle eye movements

### Idle Micro-Expressions
Add subtle life-like movements:
- Random blinks every 3-5 seconds
- Occasional eyebrow raises
- Slight mouth movements
- Eye gaze variations

### User Interaction Feedback
Visual feedback for user actions:
- User speaks → avatar shows listening expression
- Processing → thinking expression
- Response ready → slight smile, eye contact

## Performance Considerations

- **Morph Target Count:** 52 per mesh × 4 meshes = 208 total influences
- **Update Frequency:** Every frame (60 FPS)
- **Performance Impact:** Minimal on modern hardware
- **File Size Impact:** ~3x larger GLB file (worth it for expressiveness)

## References

- [Ready Player Me ARKit Documentation](https://docs.readyplayer.me/ready-player-me/api-reference/avatars/morph-targets/apple-arkit)
- [Apple ARKit Face Tracking](https://developer.apple.com/documentation/arkit/arfaceanchor/blendshapelocation)
- [Three.js Morph Targets](https://threejs.org/docs/#api/en/objects/Mesh.morphTargetInfluences)

## Version History

- **2025-11-17:** Initial documentation with full ARKit blendshape set
- Avatar ID: `6918f89f132e61458ce01a74`
- Implementation: Eye gaze control for camera eye contact

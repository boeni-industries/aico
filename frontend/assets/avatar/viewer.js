import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

// Scene setup
let scene, camera, renderer, mixer, clock;
let avatar, currentAction;
let animations = {};
let eyeMeshes = []; // Store meshes with eye morph targets

// Animation variation system
let animationGroups = {}; // Stores animation groups with their variations
let variationTimers = {}; // Stores timers for each animation group
let lastPlayedVariation = {}; // Tracks last played variation per group

// Blinking system
let blinkInterval = null;
let isBlinking = false;

// Emotion expression system
let currentEmotion = 'neutral';
let targetEmotionValues = {};
let currentEmotionValues = {};
const emotionTransitionSpeed = 0.05; // Smooth transition speed

// Lip-sync system (pure Web Audio API frequency analysis)
let audioContext;
let audioAnalyser;
let audioSource;
let audioElement = null; // Reference to audio element
let frequencyData; // Buffer for frequency analysis
let lipSyncEnabled = false;
let currentViseme = 'sil';
let lipSyncFrameTime = 0;
const MAX_LIPSYNC_TIME_MS = 2; // Performance budget: 2ms max per frame

// Initialize the scene
function init() {
    console.log('[AICO Avatar] Initializing...');
    
    // Create scene
    scene = new THREE.Scene();
    scene.background = null; // Transparent background - let body gradient show through
    
    // Create camera
    camera = new THREE.PerspectiveCamera(
        42, // Original FOV - maintain subject size
        window.innerWidth / window.innerHeight,
        0.1,
        1000
    );
    camera.position.set(0, 1.6, 3.1); // Eye level (1.6m), further back (2.7m) for full body with clearance
    camera.lookAt(0, 0.85, 0); // Look at torso to center full body in frame
    
    // Create renderer with proper transparency settings
    renderer = new THREE.WebGLRenderer({ 
        antialias: true,
        alpha: true,
        premultipliedAlpha: false, // Critical for true transparency
        powerPreference: 'high-performance'
    });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0x000000, 0); // Fully transparent background
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.0;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    
    document.getElementById('avatar-container').appendChild(renderer.domElement);
    
    // Setup 3-point lighting
    setupLighting();
    
    // Animation clock
    clock = new THREE.Clock();
    
    // Load avatar and animations
    loadAvatar();
    
    // Handle window resize
    window.addEventListener('resize', onWindowResize, false);
    
    // Initialize lip-sync system
    initLipSync();
    
    // Start render loop
    animate();
    
    console.log('[AICO Avatar] Scene initialized');
}

// Setup 3-point lighting system
function setupLighting() {
    // Key Light (main light from front-right)
    const keyLight = new THREE.DirectionalLight(0xffffff, 2.5);
    keyLight.position.set(2, 3, 3);
    keyLight.castShadow = true;
    keyLight.shadow.mapSize.width = 2048;
    keyLight.shadow.mapSize.height = 2048;
    keyLight.shadow.camera.near = 0.5;
    keyLight.shadow.camera.far = 10;
    scene.add(keyLight);
    
    // Fill Light (softer light from left to fill shadows)
    const fillLight = new THREE.DirectionalLight(0xb0c4de, 1.2);
    fillLight.position.set(-2, 2, 2);
    scene.add(fillLight);
    
    // Rim/Back Light (from behind to create edge definition)
    const rimLight = new THREE.DirectionalLight(0xffffff, 1.5);
    rimLight.position.set(0, 2, -2); // Behind and above
    scene.add(rimLight);
    
    // Ambient light for overall scene illumination
    const ambientLight = new THREE.AmbientLight(0x404040, 0.8);
    scene.add(ambientLight);
}

// Load avatar model
async function loadAvatar() {
    const loader = new GLTFLoader();
    
    try {
        console.log('[AICO Avatar] Loading avatar model from: ./models/avatar.glb');
        
        // Load main avatar
        const avatarGltf = await loader.loadAsync('./models/avatar.glb');
        avatar = avatarGltf.scene;
        
        // Position avatar
        avatar.position.set(0, 0, 0);
        avatar.scale.set(1, 1, 1);
        
        // Enable shadows and collect eye meshes for gaze control
        avatar.traverse((node) => {
            if (node.isMesh) {
                node.castShadow = true;
                node.receiveShadow = true;
            }
        });
        
        // Find and store eye meshes for morph target control
        avatar.traverse((node) => {
            if (node.isMesh && node.morphTargetDictionary && node.morphTargetInfluences) {
                const morphTargets = Object.keys(node.morphTargetDictionary);
                const hasEyeMorphs = morphTargets.some(name => 
                    name.toLowerCase().includes('eye') || 
                    name.toLowerCase().includes('blink')
                );
                if (hasEyeMorphs) {
                    eyeMeshes.push(node);
                    console.log('[AICO Avatar] Eye mesh:', node.name, '- Morph targets:', morphTargets.join(', '));
                }
            }
        });
        
        scene.add(avatar);
        
        // Start blinking if eye meshes found
        if (eyeMeshes.length > 0) {
            startBlinking();
        }
        
        // Load animations
        await loadAnimations();
        
        document.getElementById('loading').classList.add('hidden');
        
        if (window.flutter_inappwebview) {
            window.flutter_inappwebview.callHandler('ready', { status: 'loaded' });
        }
        
        console.log('[AICO Avatar] Avatar fully loaded and ready');
        
    } catch (error) {
        console.error('[AICO Avatar] Error loading avatar:', error.message);
        document.getElementById('loading').innerHTML = 
            `<div style="color: #ff6b6b;">Error loading avatar<br/><small>${error.message}</small></div>`;
    }
}

// Load animation files
async function loadAnimations() {
    const gltfLoader = new GLTFLoader();
    
    try {
        mixer = new THREE.AnimationMixer(avatar);
        
        await loadAnimationGroup(gltfLoader, 'idle', {
            base: './animations/idle.glb',
            variations: [
                './animations/idle_var1.glb',
                './animations/idle_var2.glb',
                './animations/idle_var3.glb',
                './animations/idle_var4.glb',
                './animations/idle_var5.glb',
                './animations/idle_var6.glb',
                './animations/idle_var7.glb'
            ],
            variationInterval: { min: 3, max: 10 } // Random seconds between variations
        });
        
        await loadAnimationGroup(gltfLoader, 'talking', {
            base: './animations/talking.glb',
            variations: [
                './animations/talking_var1.glb',
                './animations/talking_var2.glb',
                './animations/talking_var3.glb',
                './animations/talking_var4.glb',
                './animations/talking_var5.glb'
            ],
            variationInterval: { min: 2, max: 6 } // Shorter intervals for talking variations
        });
        
        // Disable morph target tracks in all animations to allow manual control
        for (const name in animations) {
            const clip = animations[name];
            clip.tracks = clip.tracks.filter(track => !track.name.includes('morphTarget'));
        }
        
        // Start idle animation group with variations
        if (animationGroups.idle) {
            startAnimationGroup('idle');
        }
        
        console.log('[AICO Avatar] Animations ready:', Object.keys(animations).length, 'clips loaded');
        
    } catch (error) {
        console.error('[AICO Avatar] Error in loadAnimations():', error.message);
        document.getElementById('loading').innerHTML = 
            `<div style="color: #ff6b6b;">Error loading animations<br/><small>${error.message}</small></div>`;
    }
}

// Load animation group (base + variations)
async function loadAnimationGroup(loader, groupName, config) {
    try {
        const baseGltf = await loader.loadAsync(config.base);
        
        if (!baseGltf.animations || baseGltf.animations.length === 0) {
            console.warn(`[AICO Avatar] No animation found in base file: ${config.base}`);
            return;
        }
        
        const baseAnimName = `${groupName}_base`;
        animations[baseAnimName] = baseGltf.animations[0];
        
        const variations = [];
        for (let i = 0; i < config.variations.length; i++) {
            try {
                const varGltf = await loader.loadAsync(config.variations[i]);
                if (varGltf.animations && varGltf.animations.length > 0) {
                    const varAnimName = `${groupName}_var${i + 1}`;
                    animations[varAnimName] = varGltf.animations[0];
                    variations.push(varAnimName);
                }
            } catch (error) {
                console.warn(`[AICO Avatar] Failed to load variation ${i + 1}`);
            }
        }
        
        // Store animation group configuration
        animationGroups[groupName] = {
            base: baseAnimName,
            variations: variations,
            interval: config.variationInterval || { min: 3, max: 10 }
        };
        
        console.log(`[AICO Avatar] Animation group "${groupName}" complete: 1 base + ${variations.length} variations`);
        
    } catch (error) {
        console.error(`[AICO Avatar] Failed to load animation group "${groupName}":`, error.message);
        throw error;
    }
}

// Start animation group with automatic variation cycling
function startAnimationGroup(groupName) {
    const group = animationGroups[groupName];
    if (!group) return;
    
    playAnimation(group.base);
    scheduleNextVariation(groupName);
}

// Schedule next variation for an animation group
function scheduleNextVariation(groupName) {
    const group = animationGroups[groupName];
    if (!group || group.variations.length === 0) return;
    
    const delay = (group.interval.min + Math.random() * (group.interval.max - group.interval.min)) * 1000;
    
    variationTimers[groupName] = setTimeout(() => {
        playRandomVariation(groupName);
    }, delay);
}

// Play random variation from group (avoiding last played)
function playRandomVariation(groupName) {
    const group = animationGroups[groupName];
    if (!group || group.variations.length === 0) return;
    
    let variation;
    do {
        variation = group.variations[Math.floor(Math.random() * group.variations.length)];
    } while (variation === lastPlayedVariation[groupName] && group.variations.length > 1);
    
    lastPlayedVariation[groupName] = variation;
    playAnimation(variation);
    
    const variationDuration = animations[variation].duration * 1000;
    const timeout = setTimeout(() => {
        playAnimation(group.base);
        
        // For talking: chain immediately if still talking, otherwise schedule with delay
        if (groupName === 'talking' && isTalkingContinuous) {
            // Continuous chaining for talking - play next variation immediately
            playRandomVariation(groupName);
        } else {
            // Normal delayed scheduling for idle
            scheduleNextVariation(groupName);
        }
    }, variationDuration);
    
    // Store timeout for talking so we can cancel it on stopTalking()
    if (groupName === 'talking') {
        talkingChainTimeout = timeout;
    }
}

// Stop animation group variation cycling
function stopAnimationGroup(groupName) {
    if (variationTimers[groupName]) {
        clearTimeout(variationTimers[groupName]);
        delete variationTimers[groupName];
        console.log(`[AICO Avatar] Stopped animation group: ${groupName}`);
    }
}

// Play animation by name
function playAnimation(name) {
    if (!mixer || !animations[name]) return;
    
    const clip = animations[name];
    const action = mixer.clipAction(clip);
    
    if (currentAction === action && action.isRunning()) return;
    
    if (currentAction && currentAction !== action) {
        currentAction.fadeOut(0.5);
    }
    
    action.reset();
    action.fadeIn(0.5);
    action.setLoop(THREE.LoopRepeat);
    action.play();
    
    currentAction = action;
}

// Blinking system
function startBlinking() {
    if (blinkInterval) return;
    
    const blink = () => {
        if (isBlinking || eyeMeshes.length === 0) return;
        
        isBlinking = true;
        const blinkDuration = 180; // ms - natural blink duration
        const startTime = Date.now();
        
        const animateBlink = () => {
            const elapsed = Date.now() - startTime;
            const progress = Math.min(elapsed / blinkDuration, 1);
            
            // Natural blink curve: fast close, brief pause, slower open
            let blinkValue;
            if (progress < 0.3) {
                // Fast closing phase (0-54ms)
                blinkValue = progress / 0.3;
            } else if (progress < 0.4) {
                // Fully closed pause (54-72ms)
                blinkValue = 1.0;
            } else {
                // Slower opening phase (72-180ms)
                blinkValue = 1.0 - ((progress - 0.4) / 0.6);
            }
            
            eyeMeshes.forEach(mesh => {
                const dict = mesh.morphTargetDictionary;
                const influences = mesh.morphTargetInfluences;
                
                // ARKit standard blink morph targets
                if (dict['eyeBlinkLeft'] !== undefined) {
                    influences[dict['eyeBlinkLeft']] = blinkValue;
                }
                if (dict['eyeBlinkRight'] !== undefined) {
                    influences[dict['eyeBlinkRight']] = blinkValue;
                }
            });
            
            if (progress < 1) {
                requestAnimationFrame(animateBlink);
            } else {
                isBlinking = false;
            }
        };
        
        animateBlink();
    };
    
    // Blink every 2-6 seconds randomly
    const scheduleNextBlink = () => {
        const delay = 2000 + Math.random() * 4000;
        blinkInterval = setTimeout(() => {
            blink();
            scheduleNextBlink();
        }, delay);
    };
    
    scheduleNextBlink();
}

function stopBlinking() {
    if (blinkInterval) {
        clearTimeout(blinkInterval);
        blinkInterval = null;
    }
    isBlinking = false;
}

// Emotion expression system - matches AICO's canonical emotion labels
const emotionPresets = {
    // Baseline states
    neutral: {
        // Completely relaxed, no expression
    },
    calm: {
        mouthSmileLeft: 0.1,
        mouthSmileRight: 0.1,
        eyeSquintLeft: 0.1,
        eyeSquintRight: 0.1
    },
    
    // Engaged/positive states
    curious: {
        browOuterUpLeft: 0.4,
        browOuterUpRight: 0.4,
        eyeWideLeft: 0.3,
        eyeWideRight: 0.3,
        mouthSmileLeft: 0.2,
        mouthSmileRight: 0.2
    },
    playful: {
        mouthSmileLeft: 0.6,
        mouthSmileRight: 0.6,
        cheekSquintLeft: 0.3,
        cheekSquintRight: 0.3,
        browOuterUpLeft: 0.3,
        browOuterUpRight: 0.3,
        eyeWideLeft: 0.2,
        eyeWideRight: 0.2
    },
    
    // Supportive/caring states
    warm_concern: {
        browInnerUp: 0.3,
        mouthSmileLeft: 0.3,
        mouthSmileRight: 0.3,
        eyeSquintLeft: 0.2,
        eyeSquintRight: 0.2
    },
    protective: {
        browDownLeft: 0.3,
        browDownRight: 0.3,
        mouthSmileLeft: 0.2,
        mouthSmileRight: 0.2,
        eyeSquintLeft: 0.3,
        eyeSquintRight: 0.3
    },
    
    // Active/engaged states
    focused: {
        eyeSquintLeft: 0.3,
        eyeSquintRight: 0.3,
        browDownLeft: 0.2,
        browDownRight: 0.2
    },
    encouraging: {
        mouthSmileLeft: 0.6,
        mouthSmileRight: 0.6,
        browOuterUpLeft: 0.4,
        browOuterUpRight: 0.4,
        eyeWideLeft: 0.2,
        eyeWideRight: 0.2
    },
    reassuring: {
        mouthSmileLeft: 0.5,
        mouthSmileRight: 0.5,
        browInnerUp: 0.2,
        eyeSquintLeft: 0.2,
        eyeSquintRight: 0.2
    },
    
    // Reflective/subdued states
    apologetic: {
        browInnerUp: 0.5,
        mouthFrownLeft: 0.2,
        mouthFrownRight: 0.2,
        eyeSquintLeft: 0.2,
        eyeSquintRight: 0.2
    },
    tired: {
        eyeSquintLeft: 0.4,
        eyeSquintRight: 0.4,
        browDownLeft: 0.2,
        browDownRight: 0.2,
        mouthFrownLeft: 0.1,
        mouthFrownRight: 0.1
    },
    reflective: {
        eyeSquintLeft: 0.2,
        eyeSquintRight: 0.2,
        browDownLeft: 0.2,
        browDownRight: 0.2,
        mouthPucker: 0.1
    }
};

// Set emotion expression
function setEmotion(emotion) {
    if (!emotionPresets[emotion]) {
        console.warn(`[AICO Avatar] Unknown emotion: ${emotion}`);
        return;
    }
    
    currentEmotion = emotion;
    targetEmotionValues = { ...emotionPresets[emotion] };
    console.log(`[AICO Avatar] Emotion set to: ${emotion}`);
}

// Apply emotion expressions with smooth transitions
function applyEmotionExpression() {
    if (eyeMeshes.length === 0) return;
    
    // Smoothly interpolate current values toward target values
    for (const morphTarget in targetEmotionValues) {
        const target = targetEmotionValues[morphTarget];
        const current = currentEmotionValues[morphTarget] || 0;
        const newValue = current + (target - current) * emotionTransitionSpeed;
        currentEmotionValues[morphTarget] = newValue;
    }
    
    // Reset any morph targets not in current emotion
    for (const morphTarget in currentEmotionValues) {
        if (!(morphTarget in targetEmotionValues)) {
            const current = currentEmotionValues[morphTarget];
            const newValue = current * (1 - emotionTransitionSpeed);
            currentEmotionValues[morphTarget] = newValue;
            if (Math.abs(newValue) < 0.01) {
                delete currentEmotionValues[morphTarget];
            }
        }
    }
    
    // Apply to all eye meshes
    eyeMeshes.forEach(mesh => {
        const dict = mesh.morphTargetDictionary;
        const influences = mesh.morphTargetInfluences;
        
        for (const morphTarget in currentEmotionValues) {
            if (dict[morphTarget] !== undefined) {
                influences[dict[morphTarget]] = currentEmotionValues[morphTarget];
            }
        }
    });
}

// Expose setEmotion to Flutter
window.setAvatarEmotion = setEmotion;

// Avatar state management (idle vs talking)
let currentAvatarState = 'idle';
let isTalkingContinuous = false; // Flag for continuous talking animation chaining
let talkingChainTimeout = null; // Track the timeout for talking animation chaining

// Start continuous talking animation (no delays between variations)
function startTalkingContinuous() {
    const group = animationGroups.talking;
    if (!group) return;
    
    // Play base animation first
    playAnimation(group.base);
    
    // Immediately start chaining variations
    if (group.variations.length > 0) {
        playRandomVariation('talking');
    }
}

// Switch to talking state
function startTalking() {
    if (currentAvatarState === 'talking') return;
    
    console.log('[AICO Avatar] 🗣️ Switching to TALKING state');
    currentAvatarState = 'talking';
    isTalkingContinuous = true; // Enable continuous chaining
    
    // Stop idle animation group
    stopAnimationGroup('idle');
    
    // Start talking animation group with continuous chaining
    if (animationGroups.talking) {
        startTalkingContinuous();
    } else {
        console.warn('[AICO Avatar] Talking animation group not loaded');
    }
    
    // Enable lip-sync for this talking session
    if (lipSyncEnabled) {
        console.log('[AICO Avatar] 🎤 Lip-sync enabled for talking');
    }
}

// Switch to idle state
function stopTalking() {
    if (currentAvatarState === 'idle') return;
    
    console.log('[AICO Avatar] 🤫 Switching to IDLE state - IMMEDIATE transition');
    currentAvatarState = 'idle';
    isTalkingContinuous = false; // Disable continuous chaining
    
    // Cancel any pending talking animation chain
    if (talkingChainTimeout) {
        clearTimeout(talkingChainTimeout);
        talkingChainTimeout = null;
        console.log('[AICO Avatar] Cancelled pending talking animation');
    }
    
    // Stop talking animation group
    stopAnimationGroup('talking');
    
    // Reset lip-sync to neutral mouth position
    resetLipSync();
    
    // IMMEDIATELY transition to idle (crossfade will handle smooth transition)
    if (animationGroups.idle) {
        const group = animationGroups.idle;
        playAnimation(group.base); // This will crossfade from current talking animation
        scheduleNextVariation('idle'); // Resume normal idle variation scheduling
    } else {
        console.warn('[AICO Avatar] Idle animation group not loaded');
    }
}

// Expose talking state functions to Flutter
window.startTalking = startTalking;
window.stopTalking = stopTalking;

// Apply eye gaze to look at camera
function applyEyeGaze() {
    if (eyeMeshes.length === 0) return;
    
    // Subtle downward gaze for natural eye contact (camera at eye level)
    const lookDownAmount = 0.3; // 30% influence for natural, warm eye contact
    
    eyeMeshes.forEach(mesh => {
        const dict = mesh.morphTargetDictionary;
        const influences = mesh.morphTargetInfluences;
        
        // Apply EXTREME downward gaze to both eyes
        if (dict['eyeLookDownLeft'] !== undefined) {
            influences[dict['eyeLookDownLeft']] = lookDownAmount;
        }
        if (dict['eyeLookDownRight'] !== undefined) {
            influences[dict['eyeLookDownRight']] = lookDownAmount;
        }
        
        // Reset upward gaze (in case idle animation has it)
        if (dict['eyeLookUpLeft'] !== undefined) {
            influences[dict['eyeLookUpLeft']] = 0;
        }
        if (dict['eyeLookUpRight'] !== undefined) {
            influences[dict['eyeLookUpRight']] = 0;
        }
    });
}

// Animation loop
function animate() {
    requestAnimationFrame(animate);
    
    const delta = clock.getDelta();
    
    // Update animation mixer
    if (mixer) {
        mixer.update(delta);
    }
    
    // Apply eye gaze and emotion expressions after animation updates
    applyEyeGaze();
    applyEmotionExpression();
    
    // Update lip-sync if enabled (with performance monitoring)
    if (lipSyncEnabled && currentAvatarState === 'talking') {
        updateLipSync();
    }
    
    // Render scene
    renderer.render(scene, camera);
}

// Handle window resize
function onWindowResize() {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
}

// Background aura is now handled in Flutter layer
// This function is kept for compatibility but does nothing
function updateBackgroundColor(stateColor) {
    console.log(`[AICO Avatar] 🎨 updateBackgroundColor called (no-op - aura in Flutter): "${stateColor}"`);
}

// ============================================================================
// LIP-SYNC SYSTEM
// ============================================================================

/**
 * Initialize lip-sync system with Web Audio API
 * Pure frequency analysis - TTS engine agnostic
 */
function initLipSync() {
    try {
        // Initialize Web Audio API
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        audioAnalyser = audioContext.createAnalyser();
        audioAnalyser.fftSize = 2048; // Higher resolution for frequency analysis
        audioAnalyser.smoothingTimeConstant = 0.8; // Smooth audio analysis
        
        // Initialize frequency data buffer
        frequencyData = new Uint8Array(audioAnalyser.frequencyBinCount);
        
        lipSyncEnabled = true;
        console.log('[AICO Avatar] 🎤 Lip-sync system initialized');
        console.log('[AICO Avatar] ✅ Using Web Audio API frequency analysis');
    } catch (error) {
        console.error('[AICO Avatar] ❌ Lip-sync initialization failed:', error);
        lipSyncEnabled = false;
    }
}

/**
 * Play audio in WebView and connect to lip-sync
 * @param {string} base64Audio - Base64-encoded WAV audio data
 */
window.playAudioForLipSync = function(base64Audio) {
    try {
        console.log('[AICO Avatar] 🎵 Setting up audio for lip-sync');
        
        // Clean up previous audio
        if (audioElement) {
            audioElement.pause();
            audioElement.src = '';
        }
        if (audioSource) {
            try {
                audioSource.disconnect();
            } catch (e) {
                // Ignore disconnect errors
            }
            audioSource = null;
        }
        
        // Create new audio element
        audioElement = new Audio();
        audioElement.id = 'tts-audio';
        
        // Set audio source FIRST (before connecting to Web Audio API)
        audioElement.src = `data:audio/wav;base64,${base64Audio}`;
        
        // Connect to Web Audio API for frequency analysis
        // MUST be done after setting src but before play
        if (audioContext && audioAnalyser) {
            try {
                audioSource = audioContext.createMediaElementSource(audioElement);
                audioSource.connect(audioAnalyser);
                audioAnalyser.connect(audioContext.destination);
                console.log('[AICO Avatar] 🔊 Audio connected to analyser');
            } catch (error) {
                console.error('[AICO Avatar] Failed to connect audio to analyser:', error);
            }
        }
        
        // Handle playback end
        audioElement.addEventListener('ended', () => {
            console.log('[AICO Avatar] 🎵 Audio playback ended');
            // Notify Flutter that audio ended
            if (window.flutter_inappwebview) {
                window.flutter_inappwebview.callHandler('audioEnded');
            }
        });
        
        // Play audio
        audioElement.play().then(() => {
            console.log('[AICO Avatar] 🎵 Audio playback started');
        }).catch(error => {
            console.error('[AICO Avatar] Failed to play audio:', error);
        });
        
    } catch (error) {
        console.error('[AICO Avatar] Failed to setup audio:', error);
    }
};

/**
 * Enhanced viseme to ARKit blend shapes mapping
 * Natural movement with lateral stretch, jaw, and lip detail
 * Based on professional animation principles
 */
const visemeMap = {
    // Silence - neutral mouth
    'sil': {},
    
    // aa - open vowel (ah) - wide open, slight stretch
    'aa': { 
        jawOpen: 0.45,
        mouthStretchLeft: 0.1,
        mouthStretchRight: 0.1
    },
    
    // E - mid vowel (eh) - smile + stretch (wide vowel)
    'E': { 
        jawOpen: 0.28,
        mouthSmileLeft: 0.2,
        mouthSmileRight: 0.2,
        mouthStretchLeft: 0.15,
        mouthStretchRight: 0.15
    },
    
    // I - closed vowel (ih) - wider smile, stretched (Ee shape)
    'I': { 
        jawOpen: 0.18,
        mouthSmileLeft: 0.35,
        mouthSmileRight: 0.35,
        mouthStretchLeft: 0.25,
        mouthStretchRight: 0.25
    },
    
    // O - rounded vowel (oh) - pucker + jaw + slight funnel
    'O': { 
        jawOpen: 0.25,
        mouthPucker: 0.35,
        mouthFunnel: 0.18,
        jawForward: 0.15
    },
    
    // U - rounded vowel (oo) - more funnel, forward jaw
    'U': { 
        jawOpen: 0.12,
        mouthFunnel: 0.4,
        mouthPucker: 0.25,
        jawForward: 0.2
    },
    
    // PP - bilabial (p, b, m) - lips pressed, slight upper lip up
    'PP': { 
        jawOpen: 0.03,
        mouthUpperUpLeft: 0.1,
        mouthUpperUpRight: 0.1
    },
    
    // FF - labiodental (f, v) - teeth on lower lip
    'FF': {
        jawOpen: 0.08,
        mouthLowerDownLeft: 0.15,
        mouthLowerDownRight: 0.15,
        mouthStretchLeft: 0.1,
        mouthStretchRight: 0.1
    },
    
    // TH - dental (th) - tongue visible, slight jaw
    'TH': {
        jawOpen: 0.15,
        tongueOut: 0.2
    },
    
    // DD - alveolar (d, t, n) - tongue behind teeth
    'DD': {
        jawOpen: 0.2,
        tongueOut: 0.15,
        mouthSmileLeft: 0.1,
        mouthSmileRight: 0.1
    },
    
    // kk - velar (k, g) - back of tongue, slight jaw
    'kk': {
        jawOpen: 0.22,
        mouthStretchLeft: 0.12,
        mouthStretchRight: 0.12
    },
    
    // SS - sibilant (s, z) - teeth together, stretched
    'SS': {
        jawOpen: 0.08,
        mouthStretchLeft: 0.2,
        mouthStretchRight: 0.2,
        mouthSmileLeft: 0.15,
        mouthSmileRight: 0.15
    },
    
    // CH - postalveolar (ch, j, sh) - lips forward, rounded
    'CH': {
        jawOpen: 0.15,
        mouthPucker: 0.25,
        mouthFunnel: 0.2,
        jawForward: 0.1
    },
};

// Smooth interpolation state
let targetVisemeWeights = {};
let currentVisemeWeights = {};
const LERP_SPEED = 0.5; // Interpolation speed (0-1, higher = faster)
let lastVisemeChangeTime = 0;
const MIN_VISEME_DURATION_MS = 50; // Minimum time to hold a viseme

/**
 * Detect current viseme from audio amplitude AND frequency
 * Uses both volume and spectral content for better variety
 * Returns viseme code based on audio characteristics
 */
function detectViseme() {
    if (!audioAnalyser || !lipSyncEnabled) {
        return 'sil';
    }
    
    try {
        // Get frequency data
        audioAnalyser.getByteFrequencyData(frequencyData);
        
        // Calculate RMS (root mean square) for volume
        let sum = 0;
        for (let i = 0; i < frequencyData.length; i++) {
            const normalized = frequencyData[i] / 255.0;
            sum += normalized * normalized;
        }
        const rms = Math.sqrt(sum / frequencyData.length);
        
        // Analyze frequency bands for better viseme detection
        const lowFreq = frequencyData.slice(0, 85).reduce((a, b) => a + b, 0) / 85 / 255;
        const midFreq = frequencyData.slice(85, 170).reduce((a, b) => a + b, 0) / 85 / 255;
        const highFreq = frequencyData.slice(170, 255).reduce((a, b) => a + b, 0) / 85 / 255;
        
        // Add time-based variation to prevent sticking
        const now = performance.now();
        const timeSinceLastChange = now - lastVisemeChangeTime;
        
        // Silence threshold
        if (rms < 0.015) {
            return 'sil';
        }
        
        // Use frequency content + amplitude to distinguish phonemes
        // More sensitive thresholds for better variety
        
        // Enhanced detection with 12 visemes across 9 volume levels
        if (rms > 0.18) {
            // Very loud - wide open vowels
            return lowFreq > midFreq * 1.2 ? 'aa' : 'O';
        } else if (rms > 0.14) {
            // Loud - open vowels with variation
            if (highFreq > midFreq * 1.15) {
                return 'E'; // Mid vowel
            } else if (lowFreq > highFreq * 1.1) {
                return 'aa'; // Wide open
            } else {
                return 'O'; // Rounded
            }
        } else if (rms > 0.10) {
            // Medium-high - mix of vowels and some consonants
            if (highFreq > lowFreq * 1.3) {
                return 'I'; // Closed vowel
            } else if (midFreq > highFreq * 1.15) {
                return 'kk'; // Velar (k, g)
            } else if (midFreq > lowFreq * 1.2) {
                return 'E'; // Mid vowel
            } else {
                return 'aa'; // Open
            }
        } else if (rms > 0.07) {
            // Medium - varied vowels and consonants
            if (highFreq > midFreq * 1.35) {
                return 'SS'; // Sibilant (s, z)
            } else if (highFreq > midFreq * 1.2) {
                return 'I'; // Closed vowel
            } else if (lowFreq > highFreq * 1.15) {
                return 'DD'; // Alveolar (d, t, n)
            } else {
                return 'U'; // Rounded quiet
            }
        } else if (rms > 0.05) {
            // Medium-low - consonants and quiet vowels
            if (highFreq > midFreq * 1.4) {
                return 'SS'; // Sibilant
            } else if (highFreq > midFreq * 1.25) {
                return 'CH'; // Postalveolar (ch, sh)
            } else if (midFreq > lowFreq * 1.2) {
                return 'DD'; // Alveolar
            } else {
                return 'U'; // Rounded
            }
        } else if (rms > 0.035) {
            // Low - consonants
            if (highFreq > midFreq * 1.5) {
                return 'SS'; // Sibilant
            } else if (highFreq > midFreq * 1.3) {
                return 'FF'; // Labiodental
            } else if (midFreq > lowFreq * 1.15) {
                return 'DD'; // Alveolar
            } else {
                return 'kk'; // Velar
            }
        } else if (rms > 0.025) {
            // Very low - subtle consonants
            if (highFreq > midFreq * 1.4) {
                return 'PP'; // Bilabial
            } else if (lowFreq > highFreq) {
                return 'TH'; // Dental
            } else {
                return 'CH'; // Postalveolar
            }
        } else if (rms > 0.018) {
            // Extremely low
            return highFreq > midFreq ? 'PP' : 'TH';
        } else {
            return 'sil'; // Silence
        }
        
    } catch (error) {
        console.error('[AICO Avatar] Viseme detection error:', error);
        return 'sil';
    }
}

/**
 * Apply viseme blend shapes to avatar face with smooth interpolation
 * Blends with current emotion expression
 */
function applyViseme(visemeCode, intensity = 1.0) {
    const viseme = visemeMap[visemeCode] || visemeMap['sil'];
    
    // Set target weights for this viseme
    targetVisemeWeights = {};
    for (const [target, weight] of Object.entries(viseme)) {
        targetVisemeWeights[target] = weight * intensity;
    }
    
    // Smooth interpolation toward target
    eyeMeshes.forEach(mesh => {
        const dict = mesh.morphTargetDictionary;
        const influences = mesh.morphTargetInfluences;
        
        // List of all mouth targets we control
        const mouthTargets = ['jawOpen', 'jawForward', 'mouthPucker', 'mouthFunnel', 
                             'mouthSmileLeft', 'mouthSmileRight', 'mouthStretchLeft', 'mouthStretchRight',
                             'mouthUpperUpLeft', 'mouthUpperUpRight', 'mouthLowerDownLeft', 'mouthLowerDownRight',
                             'tongueOut'];
        
        mouthTargets.forEach(target => {
            if (dict[target] !== undefined) {
                const targetIndex = dict[target];
                
                // Initialize current weight if not set
                if (currentVisemeWeights[target] === undefined) {
                    currentVisemeWeights[target] = 0;
                }
                
                // Get target weight (0 if not in current viseme)
                const targetWeight = targetVisemeWeights[target] || 0;
                
                // Smooth interpolation (lerp)
                currentVisemeWeights[target] += (targetWeight - currentVisemeWeights[target]) * LERP_SPEED;
                
                // Blend with emotion
                const emotionWeight = currentEmotionValues[target] || 0;
                const blendedWeight = Math.min(emotionWeight + currentVisemeWeights[target], 1.0);
                
                influences[targetIndex] = blendedWeight;
            }
        });
    });
}

/**
 * Update lip-sync in animation loop
 * Called every frame when talking - updates blend shapes smoothly
 */
function updateLipSync() {
    const startTime = performance.now();
    
    try {
        // Detect viseme from audio frequency
        const viseme = detectViseme();
        
        // Log only when viseme changes
        if (viseme !== currentViseme) {
            const now = performance.now();
            lastVisemeChangeTime = now;
            currentViseme = viseme;
            console.log('[AICO Avatar] 👄 Viseme:', viseme);
        }
        
        // ALWAYS update blend shapes for smooth interpolation
        applyViseme(viseme, 1.0);
        
        // Performance monitoring
        lipSyncFrameTime = performance.now() - startTime;
        
        // Auto-disable if too slow (fail loudly)
        if (lipSyncFrameTime > MAX_LIPSYNC_TIME_MS) {
            console.error(`[AICO Avatar] ⚠️ Lip-sync too slow (${lipSyncFrameTime.toFixed(2)}ms > ${MAX_LIPSYNC_TIME_MS}ms), disabling`);
            lipSyncEnabled = false;
        }
        
    } catch (error) {
        console.error('[AICO Avatar] Lip-sync update error:', error);
        lipSyncEnabled = false; // Fail loudly and disable
    }
}

/**
 * Reset lip-sync state when stopping speech
 */
function resetLipSync() {
    currentViseme = 'sil';
    
    // Clear all lip-sync blend shapes (reset mouth to neutral)
    eyeMeshes.forEach(mesh => {
        const dict = mesh.morphTargetDictionary;
        const influences = mesh.morphTargetInfluences;
        
        // Reset all mouth-related blend shapes to emotion-only values
        const mouthTargets = ['jawOpen', 'mouthPucker', 'mouthFunnel', 'mouthPressLeft', 'mouthPressRight',
                             'mouthDimpleLeft', 'mouthDimpleRight', 'mouthRollLower', 'mouthRollUpper',
                             'mouthUpperUpLeft', 'mouthUpperUpRight', 'jawForward'];
        
        mouthTargets.forEach(target => {
            if (dict[target] !== undefined) {
                const targetIndex = dict[target];
                // Reset to emotion value only (no lip-sync)
                influences[targetIndex] = currentEmotionValues[target] || 0;
            }
        });
    });
    
    if (audioElement) {
        audioElement.pause();
        audioElement = null;
    }
    audioSource = null;
    console.log('[AICO Avatar] 🤫 Lip-sync reset');
}

// Expose functions to Flutter
window.playAnimation = playAnimation;
window.updateBackgroundColor = updateBackgroundColor;
window.startTalking = startTalking;
window.stopTalking = stopTalking;
window.setAvatarEmotion = setEmotion;
// window.playAudioForLipSync is already exposed above

// Initialize on load
init();

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
    setTimeout(() => {
        playAnimation(group.base);
        scheduleNextVariation(groupName);
    }, variationDuration);
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

// Expose functions to Flutter
window.playAnimation = playAnimation;
window.updateBackgroundColor = updateBackgroundColor;

// Initialize on load
init();

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
    
    console.log('[AICO Avatar] Camera position:', camera.position);
    console.log('[AICO Avatar] Camera looking at:', new THREE.Vector3(0, 0.85, 0));
    
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
        console.log('='.repeat(60));
        console.log('[AICO Avatar] 🚀 STARTING AVATAR LOAD');
        console.log('[AICO Avatar] Loading avatar model from: ./models/avatar.glb');
        console.log('='.repeat(60));
        
        // Load main avatar
        console.log('[AICO Avatar] 📦 Fetching GLB file...');
        const avatarGltf = await loader.loadAsync('./models/avatar.glb');
        console.log('[AICO Avatar] ✅ GLB file loaded successfully');
        avatar = avatarGltf.scene;
        console.log('[AICO Avatar] 👤 Avatar scene extracted');
        
        // Position avatar
        avatar.position.set(0, 0, 0);
        avatar.scale.set(1, 1, 1);
        
        // Enable shadows and collect eye meshes for gaze control
        avatar.traverse((node) => {
            if (node.isMesh) {
                node.castShadow = true;
                node.receiveShadow = true;
                
                // Store meshes with eye-related morph targets for gaze control
                if (node.morphTargetInfluences && node.morphTargetInfluences.length > 0) {
                    if (node.morphTargetDictionary) {
                        const morphNames = Object.keys(node.morphTargetDictionary);
                        const hasEyeMorphs = morphNames.some(name => 
                            name.toLowerCase().includes('eye') || 
                            name.toLowerCase().includes('look')
                        );
                        if (hasEyeMorphs) {
                            eyeMeshes.push(node);
                        }
                    }
                }
            }
        });
        
        scene.add(avatar);
        console.log('[AICO Avatar] ✅ Avatar added to scene');
        console.log('[AICO Avatar] 👁️ Eye meshes found:', eyeMeshes.length);
        console.log('[AICO Avatar] 📊 Avatar bounding box:', avatar);
        console.log('[AICO Avatar] 📊 Avatar position:', avatar.position);
        console.log('[AICO Avatar] 📊 Avatar scale:', avatar.scale);
        console.log('[AICO Avatar] 📊 Avatar visible:', avatar.visible);
        
        // Count meshes
        let meshCount = 0;
        avatar.traverse((node) => {
            if (node.isMesh) {
                meshCount++;
                console.log(`[AICO Avatar] 🎨 Mesh: ${node.name}, visible: ${node.visible}, material: ${node.material?.type}`);
            }
        });
        console.log(`[AICO Avatar] 📊 Total meshes: ${meshCount}`);
        
        // Debug: Check if avatar is in camera view
        const box = new THREE.Box3().setFromObject(avatar);
        const center = box.getCenter(new THREE.Vector3());
        const size = box.getSize(new THREE.Vector3());
        console.log('[AICO Avatar] 📦 Bounding box center:', center);
        console.log('[AICO Avatar] 📦 Bounding box size:', size);
        console.log('[AICO Avatar] 📷 Camera distance from avatar:', camera.position.distanceTo(center));
        
        // Load animations
        console.log('[AICO Avatar] 🎬 Starting animation load...');
        await loadAnimations();
        console.log('[AICO Avatar] ✅ Animation load complete');
        
        // Hide loading indicator
        console.log('[AICO Avatar] 🎉 Hiding loading spinner');
        document.getElementById('loading').classList.add('hidden');
        
        // Notify Flutter that scene is ready
        if (window.flutter_inappwebview) {
            console.log('[AICO Avatar] 📱 Notifying Flutter: scene ready');
            window.flutter_inappwebview.callHandler('ready', { status: 'loaded' });
        } else {
            console.warn('[AICO Avatar] ⚠️ Flutter bridge not available');
        }
        
        console.log('='.repeat(60));
        console.log('[AICO Avatar] ✅ AVATAR FULLY LOADED AND READY');
        console.log('='.repeat(60));
        
    } catch (error) {
        console.error('='.repeat(60));
        console.error('[AICO Avatar] ❌ FATAL ERROR IN loadAvatar()');
        console.error('[AICO Avatar] Error:', error);
        console.error('[AICO Avatar] Stack:', error.stack);
        console.error('='.repeat(60));
        document.getElementById('loading').innerHTML = 
            `<div style="color: #ff6b6b;">Error loading avatar<br/><small>${error.message}</small></div>`;
    }
}

// Load animation files
async function loadAnimations() {
    const gltfLoader = new GLTFLoader();
    
    try {
        console.log('[AICO Avatar] 🎬 loadAnimations() started');
        console.log('[AICO Avatar] GLTFLoader instance created');
        
        // Setup animation mixer with the avatar root
        console.log('[AICO Avatar] Creating AnimationMixer with avatar root...');
        mixer = new THREE.AnimationMixer(avatar);
        console.log('[AICO Avatar] ✅ AnimationMixer created successfully');
        
        // Load idle animation group (base + variations)
        console.log('[AICO Avatar] 📂 Loading idle animation group...');
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
        
        // Load talking animation (no variations yet)
        // const talkingFbx = await fbxLoader.loadAsync('./animations/talking.fbx');
        // if (talkingFbx.animations && talkingFbx.animations.length > 0) {
        //     animations.talking = talkingFbx.animations[0];
        //     console.log('[AICO Avatar] Talking animation loaded (FBX)');
        // }
        
        // Disable morph target tracks in all animations to allow manual control
        Object.keys(animations).forEach(animName => {
            const clip = animations[animName];
            // Remove morph target tracks (they override our manual eye gaze)
            clip.tracks = clip.tracks.filter(track => {
                const isMorphTrack = track.name.includes('.morphTargetInfluences');
                if (isMorphTrack) {
                    console.log(`[AICO Avatar] Removed morph track from ${animName}:`, track.name);
                }
                return !isMorphTrack;
            });
        });
        
        // Start idle animation group with variations
        console.log('[AICO Avatar] Checking if idle group loaded...');
        if (animationGroups.idle) {
            console.log('[AICO Avatar] ✅ Idle group found, starting...');
            startAnimationGroup('idle');
        } else {
            console.error('[AICO Avatar] ❌ Idle group NOT found!');
        }
        
        // Background aura is now handled in Flutter layer
        
        console.log('[AICO Avatar] ✅ All animations ready');
        console.log('[AICO Avatar] Loaded animations:', Object.keys(animations));
        console.log('[AICO Avatar] Animation groups:', Object.keys(animationGroups));
        
    } catch (error) {
        console.error('[AICO Avatar] ❌ ERROR in loadAnimations()');
        console.error('[AICO Avatar] Error:', error);
        console.error('[AICO Avatar] Stack:', error.stack);
        document.getElementById('loading').innerHTML = 
            `<div style="color: #ff6b6b;">Error loading animations<br/><small>${error.message}</small></div>`;
        throw error; // Re-throw to stop avatar loading
    }
}

// Load animation group (base + variations)
async function loadAnimationGroup(loader, groupName, config) {
    try {
        console.log(`[AICO Avatar] 📁 loadAnimationGroup("${groupName}") started`);
        console.log(`[AICO Avatar] Base file: ${config.base}`);
        console.log(`[AICO Avatar] Variations: ${config.variations.length} files`);
        
        // Load base animation
        console.log(`[AICO Avatar] 📥 Loading base GLB: ${config.base}`);
        const baseGltf = await loader.loadAsync(config.base);
        console.log(`[AICO Avatar] ✅ Base GLB loaded successfully`);
        console.log(`[AICO Avatar] Animations in base:`, baseGltf.animations?.length || 0);
        
        if (!baseGltf.animations || baseGltf.animations.length === 0) {
            console.warn(`[AICO Avatar] No animation found in base file: ${config.base}`);
            return;
        }
        
        const baseAnimName = `${groupName}_base`;
        animations[baseAnimName] = baseGltf.animations[0];
        console.log(`[AICO Avatar] ✅ Stored base animation as: ${baseAnimName}`);
        console.log(`[AICO Avatar] Animation duration: ${baseGltf.animations[0].duration}s`);
        
        // Load variations
        console.log(`[AICO Avatar] 📥 Loading ${config.variations.length} variations...`);
        const variations = [];
        for (let i = 0; i < config.variations.length; i++) {
            try {
                console.log(`[AICO Avatar]   [${i+1}/${config.variations.length}] Loading: ${config.variations[i]}`);
                const varGltf = await loader.loadAsync(config.variations[i]);
                if (varGltf.animations && varGltf.animations.length > 0) {
                    const varAnimName = `${groupName}_var${i + 1}`;
                    animations[varAnimName] = varGltf.animations[0];
                    variations.push(varAnimName);
                    console.log(`[AICO Avatar]   ✅ Loaded: ${varAnimName} (${varGltf.animations[0].duration}s)`);
                } else {
                    console.warn(`[AICO Avatar]   ⚠️ No animations in file: ${config.variations[i]}`);
                }
            } catch (error) {
                console.error(`[AICO Avatar]   ❌ Failed variation ${i + 1}:`, error.message);
            }
        }
        
        // Store animation group configuration
        animationGroups[groupName] = {
            base: baseAnimName,
            variations: variations,
            interval: config.variationInterval || { min: 3, max: 10 }
        };
        
        console.log(`[AICO Avatar] ✅ Animation group "${groupName}" complete: 1 base + ${variations.length} variations`);
        
    } catch (error) {
        console.error(`[AICO Avatar] ❌ FATAL ERROR in loadAnimationGroup("${groupName}")`);
        console.error(`[AICO Avatar] Error:`, error);
        console.error(`[AICO Avatar] Stack:`, error.stack);
        throw error; // Re-throw to propagate error
    }
}

// Start animation group with automatic variation cycling
function startAnimationGroup(groupName) {
    const group = animationGroups[groupName];
    if (!group) {
        console.warn(`[AICO Avatar] Animation group "${groupName}" not found`);
        return;
    }
    
    // Stop any existing timer for this group
    if (variationTimers[groupName]) {
        clearTimeout(variationTimers[groupName]);
    }
    
    // Play base animation
    playAnimation(group.base);
    console.log(`[AICO Avatar] Started animation group: ${groupName}`);
    
    // Schedule first variation
    scheduleNextVariation(groupName);
}

// Schedule next variation for an animation group
function scheduleNextVariation(groupName) {
    const group = animationGroups[groupName];
    if (!group || group.variations.length === 0) return;
    
    // Random delay between min and max seconds
    const delaySeconds = group.interval.min + Math.random() * (group.interval.max - group.interval.min);
    const delayMs = delaySeconds * 1000;
    
    variationTimers[groupName] = setTimeout(() => {
        playRandomVariation(groupName);
    }, delayMs);
    
    console.log(`[AICO Avatar] Next variation for "${groupName}" in ${delaySeconds.toFixed(1)}s`);
}

// Play random variation from group (avoiding last played)
function playRandomVariation(groupName) {
    const group = animationGroups[groupName];
    if (!group || group.variations.length === 0) return;
    
    // Get available variations (exclude last played if more than 1 variation exists)
    let availableVariations = group.variations;
    const lastPlayed = lastPlayedVariation[groupName];
    
    if (group.variations.length > 1 && lastPlayed) {
        availableVariations = group.variations.filter(v => v !== lastPlayed);
    }
    
    // Select random variation
    const randomIndex = Math.floor(Math.random() * availableVariations.length);
    const selectedVariation = availableVariations[randomIndex];
    
    // Play variation
    playAnimation(selectedVariation);
    lastPlayedVariation[groupName] = selectedVariation;
    
    console.log(`[AICO Avatar] Playing variation: ${selectedVariation}`);
    
    // Get variation duration and schedule return to base
    const clip = animations[selectedVariation];
    if (clip) {
        const variationDuration = clip.duration * 1000; // Convert to ms
        
        // Return to base animation after variation completes
        setTimeout(() => {
            playAnimation(group.base);
            console.log(`[AICO Avatar] Returned to base: ${group.base}`);
            
            // Schedule next variation
            scheduleNextVariation(groupName);
        }, variationDuration);
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
    console.log(`[AICO Avatar] 🎬 playAnimation("${name}") called`);
    console.log(`[AICO Avatar] Mixer exists: ${!!mixer}, Animation exists: ${!!animations[name]}`);
    
    if (!mixer || !animations[name]) {
        console.warn(`[AICO Avatar] ❌ Animation "${name}" not available`);
        return;
    }
    
    const clip = animations[name];
    const action = mixer.clipAction(clip);
    
    console.log(`[AICO Avatar] Action created, isRunning: ${action.isRunning()}, weight: ${action.getEffectiveWeight()}`);
    
    // If already playing this animation, don't restart it
    if (currentAction === action && action.isRunning()) {
        console.log(`[AICO Avatar] Animation "${name}" already playing, skipping restart`);
        return;
    }
    
    // Crossfade from current animation
    if (currentAction && currentAction !== action) {
        console.log(`[AICO Avatar] Fading out previous animation`);
        currentAction.fadeOut(0.5);
    }
    
    // Start new animation
    action.reset(); // Reset to beginning
    action.fadeIn(0.5);
    action.setLoop(THREE.LoopRepeat);
    action.play();
    
    currentAction = action;
    
    console.log(`[AICO Avatar] ✅ Animation "${name}" started, weight: ${action.getEffectiveWeight()}`);
}

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
    
    // Apply eye gaze after animation updates
    applyEyeGaze();
    
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

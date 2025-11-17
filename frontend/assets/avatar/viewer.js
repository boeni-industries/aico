import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

// Scene setup
let scene, camera, renderer, mixer, clock;
let avatar, currentAction;
let animations = {};

// Initialize the scene
function init() {
    console.log('[AICO Avatar] Initializing Three.js scene...');
    console.log('[AICO Avatar] Current URL:', window.location.href);
    console.log('[AICO Avatar] Base URL:', window.location.origin);
    
    // Create scene
    scene = new THREE.Scene();
    scene.background = null; // Transparent background - let body gradient show through
    
    // Create camera
    camera = new THREE.PerspectiveCamera(
        35, // FOV
        window.innerWidth / window.innerHeight,
        0.1,
        1000
    );
    camera.position.set(0, 1.35, 1.3);
    camera.lookAt(0, 1.35, 0);
    
    // Create renderer
    renderer = new THREE.WebGLRenderer({ 
        antialias: true,
        alpha: true,
        powerPreference: 'high-performance'
    });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
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
    
    console.log('[AICO Avatar] 3-point lighting setup complete');
}

// Load avatar model
async function loadAvatar() {
    const loader = new GLTFLoader();
    
    try {
        console.log('[AICO Avatar] Loading avatar model from: ./models/avatar.glb');
        
        // Load main avatar
        const avatarGltf = await loader.loadAsync('./models/avatar.glb');
        console.log('[AICO Avatar] Avatar GLTF loaded:', avatarGltf);
        avatar = avatarGltf.scene;
        
        // Position avatar
        avatar.position.set(0, 0, 0);
        avatar.scale.set(1, 1, 1);
        
        // Enable shadows
        avatar.traverse((node) => {
            if (node.isMesh) {
                node.castShadow = true;
                node.receiveShadow = true;
            }
        });
        
        scene.add(avatar);
        console.log('[AICO Avatar] Avatar model loaded');
        
        // Load animations
        await loadAnimations();
        
        // Hide loading indicator
        document.getElementById('loading').classList.add('hidden');
        
        // Notify Flutter that scene is ready
        if (window.flutter_inappwebview) {
            window.flutter_inappwebview.callHandler('ready', { status: 'loaded' });
        }
        
    } catch (error) {
        console.error('[AICO Avatar] Error loading avatar:', error);
        console.error('[AICO Avatar] Error stack:', error.stack);
        document.getElementById('loading').innerHTML = 
            `<div style="color: #ff6b6b;">Error loading avatar<br/><small>${error.message}</small></div>`;
    }
}

// Load animation files
async function loadAnimations() {
    const loader = new GLTFLoader();
    
    try {
        console.log('[AICO Avatar] Loading animations...');
        
        // Load idle animation
        const idleGltf = await loader.loadAsync('./animations/idle.glb');
        if (idleGltf.animations && idleGltf.animations.length > 0) {
            animations.idle = idleGltf.animations[0];
            console.log('[AICO Avatar] Idle animation loaded');
        }
        
        // Load talking animation
        const talkingGltf = await loader.loadAsync('./animations/talking.glb');
        if (talkingGltf.animations && talkingGltf.animations.length > 0) {
            animations.talking = talkingGltf.animations[0];
            console.log('[AICO Avatar] Talking animation loaded');
        }
        
        // Setup animation mixer
        mixer = new THREE.AnimationMixer(avatar);
        
        // Play idle animation by default
        if (animations.idle) {
            playAnimation('idle');
        }
        
        // Set initial background color for idle state
        updateBackgroundColor('idle');
        
        console.log('[AICO Avatar] Animations ready');
        
    } catch (error) {
        console.error('[AICO Avatar] Error loading animations:', error);
    }
}

// Play animation by name
function playAnimation(name) {
    if (!mixer || !animations[name]) {
        console.warn(`[AICO Avatar] Animation "${name}" not available`);
        return;
    }
    
    const clip = animations[name];
    const action = mixer.clipAction(clip);
    
    // If already playing this animation, don't restart it
    if (currentAction === action && action.isRunning()) {
        console.log(`[AICO Avatar] Animation "${name}" already playing, skipping restart`);
        return;
    }
    
    // Crossfade from current animation
    if (currentAction && currentAction !== action) {
        currentAction.fadeOut(0.5); // Longer crossfade for smoother transition
    }
    
    // Don't reset - continue from current position if switching back
    action.fadeIn(0.5);
    action.setLoop(THREE.LoopRepeat);
    action.play();
    
    currentAction = action;
    
    console.log(`[AICO Avatar] Playing animation: ${name}`);
}

// Animation loop
function animate() {
    requestAnimationFrame(animate);
    
    const delta = clock.getDelta();
    
    // Update animation mixer
    if (mixer) {
        mixer.update(delta);
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

// Update background gradient based on state color
function updateBackgroundColor(stateColor) {
    console.log(`[AICO Avatar] 🎨 updateBackgroundColor called with: "${stateColor}"`);
    
    // Parse the state color (e.g., 'green', 'purple', 'blue', 'amber', 'red')
    const colorMap = {
        'idle': { r: 45, g: 120, b: 100 },      // Teal/green
        'thinking': { r: 120, g: 80, b: 160 },  // Purple
        'listening': { r: 60, g: 100, b: 180 }, // Blue
        'speaking': { r: 60, g: 100, b: 180 },  // Blue
        'connecting': { r: 60, g: 100, b: 180 },// Blue
        'error': { r: 180, g: 60, b: 60 },      // Red
        'attention': { r: 200, g: 140, b: 60 }, // Amber
        'success': { r: 80, g: 180, b: 100 },   // Green
        'processing': { r: 120, g: 80, b: 160 },// Purple
    };
    
    const color = colorMap[stateColor] || colorMap['idle'];
    console.log(`[AICO Avatar] 🎨 Mapped color:`, color);
    
    // Create depth: smooth multi-stop radial gradient with bold state color
    // Maximum saturation (80-120% with boosted values) for strong visual impact
    const gradient = `radial-gradient(circle at center, 
        rgba(${Math.floor(color.r * 0.8)}, ${Math.floor(color.g * 0.8)}, ${Math.floor(color.b * 0.8)}, 0.3) 0%,
        rgba(${Math.floor(color.r * 0.9)}, ${Math.floor(color.g * 0.9)}, ${Math.floor(color.b * 0.9)}, 0.4) 25%,
        rgba(${color.r}, ${color.g}, ${color.b}, 0.5) 45%,
        rgba(${Math.min(255, Math.floor(color.r * 1.1))}, ${Math.min(255, Math.floor(color.g * 1.1))}, ${Math.min(255, Math.floor(color.b * 1.1))}, 0.65) 65%,
        rgba(${Math.min(255, Math.floor(color.r * 1.15))}, ${Math.min(255, Math.floor(color.g * 1.15))}, ${Math.min(255, Math.floor(color.b * 1.15))}, 0.75) 80%,
        rgba(${Math.min(255, Math.floor(color.r * 1.2))}, ${Math.min(255, Math.floor(color.g * 1.2))}, ${Math.min(255, Math.floor(color.b * 1.2))}, 0.85) 100%)`;
    
    console.log(`[AICO Avatar] 🎨 Setting gradient:`, gradient);
    document.body.style.background = gradient;
    
    console.log(`[AICO Avatar] ✅ Background updated for state: ${stateColor}`);
}

// Expose functions to Flutter
window.playAnimation = playAnimation;
window.updateBackgroundColor = updateBackgroundColor;

// Initialize on load
init();

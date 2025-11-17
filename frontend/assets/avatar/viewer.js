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
    scene.background = null; // Transparent background
    
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
    const rimLight = new THREE.DirectionalLight(0xffffff, 1.0);
    rimLight.position.set(0, 2, -2);
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
    
    // Crossfade from current animation
    if (currentAction && currentAction !== action) {
        currentAction.fadeOut(0.3);
    }
    
    action.reset();
    action.fadeIn(0.3);
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

// Expose functions to Flutter
window.playAnimation = playAnimation;

// Initialize on load
init();

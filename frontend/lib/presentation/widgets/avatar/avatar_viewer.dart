import 'package:flutter/material.dart' hide Colors;
import 'package:flutter/material.dart' as material show Colors;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:vector_math/vector_math_64.dart';

import 'package:aico_frontend/presentation/providers/avatar_state_provider.dart';
import 'package:thermion_flutter/thermion_flutter.dart';

/// Native 3D avatar viewer using Thermion/Filament rendering engine.
/// 
/// Displays AICO's 3D avatar with real-time animations driven by emotional
/// state, conversation context, and procedural behaviors (breathing, blinking).
/// 
/// Uses Google's Filament PBR engine for photorealistic rendering with
/// hardware-accelerated performance across all platforms.
class AvatarViewer extends ConsumerStatefulWidget {
  const AvatarViewer({super.key});

  @override
  ConsumerState<AvatarViewer> createState() => _AvatarViewerState();
}

class _AvatarViewerState extends ConsumerState<AvatarViewer> {
  ThermionViewer? _viewer;
  bool _isLoading = true;
  String? _error;
  
  @override
  void initState() {
    super.initState();
    _initializeViewer();
  }
  
  Future<void> _initializeViewer() async {
    try {
      debugPrint('[AvatarViewer] Creating viewer...');
      
      // Create viewer
      _viewer = await ThermionFlutterPlugin.createViewer();
      debugPrint('[AvatarViewer] Viewer created');
      
      // Load model
      await _viewer!.loadGltf('assets/avatar/models/avatar.glb');
      debugPrint('[AvatarViewer] Model loaded');
      
      // TODO: Add idle animation/pose
      // Ready Player Me models are in T-pose by default
      // Options for Phase 2:
      // 1. Use morph targets for subtle breathing/blinking
      // 2. Load a GLB with embedded idle animation
      // 3. Apply procedural animations via bone manipulation
      
      // Get camera and position it for upper third shot (head, neck, shoulders)
      // Model scale: waist at Y=1.0, head at ~Y=1.6, feet at ~Y=0.4
      final camera = await _viewer!.getActiveCamera();
      await camera.lookAt(
        Vector3(0, 1.35, 1.3), // Camera closer (Z=1.3) at chest height
        focus: Vector3(0, 1.35, 0), // Focus on chest so head is in upper frame
        up: Vector3(0, 1, 0),
      );
      debugPrint('[AvatarViewer] Camera positioned for portrait framing');
      
      // Professional 3-point lighting setup
      
      // 1. Key Light - main light from front-right, slightly above
      await _viewer!.addDirectLight(
        DirectLight(
          type: LightType.DIRECTIONAL,
          color: 0xFFFFFFFF, // Pure white
          intensity: 150000, // Strong key light
          direction: Vector3(-0.6, -0.8, -1.0).normalized(), // Front-right, slightly down
          position: Vector3(0, 0, 0),
          castShadows: false,
        ),
      );
      
      // 2. Fill Light - softer light from front-left to reduce shadows
      await _viewer!.addDirectLight(
        DirectLight(
          type: LightType.DIRECTIONAL,
          color: 0xFFEEDDCC, // Warm fill light
          intensity: 50000, // Softer than key
          direction: Vector3(0.8, -0.3, -1.0).normalized(), // Front-left, gentle
          position: Vector3(0, 0, 0),
          castShadows: false,
        ),
      );
      
      // 3. Rim/Back Light - from behind to create edge definition
      await _viewer!.addDirectLight(
        DirectLight(
          type: LightType.DIRECTIONAL,
          color: 0xFFCCDDFF, // Cool rim light (slight blue)
          intensity: 80000, // Medium intensity
          direction: Vector3(0.3, -0.5, 1.0).normalized(), // From behind-right
          position: Vector3(0, 0, 0),
          castShadows: false,
        ),
      );
      
      // 4. Ambient fill from below to soften under-chin shadows
      await _viewer!.addDirectLight(
        DirectLight(
          type: LightType.DIRECTIONAL,
          color: 0xFFFFFFFF,
          intensity: 20000, // Very subtle
          direction: Vector3(0, 1.0, -0.2).normalized(), // From below
          position: Vector3(0, 0, 0),
          castShadows: false,
        ),
      );
      debugPrint('[AvatarViewer] Lights added');
      
      // Trigger a render to ensure scene is drawn
      await _viewer!.render();
      debugPrint('[AvatarViewer] Initial render complete');
      
      // Small delay to ensure texture is ready
      await Future.delayed(const Duration(milliseconds: 100));
      
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
      
      debugPrint('[AvatarViewer] Setup complete, showing widget');
      
      // Start continuous rendering
      _startRenderLoop();
    } catch (e, stackTrace) {
      debugPrint('[AvatarViewer] ERROR: $e');
      debugPrint('[AvatarViewer] Stack: $stackTrace');
      if (mounted) {
        setState(() {
          _isLoading = false;
          _error = e.toString();
        });
      }
    }
  }
  
  void _startRenderLoop() {
    // Trigger periodic renders to keep the scene updated
    Future.doWhile(() async {
      if (!mounted || _viewer == null) return false;
      await _viewer!.render();
      await Future.delayed(const Duration(milliseconds: 16)); // ~60 FPS
      return true;
    });
  }
  
  @override
  Widget build(BuildContext context) {
    // Listen to avatar state changes
    ref.listen(avatarRingStateProvider, (previous, next) {
      if (_viewer != null && !_isLoading) {
        _applyAvatarState(next);
      }
    });
    
    // Show loading or error state
    if (_isLoading || _viewer == null) {
      return const SizedBox.expand();
    }
    
    if (_error != null) {
      return Center(child: Text('Error: $_error'));
    }
    
    // Show the pre-configured viewer
    // ThermionWidget will display the viewer's rendered output
    return RepaintBoundary(
      child: ThermionWidget(
        viewer: _viewer!,
        initial: Container(color: material.Colors.transparent),
      ),
    );
  }
  
  /// Apply avatar state from AvatarRingStateProvider
  /// 
  /// Maps emotional states and conversation modes to visual expressions
  /// via blend shape (morph target) animations.
  void _applyAvatarState(AvatarRingState state) {
    if (_viewer == null) return;
    
    // TODO: Implement blend shape animations based on state.mode
    // This will be expanded in Phase 2 with emotion mapping
    
    debugPrint('[AvatarViewer] State changed: ${state.mode.name} (intensity: ${state.intensity})');
  }
  
  @override
  void dispose() {
    _viewer?.dispose();
    super.dispose();
  }
}

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
      
      // Get camera and position it for upper third shot (head, neck, shoulders)
      // Model scale: waist at Y=1.0, head at ~Y=1.6, feet at ~Y=0.4
      final camera = await _viewer!.getActiveCamera();
      await camera.lookAt(
        Vector3(0, 1.35, 1.3), // Camera closer (Z=1.3) at chest height
        focus: Vector3(0, 1.35, 0), // Focus on chest so head is in upper frame
        up: Vector3(0, 1, 0),
      );
      debugPrint('[AvatarViewer] Camera positioned for portrait framing');
      
      // Add lights
      await _viewer!.addDirectLight(
        DirectLight(
          type: LightType.DIRECTIONAL,
          color: 0xFFFFFFFF,
          intensity: 100000,
          direction: Vector3(-0.5, -1.0, -0.5).normalized(),
          position: Vector3(0, 0, 0),
          castShadows: false,
        ),
      );
      await _viewer!.addDirectLight(
        DirectLight(
          type: LightType.DIRECTIONAL,
          color: 0xFFFFFFFF,
          intensity: 30000,
          direction: Vector3(1.0, 0.0, -0.5).normalized(),
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

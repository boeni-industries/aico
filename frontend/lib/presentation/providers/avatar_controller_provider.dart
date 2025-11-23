import 'package:flutter/foundation.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'avatar_controller_provider.g.dart';

/// Controller for avatar animations
/// 
/// Provides methods to control avatar state (talking/idle) from anywhere in the app.
/// Used by conversation provider to sync avatar animations with streaming responses.
class AvatarController extends ChangeNotifier {
  VoidCallback? _startTalkingCallback;
  VoidCallback? _stopTalkingCallback;
  
  /// Register callbacks from AvatarViewer
  void registerCallbacks({
    required VoidCallback onStartTalking,
    required VoidCallback onStopTalking,
  }) {
    _startTalkingCallback = onStartTalking;
    _stopTalkingCallback = onStopTalking;
    debugPrint('[AvatarController] Callbacks registered');
  }
  
  /// Unregister callbacks (cleanup)
  void unregisterCallbacks() {
    _startTalkingCallback = null;
    _stopTalkingCallback = null;
    debugPrint('[AvatarController] Callbacks unregistered');
  }
  
  /// Start talking animation
  void startTalking() {
    debugPrint('[AvatarController] 🎬 startTalking() called');
    if (_startTalkingCallback != null) {
      debugPrint('[AvatarController] ✅ Executing startTalking callback');
      _startTalkingCallback!();
    } else {
      debugPrint('[AvatarController] ⚠️ Cannot start talking - no callback registered');
    }
  }
  
  /// Stop talking animation
  void stopTalking() {
    debugPrint('[AvatarController] 🎬 stopTalking() called');
    if (_stopTalkingCallback != null) {
      debugPrint('[AvatarController] ✅ Executing stopTalking callback');
      _stopTalkingCallback!();
    } else {
      debugPrint('[AvatarController] ⚠️ Cannot stop talking - no callback registered');
    }
  }
}

@riverpod
AvatarController avatarController(Ref ref) {
  final controller = AvatarController();
  ref.onDispose(() {
    controller.dispose();
  });
  return controller;
}

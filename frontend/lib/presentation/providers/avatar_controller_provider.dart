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
  }
  
  /// Unregister callbacks (cleanup)
  void unregisterCallbacks() {
    _startTalkingCallback = null;
    _stopTalkingCallback = null;
  }
  
  /// Start talking animation
  void startTalking() {
    if (_startTalkingCallback != null) {
      _startTalkingCallback!();
    }
  }
  
  /// Stop talking animation
  void stopTalking() {
    if (_stopTalkingCallback != null) {
      _stopTalkingCallback!();
    }
  }
}

@Riverpod(keepAlive: true)
AvatarController avatarController(Ref ref) {
  final controller = AvatarController();
  // Note: keepAlive=true means this won't auto-dispose
  // Callbacks will persist for the app lifetime
  return controller;
}

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_inappwebview/flutter_inappwebview.dart';

import 'package:aico_frontend/presentation/providers/avatar_state_provider.dart';

/// WebView-based 3D avatar viewer using Three.js rendering.
/// 
/// Displays AICO's 3D avatar with real-time animations driven by emotional
/// state, conversation context, and procedural behaviors (breathing, blinking).
/// 
/// Uses Three.js WebGL rendering with InAppLocalhostServer for ES6 module support.
/// Separate animation files (idle.glb, talking.glb) are loaded dynamically.
class AvatarViewer extends ConsumerStatefulWidget {
  const AvatarViewer({super.key});

  @override
  ConsumerState<AvatarViewer> createState() => _AvatarViewerState();
}

class _AvatarViewerState extends ConsumerState<AvatarViewer> {
  InAppWebViewController? _webViewController;
  bool _isReady = false;
  
  @override
  void initState() {
    super.initState();
    debugPrint('[AvatarViewer] Initializing WebView avatar viewer');
  }
  
  
  @override
  Widget build(BuildContext context) {
    // Listen to avatar state changes and trigger animations
    ref.listen(avatarRingStateProvider, (previous, next) {
      if (_isReady && _webViewController != null) {
        _applyAvatarState(next);
      }
    });
    
    return InAppWebView(
      initialSettings: InAppWebViewSettings(
        isInspectable: kDebugMode,
        mediaPlaybackRequiresUserGesture: false,
        allowsInlineMediaPlayback: true,
        transparentBackground: true,
        disableContextMenu: true,
        supportZoom: false,
      ),
      initialUrlRequest: URLRequest(
        url: WebUri('http://localhost:8779/viewer.html'),
      ),
      onWebViewCreated: (controller) {
        _webViewController = controller;
        debugPrint('[AvatarViewer] WebView created');
        
        // Add JavaScript handler for scene ready callback
        controller.addJavaScriptHandler(
          handlerName: 'ready',
          callback: (args) {
            debugPrint('[AvatarViewer] Three.js scene ready: $args');
            if (mounted) {
              setState(() {
                _isReady = true;
              });
            }
          },
        );
      },
      onLoadStart: (controller, url) {
        debugPrint('[AvatarViewer] Loading: $url');
      },
      onLoadStop: (controller, url) {
        debugPrint('[AvatarViewer] Loaded: $url');
      },
      onConsoleMessage: (controller, consoleMessage) {
        debugPrint('[AvatarViewer] JS Console: ${consoleMessage.message}');
      },
      onLoadError: (controller, url, code, message) {
        debugPrint('[AvatarViewer] Load error: $message');
      },
    );
  }
  
  /// Apply avatar state from AvatarRingStateProvider
  /// 
  /// Maps emotional states and conversation modes to animations.
  /// Triggers animation changes in Three.js via JavaScript bridge.
  void _applyAvatarState(AvatarRingState state) {
    if (_webViewController == null || !_isReady) return;
    
    // Map avatar mode to animation name
    final animationName = state.mode == AvatarMode.speaking ? 'talking' : 'idle';
    
    // Trigger animation in Three.js
    _webViewController!.evaluateJavascript(
      source: "window.playAnimation('$animationName')",
    );
    
    debugPrint('[AvatarViewer] Playing animation: $animationName (mode: ${state.mode.name})');
  }
  
  @override
  void dispose() {
    _webViewController?.dispose();
    super.dispose();
  }
}

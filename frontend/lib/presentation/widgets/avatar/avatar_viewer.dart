import 'package:aico_frontend/core/platform/transparent_webview_channel.dart';
import 'package:aico_frontend/presentation/providers/avatar_controller_provider.dart';
import 'package:aico_frontend/presentation/providers/avatar_state_provider.dart';
import 'package:aico_frontend/presentation/providers/emotion_provider.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_inappwebview/flutter_inappwebview.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Global key for AvatarViewer to preserve state across rebuilds
final GlobalKey _avatarViewerKey = GlobalKey(debugLabel: 'AvatarViewer');

/// WebView-based 3D avatar viewer using Three.js rendering.
/// 
/// Displays AICO's 3D avatar with real-time animations driven by emotional
/// state, conversation context, and procedural behaviors (breathing, blinking).
/// 
/// Uses Three.js WebGL rendering with InAppLocalhostServer for ES6 module support.
/// Separate animation files (idle.glb, talking.glb) are loaded dynamically.
class AvatarViewer extends ConsumerStatefulWidget {
  AvatarViewer({Key? key}) : super(key: key ?? _avatarViewerKey);

  @override
  ConsumerState<AvatarViewer> createState() => _AvatarViewerState();
}

class _AvatarViewerState extends ConsumerState<AvatarViewer> with AutomaticKeepAliveClientMixin {
  InAppWebViewController? _webViewController;
  bool _isReady = false;
  
  @override
  bool get wantKeepAlive => true; // Keep WebView alive across rebuilds
  
  @override
  void initState() {
    super.initState();
    debugPrint('[AvatarViewer] Initializing WebView avatar viewer');
    
    // Register animation callbacks with avatar controller IMMEDIATELY
    // Don't wait for post-frame callback - controller needs these NOW
    final controller = ref.read(avatarControllerProvider);
    controller.registerCallbacks(
      onStartTalking: startTalking,
      onStopTalking: stopTalking,
    );
    debugPrint('[AvatarViewer] ✅ Registered callbacks with AvatarController');
  }
  
  
  @override
  Widget build(BuildContext context) {
    super.build(context); // Required for AutomaticKeepAliveClientMixin
    
    // Listen to avatar state changes and trigger animations
    ref.listen(avatarRingStateProvider, (previous, next) {
      if (_isReady && _webViewController != null) {
        _applyAvatarState(next);
      }
    });
    
    // Listen to emotion changes and update facial expression
    ref.listen(emotionStateProvider, (previous, next) {
      if (_isReady && _webViewController != null && next != null) {
        _setAvatarEmotion(next.primary);
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
          cacheEnabled: false, // Disable cache to always load fresh content
          underPageBackgroundColor: Colors.transparent,
        ),
      initialUrlRequest: URLRequest(
        url: WebUri('http://localhost:8779/viewer.html?v=${DateTime.now().millisecondsSinceEpoch}'),
      ),
      onWebViewCreated: (controller) async {
        _webViewController = controller;
        debugPrint('[AvatarViewer] WebView created');
        
        // Force transparent background via JavaScript injection
        await controller.evaluateJavascript(source: '''
          document.documentElement.style.backgroundColor = 'transparent';
          document.body.style.backgroundColor = 'transparent';
        ''');
        
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
      onLoadStop: (controller, url) async {
        debugPrint('[AvatarViewer] Loaded: $url');
        
        // Immediately inject CSS to force transparent background
        await controller.evaluateJavascript(source: '''
          (function() {
            document.documentElement.style.backgroundColor = 'transparent';
            document.body.style.backgroundColor = 'transparent';
            
            // Also set via CSS to ensure it sticks
            var style = document.createElement('style');
            style.textContent = 'html, body { background: transparent !important; }';
            document.head.appendChild(style);
          })();
        ''');
        
        // Set native WebView to transparent (macOS only)
        // Try multiple times with delays to catch WebView at different stages
        for (int i = 0; i < 5; i++) {
          await Future.delayed(Duration(milliseconds: 100 * (i + 1)));
          final success = await TransparentWebViewChannel.setTransparentBackground();
          debugPrint('[AvatarViewer] Transparent attempt ${i + 1}: $success');
          if (success) break;
        }
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
  /// Triggers animation changes and background color in Three.js via JavaScript bridge.
  void _applyAvatarState(AvatarRingState state) {
    debugPrint('[AvatarViewer] 🎭 State change received: mode=${state.mode.name}, intensity=${state.intensity}');
    
    if (_webViewController == null) {
      debugPrint('[AvatarViewer] ⚠️ WebViewController is null, skipping state update');
      return;
    }
    
    if (!_isReady) {
      debugPrint('[AvatarViewer] ⚠️ Scene not ready, skipping state update');
      return;
    }
    
    // Trigger appropriate animation function based on mode
    if (state.mode == AvatarMode.speaking) {
      debugPrint('[AvatarViewer] 🎬 Starting talking animation');
      _webViewController!.evaluateJavascript(
        source: "window.startTalking()",
      );
    } else {
      debugPrint('[AvatarViewer] 🎬 Stopping talking animation (returning to idle)');
      _webViewController!.evaluateJavascript(
        source: "window.stopTalking()",
      );
    }
    
    // Background aura is now handled in Flutter (CompanionAvatar)
    // No need to update WebView background - keep it transparent
    
    debugPrint('[AvatarViewer] ✅ State update complete');
  }
  
  /// Set avatar facial expression based on emotion
  /// 
  /// Maps AICO's emotion states to blend shape presets in Three.js.
  /// Emotions smoothly transition using interpolation.
  void _setAvatarEmotion(String emotion) {
    if (_webViewController == null || !_isReady) {
      return;
    }
    
    // Call JavaScript function to update facial expression
    _webViewController!.evaluateJavascript(
      source: "window.setAvatarEmotion('$emotion')",
    );
  }
  
  /// Start talking animation (switch from idle to talking state)
  /// 
  /// Called when AICO starts responding (first streaming chunk).
  /// Triggers talking animation group with automatic variations.
  void startTalking() {
    debugPrint('[AvatarViewer] 🗣️ Starting talking animation');
    
    if (_webViewController == null || !_isReady) {
      debugPrint('[AvatarViewer] ⚠️ Cannot start talking - WebView not ready');
      return;
    }
    
    _webViewController!.evaluateJavascript(
      source: "window.startTalking()",
    );
  }
  
  /// Stop talking animation (switch from talking to idle state)
  /// 
  /// Called when AICO finishes responding (streaming complete).
  /// Returns to idle animation group with automatic variations.
  void stopTalking() {
    debugPrint('[AvatarViewer] 🤫 Stopping talking animation');
    
    if (_webViewController == null || !_isReady) {
      debugPrint('[AvatarViewer] ⚠️ Cannot stop talking - WebView not ready');
      return;
    }
    
    _webViewController!.evaluateJavascript(
      source: "window.stopTalking()",
    );
  }
  
  @override
  void dispose() {
    // Unregister callbacks
    final controller = ref.read(avatarControllerProvider);
    controller.unregisterCallbacks();
    
    _webViewController?.dispose();
    super.dispose();
  }
}

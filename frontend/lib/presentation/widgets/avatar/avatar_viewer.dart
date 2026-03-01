import 'package:aico_frontend/core/platform/transparent_webview_channel.dart';
import 'package:aico_frontend/domain/entities/tts_state.dart';
import 'package:aico_frontend/domain/providers/tts_provider.dart';
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
  late final dynamic _avatarController; // Save controller reference for safe disposal
  
  @override
  bool get wantKeepAlive => true; // Keep WebView alive across rebuilds
  
  @override
  void initState() {
    super.initState();
    
    // Register animation callbacks with avatar controller IMMEDIATELY
    // Don't wait for post-frame callback - controller needs these NOW
    // Save controller reference for safe disposal later
    _avatarController = ref.read(avatarControllerProvider);
    _avatarController.registerCallbacks(
      onStartTalking: startTalking,
      onStopTalking: stopTalking,
    );
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
    
    // Listen to TTS state for lip-sync text preparation
    ref.listen(ttsProvider, (previous, next) {
      if (_isReady && _webViewController != null) {
        _handleTtsStateChange(previous, next);
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
        
        // Force transparent background via JavaScript injection
        await controller.evaluateJavascript(source: '''
          document.documentElement.style.backgroundColor = 'transparent';
          document.body.style.backgroundColor = 'transparent';
        ''');
        
        // Add JavaScript handler for scene ready callback
        controller.addJavaScriptHandler(
          handlerName: 'ready',
          callback: (args) {
            if (mounted) {
              setState(() {
                _isReady = true;
              });
            }
          },
        );
        
        // Add JavaScript handler for audio ended callback
        controller.addJavaScriptHandler(
          handlerName: 'audioEnded',
          callback: (args) {
            // Notify TTS provider that audio finished
            ref.read(ttsProvider.notifier).stop();
          },
        );
      },
      onLoadStart: (controller, url) {
        // Silent
      },
      onLoadStop: (controller, url) async {
        
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
          if (success) break;
        }
      },
      onConsoleMessage: (controller, consoleMessage) {
        // Filter out verbose viseme updates - only log errors and important messages
        final msg = consoleMessage.message;
        if (!msg.contains('Viseme:') && !msg.contains('Emotion set to:')) {
          debugPrint('[AvatarViewer] JS: $msg');
        }
      },
      onReceivedError: (controller, request, error) {
        debugPrint('[AvatarViewer] Load error: ${error.description}');
      },
    );
  }
  
  /// Apply avatar state from AvatarRingStateProvider
  /// 
  /// Maps emotional states and conversation modes to animations.
  /// Triggers animation changes and background color in Three.js via JavaScript bridge.
  void _applyAvatarState(AvatarRingState state) {
    if (_webViewController == null || !_isReady) {
      return;
    }
    
    // Trigger appropriate animation function based on mode
    if (state.mode == AvatarMode.speaking) {
      _webViewController!.evaluateJavascript(
        source: "window.startTalking()",
      );
    } else {
      _webViewController!.evaluateJavascript(
        source: "window.stopTalking()",
      );
    }
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
    if (_webViewController == null || !_isReady) {
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
    if (_webViewController == null || !_isReady) {
      return;
    }
    
    _webViewController!.evaluateJavascript(
      source: "window.stopTalking()",
    );
  }
  
  /// Handle TTS state changes for lip-sync
  /// 
  /// Passes audio data to WebView for frequency-based lip-sync analysis.
  /// Audio plays in both Flutter (for user) and WebView (for lip-sync).
  void _handleTtsStateChange(TtsState? previous, TtsState next) {
    // Only act when transitioning to speaking state
    if (next.status == TtsStatus.speaking && previous?.status != TtsStatus.speaking) {
      final audioData = next.metadata?['audioData'] as String?;
      
      if (audioData != null && audioData.isNotEmpty) {
        // Pass audio to WebView for lip-sync
        _webViewController!.evaluateJavascript(
          source: """
            (function() {
              if (window.playAudioForLipSync) {
                window.playAudioForLipSync('$audioData');
              }
            })();
          """,
        );
      }
    }
  }
  
  @override
  void dispose() {
    // Unregister callbacks using saved controller reference
    // Safe to use because we saved it during initState()
    _avatarController.unregisterCallbacks();
    
    _webViewController?.dispose();
    super.dispose();
  }
}

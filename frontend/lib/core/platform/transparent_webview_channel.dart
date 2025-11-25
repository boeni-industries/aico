import 'dart:io';
import 'package:flutter/services.dart';

/// Platform channel for making WebView transparent on macOS
/// 
/// This is a workaround for flutter_inappwebview not supporting
/// transparent backgrounds on macOS natively.
class TransparentWebViewChannel {
  static const MethodChannel _channel = MethodChannel('aico.dev/transparent_webview');
  
  /// Sets the WKWebView to have a transparent background on macOS
  /// 
  /// This must be called after the WebView is created and added to the view hierarchy.
  /// Returns true if successful, false otherwise.
  static Future<bool> setTransparentBackground() async {
    // Only works on macOS
    if (!Platform.isMacOS) {
      return false;
    }
    
    try {
      final result = await _channel.invokeMethod('setTransparentBackground');
      if (result is Map && result['success'] == true) {
        final count = result['webViewsModified'] ?? 0;
        print('[TransparentWebViewChannel] Successfully set $count WebView(s) to transparent');
        return true;
      }
      return false;
    } on PlatformException catch (e) {
      print('[TransparentWebViewChannel] Error: ${e.message}');
      return false;
    }
  }
}

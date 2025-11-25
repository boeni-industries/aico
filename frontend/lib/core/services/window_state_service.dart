import 'dart:io';
import 'dart:ui';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:window_manager/window_manager.dart';

/// Service for persisting and restoring window state (position, size)
class WindowStateService with WindowListener {
  static const String _keyWindowX = 'window_x';
  static const String _keyWindowY = 'window_y';
  static const String _keyWindowWidth = 'window_width';
  static const String _keyWindowHeight = 'window_height';
  static const String _keyWindowMaximized = 'window_maximized';
  
  final SharedPreferences _prefs;
  bool _isInitialized = false;
  
  WindowStateService(this._prefs);
  
  /// Initialize window state service and restore previous state
  Future<void> initialize() async {
    if (_isInitialized) return;
    
    // Only run on desktop platforms
    if (!kIsWeb && (Platform.isWindows || Platform.isLinux || Platform.isMacOS)) {
      try {
        await windowManager.ensureInitialized();
        
        // Set minimum size and other window options (but NOT size/position/center)
        const windowOptions = WindowOptions(
          minimumSize: Size(800, 600),
          backgroundColor: Colors.transparent,
          skipTaskbar: false,
          titleBarStyle: TitleBarStyle.normal,
        );
        
        // Wait until ready, then restore state
        await windowManager.waitUntilReadyToShow(windowOptions, () async {
          // Restore previous window state (position, size, maximized)
          await _restoreWindowState();
          
          // Set window title with version
          try {
            final packageInfo = await PackageInfo.fromPlatform();
            await windowManager.setTitle('AICO v${packageInfo.version}');
          } catch (e) {
            debugPrint('[WindowStateService] Failed to set window title: $e');
            await windowManager.setTitle('AICO');
          }
          
          // Show and focus window
          await windowManager.show();
          await windowManager.focus();
        });
        
        // Add this service as a window listener AFTER restoration
        windowManager.addListener(this);
        
        _isInitialized = true;
        debugPrint('[WindowStateService] Initialized and restored window state');
      } catch (e) {
        debugPrint('[WindowStateService] Failed to initialize: $e');
      }
    }
  }
  
  /// Restore window state from preferences
  Future<void> _restoreWindowState() async {
    try {
      final isMaximized = _prefs.getBool(_keyWindowMaximized) ?? false;
      
      if (isMaximized) {
        await windowManager.maximize();
        debugPrint('[WindowStateService] Restored maximized state');
      } else {
        final x = _prefs.getDouble(_keyWindowX);
        final y = _prefs.getDouble(_keyWindowY);
        final width = _prefs.getDouble(_keyWindowWidth);
        final height = _prefs.getDouble(_keyWindowHeight);
        
        if (x != null && y != null && width != null && height != null) {
          await windowManager.setBounds(
            null,
            position: Offset(x, y),
            size: Size(width, height),
          );
          debugPrint('[WindowStateService] Restored window bounds: ($x, $y, $width, $height)');
        } else {
          // First launch - set default size and center
          await windowManager.setSize(const Size(1200, 800));
          await windowManager.center();
          debugPrint('[WindowStateService] First launch - set default size and centered');
        }
      }
    } catch (e) {
      debugPrint('[WindowStateService] Failed to restore window state: $e');
    }
  }
  
  /// Save current window state to preferences
  Future<void> _saveWindowState() async {
    try {
      final isMaximized = await windowManager.isMaximized();
      await _prefs.setBool(_keyWindowMaximized, isMaximized);
      
      if (!isMaximized) {
        final bounds = await windowManager.getBounds();
        await _prefs.setDouble(_keyWindowX, bounds.left);
        await _prefs.setDouble(_keyWindowY, bounds.top);
        await _prefs.setDouble(_keyWindowWidth, bounds.width);
        await _prefs.setDouble(_keyWindowHeight, bounds.height);
        
        debugPrint('[WindowStateService] Saved window bounds: (${bounds.left}, ${bounds.top}, ${bounds.width}, ${bounds.height})');
      } else {
        debugPrint('[WindowStateService] Saved maximized state');
      }
    } catch (e) {
      debugPrint('[WindowStateService] Failed to save window state: $e');
    }
  }
  
  /// Clean up resources
  void dispose() {
    if (_isInitialized) {
      windowManager.removeListener(this);
      _isInitialized = false;
    }
  }
  
  // WindowListener callbacks - save state on changes
  
  @override
  void onWindowMoved() {
    _saveWindowState();
  }
  
  @override
  void onWindowResized() {
    _saveWindowState();
  }
  
  @override
  void onWindowMaximize() {
    _saveWindowState();
  }
  
  @override
  void onWindowUnmaximize() {
    _saveWindowState();
  }
  
  @override
  void onWindowClose() {
    // Save one final time before closing
    _saveWindowState();
  }
}

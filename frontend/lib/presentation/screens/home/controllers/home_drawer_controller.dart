import 'package:flutter/material.dart';

/// Controller for drawer state management
/// 
/// Manages:
/// - Left drawer expanded/collapsed state
/// - Right drawer open/closed and expanded/collapsed state
/// - Thought scrolling coordination
class DrawerController extends ChangeNotifier {
  bool _isLeftDrawerExpanded = false;
  bool _isRightDrawerOpen = true;
  bool _isRightDrawerExpanded = false;
  String? _scrollToThoughtId;

  bool get isLeftDrawerExpanded => _isLeftDrawerExpanded;
  bool get isRightDrawerOpen => _isRightDrawerOpen;
  bool get isRightDrawerExpanded => _isRightDrawerExpanded;
  String? get scrollToThoughtId => _scrollToThoughtId;

  void toggleLeftDrawer() {
    _isLeftDrawerExpanded = !_isLeftDrawerExpanded;
    notifyListeners();
  }

  void toggleRightDrawer() {
    _isRightDrawerExpanded = !_isRightDrawerExpanded;
    notifyListeners();
  }

  void setRightDrawerOpen(bool isOpen) {
    _isRightDrawerOpen = isOpen;
    notifyListeners();
  }

  void scrollToThought(String? thoughtId) {
    _scrollToThoughtId = thoughtId;
    notifyListeners();
  }
}

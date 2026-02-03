import 'package:aico_frontend/presentation/screens/home/widgets/home_left_drawer.dart';
import 'package:flutter/material.dart';

/// Controller for home screen navigation
/// 
/// Manages:
/// - Current page selection (home, memory, admin, settings)
/// - Page switching logic
class NavigationController extends ChangeNotifier {
  NavigationPage _currentPage = NavigationPage.home;

  NavigationPage get currentPage => _currentPage;

  void switchToPage(NavigationPage page) {
    if (_currentPage != page) {
      _currentPage = page;
      notifyListeners();
    }
  }
}

import 'package:aico_frontend/presentation/widgets/navigation/adaptive_bottom_navigation.dart';
import 'package:aico_frontend/presentation/widgets/navigation/adaptive_sidebar_navigation.dart';
import 'package:aico_frontend/presentation/widgets/navigation/floating_voice_button.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

/// Main layout wrapper that provides adaptive navigation structure.
/// Implements hub-and-spoke navigation with platform-specific patterns:
/// - Mobile: Bottom tab navigation with floating voice button
/// - Desktop: Collapsible sidebar with persistent avatar area
/// - Web: Hybrid approach supporting both patterns
class MainLayout extends StatelessWidget {
  final Widget child;

  const MainLayout({
    super.key,
    required this.child,
  });

  @override
  Widget build(BuildContext context) {
    final currentRoute = GoRouterState.of(context).matchedLocation;
    
    return Scaffold(
      body: _buildAdaptiveLayout(context, currentRoute),
      bottomNavigationBar: _buildBottomNavigation(context, currentRoute),
      floatingActionButton: _buildFloatingVoiceButton(context),
      floatingActionButtonLocation: FloatingActionButtonLocation.centerDocked,
    );
  }

  Widget _buildAdaptiveLayout(BuildContext context, String currentRoute) {
    // Use responsive breakpoints to determine layout
    final screenWidth = MediaQuery.of(context).size.width;
    final isDesktop = screenWidth >= 1024;
    final isTablet = screenWidth >= 768 && screenWidth < 1024;

    if (isDesktop) {
      // Desktop: Sidebar + content area
      return Row(
        children: [
          AdaptiveSidebarNavigation(currentRoute: currentRoute),
          Expanded(
            child: Container(
              margin: const EdgeInsets.all(16),
              child: child,
            ),
          ),
        ],
      );
    } else if (isTablet) {
      // Tablet: Collapsible sidebar or bottom nav based on orientation
      final isLandscape = MediaQuery.of(context).orientation == Orientation.landscape;
      
      if (isLandscape) {
        return Row(
          children: [
            AdaptiveSidebarNavigation(
              currentRoute: currentRoute,
              isCollapsed: true,
            ),
            Expanded(
              child: Container(
                margin: const EdgeInsets.all(12),
                child: child,
              ),
            ),
          ],
        );
      }
    }

    // Mobile/Portrait tablet: Full-screen content with bottom navigation
    return SafeArea(
      child: child,
    );
  }

  Widget? _buildBottomNavigation(BuildContext context, String currentRoute) {
    final screenWidth = MediaQuery.of(context).size.width;
    final isDesktop = screenWidth >= 1024;
    final isTabletLandscape = screenWidth >= 768 && 
        MediaQuery.of(context).orientation == Orientation.landscape;

    // Hide bottom navigation on desktop and tablet landscape
    if (isDesktop || isTabletLandscape) {
      return null;
    }

    return AdaptiveBottomNavigation(currentRoute: currentRoute);
  }

  Widget? _buildFloatingVoiceButton(BuildContext context) {
    final screenWidth = MediaQuery.of(context).size.width;
    final isDesktop = screenWidth >= 1024;

    // Show floating voice button on mobile/tablet only
    if (isDesktop) {
      return null;
    }

    return const FloatingVoiceButton();
  }
}

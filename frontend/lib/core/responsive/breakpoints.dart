import 'package:flutter/material.dart';

/// Responsive breakpoint definitions for AICO's multi-platform UI
class Breakpoints {
  /// Mobile portrait breakpoint (width < 768px)
  static const double mobile = 768;
  
  /// Tablet breakpoint (width >= 768px, < 1024px)
  static const double tablet = 1024;
  
  /// Desktop breakpoint (width >= 1024px)
  static const double desktop = 1024;

  /// Check if current device is mobile portrait
  /// 
  /// Mobile portrait uses vertical stacking layouts:
  /// - Avatar top, messages bottom
  /// - Full width components
  static bool isMobilePortrait(BuildContext context) {
    final size = MediaQuery.of(context).size;
    return size.width < mobile && size.height > size.width;
  }

  /// Check if current device is mobile landscape
  /// 
  /// Mobile landscape uses horizontal layouts like desktop:
  /// - Avatar left, messages right
  /// - Side-by-side components
  static bool isMobileLandscape(BuildContext context) {
    final size = MediaQuery.of(context).size;
    return size.width < mobile && size.width > size.height;
  }

  /// Check if current device is tablet
  static bool isTablet(BuildContext context) {
    final width = MediaQuery.of(context).size.width;
    return width >= mobile && width < desktop;
  }

  /// Check if current device is desktop
  static bool isDesktop(BuildContext context) {
    final width = MediaQuery.of(context).size.width;
    return width >= desktop;
  }

  /// Determine if vertical layout should be used
  /// 
  /// Vertical layout (stacking):
  /// - Mobile portrait only
  /// - Avatar top, messages bottom
  /// 
  /// Horizontal layout (side-by-side):
  /// - Desktop, tablet, mobile landscape
  /// - Avatar left, messages right
  static bool shouldUseVerticalLayout(BuildContext context) {
    return isMobilePortrait(context);
  }

  /// Get horizontal padding based on screen size
  static double getHorizontalPadding(BuildContext context) {
    if (isDesktop(context)) {
      return 40.0;
    } else if (isTablet(context)) {
      return 24.0;
    } else {
      return 16.0;
    }
  }

  /// Get vertical padding based on screen size
  static double getVerticalPadding(BuildContext context) {
    if (isDesktop(context)) {
      return 40.0;
    } else if (isTablet(context)) {
      return 24.0;
    } else {
      return 20.0;
    }
  }

  /// Get maximum content width for centered layouts
  static double getMaxContentWidth(BuildContext context) {
    if (isDesktop(context)) {
      return 1200.0;
    } else if (isTablet(context)) {
      return 900.0;
    } else {
      return double.infinity; // Full width on mobile
    }
  }

  /// Get sidebar width based on screen size and collapsed state
  static double getSidebarWidth(BuildContext context, {required bool collapsed}) {
    if (!isDesktop(context)) {
      return 0.0; // No sidebar on mobile/tablet
    }
    return collapsed ? 72.0 : 240.0;
  }

  /// Get message bubble max width based on screen size
  static double getMessageMaxWidth(BuildContext context) {
    if (isDesktop(context)) {
      return 800.0;
    } else if (isTablet(context)) {
      final width = MediaQuery.of(context).size.width;
      return width * 0.9;
    } else {
      final width = MediaQuery.of(context).size.width;
      return width * 0.95;
    }
  }

  /// Get input field max width based on screen size
  static double getInputMaxWidth(BuildContext context) {
    return getMessageMaxWidth(context);
  }

  /// Get avatar container size based on modality and platform
  static Size getAvatarSize(
    BuildContext context, {
    required double heightPercent,
    required double widthPercent,
  }) {
    final screenSize = MediaQuery.of(context).size;
    return Size(
      screenSize.width * widthPercent,
      screenSize.height * heightPercent,
    );
  }

  /// Get responsive font size
  static double getFontSize(BuildContext context, double baseSize) {
    if (isDesktop(context)) {
      return baseSize;
    } else if (isTablet(context)) {
      return baseSize * 0.95;
    } else {
      return baseSize * 0.9;
    }
  }

  /// Get responsive icon size
  static double getIconSize(BuildContext context, double baseSize) {
    if (isDesktop(context)) {
      return baseSize;
    } else if (isTablet(context)) {
      return baseSize * 0.95;
    } else {
      return baseSize * 0.9;
    }
  }
}

/// Extension on BuildContext for convenient breakpoint access
extension BreakpointExtension on BuildContext {
  /// Check if mobile portrait
  bool get isMobilePortrait => Breakpoints.isMobilePortrait(this);
  
  /// Check if mobile landscape
  bool get isMobileLandscape => Breakpoints.isMobileLandscape(this);
  
  /// Check if tablet
  bool get isTablet => Breakpoints.isTablet(this);
  
  /// Check if desktop
  bool get isDesktop => Breakpoints.isDesktop(this);
  
  /// Check if should use vertical layout
  bool get shouldUseVerticalLayout => Breakpoints.shouldUseVerticalLayout(this);
  
  /// Get horizontal padding
  double get horizontalPadding => Breakpoints.getHorizontalPadding(this);
  
  /// Get vertical padding
  double get verticalPadding => Breakpoints.getVerticalPadding(this);
  
  /// Get max content width
  double get maxContentWidth => Breakpoints.getMaxContentWidth(this);
  
  /// Get message max width
  double get messageMaxWidth => Breakpoints.getMessageMaxWidth(this);
  
  /// Get input max width
  double get inputMaxWidth => Breakpoints.getInputMaxWidth(this);
}

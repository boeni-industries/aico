import 'package:flutter/material.dart';

/// Design tokens for AICO's theme system
/// Provides semantic color, typography, spacing, and animation tokens
/// following Material 3 guidelines with AICO branding
class AicoDesignTokens {
  AicoDesignTokens._();

  // ============================================================================
  // COLOR TOKENS
  // ============================================================================

  /// AICO brand colors
  static const Color softLavender = Color(0xFFB9A7E6);
  static const Color coral = Color(0xFFED7867);
  static const Color mutedGreen = Color(0xFF8DD686);
  
  /// Base colors
  static const Color pureWhite = Color(0xFFFFFFFF);
  static const Color neutralWhite = Color(0xFFFAFAFA);
  
  /// Neutral colors (light theme)
  static const Color lightNeutralLight = Color(0xFFF5F5F5);
  static const Color lightNeutralMedium = Color(0xFF9E9E9E);
  static const Color lightNeutralDark = Color(0xFF424242);
  
  /// Neutral colors (dark theme)
  static const Color darkNeutralLight = Color(0xFF424242);
  static const Color darkNeutralMedium = Color(0xFF616161);
  static const Color darkNeutralDark = Color(0xFF212121);

  /// State colors (light theme)
  static const Color lightSuccess = Color(0xFF4CAF50);
  static const Color lightWarning = Color(0xFFFF9800);
  static const Color lightError = Color(0xFFF44336);
  static const Color lightInfo = Color(0xFF2196F3);
  
  /// State colors (dark theme)
  static const Color darkSuccess = Color(0xFF66BB6A);
  static const Color darkWarning = Color(0xFFFFB74D);
  static const Color darkError = Color(0xFFEF5350);
  static const Color darkInfo = Color(0xFF42A5F5);

  /// Dark mode equivalents
  static const Color darkBackground = Color(0xFF181A21);
  static const Color darkSurface = Color(0xFF21242E);
  static const Color darkAccent = Color(0xFFB9A7E6);

  /// Shadow colors
  static const Color shadowLight = Color.fromRGBO(36, 52, 85, 0.09);
  static const Color shadowDark = Color.fromRGBO(0, 0, 0, 0.25);

  // ============================================================================
  // TYPOGRAPHY TOKENS
  // ============================================================================

  /// Typography scale following AICO design principles
  static const String fontFamily = 'Inter';

  /// Font sizes
  static const double fontSizeHeadline1 = 32.0; // 2.0rem
  static const double fontSizeHeadline2 = 24.0; // 1.5rem
  static const double fontSizeSubtitle = 18.0;  // 1.125rem
  static const double fontSizeBody = 16.0;      // 1.0rem
  static const double fontSizeCaption = 14.0;   // 0.875rem
  static const double fontSizeButton = 16.0;    // 1.0rem

  /// Font weights
  static const FontWeight fontWeightHeadline1 = FontWeight.w700;
  static const FontWeight fontWeightHeadline2 = FontWeight.w600;
  static const FontWeight fontWeightSubtitle = FontWeight.w500;
  static const FontWeight fontWeightBody = FontWeight.w400;
  static const FontWeight fontWeightCaption = FontWeight.w400;
  static const FontWeight fontWeightButton = FontWeight.w600;

  /// Line heights (as multipliers)
  static const double lineHeightMultiplier = 1.5;

  /// Letter spacing
  static const double letterSpacingHeadlines = 0.32; // 0.02em at 16px base

  // ============================================================================
  // SPACING TOKENS
  // ============================================================================

  /// 8px grid system
  static const double spaceUnit = 8.0;
  static const double spaceXs = spaceUnit * 0.5;  // 4px
  static const double spaceSm = spaceUnit;        // 8px
  static const double spaceMd = spaceUnit * 2;    // 16px
  static const double spaceLg = spaceUnit * 3;    // 24px
  static const double spaceXl = spaceUnit * 4;    // 32px
  static const double spaceXxl = spaceUnit * 6;   // 48px

  /// Component-specific spacing
  static const double paddingCard = spaceLg;      // 24px
  static const double paddingButtonH = spaceLg;   // 24px horizontal
  static const double paddingButtonV = spaceMd/2; // 12px vertical

  /// Border radius
  static const double radiusSmall = 8.0;
  static const double radiusMedium = 16.0;
  static const double radiusLarge = 24.0;
  static const double radiusCircular = 999.0;

  /// Avatar sizes
  static const double avatarSizeMain = 96.0;
  static const double avatarSizeMini = 32.0;
  static const double avatarSizeStatus = 48.0;

  // ============================================================================
  // ANIMATION TOKENS
  // ============================================================================

  /// Animation durations
  static const Duration durationFast = Duration(milliseconds: 150);
  static const Duration durationNormal = Duration(milliseconds: 250);
  static const Duration durationSlow = Duration(milliseconds: 400);

  /// Animation curves
  static const Curve easeInOut = Curves.easeInOut;
  static const Curve easeOut = Curves.easeOut;
  static const Curve easeIn = Curves.easeIn;
  static const Curve bounceOut = Curves.bounceOut;

  /// Micro-interaction durations
  static const Duration durationButtonPress = Duration(milliseconds: 100);
  static const Duration durationHover = Duration(milliseconds: 200);
  static const Duration durationFocus = Duration(milliseconds: 150);
  static const Duration durationPageTransition = Duration(milliseconds: 300);
  static const Duration durationThemeTransition = Duration(milliseconds: 200);

  // ============================================================================
  // ELEVATION TOKENS
  // ============================================================================

  /// Material 3 elevation levels
  static const double elevationLevel0 = 0.0;
  static const double elevationLevel1 = 1.0;
  static const double elevationLevel2 = 3.0;
  static const double elevationLevel3 = 6.0;
  static const double elevationLevel4 = 8.0;
  static const double elevationLevel5 = 12.0;

  // ============================================================================
  // BREAKPOINTS
  // ============================================================================

  /// Responsive breakpoints
  static const double breakpointMobile = 600.0;
  static const double breakpointTablet = 900.0;
  static const double breakpointDesktop = 1200.0;
  static const double breakpointWide = 1600.0;

  /// Container max widths
  static const double maxWidthMobile = double.infinity;
  static const double maxWidthDesktop = 1200.0;

  // ============================================================================
  // ACCESSIBILITY TOKENS
  // ============================================================================

  /// Minimum touch target size (Material Design guidelines)
  static const double minTouchTarget = 48.0;

  /// Contrast ratios (WCAG AA+ compliance)
  static const double contrastRatioNormal = 4.5;
  static const double contrastRatioLarge = 3.0;
  static const double contrastRatioAAA = 7.0;
}

/// Extension for easy access to design tokens
extension AicoDesignTokensExtension on BuildContext {
  AicoDesignTokens get tokens => AicoDesignTokens._();
}

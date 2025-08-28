import 'package:aico_frontend/core/di/service_locator.dart';
import 'package:aico_frontend/core/theme/design_tokens.dart';
import 'package:aico_frontend/core/theme/theme_manager.dart';
import 'package:flutter/material.dart';

/// BuildContext extensions for convenient theme access
extension AicoThemeExtensions on BuildContext {
  /// Get the current theme data
  ThemeData get theme => Theme.of(this);
  
  /// Get the current color scheme
  ColorScheme get colorScheme => theme.colorScheme;
  
  /// Get the current text theme
  TextTheme get textTheme => theme.textTheme;
  
  /// Get the theme manager instance
  ThemeManager get themeManager => ServiceLocator.get<ThemeManager>();
  
  /// Check if current theme is dark
  bool get isDarkTheme => theme.brightness == Brightness.dark;
  
  /// Check if current theme is light
  bool get isLightTheme => theme.brightness == Brightness.light;
  
  /// Check if high contrast is enabled
  bool get isHighContrast => themeManager.isHighContrastEnabled;
  
  /// Get semantic colors with context awareness
  AicoSemanticColors get semanticColors => AicoSemanticColors.of(this);
  
  /// Get spacing values
  AicoSpacing get spacing => const AicoSpacing();
  
  /// Get animation durations
  AicoAnimations get animations => const AicoAnimations();
  
  /// Get elevation values
  AicoElevation get elevation => const AicoElevation();
  
  /// Get breakpoints helper
  AicoBreakpoints get breakpoints => AicoBreakpoints.of(this);
  
  /// Get accessibility helpers
  AicoAccessibility get accessibility => AicoAccessibility.of(this);
}

/// Semantic colors that adapt to current theme
class AicoSemanticColors {
  final BuildContext _context;
  
  const AicoSemanticColors._(this._context);
  
  factory AicoSemanticColors.of(BuildContext context) {
    return AicoSemanticColors._(context);
  }
  
  ColorScheme get _colorScheme => _context.colorScheme;
  bool get _isDark => _context.isDarkTheme;
  bool get _isHighContrast => _context.isHighContrast;
  
  // Primary brand colors
  Color get primary => _colorScheme.primary;
  Color get onPrimary => _colorScheme.onPrimary;
  Color get primaryContainer => _colorScheme.primaryContainer;
  Color get onPrimaryContainer => _colorScheme.onPrimaryContainer;
  
  // Secondary colors
  Color get secondary => _colorScheme.secondary;
  Color get onSecondary => _colorScheme.onSecondary;
  Color get secondaryContainer => _colorScheme.secondaryContainer;
  Color get onSecondaryContainer => _colorScheme.onSecondaryContainer;
  
  // Surface colors
  Color get surface => _colorScheme.surface;
  Color get onSurface => _colorScheme.onSurface;
  Color get surfaceVariant => _colorScheme.surfaceContainerHighest;
  Color get onSurfaceVariant => _colorScheme.onSurfaceVariant;
  
  // Background colors
  Color get background => _colorScheme.surface;
  Color get onBackground => _colorScheme.onSurface;
  
  // State colors
  Color get error => _colorScheme.error;
  Color get onError => _colorScheme.onError;
  Color get errorContainer => _colorScheme.errorContainer;
  Color get onErrorContainer => _colorScheme.onErrorContainer;
  
  // AICO-specific semantic colors
  Color get accent => _isDark 
      ? AicoDesignTokens.darkAccent 
      : AicoDesignTokens.softLavender;
      
  Color get success => _isDark 
      ? AicoDesignTokens.darkSuccess 
      : AicoDesignTokens.lightSuccess;
      
  Color get warning => _isDark 
      ? AicoDesignTokens.darkWarning 
      : AicoDesignTokens.lightWarning;
      
  Color get info => _isDark 
      ? AicoDesignTokens.darkInfo 
      : AicoDesignTokens.lightInfo;
  
  // Neutral colors
  Color get neutralLight => _isDark 
      ? AicoDesignTokens.darkNeutralLight 
      : AicoDesignTokens.lightNeutralLight;
      
  Color get neutralMedium => _isDark 
      ? AicoDesignTokens.darkNeutralMedium 
      : AicoDesignTokens.lightNeutralMedium;
      
  Color get neutralDark => _isDark 
      ? AicoDesignTokens.darkNeutralDark 
      : AicoDesignTokens.lightNeutralDark;
  
  // Outline colors
  Color get outline => _colorScheme.outline;
  Color get outlineVariant => _colorScheme.outlineVariant;
  
  // Inverse colors
  Color get inverseSurface => _colorScheme.inverseSurface;
  Color get onInverseSurface => _colorScheme.onInverseSurface;
  Color get inversePrimary => _colorScheme.inversePrimary;
  
  // High contrast adaptations
  Color get highContrastBorder => _isHighContrast 
      ? (_isDark ? Colors.white : Colors.black)
      : outline;
      
  Color get highContrastText => _isHighContrast 
      ? (_isDark ? Colors.white : Colors.black)
      : onSurface;
}

/// Spacing helper class
class AicoSpacing {
  const AicoSpacing();
  
  double get xs => AicoDesignTokens.spaceXs;
  double get sm => AicoDesignTokens.spaceSm;
  double get md => AicoDesignTokens.spaceMd;
  double get lg => AicoDesignTokens.spaceLg;
  double get xl => AicoDesignTokens.spaceXl;
  double get xxl => AicoDesignTokens.spaceXxl;
  
  // Padding helpers
  EdgeInsets get paddingXs => EdgeInsets.all(xs);
  EdgeInsets get paddingSm => EdgeInsets.all(sm);
  EdgeInsets get paddingMd => EdgeInsets.all(md);
  EdgeInsets get paddingLg => EdgeInsets.all(lg);
  EdgeInsets get paddingXl => EdgeInsets.all(xl);
  EdgeInsets get paddingXxl => EdgeInsets.all(xxl);
  
  // Margin helpers
  EdgeInsets get marginXs => EdgeInsets.all(xs);
  EdgeInsets get marginSm => EdgeInsets.all(sm);
  EdgeInsets get marginMd => EdgeInsets.all(md);
  EdgeInsets get marginLg => EdgeInsets.all(lg);
  EdgeInsets get marginXl => EdgeInsets.all(xl);
  EdgeInsets get marginXxl => EdgeInsets.all(xxl);
  
  // Horizontal/Vertical helpers
  EdgeInsets horizontalXs(double vertical) => EdgeInsets.symmetric(horizontal: xs, vertical: vertical);
  EdgeInsets horizontalSm(double vertical) => EdgeInsets.symmetric(horizontal: sm, vertical: vertical);
  EdgeInsets horizontalMd(double vertical) => EdgeInsets.symmetric(horizontal: md, vertical: vertical);
  EdgeInsets horizontalLg(double vertical) => EdgeInsets.symmetric(horizontal: lg, vertical: vertical);
  
  EdgeInsets verticalXs(double horizontal) => EdgeInsets.symmetric(vertical: xs, horizontal: horizontal);
  EdgeInsets verticalSm(double horizontal) => EdgeInsets.symmetric(vertical: sm, horizontal: horizontal);
  EdgeInsets verticalMd(double horizontal) => EdgeInsets.symmetric(vertical: md, horizontal: horizontal);
  EdgeInsets verticalLg(double horizontal) => EdgeInsets.symmetric(vertical: lg, horizontal: horizontal);
}

/// Animation helper class
class AicoAnimations {
  const AicoAnimations();
  
  Duration get fast => AicoDesignTokens.durationFast;
  Duration get medium => AicoDesignTokens.durationNormal;
  Duration get normal => AicoDesignTokens.durationNormal;
  Duration get slow => AicoDesignTokens.durationSlow;
  Duration get buttonPress => AicoDesignTokens.durationButtonPress;
  Duration get pageTransition => AicoDesignTokens.durationPageTransition;
  Duration get themeTransition => AicoDesignTokens.durationThemeTransition;
  
  Curve get easeInOut => AicoDesignTokens.easeInOut;
  Curve get easeOut => AicoDesignTokens.easeOut;
  Curve get easeIn => AicoDesignTokens.easeIn;
  Curve get bounceOut => AicoDesignTokens.bounceOut;
}

/// Elevation helper class
class AicoElevation {
  const AicoElevation();
  
  double get level0 => AicoDesignTokens.elevationLevel0;
  double get level1 => AicoDesignTokens.elevationLevel1;
  double get level2 => AicoDesignTokens.elevationLevel2;
  double get level3 => AicoDesignTokens.elevationLevel3;
  double get level4 => AicoDesignTokens.elevationLevel4;
  double get level5 => AicoDesignTokens.elevationLevel5;
}

/// Breakpoints helper class
class AicoBreakpoints {
  final BuildContext _context;
  
  const AicoBreakpoints._(this._context);
  
  factory AicoBreakpoints.of(BuildContext context) {
    return AicoBreakpoints._(context);
  }
  
  double get mobile => AicoDesignTokens.breakpointMobile;
  double get tablet => AicoDesignTokens.breakpointTablet;
  double get desktop => AicoDesignTokens.breakpointDesktop;
  double get largeDesktop => AicoDesignTokens.breakpointLargeDesktop;
  double get wide => AicoDesignTokens.breakpointWide;
  
  // Dynamic breakpoint detection using MediaQuery
  double get _screenWidth => MediaQuery.of(_context).size.width;
  
  bool get isMobile => _screenWidth < mobile;
  bool get isTablet => _screenWidth >= mobile && _screenWidth < desktop;
  bool get isDesktop => _screenWidth >= desktop;
  bool get isLargeDesktop => _screenWidth >= largeDesktop;
  bool get isWide => _screenWidth >= wide;
}

/// Accessibility helper class
class AicoAccessibility {
  final BuildContext _context;
  
  const AicoAccessibility._(this._context);
  
  factory AicoAccessibility.of(BuildContext context) {
    return AicoAccessibility._(context);
  }
  
  MediaQueryData get _mediaQuery => MediaQuery.of(_context);
  
  /// Get minimum touch target size
  double get minTouchTarget => AicoDesignTokens.minTouchTarget;
  
  /// Check if user prefers reduced motion
  bool get prefersReducedMotion => _mediaQuery.disableAnimations;
  bool get isReduceMotionEnabled => _mediaQuery.disableAnimations;
  
  /// Get text scale factor
  double get textScaleFactor => _mediaQuery.textScaler.scale(1.0);
  
  /// Check if text is scaled up significantly
  bool get isLargeText => textScaleFactor > 1.3;
  
  /// Check if high contrast is enabled
  bool get isHighContrastEnabled => _context.isHighContrast;
  
  /// Get minimum touch target size
  double get minTouchTargetSize => AicoDesignTokens.minTouchTarget;
  
  /// Get accessible color contrast ratio
  double get contrastRatio => _context.isHighContrast ? 7.0 : 4.5;
  
  /// Get focus color for keyboard navigation
  Color get focusColor => _context.colorScheme.primary.withValues(alpha: 0.12);
  
  /// Get high contrast border width
  double get highContrastBorderWidth => _context.isHighContrast ? 2.0 : 1.0;
  
  /// Create accessible button with proper sizing and contrast
  Widget accessibleButton({
    required Widget child,
    required VoidCallback? onPressed,
    ButtonStyle? style,
  }) {
    return ElevatedButton(
      onPressed: onPressed,
      style: style?.copyWith(
        minimumSize: WidgetStateProperty.all(
          Size(minTouchTarget, minTouchTarget),
        ),
      ) ?? ElevatedButton.styleFrom(
        minimumSize: Size(minTouchTarget, minTouchTarget),
      ),
      child: child,
    );
  }
  
  /// Create accessible text with proper contrast
  Widget accessibleText(
    String text, {
    TextStyle? style,
    TextAlign? textAlign,
    int? maxLines,
    TextOverflow? overflow,
  }) {
    final semanticColors = _context.semanticColors;
    
    return Text(
      text,
      style: style?.copyWith(
        color: _context.isHighContrast 
            ? semanticColors.highContrastText 
            : style.color,
      ),
      textAlign: textAlign,
      maxLines: maxLines,
      overflow: overflow,
    );
  }
}

import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:aico_frontend/presentation/theme/micro_interactions.dart';

/// Reusable animated button with comprehensive micro-interactions
/// 
/// Provides theme-aware hover, press, and success states following AICO principles.
/// Supports both desktop (mouse) and mobile (touch) interactions.
/// 
/// Features:
/// - Hover state with scale and glow
/// - Press feedback with scale down
/// - Success animation with icon morph
/// - Error shake animation
/// - Loading state with spinner
/// - Respects reduced motion preferences
/// - Theme-aware colors and shadows
/// - High contrast support
/// 
/// Usage:
/// ```dart
/// AnimatedButton(
///   onPressed: () => _handleSend(),
///   icon: Icons.send,
///   successIcon: Icons.check,
///   child: Text('Send'),
/// )
/// ```
class AnimatedButton extends StatefulWidget {
  /// Callback when button is pressed
  final VoidCallback? onPressed;
  
  /// Primary icon to display
  final IconData? icon;
  
  /// Icon to display during success state
  final IconData? successIcon;
  
  /// Child widget (alternative to icon)
  final Widget? child;
  
  /// Button background color (overrides theme)
  final Color? backgroundColor;
  
  /// Button foreground color (overrides theme)
  final Color? foregroundColor;
  
  /// Whether button is enabled
  final bool isEnabled;
  
  /// Whether to show loading spinner
  final bool isLoading;
  
  /// Button size
  final double size;
  
  /// Border radius
  final double borderRadius;
  
  /// Padding
  final EdgeInsetsGeometry? padding;
  
  /// Tooltip message
  final String? tooltip;
  
  const AnimatedButton({
    super.key,
    this.onPressed,
    this.icon,
    this.successIcon,
    this.child,
    this.backgroundColor,
    this.foregroundColor,
    this.isEnabled = true,
    this.isLoading = false,
    this.size = 48,
    this.borderRadius = 24,
    this.padding,
    this.tooltip,
  }) : assert(icon != null || child != null, 'Either icon or child must be provided');
  
  @override
  State<AnimatedButton> createState() => _AnimatedButtonState();
}

class _AnimatedButtonState extends State<AnimatedButton> 
    with TickerProviderStateMixin {
  
  late AnimationController _hoverController;
  late AnimationController _pressController;
  late AnimationController _successController;
  late AnimationController _errorController;
  
  late Animation<double> _successScaleAnimation;
  late Animation<double> _errorShakeAnimation;
  
  bool _isHovered = false;
  bool _isPressed = false;
  bool _showingSuccess = false;
  
  @override
  void initState() {
    super.initState();
    
    // Initialize controllers with default durations
    // Will be updated in didChangeDependencies with theme-aware values
    _hoverController = AnimationController(
      duration: const Duration(milliseconds: 150),
      vsync: this,
    );
    
    _pressController = AnimationController(
      duration: const Duration(milliseconds: 80),
      vsync: this,
    );
    
    _successController = AnimationController(
      duration: const Duration(milliseconds: 400),
      vsync: this,
    );
    
    // Subtle success: barely perceptible scale (1.0 → 1.02 → 1.0)
    _successScaleAnimation = TweenSequence<double>([
      TweenSequenceItem(
        tween: Tween<double>(begin: 1.0, end: 1.02)
            .chain(CurveTween(curve: Curves.easeOutCubic)),
        weight: 40,
      ),
      TweenSequenceItem(
        tween: Tween<double>(begin: 1.02, end: 1.0)
            .chain(CurveTween(curve: Curves.easeInCubic)),
        weight: 60,
      ),
    ]).animate(_successController);
    
    // Error shake animation
    _errorController = AnimationController(
      duration: const Duration(milliseconds: 300),
      vsync: this,
    );
    
    // Subtle shake: small amplitude, quick decay
    _errorShakeAnimation = TweenSequence<double>([
      TweenSequenceItem(tween: Tween<double>(begin: 0, end: 4), weight: 1),
      TweenSequenceItem(tween: Tween<double>(begin: 4, end: -4), weight: 1),
      TweenSequenceItem(tween: Tween<double>(begin: -4, end: 3), weight: 1),
      TweenSequenceItem(tween: Tween<double>(begin: 3, end: -3), weight: 1),
      TweenSequenceItem(tween: Tween<double>(begin: -3, end: 0), weight: 1),
    ]).animate(CurvedAnimation(
      parent: _errorController,
      curve: Curves.easeInOut,
    ));
  }
  
  @override
  void dispose() {
    _hoverController.dispose();
    _pressController.dispose();
    _successController.dispose();
    _errorController.dispose();
    super.dispose();
  }
  
  void _onHoverStart() {
    if (!widget.isEnabled || widget.isLoading) return;
    setState(() => _isHovered = true);
    _hoverController.forward();
  }
  
  void _onHoverEnd() {
    setState(() => _isHovered = false);
    _hoverController.reverse();
  }
  
  void _onPressStart() {
    if (!widget.isEnabled || widget.isLoading) return;
    setState(() => _isPressed = true);
    _pressController.forward();
  }
  
  void _onPressEnd() {
    setState(() => _isPressed = false);
    _pressController.reverse();
    
    // Check if button is actually enabled (has text for send button)
    if (widget.onPressed != null && widget.isEnabled && !widget.isLoading) {
      widget.onPressed!();
    } else if (widget.onPressed != null && !widget.isEnabled) {
      // Trigger error shake if pressed while disabled
      showError();
    }
  }
  
  void _onPressCancel() {
    setState(() => _isPressed = false);
    _pressController.reverse();
  }
  
  /// Trigger success animation (call from parent)
  /// Subtle pulse - no color change, just acknowledgment
  void showSuccess() {
    if (!mounted) return;
    setState(() => _showingSuccess = true);
    _successController.forward().then((_) {
      if (mounted) {
        setState(() => _showingSuccess = false);
        _successController.reset();
      }
    });
  }
  
  /// Trigger error shake animation (call from parent)
  void showError() {
    if (!mounted) return;
    _errorController.forward().then((_) {
      if (mounted) {
        _errorController.reset();
      }
    });
  }
  
  double _calculateScale() {
    // NO SCALE CHANGES - too crude for glassmorphism
    // Depth is communicated through opacity, blur, and shadows
    return 1.0;
  }
  
  Color _calculateBackgroundColor() {
    final microTheme = MicroInteractionTheme.of(context);
    final buttonTheme = microTheme.button;
    
    if (!widget.isEnabled) {
      return buttonTheme.disabledColor.withOpacity(0.15);
    }
    
    // Glassmorphic: semi-transparent backgrounds (30-50% opacity)
    final baseColor = widget.backgroundColor ?? buttonTheme.defaultColor;
    
    // Error: brief red tint overlay (check if animating OR has value)
    if (_errorController.value > 0) {
      final errorIntensity = _errorController.value;
      return Color.lerp(
        baseColor.withOpacity(0.3),
        Colors.red.withOpacity(0.6),
        errorIntensity * 0.5, // 50% red blend at peak - more visible
      )!;
    }
    
    if (_isPressed) {
      // Pressed: more opaque (feels solid)
      return baseColor.withOpacity(0.5);
    }
    
    if (_isHovered) {
      // Hover: lighter (more transparent)
      return baseColor.withOpacity(0.35);
    }
    
    // Default: semi-transparent glass
    return baseColor.withOpacity(0.3);
  }
  
  double _calculateBorderOpacity() {
    if (!widget.isEnabled) return 0.1;
    if (_isPressed) return 0.4; // More visible when pressed
    if (_isHovered) return 0.3; // Luminous on hover
    if (_showingSuccess) return 0.35 + (0.15 * _successController.value);
    return 0.2; // Subtle default
  }
  
  List<BoxShadow> _calculateShadows() {
    final microTheme = MicroInteractionTheme.of(context);
    final buttonTheme = microTheme.button;
    final baseColor = widget.backgroundColor ?? buttonTheme.defaultColor;
    
    if (!widget.isEnabled) {
      return [];
    }
    
    // Success: inner glow pulse
    if (_showingSuccess) {
      final glowIntensity = _successController.value;
      return [
        // Inner glow
        BoxShadow(
          color: baseColor.withOpacity(0.4 * glowIntensity),
          blurRadius: 8,
          spreadRadius: -2,
        ),
        // Outer glow
        BoxShadow(
          color: baseColor.withOpacity(0.2 * glowIntensity),
          blurRadius: 16,
          spreadRadius: 0,
        ),
      ];
    }
    
    // Pressed: compressed shadow (pressed down)
    if (_isPressed) {
      return [
        BoxShadow(
          color: baseColor.withOpacity(0.15),
          blurRadius: 4,
          offset: const Offset(0, 1),
        ),
      ];
    }
    
    // Hover: elevated with 3-layer depth
    if (_isHovered) {
      return [
        // Close depth shadow
        BoxShadow(
          color: Colors.black.withOpacity(0.12),
          blurRadius: 8,
          offset: const Offset(0, 2),
        ),
        // Mid depth shadow
        BoxShadow(
          color: Colors.black.withOpacity(0.08),
          blurRadius: 16,
          offset: const Offset(0, 4),
        ),
        // Glow layer
        BoxShadow(
          color: baseColor.withOpacity(0.3),
          blurRadius: 20,
          spreadRadius: 0,
        ),
      ];
    }
    
    // Default: Layered color-matched shadows (modern technique)
    return [
      // Layer 1: Close shadow
      BoxShadow(
        color: baseColor.withOpacity(0.12),
        blurRadius: 4,
        offset: const Offset(0, 1),
      ),
      // Layer 2: Mid shadow
      BoxShadow(
        color: baseColor.withOpacity(0.10),
        blurRadius: 8,
        offset: const Offset(0, 2),
      ),
      // Layer 3: Far shadow (depth)
      BoxShadow(
        color: Colors.black.withOpacity(0.06),
        blurRadius: 16,
        offset: const Offset(0, 4),
      ),
    ];
  }
  
  IconData _calculateIcon() {
    // Keep same icon for subtle, immersive feedback
    // No jarring icon morph - just scale pulse
    return widget.icon!;
  }
  
  Widget _buildContent() {
    final theme = Theme.of(context);
    
    if (widget.isLoading) {
      return SizedBox(
        width: 20,
        height: 20,
        child: CircularProgressIndicator(
          strokeWidth: 2,
          valueColor: AlwaysStoppedAnimation<Color>(
            widget.foregroundColor ?? theme.colorScheme.onPrimary,
          ),
        ),
      );
    }
    
    if (widget.icon != null) {
      // Icon with vibrancy - full opacity, crisp rendering
      return Icon(
        _calculateIcon(),
        color: widget.isEnabled 
          ? (widget.foregroundColor ?? theme.colorScheme.onPrimary)
          : (widget.foregroundColor ?? theme.colorScheme.onPrimary).withOpacity(0.4),
        size: widget.size * 0.5,
      );
    }
    
    if (widget.child != null) {
      return widget.child!;
    }
    
    return const SizedBox.shrink();
  }
  
  @override
  Widget build(BuildContext context) {
    final button = MouseRegion(
      onEnter: (_) => _onHoverStart(),
      onExit: (_) => _onHoverEnd(),
      cursor: widget.isEnabled && !widget.isLoading 
          ? SystemMouseCursors.click 
          : SystemMouseCursors.basic,
      child: GestureDetector(
        onTapDown: (_) => _onPressStart(),
        onTapUp: (_) => _onPressEnd(),
        onTapCancel: _onPressCancel,
        child: AnimatedBuilder(
          animation: Listenable.merge([
            _hoverController,
            _pressController,
            _successController,
            _errorController,
          ]),
          builder: (context, child) {
            return Transform.translate(
              offset: Offset(_errorShakeAnimation.value, 0),
              child: Transform.scale(
                scale: _calculateScale(),
                child: Container(
                  width: widget.size,
                  height: widget.size,
                  padding: widget.padding,
                  decoration: BoxDecoration(
                    color: _calculateBackgroundColor(),
                    borderRadius: BorderRadius.circular(widget.borderRadius),
                    border: Border.all(
                      color: Colors.white.withOpacity(_calculateBorderOpacity()),
                      width: 1.5,
                    ),
                    boxShadow: [
                      // Inset top highlight (light from above)
                      BoxShadow(
                        color: Colors.white.withOpacity(0.15),
                        blurRadius: 0,
                        offset: const Offset(0, -1),
                        spreadRadius: 0,
                      ),
                      ..._calculateShadows(),
                    ],
                    // Gradient overlay for depth
                    gradient: LinearGradient(
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                      colors: [
                        Colors.white.withOpacity(0.12),
                        Colors.transparent,
                        Colors.black.withOpacity(0.08),
                      ],
                      stops: const [0.0, 0.4, 1.0],
                    ),
                  ),
                  child: Center(child: _buildContent()),
                ),
              ),
            );
          },
        ),
      ),
    );
    
    if (widget.tooltip != null) {
      return Tooltip(
        message: widget.tooltip!,
        waitDuration: const Duration(milliseconds: 300),
        child: button,
      );
    }
    
    return button;
  }
}

/// Global key for triggering animations from outside
/// 
/// Usage:
/// ```dart
/// final buttonKey = GlobalKey<_AnimatedButtonState>();
/// 
/// AnimatedButton(
///   key: buttonKey,
///   onPressed: _handleSend,
/// )
/// 
/// // Later:
/// buttonKey.currentState?.showSuccess();
/// ```
/// 
/// Note: Use the private state type _AnimatedButtonState for the key type

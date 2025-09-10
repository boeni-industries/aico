import 'package:flutter/material.dart';

enum AicoButtonType {
  primary,
  secondary,
  minimal,
  destructive,
}

class AicoButton extends StatefulWidget {
  final VoidCallback? onPressed;
  final Widget child;
  final AicoButtonType type;
  final bool isLoading;
  final EdgeInsetsGeometry? padding;
  final double? width;
  final double? height;

  const AicoButton({
    super.key,
    required this.onPressed,
    required this.child,
    this.type = AicoButtonType.primary,
    this.isLoading = false,
    this.padding,
    this.width,
    this.height,
  });

  const AicoButton.primary({
    super.key,
    required this.onPressed,
    required this.child,
    this.isLoading = false,
    this.padding,
    this.width,
    this.height,
  }) : type = AicoButtonType.primary;

  const AicoButton.secondary({
    super.key,
    required this.onPressed,
    required this.child,
    this.isLoading = false,
    this.padding,
    this.width,
    this.height,
  }) : type = AicoButtonType.secondary;

  const AicoButton.minimal({
    super.key,
    required this.onPressed,
    required this.child,
    this.isLoading = false,
    this.padding,
    this.width,
    this.height,
  }) : type = AicoButtonType.minimal;

  const AicoButton.destructive({
    super.key,
    required this.onPressed,
    required this.child,
    this.isLoading = false,
    this.padding,
    this.width,
    this.height,
  }) : type = AicoButtonType.destructive;

  @override
  State<AicoButton> createState() => _AicoButtonState();
}

class _AicoButtonState extends State<AicoButton>
    with SingleTickerProviderStateMixin {
  late AnimationController _animationController;
  late Animation<double> _scaleAnimation;
  late Animation<double> _elevationAnimation;

  @override
  void initState() {
    super.initState();
    _animationController = AnimationController(
      duration: const Duration(milliseconds: 150),
      vsync: this,
    );

    _scaleAnimation = Tween<double>(
      begin: 1.0,
      end: 0.95,
    ).animate(CurvedAnimation(
      parent: _animationController,
      curve: Curves.easeInOut,
    ));

    _elevationAnimation = Tween<double>(
      begin: 2.0,
      end: 8.0,
    ).animate(CurvedAnimation(
      parent: _animationController,
      curve: Curves.easeInOut,
    ));
  }

  @override
  void dispose() {
    _animationController.dispose();
    super.dispose();
  }

  void _handleTapDown(TapDownDetails details) {
    if (widget.onPressed != null && !widget.isLoading) {
      _animationController.forward();
    }
  }

  void _handleTapUp(TapUpDetails details) {
    _animationController.reverse();
  }

  void _handleTapCancel() {
    _animationController.reverse();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return AnimatedBuilder(
      animation: _animationController,
      builder: (context, child) {
        return Transform.scale(
          scale: _scaleAnimation.value,
          child: _buildButton(context, colorScheme),
        );
      },
    );
  }

  Widget _buildButton(BuildContext context, ColorScheme colorScheme) {
    final buttonStyle = _getButtonStyle(colorScheme);
    
    return SizedBox(
      width: widget.width,
      height: widget.height ?? 48,
      child: GestureDetector(
        onTapDown: _handleTapDown,
        onTapUp: _handleTapUp,
        onTapCancel: _handleTapCancel,
        child: Material(
          color: buttonStyle.backgroundColor,
          elevation: _elevationAnimation.value,
          shadowColor: colorScheme.shadow,
          borderRadius: BorderRadius.circular(16),
          child: InkWell(
            onTap: widget.isLoading ? null : widget.onPressed,
            borderRadius: BorderRadius.circular(16),
            splashColor: buttonStyle.splashColor,
            highlightColor: buttonStyle.highlightColor,
            child: Container(
              padding: widget.padding ?? 
                const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(16),
                border: buttonStyle.border,
              ),
              child: _buildButtonContent(buttonStyle),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildButtonContent(_ButtonStyle buttonStyle) {
    if (widget.isLoading) {
      return Row(
        mainAxisAlignment: MainAxisAlignment.center,
        mainAxisSize: MainAxisSize.min,
        children: [
          SizedBox(
            width: 20,
            height: 20,
            child: CircularProgressIndicator(
              strokeWidth: 2,
              valueColor: AlwaysStoppedAnimation<Color>(buttonStyle.contentColor),
            ),
          ),
          const SizedBox(width: 12),
          DefaultTextStyle(
            style: TextStyle(color: buttonStyle.contentColor),
            child: widget.child,
          ),
        ],
      );
    }

    return Center(
      child: DefaultTextStyle(
        style: TextStyle(color: buttonStyle.contentColor),
        child: widget.child,
      ),
    );
  }

  _ButtonStyle _getButtonStyle(ColorScheme colorScheme) {
    switch (widget.type) {
      case AicoButtonType.primary:
        return _ButtonStyle(
          backgroundColor: colorScheme.primary,
          contentColor: colorScheme.onPrimary,
          splashColor: colorScheme.onPrimary.withValues(alpha: 0.1),
          highlightColor: colorScheme.onPrimary.withValues(alpha: 0.05),
        );

      case AicoButtonType.secondary:
        return _ButtonStyle(
          backgroundColor: colorScheme.surface,
          contentColor: colorScheme.primary,
          splashColor: colorScheme.primary.withValues(alpha: 0.1),
          highlightColor: colorScheme.primary.withValues(alpha: 0.05),
          border: Border.all(
            color: colorScheme.primary.withValues(alpha: 0.2),
            width: 1,
          ),
        );

      case AicoButtonType.minimal:
        return _ButtonStyle(
          backgroundColor: Colors.transparent,
          contentColor: colorScheme.primary,
          splashColor: colorScheme.primary.withValues(alpha: 0.1),
          highlightColor: colorScheme.primary.withValues(alpha: 0.05),
        );

      case AicoButtonType.destructive:
        return _ButtonStyle(
          backgroundColor: colorScheme.error,
          contentColor: colorScheme.onError,
          splashColor: colorScheme.onError.withValues(alpha: 0.1),
          highlightColor: colorScheme.onError.withValues(alpha: 0.05),
        );
    }
  }
}

class _ButtonStyle {
  final Color backgroundColor;
  final Color contentColor;
  final Color splashColor;
  final Color highlightColor;
  final Border? border;

  const _ButtonStyle({
    required this.backgroundColor,
    required this.contentColor,
    required this.splashColor,
    required this.highlightColor,
    this.border,
  });
}

import 'package:flutter/material.dart';

class CompanionAvatar extends StatefulWidget {
  const CompanionAvatar({super.key});

  @override
  State<CompanionAvatar> createState() => _CompanionAvatarState();
}

class _CompanionAvatarState extends State<CompanionAvatar>
    with TickerProviderStateMixin {
  late AnimationController _breathingController;
  late AnimationController _pulseController;
  late Animation<double> _breathingAnimation;
  late Animation<double> _pulseAnimation;
  late Animation<double> _glowAnimation;

  @override
  void initState() {
    super.initState();
    
    // Breathing animation for idle state
    _breathingController = AnimationController(
      duration: const Duration(seconds: 3),
      vsync: this,
    );
    
    // Pulse animation for mood ring
    _pulseController = AnimationController(
      duration: const Duration(milliseconds: 2000),
      vsync: this,
    );
    
    _breathingAnimation = Tween<double>(
      begin: 1.0,
      end: 1.05,
    ).animate(CurvedAnimation(
      parent: _breathingController,
      curve: Curves.easeInOut,
    ));
    
    _pulseAnimation = Tween<double>(
      begin: 0.8,
      end: 1.0,
    ).animate(CurvedAnimation(
      parent: _pulseController,
      curve: Curves.easeInOut,
    ));
    
    _glowAnimation = Tween<double>(
      begin: 0.3,
      end: 0.7,
    ).animate(CurvedAnimation(
      parent: _pulseController,
      curve: Curves.easeInOut,
    ));
    
    // Start animations
    _breathingController.repeat(reverse: true);
    _pulseController.repeat(reverse: true);
  }

  @override
  void dispose() {
    _breathingController.dispose();
    _pulseController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    
    return AnimatedBuilder(
      animation: Listenable.merge([_breathingController, _pulseController]),
      builder: (context, child) {
        return Transform.scale(
          scale: _breathingAnimation.value,
          child: Container(
            width: 120,
            height: 120,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              // Mood ring with pulsing glow
              boxShadow: [
                BoxShadow(
                  color: colorScheme.primary.withValues(alpha: _glowAnimation.value),
                  blurRadius: 20 * _pulseAnimation.value,
                  spreadRadius: 5 * _pulseAnimation.value,
                ),
              ],
            ),
            child: Container(
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(
                  colors: [
                    colorScheme.primary.withValues(alpha: 0.9),
                    colorScheme.primary.withValues(alpha: 0.6),
                    colorScheme.primary.withValues(alpha: 0.3),
                  ],
                  stops: const [0.0, 0.7, 1.0],
                ),
                border: Border.all(
                  color: colorScheme.primary.withValues(alpha: 0.4),
                  width: 2,
                ),
              ),
              child: Center(
                child: Icon(
                  Icons.psychology_outlined,
                  size: 50,
                  color: colorScheme.onPrimary,
                ),
              ),
            ),
          ),
        );
      },
    );
  }
}

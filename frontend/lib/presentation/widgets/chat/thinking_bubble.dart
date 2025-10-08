import 'dart:async';
import 'dart:math';
import 'package:flutter/material.dart';

/// Premium thinking bubble with particle formation and soft glow pulse
/// Particles spawn from edges, converge to center where text will appear
class ThinkingBubble extends StatefulWidget {
  const ThinkingBubble({super.key});

  @override
  State<ThinkingBubble> createState() => _ThinkingBubbleState();
}

class _ThinkingBubbleState extends State<ThinkingBubble>
    with TickerProviderStateMixin {
  late AnimationController _glowController;
  late AnimationController _scaleController;
  late Animation<double> _glowAnimation;
  late Animation<double> _scaleAnimation;

  final List<ThinkingParticle> _particles = [];
  final Random _random = Random();
  Timer? _particleSpawnTimer;

  @override
  void initState() {
    super.initState();
    
    print('🎨🎨🎨 [ThinkingBubble] WIDGET INITIALIZED - Particles should appear!');

    // Scale animation for entrance
    _scaleController = AnimationController(
      duration: const Duration(milliseconds: 300),
      vsync: this,
    );
    _scaleAnimation = CurvedAnimation(
      parent: _scaleController,
      curve: Curves.easeOutBack,
    );
    _scaleController.forward();

    // Glow pulse animation
    _glowController = AnimationController(
      duration: const Duration(milliseconds: 1800),
      vsync: this,
    );
    _glowAnimation = Tween<double>(begin: 0.02, end: 0.05).animate(
      CurvedAnimation(
        parent: _glowController,
        curve: Curves.easeInOut,
      ),
    );
    _glowController.repeat(reverse: true);

    // Start particles immediately
    print('🎨🎨🎨 [ThinkingBubble] Starting particle system!');
    _startParticleSystem();
  }
  void _startParticleSystem() {
    // Spawn particles more frequently
    _particleSpawnTimer = Timer.periodic(
      const Duration(milliseconds: 200), // Faster spawning (was 400ms)
      (timer) {
        if (mounted) {
          setState(() {
            _spawnParticle();
            _spawnParticle(); // Spawn 2 particles at once
          });
        }
      },
    );
  }

  void _spawnParticle() {
    // Random spawn position (from edges)
    final spawnSide = _random.nextInt(4); // 0=top, 1=right, 2=bottom, 3=left
    Offset startPos;

    switch (spawnSide) {
      case 0: // Top
        startPos = Offset(_random.nextDouble(), 0);
        break;
      case 1: // Right
        startPos = Offset(1, _random.nextDouble());
        break;
      case 2: // Bottom
        startPos = Offset(_random.nextDouble(), 1);
        break;
      default: // Left
        startPos = Offset(0, _random.nextDouble());
    }

    // Target position (text start area - left-center)
    final targetPos = Offset(0.15, 0.5);

    // Create particle with much more visible properties
    final particle = ThinkingParticle(
      id: DateTime.now().millisecondsSinceEpoch + _random.nextInt(1000),
      startPosition: startPos,
      targetPosition: targetPos,
      size: 6.0 + _random.nextDouble() * 6.0, // 6-12px (was 3-6px)
      opacity: 0.6 + _random.nextDouble() * 0.4, // 0.6-1.0 (was 0.3-0.7)
      duration: Duration(
        milliseconds: 1000 + _random.nextInt(800), // 1000-1800ms (slower for visibility)
      ),
      color: Color.lerp(
        const Color(0xFF6B9BD1), // Sapphire
        const Color(0xFFB8A1EA), // Soft purple
        _random.nextDouble(),
      )!,
    );

    _particles.add(particle);

    // Remove particle after animation completes
    Future.delayed(particle.duration, () {
      if (mounted) {
        setState(() {
          _particles.removeWhere((p) => p.id == particle.id);
        });
      }
    });

    // Allow more particles (was 12)
    if (_particles.length > 24) {
      _particles.removeAt(0);
    }
  }

  @override
  void dispose() {
    _scaleController.dispose();
    _glowController.dispose();
    _particleSpawnTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final surfaceColor = theme.colorScheme.surface;
    
    return ScaleTransition(
      scale: _scaleAnimation,
      child: AnimatedBuilder(
        animation: _glowAnimation,
        builder: (context, child) {
          return Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              gradient: RadialGradient(
                center: Alignment.center,
                radius: 1.5,
                colors: [
                  const Color(0xFFB8A1EA).withOpacity(_glowAnimation.value * 0.5),
                  surfaceColor.withOpacity(0.0),
                ],
              ),
            ),
            child: Stack(
              children: [
                // Particle system - no size constraints, fills available space
                ..._particles
                    .map((particle) => ParticleWidget(particle: particle))
                    .toList(),
              ],
            ),
          );
        },
      ),
    );
  }
}

/// Particle data model
class ThinkingParticle {
  final int id;
  final Offset startPosition;
  final Offset targetPosition;
  final double size;
  final double opacity;
  final Duration duration;
  final Color color;

  ThinkingParticle({
    required this.id,
    required this.startPosition,
    required this.targetPosition,
    required this.size,
    required this.opacity,
    required this.duration,
    required this.color,
  });
}

/// Individual particle widget with bezier curve animation
class ParticleWidget extends StatefulWidget {
  final ThinkingParticle particle;

  const ParticleWidget({super.key, required this.particle});

  @override
  State<ParticleWidget> createState() => _ParticleWidgetState();
}

class _ParticleWidgetState extends State<ParticleWidget>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<Offset> _positionAnimation;
  late Animation<double> _opacityAnimation;

  @override
  void initState() {
    super.initState();

    _controller = AnimationController(
      duration: widget.particle.duration,
      vsync: this,
    );

    // Bezier curve path (not straight line)
    _positionAnimation = TweenSequence<Offset>([
      TweenSequenceItem(
        tween: Tween<Offset>(
          begin: widget.particle.startPosition,
          end: Offset(
            (widget.particle.startPosition.dx +
                    widget.particle.targetPosition.dx) /
                2,
            (widget.particle.startPosition.dy +
                    widget.particle.targetPosition.dy) /
                    2 -
                0.1,
          ),
        ).chain(CurveTween(curve: Curves.easeOut)),
        weight: 50,
      ),
      TweenSequenceItem(
        tween: Tween<Offset>(
          begin: Offset(
            (widget.particle.startPosition.dx +
                    widget.particle.targetPosition.dx) /
                2,
            (widget.particle.startPosition.dy +
                    widget.particle.targetPosition.dy) /
                    2 -
                0.1,
          ),
          end: widget.particle.targetPosition,
        ).chain(CurveTween(curve: Curves.easeIn)),
        weight: 50,
      ),
    ]).animate(_controller);

    // Fade in, stay, fade out near end
    _opacityAnimation = TweenSequence<double>([
      TweenSequenceItem(
        tween: Tween<double>(begin: 0.0, end: widget.particle.opacity),
        weight: 20,
      ),
      TweenSequenceItem(
        tween: ConstantTween<double>(widget.particle.opacity),
        weight: 60,
      ),
      TweenSequenceItem(
        tween: Tween<double>(begin: widget.particle.opacity, end: 0.0),
        weight: 20,
      ),
    ]).animate(_controller);

    _controller.forward();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        return Positioned(
          left: _positionAnimation.value.dx * 200,
          top: _positionAnimation.value.dy * 40,
          child: Opacity(
            opacity: _opacityAnimation.value,
            child: Container(
              width: widget.particle.size,
              height: widget.particle.size,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(
                  colors: [
                    widget.particle.color.withOpacity(0.9),
                    widget.particle.color.withOpacity(0.4),
                    widget.particle.color.withOpacity(0.1),
                    widget.particle.color.withOpacity(0.0),
                  ],
                  stops: const [0.0, 0.4, 0.7, 1.0],
                ),
                boxShadow: [
                  BoxShadow(
                    color: widget.particle.color.withOpacity(0.3),
                    blurRadius: widget.particle.size * 2.0,
                    spreadRadius: 0,
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}

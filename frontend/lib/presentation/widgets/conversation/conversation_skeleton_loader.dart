import 'package:flutter/material.dart';

/// Glassmorphic skeleton loader for conversation loading state
class ConversationSkeletonLoader extends StatefulWidget {
  const ConversationSkeletonLoader({super.key});

  @override
  State<ConversationSkeletonLoader> createState() => _ConversationSkeletonLoaderState();
}

class _ConversationSkeletonLoaderState extends State<ConversationSkeletonLoader>
    with TickerProviderStateMixin {
  late AnimationController _pulseController;
  late List<AnimationController> _bubbleControllers;
  late List<Animation<double>> _bubbleAnimations;

  @override
  void initState() {
    super.initState();

    _pulseController = AnimationController(
      duration: const Duration(milliseconds: 2000),
      vsync: this,
    )..repeat(reverse: true);

    _bubbleControllers = List.generate(
      3,
      (index) => AnimationController(
        duration: const Duration(milliseconds: 2000),
        vsync: this,
      )..repeat(reverse: true),
    );

    _bubbleAnimations = _bubbleControllers.asMap().entries.map((entry) {
      final index = entry.key;
      final controller = entry.value;
      
      Future.delayed(Duration(milliseconds: index * 200), () {
        if (mounted) controller.forward();
      });

      return Tween<double>(begin: 0.3, end: 0.6).animate(
        CurvedAnimation(parent: controller, curve: Curves.easeInOut),
      );
    }).toList();
  }

  @override
  void dispose() {
    _pulseController.dispose();
    for (var controller in _bubbleControllers) {
      controller.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 40, vertical: 24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            _buildSkeletonBubble(0, isUser: true, isDark: isDark),
            const SizedBox(height: 12),
            _buildSkeletonBubble(1, isUser: false, isDark: isDark),
            const SizedBox(height: 12),
            _buildSkeletonBubble(2, isUser: true, isDark: isDark),
            const SizedBox(height: 24),
            AnimatedBuilder(
              animation: _pulseController,
              builder: (context, child) {
                return Opacity(
                  opacity: 0.3 + (_pulseController.value * 0.3),
                  child: Text(
                    'Loading conversation...',
                    style: theme.textTheme.bodySmall?.copyWith(
                      fontStyle: FontStyle.italic,
                      color: isDark ? Colors.white70 : Colors.black54,
                    ),
                  ),
                );
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSkeletonBubble(int index, {required bool isUser, required bool isDark}) {
    return AnimatedBuilder(
      animation: _bubbleAnimations[index],
      builder: (context, child) {
        final opacity = _bubbleAnimations[index].value;
        
        return Align(
          alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
          child: Container(
            constraints: const BoxConstraints(maxWidth: 400),
            height: 60,
            decoration: BoxDecoration(
              color: isDark
                  ? Colors.white.withOpacity(0.04 * opacity)
                  : Colors.white.withOpacity(0.5 * opacity),
              borderRadius: BorderRadius.circular(28),
              border: Border.all(
                color: isDark
                    ? Colors.white.withOpacity(0.1 * opacity)
                    : Colors.white.withOpacity(0.3 * opacity),
                width: 1.5,
              ),
              boxShadow: [
                BoxShadow(
                  color: isDark
                      ? Colors.black.withOpacity(0.3 * opacity)
                      : Colors.black.withOpacity(0.08 * opacity),
                  blurRadius: 20,
                  offset: const Offset(0, 6),
                  spreadRadius: -4,
                ),
                if (!isUser)
                  BoxShadow(
                    color: const Color(0xFFB8A1EA).withOpacity(0.1 * opacity),
                    blurRadius: 40,
                    spreadRadius: -5,
                  ),
              ],
            ),
          ),
        );
      },
    );
  }
}

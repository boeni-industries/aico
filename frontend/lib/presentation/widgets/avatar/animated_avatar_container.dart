import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/responsive/breakpoints.dart';
import '../../providers/layout_provider.dart';

/// Animated container for avatar that smoothly transitions between modalities
/// 
/// Handles:
/// - Size changes (30-80% height, 30-100% width)
/// - Position changes (center, left, top)
/// - Scale changes (0.95 when thinking)
/// - Smooth 800ms cubic-bezier transitions
class AnimatedAvatarContainer extends ConsumerWidget {
  final Widget child;

  const AnimatedAvatarContainer({
    super.key,
    required this.child,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final layoutState = ref.watch(layoutProvider);
    final isVertical = context.shouldUseVerticalLayout;
    
    final screenSize = MediaQuery.of(context).size;
    final heightPercent = layoutState.getAvatarHeightPercent(isVertical);
    final widthPercent = layoutState.getAvatarWidthPercent(isVertical);
    final alignment = layoutState.getAvatarAlignment(isVertical);
    final scale = layoutState.avatarScale;

    return AnimatedAlign(
      duration: const Duration(milliseconds: 800),
      curve: Curves.easeInOutCubic,
      alignment: alignment,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 800),
        curve: Curves.easeInOutCubic,
        width: screenSize.width * widthPercent,
        height: screenSize.height * heightPercent,
        child: AnimatedScale(
          duration: const Duration(milliseconds: 800),
          curve: Curves.easeInOutCubic,
          scale: scale,
          child: child,
        ),
      ),
    );
  }
}

/// Wrapper for avatar WebView with proper sizing and transitions
class AvatarWebViewContainer extends ConsumerWidget {
  final Widget webView;

  const AvatarWebViewContainer({
    super.key,
    required this.webView,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return RepaintBoundary(
      child: ClipRRect(
        borderRadius: BorderRadius.circular(0), // No clipping for full avatar
        child: webView,
      ),
    );
  }
}

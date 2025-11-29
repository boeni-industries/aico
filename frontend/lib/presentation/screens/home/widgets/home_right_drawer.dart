import 'dart:async';
import 'dart:ui';

import 'package:aico_frontend/presentation/providers/conversation_provider.dart';
import 'package:aico_frontend/presentation/providers/emotion_provider.dart';
import 'package:aico_frontend/presentation/providers/settings_provider.dart';
import 'package:aico_frontend/presentation/theme/glassmorphism.dart';
import 'package:aico_frontend/presentation/widgets/drawer/drawer_tab_switcher.dart';
import 'package:aico_frontend/presentation/widgets/emotion/emotional_timeline.dart';
import 'package:aico_frontend/presentation/widgets/thinking/ambient_thinking_indicator.dart';
import 'package:aico_frontend/presentation/widgets/thinking/thinking_preview_card.dart';
import 'package:aico_frontend/presentation/widgets/thinking_display.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Right drawer for thoughts and thinking display
/// Features progressive disclosure with three layers:
/// 1. Ambient indicator (collapsed)
/// 2. Preview card (on hover)
/// 3. Full drawer (on click)
class HomeRightDrawer extends ConsumerStatefulWidget {
  final Color accentColor;
  final AnimationController glowController;
  final Animation<double> glowAnimation;
  final bool isExpanded;
  final VoidCallback onToggle;
  final String? scrollToMessageId;

  const HomeRightDrawer({
    super.key,
    required this.accentColor,
    required this.glowController,
    required this.glowAnimation,
    required this.isExpanded,
    required this.onToggle,
    this.scrollToMessageId,
  });

  @override
  ConsumerState<HomeRightDrawer> createState() => _HomeRightDrawerState();
}

class _HomeRightDrawerState extends ConsumerState<HomeRightDrawer> {
  bool _showThinkingPreview = false;
  Timer? _hoverTimer;
  DrawerTab _selectedTab = DrawerTab.thinking;

  @override
  void dispose() {
    _hoverTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final conversationState = ref.watch(conversationProvider);
    final isActivelyThinking = conversationState.streamingThinking != null &&
        conversationState.streamingThinking!.isNotEmpty;

    return Padding(
      padding: const EdgeInsets.all(16.0),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(GlassTheme.radiusXLarge),
        child: AnimatedBuilder(
          animation: widget.glowController,
          builder: (context, child) {
            // Beautiful breathing effect
            final pulseValue = widget.glowAnimation.value;
            final blurIntensity = isActivelyThinking
                ? GlassTheme.blurHeavy + (pulseValue * 6.0)
                : GlassTheme.blurHeavy;

            final glassOpacity = isActivelyThinking
                ? (isDark ? 0.04 : 0.6) + (pulseValue * (isDark ? 0.02 : 0.08))
                : (isDark ? 0.04 : 0.6);

            final borderOpacity = isActivelyThinking
                ? (isDark ? 0.1 : 0.4) + (pulseValue * 0.15)
                : (isDark ? 0.1 : 0.4);

            return BackdropFilter(
              filter: ImageFilter.blur(
                sigmaX: blurIntensity,
                sigmaY: blurIntensity,
              ),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(GlassTheme.radiusXLarge),
                clipBehavior: Clip.hardEdge,
                child: Container(
                  width: widget.isExpanded ? 300 : 72,
                  decoration: BoxDecoration(
                    color: isDark
                        ? Colors.white.withValues(alpha: glassOpacity)
                        : Colors.white.withValues(alpha: glassOpacity),
                    borderRadius: BorderRadius.circular(GlassTheme.radiusXLarge),
                    border: Border.all(
                      color: isDark
                          ? Colors.white.withValues(alpha: borderOpacity)
                          : Colors.white.withValues(alpha: borderOpacity),
                      width: 1.5,
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withValues(alpha: isDark ? 0.4 : 0.08),
                        blurRadius: 40,
                        offset: const Offset(-8, 0),
                        spreadRadius: -10,
                      ),
                      if (isDark)
                        BoxShadow(
                          color: widget.accentColor.withValues(
                              alpha: 0.08 + (isActivelyThinking ? pulseValue * 0.06 : 0.0)),
                          blurRadius: 60 + (isActivelyThinking ? pulseValue * 20 : 0.0),
                          spreadRadius: -5,
                        ),
                    ],
                  ),
                  child: SafeArea(
                    child: Column(
                      children: [
                        // Tab switcher (only when expanded)
                        if (widget.isExpanded) ...[
                          Padding(
                            padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
                            child: DrawerTabSwitcher(
                              selectedTab: _selectedTab,
                              onTabChanged: (tab) {
                                setState(() {
                                  _selectedTab = tab;
                                });
                              },
                            ),
                          ),
                        ],
                        Expanded(
                          child: _buildContent(theme, conversationState, isActivelyThinking),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            );
          },
        ),
      ),
    );
  }

  Widget _buildContent(ThemeData theme, ConversationState conversationState, bool isActivelyThinking) {
    final settings = ref.watch(settingsProvider);

    if (!settings.showThinking) {
      return widget.isExpanded
          ? Center(
              child: Text(
                'Thinking display disabled in settings',
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.onSurface.withValues(alpha: 0.5),
                ),
              ),
            )
          : const SizedBox.shrink();
    }

    // Progressive disclosure: Only render full content when expanded
    // This prevents overflow errors when collapsed to 72px width
    if (widget.isExpanded) {
      return AnimatedSwitcher(
        duration: const Duration(milliseconds: 300),
        transitionBuilder: (child, animation) {
          return FadeTransition(
            opacity: animation,
            child: SlideTransition(
              position: Tween<Offset>(
                begin: const Offset(0.1, 0),
                end: Offset.zero,
              ).animate(CurvedAnimation(
                parent: animation,
                curve: Curves.easeOutCubic,
              )),
              child: child,
            ),
          );
        },
        child: _selectedTab == DrawerTab.thinking
            ? ThinkingDisplay(
                key: const ValueKey('thinking'),
                thinkingHistory: conversationState.thinkingHistory,
                currentThinking: conversationState.streamingThinking,
                isStreaming: isActivelyThinking,
                scrollToMessageId: widget.scrollToMessageId,
                onCollapse: widget.onToggle,
              )
            : _buildEmotionalTimeline(),
      );
    }

    // Collapsed state: Only show ambient indicator (fits in 72px)
    return _buildCollapsedIndicator(conversationState, isActivelyThinking);
  }

  Widget _buildEmotionalTimeline() {
    // Lazy loading: only fetch when Emotions tab is selected
    if (_selectedTab != DrawerTab.emotions) {
      return EmotionalTimeline(
        key: const ValueKey('emotions_not_selected'),
        emotionHistory: const [],
        isLoading: false,
        onCollapse: widget.onToggle,
      );
    }
    
    return Consumer(
      builder: (context, ref, child) {
        final historyAsync = ref.watch(emotionHistoryProvider(limit: 50));
        
        return historyAsync.when(
          data: (history) => EmotionalTimeline(
            key: const ValueKey('emotions'),
            emotionHistory: history,
            isLoading: false,
            onCollapse: widget.onToggle,
          ),
          loading: () => EmotionalTimeline(
            key: const ValueKey('emotions_loading'),
            emotionHistory: const [],
            isLoading: true,
            onCollapse: widget.onToggle,
          ),
          error: (error, stack) {
            debugPrint('Error loading emotion history: $error');
            return EmotionalTimeline(
              key: const ValueKey('emotions_error'),
              emotionHistory: const [],
              isLoading: false,
              onCollapse: widget.onToggle,
            );
          },
        );
      },
    );
  }

  Widget _buildCollapsedIndicator(ConversationState conversationState, bool isStreaming) {
    return GestureDetector(
      onTap: widget.onToggle,
      child: Stack(
        children: [
          // Ambient indicator
          Positioned(
            left: 0,
            top: 0,
            bottom: 0,
            child: AmbientThinkingIndicator(
              key: const ValueKey('ambient_indicator'),
              isStreaming: isStreaming,
              thoughtCount: conversationState.thinkingHistory.length,
              onTap: widget.onToggle,
              onHoverStart: () {
                _hoverTimer?.cancel();
                _hoverTimer = Timer(const Duration(milliseconds: 300), () {
                  if (mounted) {
                    setState(() => _showThinkingPreview = true);
                  }
                });
              },
              onHoverEnd: () {
                _hoverTimer?.cancel();
                setState(() => _showThinkingPreview = false);
              },
            ),
          ),

          // Preview card on hover
          if (_showThinkingPreview)
            Positioned(
              right: 88,
              top: 16,
              child: ThinkingPreviewCard(
                streamingThought: conversationState.streamingThinking,
                recentThoughts: conversationState.thinkingHistory.take(3).toList(),
                isStreaming: isStreaming,
                onExpand: widget.onToggle,
              ),
            ),
        ],
      ),
    );
  }
}

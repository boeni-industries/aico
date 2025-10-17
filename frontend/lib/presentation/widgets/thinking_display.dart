import 'package:aico_frontend/presentation/providers/conversation_provider.dart';
import 'package:flutter/material.dart';

/// Widget to display AI's inner monologue (thinking) in the right drawer
/// Following AICO guidelines: Stateless presentation widget, data from provider
/// Research-based design inspired by Claude Artifacts, ChatGPT reasoning display,
/// and modern AI UX patterns with timeline visualization
class ThinkingDisplay extends StatefulWidget {
  final List<ThinkingTurn> thinkingHistory; // From provider
  final String? currentThinking; // Currently streaming thinking
  final bool isStreaming;

  const ThinkingDisplay({
    super.key,
    required this.thinkingHistory,
    this.currentThinking,
    this.isStreaming = false,
  });

  @override
  State<ThinkingDisplay> createState() => _ThinkingDisplayState();
}

class _ThinkingDisplayState extends State<ThinkingDisplay>
    with SingleTickerProviderStateMixin {
  late AnimationController _pulseController;
  late Animation<double> _pulseAnimation;
  final ScrollController _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      duration: const Duration(milliseconds: 1500),
      vsync: this,
    )..repeat(reverse: true);
    _pulseAnimation = Tween<double>(begin: 0.4, end: 1.0).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );
  }

  @override
  void didUpdateWidget(ThinkingDisplay oldWidget) {
    super.didUpdateWidget(oldWidget);
    
    // Auto-scroll to bottom when new content arrives
    // Simple logic: scroll when history changes or current thinking updates
    if (widget.thinkingHistory.length != oldWidget.thinkingHistory.length ||
        widget.currentThinking != oldWidget.currentThinking) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (_scrollController.hasClients) {
          _scrollController.animateTo(
            _scrollController.position.maxScrollExtent,
            duration: const Duration(milliseconds: 300),
            curve: Curves.easeOut,
          );
        }
      });
    }
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final hasContent = widget.thinkingHistory.isNotEmpty || 
                      (widget.currentThinking != null && widget.currentThinking!.trim().isNotEmpty);
    
    return Column(
      children: [
        _buildIntegratedHeader(context),
        Expanded(
          child: hasContent
              ? _buildThinkingTimeline(context)
              : _buildEmptyState(context),
        ),
      ],
    );
  }

  /// Integrated header - AICO design principles
  Widget _buildIntegratedHeader(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    
    // AICO soft purple accent
    final purpleAccent = isDark 
        ? const Color(0xFFB9A7E6)
        : const Color(0xFFB8A1EA);
    
    return Container(
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHighest.withOpacity(isDark ? 0.2 : 0.3),
        border: Border(
          bottom: BorderSide(
            color: theme.colorScheme.outline.withOpacity(0.12),
            width: 1,
          ),
        ),
      ),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12), // 8px grid
      child: Row(
        children: [
          // Icon with subtle animation - soft purple accent
          AnimatedBuilder(
            animation: _pulseAnimation,
            builder: (context, child) {
              return Opacity(
                opacity: widget.isStreaming ? (0.6 + _pulseAnimation.value * 0.4) : 1.0,
                child: Icon(
                  Icons.psychology,
                  size: 18,
                  color: purpleAccent,
                ),
              );
            },
          ),
          const SizedBox(width: 8), // 8px grid
          Text(
            'Inner Monologue',
            style: theme.textTheme.titleSmall?.copyWith(
              color: theme.colorScheme.onSurface.withOpacity(0.9),
              fontWeight: FontWeight.w600,
              fontSize: 13,
              letterSpacing: 0.02, // AICO standard
            ),
          ),
          const Spacer(),
          if (widget.isStreaming)
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                // Pulsing dot with soft purple
                AnimatedBuilder(
                  animation: _pulseAnimation,
                  builder: (context, child) {
                    return Container(
                      width: 6,
                      height: 6,
                      decoration: BoxDecoration(
                        color: purpleAccent,
                        shape: BoxShape.circle,
                        boxShadow: [
                          BoxShadow(
                            color: purpleAccent.withOpacity(_pulseAnimation.value * 0.5),
                            blurRadius: 4,
                            spreadRadius: 1,
                          ),
                        ],
                      ),
                    );
                  },
                ),
                const SizedBox(width: 6),
                Text(
                  'Thinking',
                  style: theme.textTheme.labelSmall?.copyWith(
                    color: purpleAccent.withOpacity(0.9),
                    fontSize: 11,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
        ],
      ),
    );
  }

  Widget _buildEmptyState(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final purpleAccent = isDark 
        ? const Color(0xFFB9A7E6)
        : const Color(0xFFB8A1EA);
    
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32), // 8px grid: 4×8
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.psychology_outlined,
              size: 40,
              color: purpleAccent.withOpacity(0.25),
            ),
            const SizedBox(height: 16), // 8px grid: 2×8
            Text(
              'No thoughts yet',
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.onSurface.withOpacity(0.5),
                fontSize: 13,
                letterSpacing: 0.02,
              ),
            ),
            const SizedBox(height: 8), // 8px grid
            Text(
              'Reasoning will appear here',
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurface.withOpacity(0.35),
                fontSize: 11,
                letterSpacing: 0.02,
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// Timeline-based thinking display with clear turn separation
  /// Inspired by ChatGPT reasoning view and Claude Artifacts
  /// Data comes from provider (Single Source of Truth)
  Widget _buildThinkingTimeline(BuildContext context) {
    // Check if current thinking is already in history (prevent duplicates)
    final currentThinkingTrimmed = widget.currentThinking?.trim() ?? '';
    final isAlreadyInHistory = widget.thinkingHistory.isNotEmpty &&
        widget.thinkingHistory.last.content == currentThinkingTrimmed;
    
    final hasCurrentThinking = currentThinkingTrimmed.isNotEmpty && !isAlreadyInHistory;
    final totalItems = widget.thinkingHistory.length + (hasCurrentThinking ? 1 : 0);
    
    return ListView.builder(
      controller: _scrollController,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      itemCount: totalItems,
      itemBuilder: (context, index) {
        final isCurrentTurn = hasCurrentThinking && index == widget.thinkingHistory.length;
        final turn = isCurrentTurn
            ? ThinkingTurn(
                content: currentThinkingTrimmed,
                timestamp: DateTime.now(),
                messageId: 'streaming', // Temporary ID for streaming
                isComplete: false,
              )
            : widget.thinkingHistory[index];
        
        return _buildThinkingTurnCard(
          context,
          turn,
          isCurrentTurn: isCurrentTurn,
          isLastTurn: index == totalItems - 1,
        );
      },
    );
  }

  /// Individual turn card - AICO design principles
  /// Minimalism, soft purple accents, 8px grid, rounded corners
  Widget _buildThinkingTurnCard(
    BuildContext context,
    ThinkingTurn turn, {
    required bool isCurrentTurn,
    required bool isLastTurn,
  }) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    
    // AICO soft purple accent (#B8A1EA / #B9A7E6)
    final purpleAccent = isDark 
        ? const Color(0xFFB9A7E6)
        : const Color(0xFFB8A1EA);
    
    return Padding(
      padding: const EdgeInsets.only(bottom: 24), // 8px grid: 3×8
      child: Container(
        padding: const EdgeInsets.all(16), // 8px grid: 2×8
        decoration: BoxDecoration(
          // Subtle background - barely visible
          color: isDark
              ? theme.colorScheme.surfaceContainerHighest.withOpacity(0.12)
              : theme.colorScheme.surfaceContainerHighest.withOpacity(0.2),
          borderRadius: BorderRadius.circular(16), // AICO standard: 16-24px
          // Very subtle border - soft purple for current turn
          border: Border.all(
            color: isCurrentTurn
                ? purpleAccent.withOpacity(0.2)
                : theme.colorScheme.outline.withOpacity(0.08),
            width: 1,
          ),
          // Soft elevation per AICO guidelines
          boxShadow: [
            BoxShadow(
              color: const Color(0xFF243455).withOpacity(0.06), // AICO shadow color
              blurRadius: 12,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Minimal timestamp header
            Row(
              children: [
                // Subtle timestamp - very muted
                Text(
                  _formatTimestamp(turn.timestamp),
                  style: theme.textTheme.labelSmall?.copyWith(
                    color: theme.colorScheme.onSurface.withOpacity(0.35),
                    fontSize: 10,
                    fontWeight: FontWeight.w500,
                    letterSpacing: 0.02, // AICO: 0.02em on captions
                  ),
                ),
                if (isCurrentTurn) ...[
                  const SizedBox(width: 8), // 8px grid
                  // LIVE indicator with soft purple accent
                  AnimatedBuilder(
                    animation: _pulseAnimation,
                    builder: (context, child) {
                      return Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          // Pulsing dot - soft purple
                          Opacity(
                            opacity: 0.5 + (_pulseAnimation.value * 0.4),
                            child: Container(
                              width: 6,
                              height: 6,
                              decoration: BoxDecoration(
                                color: purpleAccent,
                                shape: BoxShape.circle,
                                boxShadow: [
                                  BoxShadow(
                                    color: purpleAccent.withOpacity(0.4),
                                    blurRadius: 4,
                                    spreadRadius: 1,
                                  ),
                                ],
                              ),
                            ),
                          ),
                          const SizedBox(width: 4),
                          Text(
                            'Live',
                            style: theme.textTheme.labelSmall?.copyWith(
                              color: purpleAccent.withOpacity(0.8),
                              fontSize: 9,
                              fontWeight: FontWeight.w600,
                              letterSpacing: 0.5,
                            ),
                          ),
                        ],
                      );
                    },
                  ),
                ],
              ],
            ),
            const SizedBox(height: 12), // 8px grid: 1.5×8
            
            // Thinking content - MUTED for secondary information hierarchy
            // AICO principle: Auxiliary content uses reduced opacity
            SelectableText(
              turn.content.trim(),
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurface.withOpacity(0.6), // ← MUTED
                height: 1.5, // AICO: 1.5× font size line-height
                fontSize: 13, // Slightly larger for better readability
                letterSpacing: 0.02, // AICO standard
                fontWeight: FontWeight.w400,
              ),
            ),
          ],
        ),
      ),
    );
  }

  String _formatTimestamp(DateTime timestamp) {
    final now = DateTime.now();
    final diff = now.difference(timestamp);
    
    if (diff.inSeconds < 5) return 'Just now';
    if (diff.inSeconds < 60) return '${diff.inSeconds}s ago';
    if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
    return '${timestamp.hour.toString().padLeft(2, '0')}:${timestamp.minute.toString().padLeft(2, '0')}';
  }
}

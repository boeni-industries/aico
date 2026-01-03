import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:aico_frontend/presentation/providers/proactive_state_provider.dart';
import 'package:aico_frontend/presentation/theme/glassmorphism.dart';

/// Ambient floating orb that pulses when AICO wants to initiate conversation.
/// Replaces enterprise-style notification badge with immersive, mood-aware presence.
class ProactiveOrbIndicator extends ConsumerStatefulWidget {
  const ProactiveOrbIndicator({super.key});

  @override
  ConsumerState<ProactiveOrbIndicator> createState() => _ProactiveOrbIndicatorState();
}

class _ProactiveOrbIndicatorState extends ConsumerState<ProactiveOrbIndicator>
    with SingleTickerProviderStateMixin {
  late AnimationController _pulseController;
  late Animation<double> _pulseAnimation;
  late Animation<double> _glowAnimation;

  @override
  void initState() {
    super.initState();
    
    _pulseController = AnimationController(
      duration: const Duration(milliseconds: 2000),
      vsync: this,
    )..repeat(reverse: true);

    _pulseAnimation = Tween<double>(begin: 0.85, end: 1.0).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );

    _glowAnimation = Tween<double>(begin: 0.15, end: 0.35).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _pulseController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final proactiveState = ref.watch(proactiveStateProvider);
    
    final hasPending = proactiveState.pendingInitiations.isNotEmpty;
    
    if (!hasPending) {
      return const SizedBox.shrink();
    }

    final accentColor = theme.colorScheme.primary;

    return Positioned(
      top: 24,
      right: 24,
      child: GestureDetector(
        onTap: () => _showProactiveCard(context),
        child: AnimatedBuilder(
          animation: _pulseController,
          builder: (context, child) {
            return Container(
              width: 48,
              height: 48,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                boxShadow: [
                  // Ambient glow
                  BoxShadow(
                    color: accentColor.withValues(alpha: _glowAnimation.value),
                    blurRadius: 30,
                    spreadRadius: 5,
                  ),
                  // Depth shadow
                  BoxShadow(
                    color: Colors.black.withValues(alpha: isDark ? 0.4 : 0.08),
                    blurRadius: 20,
                    offset: const Offset(0, 8),
                  ),
                ],
              ),
              child: Transform.scale(
                scale: _pulseAnimation.value,
                child: ClipOval(
                  child: BackdropFilter(
                    filter: ImageFilter.blur(
                      sigmaX: GlassTheme.blurMedium,
                      sigmaY: GlassTheme.blurMedium,
                    ),
                    child: Container(
                      decoration: BoxDecoration(
                        color: isDark
                            ? Colors.white.withValues(alpha: 0.06)
                            : Colors.white.withValues(alpha: 0.7),
                        shape: BoxShape.circle,
                        border: Border.all(
                          color: accentColor.withValues(alpha: 0.4),
                          width: 2,
                        ),
                      ),
                      child: Center(
                        child: Icon(
                          Icons.chat_bubble_outline,
                          color: accentColor,
                          size: 22,
                        ),
                      ),
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

  void _showProactiveCard(BuildContext context) {
    showDialog(
      context: context,
      barrierColor: Colors.black.withValues(alpha: 0.5),
      barrierDismissible: true,
      builder: (context) => const ProactiveConversationCard(),
    );
  }
}

/// Glassmorphic card that expands from orb showing AICO's question
class ProactiveConversationCard extends ConsumerWidget {
  const ProactiveConversationCard({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final proactiveState = ref.watch(proactiveStateProvider);
    final accentColor = theme.colorScheme.primary;

    if (proactiveState.pendingInitiations.isEmpty) {
      Navigator.of(context).pop();
      return const SizedBox.shrink();
    }

    final initiation = proactiveState.pendingInitiations.first;

    return Dialog(
      backgroundColor: Colors.transparent,
      elevation: 0,
      insetPadding: const EdgeInsets.all(24),
      child: Align(
        alignment: Alignment.center,
        child: ConstrainedBox(
          constraints: const BoxConstraints(
            maxWidth: 440,
            maxHeight: 600,
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(GlassTheme.radiusXLarge),
            child: BackdropFilter(
              filter: ImageFilter.blur(
                sigmaX: GlassTheme.blurHeavy,
                sigmaY: GlassTheme.blurHeavy,
              ),
              child: Container(
                decoration: BoxDecoration(
                  color: isDark
                      ? Colors.white.withValues(alpha: 0.04)
                      : Colors.white.withValues(alpha: 0.7),
                  borderRadius: BorderRadius.circular(GlassTheme.radiusXLarge),
                  border: Border.all(
                    color: isDark
                        ? Colors.white.withValues(alpha: 0.1)
                        : Colors.white.withValues(alpha: 0.4),
                    width: 1.5,
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: isDark ? 0.4 : 0.08),
                      blurRadius: 40,
                      offset: const Offset(0, 20),
                      spreadRadius: -10,
                    ),
                    BoxShadow(
                      color: accentColor.withValues(alpha: 0.1),
                      blurRadius: 60,
                      spreadRadius: -5,
                    ),
                  ],
                ),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    // Header
                    Padding(
                      padding: const EdgeInsets.all(24),
                      child: Row(
                        children: [
                          Container(
                            width: 40,
                            height: 40,
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              color: accentColor.withValues(alpha: 0.15),
                            ),
                            child: Icon(
                              Icons.chat_bubble,
                              color: accentColor,
                              size: 20,
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Text(
                              'AICO wants to ask you',
                              style: theme.textTheme.titleMedium?.copyWith(
                                fontWeight: FontWeight.w600,
                                color: isDark ? Colors.white : Colors.black87,
                              ),
                            ),
                          ),
                          IconButton(
                            icon: Icon(
                              Icons.close,
                              color: isDark ? Colors.white70 : Colors.black54,
                            ),
                            onPressed: () => Navigator.of(context).pop(),
                          ),
                        ],
                      ),
                    ),

                    // Question
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 24),
                      child: Text(
                        initiation.question,
                        style: theme.textTheme.bodyLarge?.copyWith(
                          height: 1.6,
                          color: isDark ? Colors.white.withValues(alpha: 0.9) : Colors.black87,
                        ),
                      ),
                    ),

                    const SizedBox(height: 32),

                    // Actions
                    Padding(
                      padding: const EdgeInsets.fromLTRB(24, 0, 24, 24),
                      child: Column(
                        children: [
                          SizedBox(
                            width: double.infinity,
                            child: _buildActionButton(
                              context,
                              ref,
                              'Let\'s talk',
                              Icons.chat,
                              true,
                              () => _handleAnswer(context, ref, initiation.initiationId),
                            ),
                          ),
                          const SizedBox(height: 12),
                          Row(
                            children: [
                              Expanded(
                                child: _buildActionButton(
                                  context,
                                  ref,
                                  'Later',
                                  Icons.schedule,
                                  false,
                                  () => _handleLater(context, ref, initiation.initiationId),
                                ),
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: _buildActionButton(
                                  context,
                                  ref,
                                  'Dismiss',
                                  Icons.close,
                                  false,
                                  () => _handleDismiss(context, ref, initiation.initiationId),
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),

                    // History link
                    if (proactiveState.pendingInitiations.length > 1)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 16),
                        child: TextButton.icon(
                          onPressed: () => _showHistory(context),
                          icon: Icon(
                            Icons.history,
                            size: 16,
                            color: accentColor,
                          ),
                          label: Text(
                            '${proactiveState.pendingInitiations.length - 1} more waiting',
                            style: TextStyle(
                              color: accentColor,
                              fontSize: 13,
                            ),
                          ),
                        ),
                      ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildActionButton(
    BuildContext context,
    WidgetRef ref,
    String label,
    IconData icon,
    bool isPrimary,
    VoidCallback onPressed,
  ) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final accentColor = theme.colorScheme.primary;

    return Material(
      color: Colors.transparent,
      borderRadius: BorderRadius.circular(GlassTheme.radiusMedium),
      child: InkWell(
        onTap: onPressed,
        borderRadius: BorderRadius.circular(GlassTheme.radiusMedium),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 20),
          decoration: BoxDecoration(
            color: isPrimary
                ? accentColor.withValues(alpha: 0.2)
                : (isDark
                    ? Colors.white.withValues(alpha: 0.06)
                    : Colors.black.withValues(alpha: 0.04)),
            borderRadius: BorderRadius.circular(GlassTheme.radiusMedium),
            border: Border.all(
              color: isPrimary
                  ? accentColor.withValues(alpha: 0.4)
                  : (isDark
                      ? Colors.white.withValues(alpha: 0.12)
                      : Colors.black.withValues(alpha: 0.12)),
              width: 1.5,
            ),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                icon,
                size: 18,
                color: isPrimary ? accentColor : (isDark ? Colors.white70 : Colors.black54),
              ),
              const SizedBox(width: 8),
              Flexible(
                child: Text(
                  label,
                  style: theme.textTheme.bodyMedium?.copyWith(
                    fontWeight: isPrimary ? FontWeight.w600 : FontWeight.w500,
                    color: isPrimary ? accentColor : (isDark ? Colors.white70 : Colors.black54),
                    fontSize: 14,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _handleDismiss(BuildContext context, WidgetRef ref, String initiationId) async {
    await ref.read(proactiveStateProvider.notifier).respondToInitiation(
      initiationId: initiationId,
      responseType: 'dismissed',
    );
    if (context.mounted) Navigator.of(context).pop();
  }

  void _handleLater(BuildContext context, WidgetRef ref, String initiationId) async {
    await ref.read(proactiveStateProvider.notifier).respondToInitiation(
      initiationId: initiationId,
      responseType: 'later',
    );
    if (context.mounted) Navigator.of(context).pop();
  }

  void _handleAnswer(BuildContext context, WidgetRef ref, String initiationId) async {
    await ref.read(proactiveStateProvider.notifier).respondToInitiation(
      initiationId: initiationId,
      responseType: 'answered',
    );
    if (context.mounted) {
      Navigator.of(context).pop();
      // TODO: Open conversation with this initiation as context
    }
  }

  void _showHistory(BuildContext context) {
    Navigator.of(context).pop();
    showDialog(
      context: context,
      barrierColor: Colors.black.withValues(alpha: 0.3),
      builder: (context) => const ProactiveHistoryView(),
    );
  }
}

/// Timeline view of all proactive conversation history
class ProactiveHistoryView extends ConsumerWidget {
  const ProactiveHistoryView({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final accentColor = theme.colorScheme.primary;

    return Align(
      alignment: Alignment.topRight,
      child: Padding(
        padding: const EdgeInsets.only(top: 80, right: 24),
        child: Material(
          color: Colors.transparent,
          child: ClipRRect(
            borderRadius: BorderRadius.circular(GlassTheme.radiusXLarge),
            child: BackdropFilter(
              filter: ImageFilter.blur(
                sigmaX: GlassTheme.blurHeavy,
                sigmaY: GlassTheme.blurHeavy,
              ),
              child: Container(
                width: 420,
                height: 600,
                decoration: BoxDecoration(
                  color: isDark
                      ? Colors.white.withValues(alpha: 0.04)
                      : Colors.white.withValues(alpha: 0.7),
                  borderRadius: BorderRadius.circular(GlassTheme.radiusXLarge),
                  border: Border.all(
                    color: isDark
                        ? Colors.white.withValues(alpha: 0.1)
                        : Colors.white.withValues(alpha: 0.4),
                    width: 1.5,
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: isDark ? 0.4 : 0.08),
                      blurRadius: 40,
                      offset: const Offset(0, 20),
                      spreadRadius: -10,
                    ),
                  ],
                ),
                child: Column(
                  children: [
                    // Header
                    Padding(
                      padding: const EdgeInsets.all(24),
                      child: Row(
                        children: [
                          Icon(
                            Icons.history,
                            color: accentColor,
                            size: 24,
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Text(
                              'Conversation History',
                              style: theme.textTheme.titleLarge?.copyWith(
                                fontWeight: FontWeight.w600,
                                color: isDark ? Colors.white : Colors.black87,
                              ),
                            ),
                          ),
                          IconButton(
                            icon: Icon(
                              Icons.close,
                              color: isDark ? Colors.white70 : Colors.black54,
                            ),
                            onPressed: () => Navigator.of(context).pop(),
                          ),
                        ],
                      ),
                    ),

                    // History list
                    Expanded(
                      child: ListView(
                        padding: const EdgeInsets.symmetric(horizontal: 24),
                        children: [
                          Text(
                            'History view coming soon...',
                            style: theme.textTheme.bodyMedium?.copyWith(
                              color: isDark ? Colors.white60 : Colors.black54,
                              fontStyle: FontStyle.italic,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

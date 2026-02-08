import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:aico_frontend/data/models/interaction_model.dart';
import 'package:aico_frontend/presentation/providers/interaction_provider.dart';
import 'package:aico_frontend/presentation/widgets/interactions/interaction_card.dart';
import 'package:aico_frontend/presentation/widgets/interactions/answer_dialog.dart';

/// Timeline view for interactions
/// Replaces ProactiveTimeline with new interaction system
class InteractionTimeline extends ConsumerStatefulWidget {
  final VoidCallback onCollapse;

  const InteractionTimeline({
    super.key,
    required this.onCollapse,
  });

  @override
  ConsumerState<InteractionTimeline> createState() => _InteractionTimelineState();
}

class _InteractionTimelineState extends ConsumerState<InteractionTimeline> {
  String _filter = 'pending';

  @override
  void initState() {
    super.initState();
    Future.microtask(() => ref.read(interactionProvider.notifier).refresh());
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final state = ref.watch(interactionProvider);
    
    final filteredInteractions = _getFilteredInteractions(state);
    final isDark = theme.brightness == Brightness.dark;
    final purpleAccent = isDark ? const Color(0xFFB9A7E6) : const Color(0xFFB8A1EA);

    return Column(
      children: [
        // Header with collapse button
        Padding(
          padding: const EdgeInsets.only(left: 12, right: 20, top: 16, bottom: 24),
          child: Row(
            children: [
              // Collapse button
              Container(
                width: 28,
                height: 28,
                decoration: BoxDecoration(
                  color: isDark
                      ? Colors.white.withValues(alpha: 0.06)
                      : Colors.white.withValues(alpha: 0.8),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(
                    color: isDark
                        ? Colors.white.withValues(alpha: 0.1)
                        : Colors.white.withValues(alpha: 0.3),
                    width: 1,
                  ),
                ),
                child: IconButton(
                  onPressed: widget.onCollapse,
                  icon: Icon(
                    Icons.chevron_right,
                    color: purpleAccent.withValues(alpha: 0.6),
                    size: 16,
                  ),
                  tooltip: 'Collapse',
                  padding: EdgeInsets.zero,
                  iconSize: 16,
                ),
              ),
              const SizedBox(width: 12),
              // Title
              Flexible(
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(
                      Icons.notifications_outlined,
                      color: purpleAccent.withValues(alpha: 0.6),
                      size: 16,
                    ),
                    const SizedBox(width: 8),
                    Flexible(
                      child: Text(
                        'Interactions',
                        style: theme.textTheme.titleSmall?.copyWith(
                          fontWeight: FontWeight.w600,
                          fontSize: 13,
                          color: isDark 
                              ? Colors.white.withValues(alpha: 0.85) 
                              : Colors.black.withValues(alpha: 0.85),
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 40),
            ],
          ),
        ),

        // Filter tabs
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
          child: _buildFilterTabs(theme, state, isDark),
        ),

        // Loading indicator
        if (state.isLoading && state.interactions.isEmpty)
          const Expanded(
            child: Center(
              child: CircularProgressIndicator(),
            ),
          )
        // Error state
        else if (state.error != null)
          Expanded(
            child: _buildErrorState(theme, state.error!),
          )
        // Timeline list
        else if (filteredInteractions.isEmpty)
          Expanded(
            child: _buildEmptyState(theme),
          )
        else
          Expanded(
            child: ListView.separated(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              itemCount: filteredInteractions.length,
              separatorBuilder: (context, index) => const SizedBox(height: 12),
              itemBuilder: (context, index) {
                return InteractionCard(
                  interaction: filteredInteractions[index],
                  onTap: () => _handleTap(filteredInteractions[index]),
                  onAnswer: () => _handleAnswer(filteredInteractions[index]),
                  onApprove: () => _handleApprove(filteredInteractions[index]),
                  onReject: () => _handleReject(filteredInteractions[index]),
                  onDefer: () => _handleDefer(filteredInteractions[index]),
                );
              },
            ),
          ),
      ],
    );
  }

  List<InteractionRequest> _getFilteredInteractions(InteractionState state) {
    switch (_filter) {
      case 'pending':
        return state.pending;
      case 'deferred':
        return state.deferred;
      case 'answered':
        return state.answered;
      case 'dismissed':
        return state.dismissed;
      case 'all':
      default:
        return state.interactions;
    }
  }

  Widget _buildFilterTabs(ThemeData theme, InteractionState state, bool isDark) {
    return Container(
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(
        color: isDark 
            ? Colors.white.withValues(alpha: 0.03)
            : Colors.black.withValues(alpha: 0.03),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: isDark
              ? Colors.white.withValues(alpha: 0.08)
              : Colors.black.withValues(alpha: 0.08),
          width: 1,
        ),
      ),
      child: Row(
        children: [
          Expanded(child: _buildFilterTab('pending', Icons.schedule, 'Pending', state.pending.length, isDark)),
          const SizedBox(width: 4),
          Expanded(child: _buildFilterTab('deferred', Icons.snooze, 'Deferred', state.deferred.length, isDark)),
          const SizedBox(width: 4),
          Expanded(child: _buildFilterTab('all', Icons.grid_view_rounded, 'All', state.interactions.length, isDark)),
          const SizedBox(width: 4),
          Expanded(child: _buildFilterTab('answered', Icons.check_circle_outline, 'Answered', state.answered.length, isDark)),
        ],
      ),
    );
  }

  Widget _buildFilterTab(String value, IconData icon, String label, int count, bool isDark) {
    final theme = Theme.of(context);
    final isSelected = _filter == value;
    final purpleAccent = isDark ? const Color(0xFFB9A7E6) : const Color(0xFFB8A1EA);

    return Tooltip(
      message: label,
      child: GestureDetector(
        onTap: () => setState(() => _filter = value),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 10),
          decoration: BoxDecoration(
            color: isSelected
                ? (isDark ? Colors.white.withValues(alpha: 0.1) : Colors.white.withValues(alpha: 0.9))
                : Colors.transparent,
            borderRadius: BorderRadius.circular(6),
            border: isSelected ? Border.all(
              color: purpleAccent.withValues(alpha: 0.3),
              width: 1,
            ) : null,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                icon,
                size: 20,
                color: isSelected
                    ? purpleAccent
                    : theme.colorScheme.onSurface.withValues(alpha: 0.5),
              ),
              const SizedBox(height: 4),
              Container(
                constraints: const BoxConstraints(minWidth: 20),
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: count > 0
                      ? (isSelected 
                          ? purpleAccent.withValues(alpha: 0.25)
                          : theme.colorScheme.onSurface.withValues(alpha: 0.1))
                      : Colors.transparent,
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Text(
                  '$count',
                  textAlign: TextAlign.center,
                  style: theme.textTheme.labelSmall?.copyWith(
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                    color: count > 0
                        ? (isSelected
                            ? purpleAccent
                            : theme.colorScheme.onSurface.withValues(alpha: 0.6))
                        : theme.colorScheme.onSurface.withValues(alpha: 0.3),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildEmptyState(ThemeData theme) {
    String message;
    IconData icon;
    
    switch (_filter) {
      case 'pending':
        message = 'No pending interactions';
        icon = Icons.check_circle_outline;
        break;
      case 'deferred':
        message = 'No deferred interactions';
        icon = Icons.schedule;
        break;
      case 'answered':
        message = 'No answered interactions';
        icon = Icons.done_all;
        break;
      case 'dismissed':
        message = 'No dismissed interactions';
        icon = Icons.close;
        break;
      default:
        message = 'No interactions';
        icon = Icons.notifications_outlined;
    }

    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            icon,
            size: 48,
            color: theme.colorScheme.onSurface.withValues(alpha: 0.2),
          ),
          const SizedBox(height: 12),
          Text(
            message,
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.colorScheme.onSurface.withValues(alpha: 0.4),
              fontStyle: FontStyle.italic,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildErrorState(ThemeData theme, String error) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.error_outline,
            size: 48,
            color: Colors.red.withValues(alpha: 0.6),
          ),
          const SizedBox(height: 12),
          Text(
            'Error loading interactions',
            style: theme.textTheme.bodyMedium?.copyWith(
              color: theme.colorScheme.onSurface.withValues(alpha: 0.7),
            ),
          ),
          const SizedBox(height: 4),
          Text(
            error,
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.colorScheme.onSurface.withValues(alpha: 0.5),
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 16),
          OutlinedButton.icon(
            onPressed: () => ref.read(interactionProvider.notifier).refresh(),
            icon: const Icon(Icons.refresh, size: 18),
            label: const Text('Retry'),
          ),
        ],
      ),
    );
  }

  void _handleTap(InteractionRequest interaction) {
    // Navigate to conversation or show detail
    // TODO: Implement navigation to conversation
  }

  void _handleAnswer(InteractionRequest interaction) async {
    final result = await showDialog<String>(
      context: context,
      builder: (context) => AnswerDialog(interaction: interaction),
    );
    
    if (result != null && result.isNotEmpty) {
      await ref.read(interactionProvider.notifier).answer(
        interaction.interactionId,
        text: result,
      );
    }
  }

  void _handleApprove(InteractionRequest interaction) async {
    await ref.read(interactionProvider.notifier).approve(interaction.interactionId);
  }

  void _handleReject(InteractionRequest interaction) async {
    await ref.read(interactionProvider.notifier).reject(interaction.interactionId);
  }

  void _handleDefer(InteractionRequest interaction) async {
    await ref.read(interactionProvider.notifier).defer(interaction.interactionId);
  }
}

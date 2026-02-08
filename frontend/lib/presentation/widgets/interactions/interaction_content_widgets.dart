import 'package:flutter/material.dart';
import 'package:aico_frontend/data/models/interaction_model.dart';

/// Content widgets for different interaction types
/// These are designed to be used inside MessageBubble's customChild parameter

/// Question interaction content
class QuestionInteractionContent extends StatefulWidget {
  final InteractionRequest interaction;
  final Function(String)? onAnswer;

  const QuestionInteractionContent({
    super.key,
    required this.interaction,
    this.onAnswer,
  });

  @override
  State<QuestionInteractionContent> createState() => _QuestionInteractionContentState();
}

class _QuestionInteractionContentState extends State<QuestionInteractionContent> {
  final _controller = TextEditingController();
  bool _isSubmitting = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_controller.text.trim().isEmpty) return;
    
    setState(() => _isSubmitting = true);
    widget.onAnswer?.call(_controller.text.trim());
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          widget.interaction.prompt,
          style: theme.textTheme.bodyMedium?.copyWith(
            height: 1.5,
          ),
        ),
        const SizedBox(height: 16),
        TextField(
          controller: _controller,
          enabled: !_isSubmitting,
          decoration: InputDecoration(
            hintText: 'Type your answer...',
            filled: true,
            fillColor: theme.colorScheme.surface.withValues(alpha: 0.5),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide: BorderSide(
                color: theme.colorScheme.outline.withValues(alpha: 0.3),
              ),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide: BorderSide(
                color: theme.colorScheme.outline.withValues(alpha: 0.3),
              ),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide: BorderSide(
                color: theme.colorScheme.primary,
                width: 2,
              ),
            ),
          ),
          maxLines: 3,
          textInputAction: TextInputAction.send,
          onSubmitted: (_) => _submit(),
        ),
        const SizedBox(height: 12),
        Align(
          alignment: Alignment.centerRight,
          child: FilledButton.icon(
            onPressed: _isSubmitting ? null : _submit,
            icon: _isSubmitting
                ? SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: theme.colorScheme.onPrimary,
                    ),
                  )
                : const Icon(Icons.send, size: 18),
            label: Text(_isSubmitting ? 'Sending...' : 'Submit Answer'),
          ),
        ),
      ],
    );
  }
}

/// Choice interaction content
class ChoiceInteractionContent extends StatefulWidget {
  final InteractionRequest interaction;
  final Function(String)? onSelect;

  const ChoiceInteractionContent({
    super.key,
    required this.interaction,
    this.onSelect,
  });

  @override
  State<ChoiceInteractionContent> createState() => _ChoiceInteractionContentState();
}

class _ChoiceInteractionContentState extends State<ChoiceInteractionContent> {
  String? _selectedOption;
  bool _isSubmitting = false;

  Future<void> _submit() async {
    if (_selectedOption == null) return;
    
    setState(() => _isSubmitting = true);
    widget.onSelect?.call(_selectedOption!);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final options = widget.interaction.allowedOptions ?? [];
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          widget.interaction.prompt,
          style: theme.textTheme.bodyMedium?.copyWith(
            height: 1.5,
          ),
        ),
        const SizedBox(height: 16),
        ...options.map((option) => Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: RadioListTile<String>(
            value: option,
            groupValue: _selectedOption,
            onChanged: _isSubmitting ? null : (value) {
              setState(() => _selectedOption = value);
            },
            title: Text(option),
            dense: true,
            contentPadding: EdgeInsets.zero,
            activeColor: theme.colorScheme.primary,
          ),
        )),
        const SizedBox(height: 8),
        Align(
          alignment: Alignment.centerRight,
          child: FilledButton.icon(
            onPressed: (_isSubmitting || _selectedOption == null) ? null : _submit,
            icon: _isSubmitting
                ? SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: theme.colorScheme.onPrimary,
                    ),
                  )
                : const Icon(Icons.check, size: 18),
            label: Text(_isSubmitting ? 'Submitting...' : 'Confirm Choice'),
          ),
        ),
      ],
    );
  }
}

/// Approval interaction content
class ApprovalInteractionContent extends StatefulWidget {
  final InteractionRequest interaction;
  final VoidCallback? onApprove;
  final VoidCallback? onReject;

  const ApprovalInteractionContent({
    super.key,
    required this.interaction,
    this.onApprove,
    this.onReject,
  });

  @override
  State<ApprovalInteractionContent> createState() => _ApprovalInteractionContentState();
}

class _ApprovalInteractionContentState extends State<ApprovalInteractionContent> {
  bool _isProcessing = false;

  Future<void> _handleApprove() async {
    setState(() => _isProcessing = true);
    widget.onApprove?.call();
  }

  Future<void> _handleReject() async {
    setState(() => _isProcessing = true);
    widget.onReject?.call();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          widget.interaction.prompt,
          style: theme.textTheme.bodyMedium?.copyWith(
            height: 1.5,
          ),
        ),
        const SizedBox(height: 16),
        Row(
          mainAxisAlignment: MainAxisAlignment.end,
          children: [
            OutlinedButton.icon(
              onPressed: _isProcessing ? null : _handleReject,
              icon: const Icon(Icons.close, size: 18),
              label: const Text('Reject'),
              style: OutlinedButton.styleFrom(
                foregroundColor: Colors.red,
              ),
            ),
            const SizedBox(width: 12),
            FilledButton.icon(
              onPressed: _isProcessing ? null : _handleApprove,
              icon: _isProcessing
                  ? SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: theme.colorScheme.onPrimary,
                      ),
                    )
                  : const Icon(Icons.check, size: 18),
              label: Text(_isProcessing ? 'Processing...' : 'Approve'),
              style: FilledButton.styleFrom(
                backgroundColor: Colors.green,
              ),
            ),
          ],
        ),
      ],
    );
  }
}

/// Dialogue interaction content
class DialogueInteractionContent extends StatelessWidget {
  final InteractionRequest interaction;
  final VoidCallback? onStart;

  const DialogueInteractionContent({
    super.key,
    required this.interaction,
    this.onStart,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          interaction.prompt,
          style: theme.textTheme.bodyMedium?.copyWith(
            height: 1.5,
          ),
        ),
        const SizedBox(height: 16),
        Align(
          alignment: Alignment.centerRight,
          child: FilledButton.icon(
            onPressed: onStart,
            icon: const Icon(Icons.chat, size: 18),
            label: const Text('Start Conversation'),
          ),
        ),
      ],
    );
  }
}

/// Acknowledgement interaction content
class AcknowledgementInteractionContent extends StatefulWidget {
  final InteractionRequest interaction;
  final VoidCallback? onAcknowledge;

  const AcknowledgementInteractionContent({
    super.key,
    required this.interaction,
    this.onAcknowledge,
  });

  @override
  State<AcknowledgementInteractionContent> createState() => _AcknowledgementInteractionContentState();
}

class _AcknowledgementInteractionContentState extends State<AcknowledgementInteractionContent> {
  bool _isProcessing = false;

  Future<void> _handleAcknowledge() async {
    setState(() => _isProcessing = true);
    widget.onAcknowledge?.call();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          widget.interaction.prompt,
          style: theme.textTheme.bodyMedium?.copyWith(
            height: 1.5,
          ),
        ),
        const SizedBox(height: 16),
        Align(
          alignment: Alignment.centerRight,
          child: FilledButton.icon(
            onPressed: _isProcessing ? null : _handleAcknowledge,
            icon: _isProcessing
                ? SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: theme.colorScheme.onPrimary,
                    ),
                  )
                : const Icon(Icons.done, size: 18),
            label: Text(_isProcessing ? 'Processing...' : 'Got it'),
          ),
        ),
      ],
    );
  }
}

import 'package:flutter/material.dart';
import 'package:aico_frontend/data/models/interaction_model.dart';
import 'package:aico_frontend/presentation/widgets/chat/message_bubble.dart';
import 'package:aico_frontend/presentation/widgets/interactions/interaction_content_widgets.dart';

/// Interaction message bubble that extends MessageBubble
/// 
/// Uses MessageBubble's glassmorphic styling and features while providing
/// interaction-specific content widgets for different interaction types
class InteractionMessageBubble extends StatelessWidget {
  final InteractionRequest interaction;
  final Color accentColor;
  final Function(String)? onAnswerText;
  final VoidCallback? onApprove;
  final VoidCallback? onReject;

  const InteractionMessageBubble({
    super.key,
    required this.interaction,
    required this.accentColor,
    this.onAnswerText,
    this.onApprove,
    this.onReject,
  });

  @override
  Widget build(BuildContext context) {
    return MessageBubble(
      content: interaction.prompt,
      isFromAico: true,
      isThinking: false,
      timestamp: DateTime.parse(interaction.createdAt),
      accentColor: accentColor,
      customChild: _buildInteractionContent(),
    );
  }

  Widget _buildInteractionContent() {
    switch (interaction.interactionType) {
      case 'question':
        return QuestionInteractionContent(
          interaction: interaction,
          onAnswer: onAnswerText,
        );
      
      case 'choice':
        return ChoiceInteractionContent(
          interaction: interaction,
          onSelect: onAnswerText,
        );
      
      case 'approval':
        return ApprovalInteractionContent(
          interaction: interaction,
          onApprove: onApprove,
          onReject: onReject,
        );
      
      case 'dialogue':
        return DialogueInteractionContent(
          interaction: interaction,
          onStart: onAnswerText != null ? () => onAnswerText!('start') : null,
        );
      
      case 'ack':
        return AcknowledgementInteractionContent(
          interaction: interaction,
          onAcknowledge: onAnswerText != null ? () => onAnswerText!('acknowledged') : null,
        );
      
      default:
        // Fallback to simple text display
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(interaction.prompt),
          ],
        );
    }
  }
}

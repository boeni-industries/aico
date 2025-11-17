import 'package:flutter/material.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'layout_provider.g.dart';

/// Defines the conversation interaction modality
enum ConversationModality {
  /// Voice-based conversation (avatar center stage, chat minimized)
  voice,
  
  /// Text-based conversation (avatar left/top, chat prominent)
  text,
  
  /// Hybrid mode (both voice and text active)
  hybrid,
}

/// Immutable state representing the current layout configuration
@immutable
class LayoutState {
  final ConversationModality modality;
  final bool isThinking;
  final bool hasMessages;
  final String moodColor;

  const LayoutState({
    this.modality = ConversationModality.voice, // Start in voice mode (centered avatar)
    this.isThinking = false,
    this.hasMessages = false,
    this.moodColor = 'idle',
  });

  /// Returns avatar height percentage based on modality and platform
  double getAvatarHeightPercent(bool isMobilePortrait) {
    if (isMobilePortrait) {
      // Mobile portrait: vertical stacking
      switch (modality) {
        case ConversationModality.voice:
          return 0.7; // 70% height, centered
        case ConversationModality.text:
          return 0.6; // 60% height, top (increased from 40%)
        case ConversationModality.hybrid:
          return 0.3; // 30% height, top
      }
    } else {
      // Desktop/tablet/landscape: horizontal layouts
      switch (modality) {
        case ConversationModality.voice:
          return 1.0; // Full height - extends from top to input area
        case ConversationModality.text:
          return 1.0; // Full height - same as voice mode for maximum presence
        case ConversationModality.hybrid:
          return 1.0; // Full height, left side
      }
    }
  }

  /// Returns avatar width percentage based on modality and platform
  double getAvatarWidthPercent(bool isMobilePortrait) {
    if (isMobilePortrait) {
      // Mobile portrait: full width for all modes
      return 1.0;
    } else {
      // Desktop/tablet/landscape: side-by-side
      switch (modality) {
        case ConversationModality.voice:
          return 1.0; // Full width, centered
        case ConversationModality.text:
          return 0.45; // 45% width, left - larger for better presence
        case ConversationModality.hybrid:
          return 0.4; // 40% width, left
      }
    }
  }

  /// Returns avatar alignment based on modality and platform
  Alignment getAvatarAlignment(bool isMobilePortrait) {
    if (isMobilePortrait) {
      // Mobile portrait: top alignment for text/hybrid
      switch (modality) {
        case ConversationModality.voice:
          return Alignment.center;
        case ConversationModality.text:
        case ConversationModality.hybrid:
          return Alignment.topCenter;
      }
    } else {
      // Desktop/tablet/landscape
      switch (modality) {
        case ConversationModality.voice:
          return Alignment.topCenter; // Top-aligned to maximize viewport
        case ConversationModality.text:
        case ConversationModality.hybrid:
          return Alignment.centerLeft;
      }
    }
  }

  /// Returns message area width percentage
  double getMessageWidthPercent(bool isMobilePortrait) {
    if (isMobilePortrait) {
      return 1.0; // Full width on mobile
    } else {
      switch (modality) {
        case ConversationModality.voice:
          return 0.0; // Hidden/minimized
        case ConversationModality.text:
          return 0.55; // 55% width - balanced with 45% avatar
        case ConversationModality.hybrid:
          return 0.6; // 60% width
      }
    }
  }

  /// Returns whether chat UI should be visible
  bool get isChatVisible {
    return modality != ConversationModality.voice;
  }

  /// Returns avatar scale factor when thinking
  double get avatarScale {
    return isThinking ? 0.95 : 1.0;
  }

  LayoutState copyWith({
    ConversationModality? modality,
    bool? isThinking,
    bool? hasMessages,
    String? moodColor,
  }) {
    return LayoutState(
      modality: modality ?? this.modality,
      isThinking: isThinking ?? this.isThinking,
      hasMessages: hasMessages ?? this.hasMessages,
      moodColor: moodColor ?? this.moodColor,
    );
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is LayoutState &&
        other.modality == modality &&
        other.isThinking == isThinking &&
        other.hasMessages == hasMessages &&
        other.moodColor == moodColor;
  }

  @override
  int get hashCode {
    return Object.hash(modality, isThinking, hasMessages, moodColor);
  }
}

/// Notifier class for layout state management
@riverpod
class Layout extends _$Layout {
  @override
  LayoutState build() {
    return const LayoutState();
  }

  /// Switch conversation modality with smooth transition
  void switchModality(ConversationModality newModality) {
    if (state.modality != newModality) {
      state = state.copyWith(modality: newModality);
    }
  }

  /// Update thinking state
  void setThinking(bool isThinking) {
    if (state.isThinking != isThinking) {
      state = state.copyWith(isThinking: isThinking);
    }
  }

  /// Update message presence
  void setHasMessages(bool hasMessages) {
    if (state.hasMessages != hasMessages) {
      state = state.copyWith(hasMessages: hasMessages);
    }
  }

  /// Update mood color for environmental gradient
  void setMoodColor(String moodColor) {
    if (state.moodColor != moodColor) {
      state = state.copyWith(moodColor: moodColor);
    }
  }

  /// Toggle between voice and text modes
  void toggleVoiceText() {
    final newModality = state.modality == ConversationModality.voice
        ? ConversationModality.text
        : ConversationModality.voice;
    switchModality(newModality);
  }
}

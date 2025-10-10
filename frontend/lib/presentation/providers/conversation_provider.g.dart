// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'conversation_provider.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning
/// Conversation provider using Riverpod Notifier

@ProviderFor(ConversationNotifier)
const conversationProvider = ConversationNotifierProvider._();

/// Conversation provider using Riverpod Notifier
final class ConversationNotifierProvider
    extends $NotifierProvider<ConversationNotifier, ConversationState> {
  /// Conversation provider using Riverpod Notifier
  const ConversationNotifierProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'conversationProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$conversationNotifierHash();

  @$internal
  @override
  ConversationNotifier create() => ConversationNotifier();

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(ConversationState value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<ConversationState>(value),
    );
  }
}

String _$conversationNotifierHash() =>
    r'9579606af6381c5b78154eb81a6d45df0e60167b';

/// Conversation provider using Riverpod Notifier

abstract class _$ConversationNotifier extends $Notifier<ConversationState> {
  ConversationState build();
  @$mustCallSuper
  @override
  void runBuild() {
    final created = build();
    final ref = this.ref as $Ref<ConversationState, ConversationState>;
    final element =
        ref.element
            as $ClassProviderElement<
              AnyNotifier<ConversationState, ConversationState>,
              ConversationState,
              Object?,
              Object?
            >;
    element.handleValue(ref, created);
  }
}

/// Provider for message repository

@ProviderFor(messageRepository)
const messageRepositoryProvider = MessageRepositoryProvider._();

/// Provider for message repository

final class MessageRepositoryProvider
    extends
        $FunctionalProvider<
          MessageRepository,
          MessageRepository,
          MessageRepository
        >
    with $Provider<MessageRepository> {
  /// Provider for message repository
  const MessageRepositoryProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'messageRepositoryProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$messageRepositoryHash();

  @$internal
  @override
  $ProviderElement<MessageRepository> $createElement(
    $ProviderPointer pointer,
  ) => $ProviderElement(pointer);

  @override
  MessageRepository create(Ref ref) {
    return messageRepository(ref);
  }

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(MessageRepository value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<MessageRepository>(value),
    );
  }
}

String _$messageRepositoryHash() => r'04b5c34bc1f5d7ec0c12fa79f51e90898a4799cd';

/// Provider for send message use case

@ProviderFor(sendMessageUseCase)
const sendMessageUseCaseProvider = SendMessageUseCaseProvider._();

/// Provider for send message use case

final class SendMessageUseCaseProvider
    extends
        $FunctionalProvider<
          SendMessageUseCase,
          SendMessageUseCase,
          SendMessageUseCase
        >
    with $Provider<SendMessageUseCase> {
  /// Provider for send message use case
  const SendMessageUseCaseProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'sendMessageUseCaseProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$sendMessageUseCaseHash();

  @$internal
  @override
  $ProviderElement<SendMessageUseCase> $createElement(
    $ProviderPointer pointer,
  ) => $ProviderElement(pointer);

  @override
  SendMessageUseCase create(Ref ref) {
    return sendMessageUseCase(ref);
  }

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(SendMessageUseCase value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<SendMessageUseCase>(value),
    );
  }
}

String _$sendMessageUseCaseHash() =>
    r'f7f8f44052859137e241af8683f7aad2a404dcb2';

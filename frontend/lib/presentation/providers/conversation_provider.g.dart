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
    r'e85ea7f00e11d7d552ef79a96d2f2fe9bf02ac1d';

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

/// Provider for message database

@ProviderFor(messageDatabase)
const messageDatabaseProvider = MessageDatabaseProvider._();

/// Provider for message database

final class MessageDatabaseProvider
    extends
        $FunctionalProvider<MessageDatabase, MessageDatabase, MessageDatabase>
    with $Provider<MessageDatabase> {
  /// Provider for message database
  const MessageDatabaseProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'messageDatabaseProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$messageDatabaseHash();

  @$internal
  @override
  $ProviderElement<MessageDatabase> $createElement($ProviderPointer pointer) =>
      $ProviderElement(pointer);

  @override
  MessageDatabase create(Ref ref) {
    return messageDatabase(ref);
  }

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(MessageDatabase value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<MessageDatabase>(value),
    );
  }
}

String _$messageDatabaseHash() => r'7adf716d3d453516717060b0a5259c0f8e60aa1f';

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

String _$messageRepositoryHash() => r'7ad658cd9209b3df2b61995a60760c7397aa63c0';

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

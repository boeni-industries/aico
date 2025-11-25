// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'avatar_controller_provider.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning

@ProviderFor(avatarController)
const avatarControllerProvider = AvatarControllerProvider._();

final class AvatarControllerProvider
    extends
        $FunctionalProvider<
          AvatarController,
          AvatarController,
          AvatarController
        >
    with $Provider<AvatarController> {
  const AvatarControllerProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'avatarControllerProvider',
        isAutoDispose: false,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$avatarControllerHash();

  @$internal
  @override
  $ProviderElement<AvatarController> $createElement($ProviderPointer pointer) =>
      $ProviderElement(pointer);

  @override
  AvatarController create(Ref ref) {
    return avatarController(ref);
  }

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(AvatarController value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<AvatarController>(value),
    );
  }
}

String _$avatarControllerHash() => r'749943227699daef705a311645202a8a00e11a4e';

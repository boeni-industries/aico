import 'package:bloc/bloc.dart';
import 'package:equatable/equatable.dart';

// Events
abstract class SettingsEvent extends Equatable {
  const SettingsEvent();

  @override
  List<Object?> get props => [];
}

class SettingsLoad extends SettingsEvent {
  const SettingsLoad();
}

class SettingsThemeChanged extends SettingsEvent {
  final String theme;

  const SettingsThemeChanged(this.theme);

  @override
  List<Object?> get props => [theme];
}

class SettingsLocaleChanged extends SettingsEvent {
  final String locale;

  const SettingsLocaleChanged(this.locale);

  @override
  List<Object?> get props => [locale];
}

class SettingsNotificationsChanged extends SettingsEvent {
  final bool enabled;

  const SettingsNotificationsChanged(this.enabled);

  @override
  List<Object?> get props => [enabled];
}

class SettingsVoiceChanged extends SettingsEvent {
  final bool enabled;

  const SettingsVoiceChanged(this.enabled);

  @override
  List<Object?> get props => [enabled];
}

class SettingsPrivacyChanged extends SettingsEvent {
  final Map<String, bool> privacySettings;

  const SettingsPrivacyChanged(this.privacySettings);

  @override
  List<Object?> get props => [privacySettings];
}

// States
abstract class SettingsState extends Equatable {
  const SettingsState();

  @override
  List<Object?> get props => [];
}

class SettingsInitial extends SettingsState {
  const SettingsInitial();
}

class SettingsLoading extends SettingsState {
  const SettingsLoading();
}

class SettingsLoaded extends SettingsState {
  final String theme;
  final String locale;
  final bool notificationsEnabled;
  final bool voiceEnabled;
  final Map<String, bool> privacySettings;

  const SettingsLoaded({
    required this.theme,
    required this.locale,
    required this.notificationsEnabled,
    required this.voiceEnabled,
    required this.privacySettings,
  });

  @override
  List<Object?> get props => [
    theme,
    locale,
    notificationsEnabled,
    voiceEnabled,
    privacySettings,
  ];

  SettingsLoaded copyWith({
    String? theme,
    String? locale,
    bool? notificationsEnabled,
    bool? voiceEnabled,
    Map<String, bool>? privacySettings,
  }) {
    return SettingsLoaded(
      theme: theme ?? this.theme,
      locale: locale ?? this.locale,
      notificationsEnabled: notificationsEnabled ?? this.notificationsEnabled,
      voiceEnabled: voiceEnabled ?? this.voiceEnabled,
      privacySettings: privacySettings ?? this.privacySettings,
    );
  }
}

class SettingsError extends SettingsState {
  final String message;

  const SettingsError(this.message);

  @override
  List<Object?> get props => [message];
}

// BLoC
class SettingsBloc extends Bloc<SettingsEvent, SettingsState> {
  SettingsBloc() : super(const SettingsInitial()) {
    on<SettingsLoad>(_onLoad);
    on<SettingsThemeChanged>(_onThemeChanged);
    on<SettingsLocaleChanged>(_onLocaleChanged);
    on<SettingsNotificationsChanged>(_onNotificationsChanged);
    on<SettingsVoiceChanged>(_onVoiceChanged);
    on<SettingsPrivacyChanged>(_onPrivacyChanged);
  }

  Future<void> _onLoad(
    SettingsLoad event,
    Emitter<SettingsState> emit,
  ) async {
    emit(const SettingsLoading());

    try {
      // TODO: Load settings from repository
      emit(const SettingsLoaded(
        theme: 'system',
        locale: 'en',
        notificationsEnabled: true,
        voiceEnabled: true,
        privacySettings: {
          'dataCollection': true,
          'analytics': false,
          'personalization': true,
        },
      ));
    } catch (e) {
      emit(SettingsError('Failed to load settings: $e'));
    }
  }

  Future<void> _onThemeChanged(
    SettingsThemeChanged event,
    Emitter<SettingsState> emit,
  ) async {
    if (state is SettingsLoaded) {
      final currentState = state as SettingsLoaded;
      emit(currentState.copyWith(theme: event.theme));
      // TODO: Save to repository
    }
  }

  Future<void> _onLocaleChanged(
    SettingsLocaleChanged event,
    Emitter<SettingsState> emit,
  ) async {
    if (state is SettingsLoaded) {
      final currentState = state as SettingsLoaded;
      emit(currentState.copyWith(locale: event.locale));
      // TODO: Save to repository
    }
  }

  Future<void> _onNotificationsChanged(
    SettingsNotificationsChanged event,
    Emitter<SettingsState> emit,
  ) async {
    if (state is SettingsLoaded) {
      final currentState = state as SettingsLoaded;
      emit(currentState.copyWith(notificationsEnabled: event.enabled));
      // TODO: Save to repository
    }
  }

  Future<void> _onVoiceChanged(
    SettingsVoiceChanged event,
    Emitter<SettingsState> emit,
  ) async {
    if (state is SettingsLoaded) {
      final currentState = state as SettingsLoaded;
      emit(currentState.copyWith(voiceEnabled: event.enabled));
      // TODO: Save to repository
    }
  }

  Future<void> _onPrivacyChanged(
    SettingsPrivacyChanged event,
    Emitter<SettingsState> emit,
  ) async {
    if (state is SettingsLoaded) {
      final currentState = state as SettingsLoaded;
      emit(currentState.copyWith(privacySettings: event.privacySettings));
      // TODO: Save to repository
    }
  }
}

import 'package:hydrated_bloc/hydrated_bloc.dart';
import '../models/settings_event.dart';
import '../models/settings_state.dart';
import '../repositories/settings_repository.dart';

/// BLoC for managing app settings with automatic persistence
/// Handles all settings-related business logic and state transitions
class SettingsBloc extends HydratedBloc<SettingsEvent, SettingsState> {
  final SettingsRepository _repository;

  SettingsBloc({
    required SettingsRepository repository,
  })  : _repository = repository,
        super(const SettingsInitial()) {
    on<SettingsLoad>(_onLoad);
    on<SettingsUpdateTheme>(_onUpdateTheme);
    on<SettingsUpdateLanguage>(_onUpdateLanguage);
    on<SettingsUpdateNotifications>(_onUpdateNotifications);
    on<SettingsUpdateAutoConnect>(_onUpdateAutoConnect);
    on<SettingsUpdateServerUrl>(_onUpdateServerUrl);
    on<SettingsUpdateCustom>(_onUpdateCustom);
    on<SettingsReset>(_onReset);
    on<SettingsSave>(_onSave);
    on<SettingsImport>(_onImport);
    on<SettingsExport>(_onExport);
  }

  /// Handle settings load request
  Future<void> _onLoad(
    SettingsLoad event,
    Emitter<SettingsState> emit,
  ) async {
    emit(const SettingsLoading());

    try {
      final settings = await _repository.loadSettings();
      emit(SettingsLoaded(settings: settings));
    } catch (e) {
      emit(SettingsError(
        message: e.toString(),
        occurredAt: DateTime.now(),
      ));
    }
  }

  /// Handle theme update
  Future<void> _onUpdateTheme(
    SettingsUpdateTheme event,
    Emitter<SettingsState> emit,
  ) async {
    await _updateSetting(
      emit,
      (settings) => settings.copyWith(theme: event.theme),
    );
  }

  /// Handle language update
  Future<void> _onUpdateLanguage(
    SettingsUpdateLanguage event,
    Emitter<SettingsState> emit,
  ) async {
    await _updateSetting(
      emit,
      (settings) => settings.copyWith(language: event.language),
    );
  }

  /// Handle notifications update
  Future<void> _onUpdateNotifications(
    SettingsUpdateNotifications event,
    Emitter<SettingsState> emit,
  ) async {
    await _updateSetting(
      emit,
      (settings) => settings.copyWith(notificationsEnabled: event.enabled),
    );
  }

  /// Handle auto-connect update
  Future<void> _onUpdateAutoConnect(
    SettingsUpdateAutoConnect event,
    Emitter<SettingsState> emit,
  ) async {
    await _updateSetting(
      emit,
      (settings) => settings.copyWith(autoConnect: event.enabled),
    );
  }

  /// Handle server URL update
  Future<void> _onUpdateServerUrl(
    SettingsUpdateServerUrl event,
    Emitter<SettingsState> emit,
  ) async {
    await _updateSetting(
      emit,
      (settings) => settings.copyWith(defaultServerUrl: event.serverUrl),
    );
  }

  /// Handle custom setting update
  Future<void> _onUpdateCustom(
    SettingsUpdateCustom event,
    Emitter<SettingsState> emit,
  ) async {
    await _updateSetting(
      emit,
      (settings) {
        final customSettings = Map<String, dynamic>.from(settings.customSettings);
        customSettings[event.key] = event.value;
        return settings.copyWith(customSettings: customSettings);
      },
    );
  }

  /// Handle settings reset
  Future<void> _onReset(
    SettingsReset event,
    Emitter<SettingsState> emit,
  ) async {
    try {
      await _repository.resetSettings();
      const defaultSettings = AppSettings();
      emit(const SettingsLoaded(settings: defaultSettings));
    } catch (e) {
      emit(SettingsError(
        message: e.toString(),
        occurredAt: DateTime.now(),
      ));
    }
  }

  /// Handle settings save
  Future<void> _onSave(
    SettingsSave event,
    Emitter<SettingsState> emit,
  ) async {
    if (state is SettingsLoaded) {
      try {
        final currentState = state as SettingsLoaded;
        await _repository.saveSettings(currentState.settings);
        // State remains the same, just saved
      } catch (e) {
        emit(SettingsError(
          message: e.toString(),
          occurredAt: DateTime.now(),
        ));
      }
    }
  }

  /// Handle settings import
  Future<void> _onImport(
    SettingsImport event,
    Emitter<SettingsState> emit,
  ) async {
    try {
      await _repository.importSettings(event.settingsData);
      final settings = await _repository.loadSettings();
      emit(SettingsLoaded(settings: settings));
    } catch (e) {
      emit(SettingsError(
        message: e.toString(),
        occurredAt: DateTime.now(),
      ));
    }
  }

  /// Handle settings export
  Future<void> _onExport(
    SettingsExport event,
    Emitter<SettingsState> emit,
  ) async {
    try {
      await _repository.exportSettings();
      // Note: In a real app, you'd typically save this to a file or share it
      // For now, we just ensure the export works without changing state
    } catch (e) {
      emit(SettingsError(
        message: e.toString(),
        occurredAt: DateTime.now(),
      ));
    }
  }

  /// Helper method to update settings
  Future<void> _updateSetting(
    Emitter<SettingsState> emit,
    AppSettings Function(AppSettings) updater,
  ) async {
    if (state is SettingsLoaded) {
      try {
        final currentState = state as SettingsLoaded;
        final updatedSettings = updater(currentState.settings);
        
        await _repository.saveSettings(updatedSettings);
        emit(SettingsLoaded(settings: updatedSettings));
      } catch (e) {
        emit(SettingsError(
          message: e.toString(),
          occurredAt: DateTime.now(),
        ));
      }
    } else {
      // If not loaded, load first then update
      add(const SettingsLoad());
    }
  }

  @override
  SettingsState? fromJson(Map<String, dynamic> json) {
    try {
      final type = json['type'] as String;
      switch (type) {
        case 'initial':
          return const SettingsInitial();
        case 'loading':
          return const SettingsLoading();
        case 'loaded':
          return SettingsLoaded(
            settings: AppSettings.fromJson(
              json['settings'] as Map<String, dynamic>,
            ),
          );
        case 'error':
          return SettingsError(
            message: json['message'] as String,
            occurredAt: DateTime.parse(json['occurredAt'] as String),
          );
        default:
          return null;
      }
    } catch (e) {
      return null; // Return null to use initial state
    }
  }

  @override
  Map<String, dynamic>? toJson(SettingsState state) {
    return state.toJson();
  }
}

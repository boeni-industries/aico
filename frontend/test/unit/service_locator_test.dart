import 'package:flutter_test/flutter_test.dart';
import 'package:aico_ui/core/di/service_locator.dart';
import 'package:aico_ui/core/utils/aico_paths.dart';

import 'package:hydrated_bloc/hydrated_bloc.dart';
import 'dart:io';

void main() {
  setUpAll(() async {
    TestWidgetsFlutterBinding.ensureInitialized();
    // Use a temp dir for HydratedBloc and AICOPaths
    final tempDir = await Directory.systemTemp.createTemp('service_locator_test');
    // Patch AICOPaths to use temp dir
    AICOPaths.setTestConfig(
      baseDataDir: tempDir.path,
      config: {
        'system': {
          'paths': {
            'data_subdirectory': 'data',
            'config_subdirectory': 'config',
            'cache_subdirectory': 'cache',
            'logs_subdirectory': 'logs',
            'frontend_subdirectory': 'frontend',
          }
        }
      },
    );
    final storage = await HydratedStorage.build(
      storageDirectory: HydratedStorageDirectory(tempDir.path),
    );
    HydratedBloc.storage = storage;
  });
  group('ServiceLocator', () {
    test('initializes without error', () async {
      await ServiceLocator.initialize();
      // If initialize() completes without throwing, consider it success.
      expect(true, isTrue);
    });
  });
}

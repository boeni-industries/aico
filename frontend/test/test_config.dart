import 'dart:async';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:get_it/get_it.dart';
import 'package:hydrated_bloc/hydrated_bloc.dart';

Future<void> testExecutable(FutureOr<void> Function() testMain) async {
  setUpAll(() async {
    // Reset dependency injection, platform overrides, etc.
    GetIt.I.reset();
    // Initialize HydratedBloc storage for tests
    final storage = await HydratedStorage.build(
      storageDirectory: HydratedStorageDirectory((await Directory.systemTemp.createTemp('hydrated_bloc_test')).path),
    );
    HydratedBloc.storage = storage;
  });
  await testMain();
}

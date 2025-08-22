import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:equatable/equatable.dart';
import 'package:go_router/go_router.dart';
import '../../../core/constants/route_names.dart';

/// Navigation BLoC for managing navigation state and deep link handling.
/// Implements state persistence and cross-platform navigation coordination.
class NavigationBloc extends Bloc<NavigationEvent, NavigationState> {
  NavigationBloc() : super(const NavigationState.initial()) {
    on<NavigationRouteChanged>(_onRouteChanged);
    on<NavigationDeepLinkReceived>(_onDeepLinkReceived);
    on<NavigationBackPressed>(_onBackPressed);
    on<NavigationTabSelected>(_onTabSelected);
  }

  void _onRouteChanged(
    NavigationRouteChanged event,
    Emitter<NavigationState> emit,
  ) {
    final primarySection = RouteNames.getPrimarySection(event.route);
    
    emit(state.copyWith(
      currentRoute: event.route,
      primarySection: primarySection,
      navigationHistory: [...state.navigationHistory, event.route],
    ));
  }

  void _onDeepLinkReceived(
    NavigationDeepLinkReceived event,
    Emitter<NavigationState> emit,
  ) {
    // Process deep link and extract route information
    final route = _processDeepLink(event.deepLink);
    
    if (route != null) {
      add(NavigationRouteChanged(route));
    }
  }

  void _onBackPressed(
    NavigationBackPressed event,
    Emitter<NavigationState> emit,
  ) {
    if (state.navigationHistory.length > 1) {
      final history = List<String>.from(state.navigationHistory);
      history.removeLast(); // Remove current route
      final previousRoute = history.last;
      
      emit(state.copyWith(
        currentRoute: previousRoute,
        primarySection: RouteNames.getPrimarySection(previousRoute),
        navigationHistory: history,
      ));
    }
  }

  void _onTabSelected(
    NavigationTabSelected event,
    Emitter<NavigationState> emit,
  ) {
    // Handle tab selection and route navigation
    add(NavigationRouteChanged(event.route));
  }

  String? _processDeepLink(String deepLink) {
    // Convert deep link to internal route
    if (deepLink.startsWith('aico://')) {
      final path = deepLink.replaceFirst('aico://', '/');
      return path == '/' ? RouteNames.home : path;
    }
    
    // Handle web URLs
    if (deepLink.startsWith('http')) {
      final uri = Uri.parse(deepLink);
      return uri.path;
    }
    
    return null;
  }
}

/// Navigation events
abstract class NavigationEvent extends Equatable {
  const NavigationEvent();

  @override
  List<Object?> get props => [];
}

class NavigationRouteChanged extends NavigationEvent {
  final String route;

  const NavigationRouteChanged(this.route);

  @override
  List<Object?> get props => [route];
}

class NavigationDeepLinkReceived extends NavigationEvent {
  final String deepLink;

  const NavigationDeepLinkReceived(this.deepLink);

  @override
  List<Object?> get props => [deepLink];
}

class NavigationBackPressed extends NavigationEvent {
  const NavigationBackPressed();
}

class NavigationTabSelected extends NavigationEvent {
  final String route;

  const NavigationTabSelected(this.route);

  @override
  List<Object?> get props => [route];
}

/// Navigation state
class NavigationState extends Equatable {
  final String currentRoute;
  final String primarySection;
  final List<String> navigationHistory;
  final bool canGoBack;

  const NavigationState({
    required this.currentRoute,
    required this.primarySection,
    required this.navigationHistory,
    required this.canGoBack,
  });

  const NavigationState.initial()
      : currentRoute = RouteNames.home,
        primarySection = RouteNames.home,
        navigationHistory = const [RouteNames.home],
        canGoBack = false;

  NavigationState copyWith({
    String? currentRoute,
    String? primarySection,
    List<String>? navigationHistory,
    bool? canGoBack,
  }) {
    final newHistory = navigationHistory ?? this.navigationHistory;
    
    return NavigationState(
      currentRoute: currentRoute ?? this.currentRoute,
      primarySection: primarySection ?? this.primarySection,
      navigationHistory: newHistory,
      canGoBack: canGoBack ?? newHistory.length > 1,
    );
  }

  @override
  List<Object?> get props => [
        currentRoute,
        primarySection,
        navigationHistory,
        canGoBack,
      ];
}

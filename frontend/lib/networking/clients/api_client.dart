import 'package:aico_frontend/networking/models/admin_models.dart';
import 'package:aico_frontend/networking/models/health_models.dart';
import 'package:aico_frontend/networking/models/user_models.dart';
import 'package:dio/dio.dart';
import 'package:retrofit/retrofit.dart';

part 'api_client.g.dart';

@RestApi()
abstract class AicoApiClient {
  factory AicoApiClient(Dio dio, {String baseUrl}) = _AicoApiClient;

  // Users API endpoints
  @GET("/users")
  Future<UserListResponse> getUsers({
    @Query("user_type") String? userType,
    @Query("limit") int limit = 100,
  });

  @POST("/users")
  Future<User> createUser(@Body() CreateUserRequest request);

  @GET("/users/{uuid}")
  Future<User> getUser(@Path("uuid") String uuid);

  @PUT("/users/{uuid}")
  Future<User> updateUser(
    @Path("uuid") String uuid,
    @Body() UpdateUserRequest request,
  );

  @DELETE("/users/{uuid}")
  Future<void> deleteUser(@Path("uuid") String uuid);

  @POST("/users/authenticate/")
  Future<AuthenticationResponse> authenticate(@Body() AuthenticateRequest request);

  // Admin API endpoints
  @GET("/admin/health")
  Future<AdminHealthResponse> getAdminHealth();

  @GET("/admin/gateway/status")
  Future<GatewayStatusResponse> getGatewayStatus();

  @GET("/admin/logs")
  Future<LogsListResponse> getLogs({
    @Query("limit") int? limit,
    @Query("offset") int? offset,
    @Query("level") String? level,
    @Query("subsystem") String? subsystem,
  });

  // Health API endpoints
  @GET("/health")
  Future<HealthResponse> getHealth();

  @GET("/health/detailed")
  Future<DetailedHealthResponse> getDetailedHealth();
}

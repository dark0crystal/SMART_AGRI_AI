import 'api_client.dart';

class AuthApiException implements Exception {
  AuthApiException(this.message, {this.statusCode});

  final String message;
  final int? statusCode;

  @override
  String toString() => message;
}

class AuthApi {
  static Future<Map<String, dynamic>> syncUser({String? username}) async {
    final payload = <String, dynamic>{};
    if (username != null && username.trim().isNotEmpty) {
      payload['username'] = username.trim();
    }
    return ApiClient.post('/api/users/sync/', body: payload);
  }

  static Future<Map<String, dynamic>> me() {
    return ApiClient.get('/api/me/');
  }
}

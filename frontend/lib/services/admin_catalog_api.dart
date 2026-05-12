import 'api_client.dart';

class AdminCatalogApi {
  static Future<Map<String, dynamic>> listPlants() {
    return ApiClient.get('/api/admin/catalog/plants/');
  }

  static Future<Map<String, dynamic>> getPlant(int plantId) {
    return ApiClient.get('/api/admin/catalog/plants/$plantId/');
  }

  static Future<Map<String, dynamic>> listDiseasesForPlant(int plantId) {
    return ApiClient.get('/api/admin/catalog/plants/$plantId/diseases/');
  }

  static Future<Map<String, dynamic>> getDisease(int diseaseId) {
    return ApiClient.get('/api/admin/catalog/diseases/$diseaseId/');
  }

  static Future<Map<String, dynamic>> updateDisease(
    int diseaseId,
    Map<String, dynamic> body,
  ) {
    return ApiClient.patch(
      '/api/admin/catalog/diseases/$diseaseId/',
      body: body,
    );
  }
}

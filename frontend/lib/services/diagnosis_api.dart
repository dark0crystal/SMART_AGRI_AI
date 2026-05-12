import 'api_client.dart';

class DiagnosisApi {
  /// Paginated list: keys `count`, `next`, `previous`, `results`.
  static Future<Map<String, dynamic>> listDiagnoses({int page = 1}) {
    return ApiClient.get('/api/diagnoses/', query: {'page': '$page'});
  }

  static Future<Map<String, dynamic>> getDiagnosis(int id) {
    return ApiClient.get('/api/diagnoses/$id/');
  }

  static Future<Map<String, dynamic>> createDiagnosis({
    required String inputType,
    String? textInput,
    String? imageUrl,
  }) {
    final payload = <String, dynamic>{
      'input_type': inputType,
    };
    if (textInput != null && textInput.isNotEmpty) {
      payload['text_input'] = textInput;
    }
    if (imageUrl != null && imageUrl.isNotEmpty) {
      payload['image_url'] = imageUrl;
    }
    // Image diagnoses can run inference on the server; allow extra time.
    return ApiClient.postDiagnosis('/api/diagnoses/', body: payload);
  }
}

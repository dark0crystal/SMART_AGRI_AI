/// Backend base URL. For Android emulator use:
/// `--dart-define=API_BASE_URL=http://10.0.2.2:8000`
const String kApiBaseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'http://127.0.0.1:8000',
);

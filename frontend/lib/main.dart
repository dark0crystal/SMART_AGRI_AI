import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';

import 'auth_refresh.dart';
import 'firebase_options.dart';
import 'screens/diagnosis_camera_screen.dart';
import 'screens/diagnosis_detail_screen.dart';
import 'screens/diagnosis_history_screen.dart';
import 'screens/diagnosis_hub_screen.dart';
import 'screens/diagnosis_text_screen.dart';
import 'screens/admin_catalog_screen.dart';
import 'screens/admin_disease_edit_screen.dart';
import 'screens/admin_plant_diseases_screen.dart';
import 'screens/home_screen.dart';
import 'screens/login_screen.dart';
import 'screens/register_screen.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  try {
    await Firebase.initializeApp(
      options: DefaultFirebaseOptions.currentPlatform,
    );
  } on PlatformException catch (e, st) {
    debugPrint('Firebase init failed: $e\n$st');
    if (e.code == 'channel-error') {
      // Hot Restart (R) often breaks the Firebase ↔ native pigeon channel.
      runApp(const _FirebaseInitErrorApp());
      return;
    }
    rethrow;
  } on FirebaseException catch (e, st) {
    debugPrint('Firebase init failed: $e\n$st');
    runApp(_FirebaseInitErrorApp(message: e.message ?? e.code));
    return;
  }
  runApp(const MyApp());
}

class _FirebaseInitErrorApp extends StatelessWidget {
  const _FirebaseInitErrorApp({this.message});

  final String? message;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      home: Scaffold(
        body: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Center(
              child: Text(
                message ??
                    'Firebase could not talk to the iOS engine. This often '
                    'happens after Hot Restart (R).\n\n'
                    'Fix: in the terminal press q to quit, then run '
                    '`flutter run` again (full process restart). Use hot '
                    'reload (r) instead of hot restart when working with '
                    'Firebase.',
                textAlign: TextAlign.center,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class MyApp extends StatefulWidget {
  const MyApp({super.key});

  @override
  State<MyApp> createState() => _MyAppState();
}

class _MyAppState extends State<MyApp> {
  late final AuthStateRefresh _authRefresh;
  late final GoRouter _router;

  @override
  void initState() {
    super.initState();
    _authRefresh = AuthStateRefresh();
    _router = GoRouter(
      initialLocation: '/login',
      refreshListenable: _authRefresh,
      redirect: (context, state) {
        final loggedIn = FirebaseAuth.instance.currentUser != null;
        final loc = state.matchedLocation;
        final onAuthPage = loc == '/login' || loc == '/register';
        if (!loggedIn && !onAuthPage) return '/login';
        if (loggedIn && onAuthPage) return '/';
        return null;
      },
      routes: [
        GoRoute(
          path: '/login',
          builder: (context, state) => const LoginScreen(),
        ),
        GoRoute(
          path: '/register',
          builder: (context, state) => const RegisterScreen(),
        ),
        GoRoute(
          path: '/',
          builder: (context, state) => const HomeScreen(),
        ),
        GoRoute(
          path: '/admin',
          builder: (context, state) => const AdminCatalogScreen(),
        ),
        GoRoute(
          path: '/admin/plant/:plantId',
          builder: (context, state) {
            final raw = state.pathParameters['plantId'];
            final plantId = int.tryParse(raw ?? '');
            if (plantId == null) {
              return const Scaffold(
                body: Center(child: Text('Invalid plant')),
              );
            }
            return AdminPlantDiseasesScreen(plantId: plantId);
          },
        ),
        GoRoute(
          path: '/admin/disease/:diseaseId',
          builder: (context, state) {
            final raw = state.pathParameters['diseaseId'];
            final diseaseId = int.tryParse(raw ?? '');
            if (diseaseId == null) {
              return const Scaffold(
                body: Center(child: Text('Invalid disease')),
              );
            }
            return AdminDiseaseEditScreen(diseaseId: diseaseId);
          },
        ),
        GoRoute(
          path: '/diagnosis',
          builder: (context, state) => const DiagnosisHubScreen(),
        ),
        GoRoute(
          path: '/diagnosis/text',
          builder: (context, state) => const DiagnosisTextScreen(),
        ),
        GoRoute(
          path: '/diagnosis/camera',
          builder: (context, state) => const DiagnosisCameraScreen(),
        ),
        GoRoute(
          path: '/diagnosis/history',
          builder: (context, state) => const DiagnosisHistoryScreen(),
        ),
        GoRoute(
          path: '/diagnosis/detail/:id',
          builder: (context, state) {
            final raw = state.pathParameters['id'];
            final id = int.tryParse(raw ?? '');
            if (id == null) {
              return const Scaffold(
                body: Center(child: Text('Invalid diagnosis id')),
              );
            }
            return DiagnosisDetailScreen(id: id);
          },
        ),
      ],
    );
  }

  @override
  void dispose() {
    _router.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'Smart Agri AI',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF3AAED8),
          primary: const Color(0xFF3AAED8),
          surface: Colors.white,
        ),
        scaffoldBackgroundColor: Colors.white,
        filledButtonTheme: FilledButtonThemeData(
          style: FilledButton.styleFrom(
            backgroundColor: const Color(0xFF3AAED8),
            foregroundColor: Colors.white,
          ),
        ),
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            backgroundColor: const Color(0xFF3AAED8),
            foregroundColor: Colors.white,
          ),
        ),
        floatingActionButtonTheme: const FloatingActionButtonThemeData(
          backgroundColor: Color(0xFF3AAED8),
          foregroundColor: Colors.white,
        ),
      ),
      routerConfig: _router,
    );
  }
}

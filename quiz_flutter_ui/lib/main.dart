import 'package:flutter/material.dart';
import 'package:window_manager/window_manager.dart';
import 'screens/digitize_screen.dart';
import 'screens/exam_list_screen.dart';
import 'screens/generate_screen.dart';
import 'screens/analytics_screen.dart';
import 'screens/settings_screen.dart';
import 'services/settings_service.dart';

// Global notifier for theme change
final themeNotifier = ValueNotifier<ThemeMode>(ThemeMode.light);

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await windowManager.ensureInitialized();

  final settings = await SettingsService.getInstance();
  await settings.ensureWorkspaceExists();
  
  // Load saved settings
  final width = settings.windowWidth;
  final height = settings.windowHeight;
  themeNotifier.value = settings.darkMode ? ThemeMode.dark : ThemeMode.light;

  windowManager.waitUntilReadyToShow(
    WindowOptions(
      size: Size(width, height),
      title: 'Quiz Processor',
      center: true,
      minimumSize: const Size(900, 600),
    ),
    () async {
      await windowManager.show();
      await windowManager.focus();
    },
  );

  runApp(const QuizProcessorApp());
}

class QuizProcessorApp extends StatelessWidget {
  const QuizProcessorApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder<ThemeMode>(
      valueListenable: themeNotifier,
      builder: (_, mode, __) {
        return MaterialApp(
          title: 'Quiz Processor',
          debugShowCheckedModeBanner: false,
          theme: ThemeData(
            useMaterial3: true,
            colorScheme: ColorScheme.fromSeed(
              seedColor: Colors.deepPurple,
              brightness: Brightness.light,
            ),
          ),
          darkTheme: ThemeData(
            useMaterial3: true,
            colorScheme: ColorScheme.fromSeed(
              seedColor: Colors.deepPurple,
              brightness: Brightness.dark,
            ),
          ),
          themeMode: mode,
          home: const MainNavigationScreen(),
        );
      },
    );
  }
}

class MainNavigationScreen extends StatefulWidget {
  const MainNavigationScreen({super.key});

  @override
  State<MainNavigationScreen> createState() => _MainNavigationScreenState();
}

class _MainNavigationScreenState extends State<MainNavigationScreen> {
  int _selectedIndex = 1; // Default to Exam List

  final List<Widget> _screens = [
    const DigitizeScreen(),
    const ExamListScreen(),
    const GenerateScreen(),
    const AnalyticsScreen(),
    const SettingsScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Row(
        children: [
          NavigationRail(
            extended: MediaQuery.of(context).size.width >= 1100,
            selectedIndex: _selectedIndex,
            onDestinationSelected: (int index) {
              setState(() {
                _selectedIndex = index;
              });
            },
            leading: Padding(
              padding: const EdgeInsets.symmetric(vertical: 24),
              child: Image.network(
                'https://cdn-icons-png.flaticon.com/512/3306/3306613.png',
                height: 48,
                errorBuilder: (_, __, ___) => const Icon(Icons.quiz, size: 48, color: Colors.deepPurple),
              ),
            ),
            destinations: const [
              NavigationRailDestination(
                icon: Icon(Icons.description_outlined),
                selectedIcon: Icon(Icons.description),
                label: Text('Số hóa & Kiểm tra'),
              ),
              NavigationRailDestination(
                icon: Icon(Icons.quiz_outlined),
                selectedIcon: Icon(Icons.quiz),
                label: Text('Làm bài'),
              ),
              NavigationRailDestination(
                icon: Icon(Icons.auto_awesome_outlined),
                selectedIcon: Icon(Icons.auto_awesome),
                label: Text('Tạo đề mới'),
              ),
               NavigationRailDestination(
                icon: Icon(Icons.analytics_outlined),
                selectedIcon: Icon(Icons.analytics),
                label: Text('Phân tích'),
              ),
              NavigationRailDestination(
                icon: Icon(Icons.settings_outlined),
                selectedIcon: Icon(Icons.settings),
                label: Text('Cài đặt'),
              ),
            ],
          ),
          const VerticalDivider(thickness: 1, width: 1),
          Expanded(
            child: _screens[_selectedIndex],
          ),
        ],
      ),
    );
  }
}

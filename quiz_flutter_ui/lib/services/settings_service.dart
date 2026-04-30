import 'package:shared_preferences/shared_preferences.dart';
import 'dart:io';
import 'package:path/path.dart' as p;

class SettingsService {
  static SettingsService? _instance;
  static SharedPreferences? _prefs;

  SettingsService._();

  static Future<SettingsService> getInstance() async {
    _prefs ??= await SharedPreferences.getInstance();
    _instance ??= SettingsService._();
    return _instance!;
  }

  // --- Shuffle ---
  bool get shuffleEnabled => _prefs?.getBool('shuffle_enabled') ?? true;
  Future<void> setShuffleEnabled(bool value) async =>
      _prefs?.setBool('shuffle_enabled', value);

  // --- Window Size ---
  double get windowWidth => _prefs?.getDouble('window_width') ?? 1280.0;
  double get windowHeight => _prefs?.getDouble('window_height') ?? 720.0;
  Future<void> setWindowSize(double width, double height) async {
    await _prefs?.setDouble('window_width', width);
    await _prefs?.setDouble('window_height', height);
  }

  // --- Dark Mode ---
  bool get darkMode => _prefs?.getBool('dark_mode') ?? false;
  Future<void> setDarkMode(bool value) async => _prefs?.setBool('dark_mode', value);

  // --- Workspace Path ---
  String get workspacePath {
    String? path = _prefs?.getString('workspace_path');
    if (path == null || path.isEmpty) {
      // Default to current directory / quiz_workspace
      path = p.join(Directory.current.path, 'quiz_workspace');
    }
    return path;
  }
  Future<void> setWorkspacePath(String path) async =>
      _prefs?.setString('workspace_path', path);

  // Helper to get exams folder
  String get examsPath => p.join(workspacePath, 'exams');
  String get digitsPath => p.join(workspacePath, 'digits');
  String get exportsPath => p.join(workspacePath, 'exports');

  // Ensure workspace exists
  Future<void> ensureWorkspaceExists() async {
    await Directory(workspacePath).create(recursive: true);
    await Directory(examsPath).create(recursive: true);
    await Directory(digitsPath).create(recursive: true);
    await Directory(exportsPath).create(recursive: true);
  }
}

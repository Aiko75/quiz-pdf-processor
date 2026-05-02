import 'package:shared_preferences/shared_preferences.dart';
import 'dart:io';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

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

  // --- Paths Persistence ---
  String get digitizeInputPath => _prefs?.getString('digitize_input_path') ?? '';
  Future<void> setDigitizeInputPath(String path) async => _prefs?.setString('digitize_input_path', path);

  String get digitizeOutputPath => _prefs?.getString('digitize_output_path') ?? '';
  Future<void> setDigitizeOutputPath(String path) async => _prefs?.setString('digitize_output_path', path);

  String get generateInputPath => _prefs?.getString('generate_input_path') ?? '';
  Future<void> setGenerateInputPath(String path) async => _prefs?.setString('generate_input_path', path);

  String get generateOutputPath => _prefs?.getString('generate_output_path') ?? '';
  Future<void> setGenerateOutputPath(String path) async => _prefs?.setString('generate_output_path', path);

  // --- Quiz Preferences ---
  bool get autoAdvanceQuiz => _prefs?.getBool('auto_advance_quiz') ?? false;
  Future<void> setAutoAdvanceQuiz(bool value) async => _prefs?.setBool('auto_advance_quiz', value);

  bool get quizShortcutsEnabled => _prefs?.getBool('quiz_shortcuts_enabled') ?? true;
  Future<void> setQuizShortcutsEnabled(bool value) async => _prefs?.setBool('quiz_shortcuts_enabled', value);

  // --- View Mode ---
  String get examViewMode => _prefs?.getString('exam_view_mode') ?? 'list'; // 'list' or 'grid'
  Future<void> setExamViewMode(String mode) async => _prefs?.setString('exam_view_mode', mode);

  // --- Generate Session State ---
  bool get generateRangeMode => _prefs?.getBool('gen_range_mode') ?? false;
  Future<void> setGenerateRangeMode(bool value) async => _prefs?.setBool('gen_range_mode', value);

  int get generateFromQ => _prefs?.getInt('gen_from_q') ?? 1;
  Future<void> setGenerateFromQ(int value) async => _prefs?.setInt('gen_from_q', value);

  int get generateToQ => _prefs?.getInt('gen_to_q') ?? 0;
  Future<void> setGenerateToQ(int value) async => _prefs?.setInt('gen_to_q', value);

  double get generateCount => _prefs?.getDouble('gen_count') ?? 40.0;
  Future<void> setGenerateCount(double value) async => _prefs?.setDouble('gen_count', value);

  int get generateTimeLimit => _prefs?.getInt('gen_time_limit') ?? 45;
  Future<void> setGenerateTimeLimit(int value) async => _prefs?.setInt('gen_time_limit', value);

  String get generateTargetFolder => _prefs?.getString('gen_target_folder') ?? '';
  Future<void> setGenerateTargetFolder(String folder) async => _prefs?.setString('gen_target_folder', folder);

  bool get generateDocx => _prefs?.getBool('gen_docx') ?? true;
  Future<void> setGenerateDocx(bool value) async => _prefs?.setBool('gen_docx', value);

  bool get generateJson => _prefs?.getBool('gen_json') ?? true;
  Future<void> setGenerateJson(bool value) async => _prefs?.setBool('gen_json', value);

  // --- Workspace Path ---
  String get workspacePath {
    String? path = _prefs?.getString('workspace_path');
    if (path == null || path.isEmpty) {
      // Fallback to a safe relative path if not yet initialized
      return p.join(Directory.current.path, 'quiz_workspace');
    }
    return path;
  }

  Future<void> initDefaultWorkspace() async {
    String? path = _prefs?.getString('workspace_path');
    if (path == null || path.isEmpty) {
      try {
        final docDir = await getApplicationDocumentsDirectory();
        path = p.join(docDir.path, 'QuizProcessor');
        await _prefs?.setString('workspace_path', path);
      } catch (e) {
        // Fallback for environments where path_provider might fail
        path = p.join(Directory.current.path, 'quiz_workspace');
        await _prefs?.setString('workspace_path', path);
      }
    }
  }

  Future<void> setWorkspacePath(String path) async =>
      _prefs?.setString('workspace_path', path);

  // Helper to get exams folder
  String get examsPath => p.join(workspacePath, 'exams');
  String get digitsPath => p.join(workspacePath, 'digits');
  String get exportsPath => p.join(workspacePath, 'exports');

  // Discover subfolders in exams directory
  List<String> getExamSubFolders() {
    final dir = Directory(examsPath);
    if (!dir.existsSync()) return [];
    
    return dir.listSync()
        .whereType<Directory>()
        .map((d) => p.basename(d.path))
        .toList();
  }

  // Ensure workspace exists
  Future<void> ensureWorkspaceExists() async {
    await Directory(workspacePath).create(recursive: true);
    await Directory(examsPath).create(recursive: true);
    await Directory(digitsPath).create(recursive: true);
    await Directory(exportsPath).create(recursive: true);
  }
}

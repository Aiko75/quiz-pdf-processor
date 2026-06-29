import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:path/path.dart' as p;
import 'dart:io';
import 'dart:convert';
import 'settings_service.dart';

class DatabaseService {
  static DatabaseService? _instance;
  static Database? _db;

  DatabaseService._();

  static Future<DatabaseService> getInstance() async {
    if (_instance == null) {
      if (Platform.isWindows || Platform.isLinux) {
        sqfliteFfiInit();
        databaseFactory = databaseFactoryFfi;
      }
      _instance = DatabaseService._();
      await _instance!._initDb();
    }
    return _instance!;
  }

  Future<void> _initDb() async {
    final settings = await SettingsService.getInstance();
    final dbPath = p.join(settings.workspacePath, 'quiz_history.db');

    _db = await openDatabase(
      dbPath,
      version: 2,
      onCreate: (db, version) async {
        await db.execute('''
          CREATE TABLE history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exam_id TEXT,
            exam_title TEXT,
            folder TEXT,
            score_correct INTEGER,
            score_total INTEGER,
            time_spent_seconds INTEGER,
            timestamp TEXT,
            answers_json TEXT
          )
        ''');
      },
      onUpgrade: (db, oldVersion, newVersion) async {
        if (oldVersion < 2) {
          await db.execute('ALTER TABLE history ADD COLUMN folder TEXT');
        }
      },
    );
    await _updateMissingFolders();
  }

  Future<void> _updateMissingFolders() async {
    try {
      final settings = await SettingsService.getInstance();
      final examsPath = p.join(settings.workspacePath, 'exams');
      final examsDir = Directory(examsPath);
      if (!await examsDir.exists()) return;

      final missing = await _db!.rawQuery(
        "SELECT COUNT(*) as count FROM history WHERE folder IS NULL OR folder = ''"
      );
      if (missing.isEmpty || (missing.first['count'] as int) == 0) return;

      final Map<String, String> examIdToFolder = {};
      final entities = examsDir.listSync(recursive: true);
      for (var entity in entities) {
        if (entity is File && entity.path.endsWith('.json')) {
          try {
            final content = await entity.readAsString();
            final data = jsonDecode(content);
            final examId = data['id'];
            if (examId != null) {
              final relPath = p.relative(entity.path, from: examsPath);
              final parts = p.split(relPath);
              if (parts.length > 1) {
                examIdToFolder[examId] = parts[0];
              }
            }
          } catch (e) {}
        }
      }

      if (examIdToFolder.isNotEmpty) {
        await _db!.transaction((txn) async {
          for (var entry in examIdToFolder.entries) {
            await txn.rawUpdate(
              "UPDATE history SET folder = ? WHERE exam_id = ? AND (folder IS NULL OR folder = '')",
              [entry.value, entry.key],
            );
          }
        });
      }
    } catch (e) {}
  }

  Future<int> saveAttempt({
    required String examId,
    required String examTitle,
    String? folder,
    required int scoreCorrect,
    required int scoreTotal,
    required int timeSpentSeconds,
    required String answersJson,
  }) async {
    return await _db!.insert('history', {
      'exam_id': examId,
      'exam_title': examTitle,
      'folder': folder,
      'score_correct': scoreCorrect,
      'score_total': scoreTotal,
      'time_spent_seconds': timeSpentSeconds,
      'timestamp': DateTime.now().toIso8601String(),
      'answers_json': answersJson,
    });
  }

  Future<List<Map<String, dynamic>>> getHistory({String? examId}) async {
    if (examId != null) {
      return await _db!.query(
        'history',
        where: 'exam_id = ?',
        whereArgs: [examId],
        orderBy: 'timestamp DESC',
      );
    }
    return await _db!.query('history', orderBy: 'timestamp DESC');
  }

  Future<void> clearHistory() async {
    await _db!.delete('history');
  }

  // E6: Smart Statistics
  Future<Map<String, dynamic>> getGlobalStats() async {
    final result = await _db!.rawQuery(
      'SELECT COUNT(*) as total_attempts, SUM(score_correct) as total_correct, SUM(score_total) as total_questions, SUM(time_spent_seconds) as total_time FROM history',
    );
    if (result.isEmpty || result.first['total_attempts'] == 0) {
      return {
        'total_attempts': 0,
        'total_correct': 0,
        'total_questions': 0,
        'total_time': 0,
      };
    }
    return result.first;
  }

  Future<List<Map<String, dynamic>>> getStatsByFolder() async {
    return await _db!.rawQuery('''
      SELECT 
        COALESCE(folder, 'Khác') as subject, 
        COUNT(*) as attempts, 
        SUM(score_correct) as correct, 
        SUM(score_total) as total,
        AVG(CAST(score_correct AS FLOAT) / score_total) * 100 as avg_percent
      FROM history 
      GROUP BY folder 
      ORDER BY avg_percent DESC
    ''');
  }

  Future<List<Map<String, dynamic>>> getWeakExams() async {
    return await _db!.rawQuery('''
      SELECT exam_title, folder, AVG(CAST(score_correct AS FLOAT) / score_total) as avg_rate
      FROM history
      GROUP BY exam_id
      HAVING avg_rate < 0.5
      ORDER BY avg_rate ASC
      LIMIT 5
    ''');
  }
}

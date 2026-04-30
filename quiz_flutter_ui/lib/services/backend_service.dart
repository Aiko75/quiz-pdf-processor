import 'dart:convert';
import 'dart:io';
import 'package:path/path.dart' as p;

class BackendService {
  static final BackendService _instance = BackendService._internal();
  factory BackendService() => _instance;
  BackendService._internal();

  Process? _currentProcess;

  Future<void> runAction({
    required String action,
    Map<String, String>? params,
    required Function(String) onLog,
    required Function(Map<String, dynamic>) onResult,
    required Function(String) onError,
  }) async {
    try {
      // Xác định đường dẫn tới quiz_cli
      // Trong môi trường dev, nó nằm ở thư mục cha: ../quiz_cli.py
      // Trong môi trường production, nó nằm cùng thư mục với file exe: quiz_cli.exe
      
      final exePath = p.join(p.dirname(Platform.resolvedExecutable), 'quiz_cli.exe');
      final scriptPath = p.join(Directory.current.parent.path, 'quiz_cli.py');
      
      String executable;
      List<String> args = [];

      if (await File(exePath).exists()) {
        executable = exePath;
        args.add('--action');
        args.add(action);
      } else {
        executable = 'python';
        args.add(scriptPath);
        args.add('--action');
        args.add(action);
      }

      if (params != null) {
        params.forEach((key, value) {
          args.add('--$key');
          args.add(value);
        });
      }

      // TODO: Khi đóng gói, chúng ta sẽ gọi file .exe thay vì python script
      _currentProcess = await Process.start(executable, args);

      _currentProcess!.stdout
          .transform(utf8.decoder)
          .transform(const LineSplitter())
          .listen((line) {
        try {
          final data = jsonDecode(line);
          if (data['type'] == 'log') {
            onLog(data['message']);
          } else if (data['type'] == 'result') {
            onResult(data);
          }
        } catch (e) {
          // Nếu không phải JSON, coi như log thường
          if (line.trim().isNotEmpty) onLog(line);
        }
      });

      _currentProcess!.stderr
          .transform(utf8.decoder)
          .transform(const LineSplitter())
          .listen((line) {
        if (line.trim().isNotEmpty) onError(line);
      });

      final exitCode = await _currentProcess!.exitCode;
      if (exitCode != 0) {
        onError("Tiến trình kết thúc với mã lỗi: $exitCode");
      }
    } catch (e) {
      onError("Không thể khởi động tiến trình: $e");
    } finally {
      _currentProcess = null;
    }
  }

  void stop() {
    _currentProcess?.kill();
  }
}

import 'package:flutter/material.dart';
import 'dart:io';
import '../widgets/path_selector.dart';
import '../widgets/log_console.dart';
import '../services/backend_service.dart';
import '../services/settings_service.dart';

class GenerateScreen extends StatefulWidget {
  const GenerateScreen({super.key});

  @override
  State<GenerateScreen> createState() => _GenerateScreenState();
}

class _GenerateScreenState extends State<GenerateScreen> {
  String _answerFile = '';
  String _outputDir = '';
  String _targetFolder = '';
  double _count = 40;
  int _fromQ = 1;
  int _toQ = 0;
  bool _genAnswer = true;
  bool _isInteractive = true;
  int _timeLimit = 45;
  final List<String> _logs = [];
  bool _isRunning = false;
  bool _useRange = false;
  late SettingsService _settings;
  List<String> _existingFolders = [];
  String? _lastGeneratedFile;
  String? _lastCheckedFile;
  bool _checkedFileHasErrors = false;
  final _manualQIndexController = TextEditingController();
  final _manualMsgController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _loadSettings();
  }

  @override
  void dispose() {
    _manualQIndexController.dispose();
    _manualMsgController.dispose();
    super.dispose();
  }

  Future<void> _loadSettings() async {
    _settings = await SettingsService.getInstance();
    setState(() {
      _answerFile = _settings.generateInputPath;
      _outputDir = _settings.generateOutputPath;
      _useRange = _settings.generateRangeMode;
      _fromQ = _settings.generateFromQ;
      _toQ = _settings.generateToQ;
      _count = _settings.generateCount;
      _timeLimit = _settings.generateTimeLimit;
      _targetFolder = _settings.generateTargetFolder;
      _genAnswer = _settings.generateDocx;
      _isInteractive = _settings.generateJson;
      _existingFolders = _settings.getExamSubFolders();
      if (_targetFolder.isNotEmpty &&
          !_existingFolders.contains(_targetFolder)) {
        _existingFolders.add(_targetFolder);
      }
    });
  }

  void _updateSettings() {
    _settings.setGenerateInputPath(_answerFile);
    _settings.setGenerateOutputPath(_outputDir);
    _settings.setGenerateRangeMode(_useRange);
    _settings.setGenerateFromQ(_fromQ);
    _settings.setGenerateToQ(_toQ);
    _settings.setGenerateCount(_count);
    _settings.setGenerateTimeLimit(_timeLimit);
    _settings.setGenerateTargetFolder(_targetFolder);
    _settings.setGenerateDocx(_genAnswer);
    _settings.setGenerateJson(_isInteractive);
  }

  void _runGenerate() {
    if (_answerFile.isEmpty || _outputDir.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Vui lòng chọn đầy đủ file đáp án và thư mục output'),
        ),
      );
      return;
    }

    _updateSettings();

    setState(() {
      _isRunning = true;
      _lastGeneratedFile = null;
      _lastCheckedFile = null;
      _checkedFileHasErrors = false;
      _logs.add('\n--- Bắt đầu: Tạo đề mới ---');
    });

    BackendService().runAction(
      action: 'generate',
      params: {
        'answer-file': _answerFile,
        'output': _outputDir,
        if (_targetFolder.isNotEmpty) 'folder': _targetFolder,
        if (!_useRange) 'count': _count.toInt().toString(),
        if (_useRange) 'from-q': _fromQ.toString(),
        if (_useRange) 'to-q': _toQ.toString(),
        if (_genAnswer) 'gen-answer': '',
        if (_isInteractive) 'interactive': '',
        if (_isInteractive) 'time-limit': _timeLimit.toString(),
      },
      onLog: (msg) => setState(() => _logs.add(msg)),
      onResult: (res) {
        setState(() {
          _isRunning = false;
          _existingFolders = _settings.getExamSubFolders(); // Refresh folders
          if (res['status'] == 'success') {
            _lastGeneratedFile = res['file'];
          }
        });
        if (res['status'] == 'success') {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Tạo đề hoàn tất: ${res['message']}')),
          );
        } else if (res['status'] == 'error') {
          setState(() => _logs.add('[LỖI] ${res['message']}'));
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Lỗi tạo đề: ${res['message']}')),
          );
        }
      },
      onError: (err) {
        setState(() {
          _isRunning = false;
          _logs.add('[LỖI] $err');
        });
      },
    );
  }

  void _runDoubleCheck() {
    if (_answerFile.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Vui lòng chọn file đáp án nguồn để kiểm định'),
        ),
      );
      return;
    }

    _updateSettings();

    setState(() {
      _isRunning = true;
      _lastGeneratedFile = null;
      _lastCheckedFile = null;
      _checkedFileHasErrors = false;
      _logs.add('\n--- Bắt đầu: Kiểm định cấu trúc câu ---');
    });

    BackendService().runAction(
      action: 'doublecheck',
      params: {
        'answer-file': _answerFile,
      },
      onLog: (msg) => setState(() => _logs.add(msg)),
      onResult: (res) {
        setState(() {
          _isRunning = false;
          _lastCheckedFile = _answerFile;
          _checkedFileHasErrors = res['message'] != null && res['message']!.contains('lỗi cấu trúc');
        });
        if (res['status'] == 'success') {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(res['message'] ?? 'Kiểm định hoàn tất')),
          );
        } else if (res['status'] == 'error') {
          setState(() => _logs.add('[LỖI] ${res['message']}'));
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Lỗi kiểm định: ${res['message']}')),
          );
        }
      },
      onError: (err) {
        setState(() {
          _isRunning = false;
          _logs.add('[LỖI] $err');
        });
      },
    );
  }

  void _submitManualFeedback() {
    if (_answerFile.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Vui lòng chọn file đáp án nguồn trước')),
      );
      return;
    }
    final qIndexText = _manualQIndexController.text.trim();
    final message = _manualMsgController.text.trim();
    if (qIndexText.isEmpty || message.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Vui lòng điền đủ Số câu và Mô tả lỗi')),
      );
      return;
    }
    final qIndex = int.tryParse(qIndexText);
    if (qIndex == null || qIndex <= 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Số câu phải là số nguyên dương')),
      );
      return;
    }

    setState(() {
      _isRunning = true;
      _logs.add('\n--- Bắt đầu: Gửi báo lỗi thủ công ---');
    });

    BackendService().runAction(
      action: 'add_feedback',
      params: {
        'answer-file': _answerFile,
        'question-index': qIndex.toString(),
        'message': message,
      },
      onLog: (msg) => setState(() => _logs.add(msg)),
      onResult: (res) {
        setState(() {
          _isRunning = false;
        });
        if (res['status'] == 'success') {
          _manualQIndexController.clear();
          _manualMsgController.clear();
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(res['message'] ?? 'Đã gửi báo lỗi thành công')),
          );
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Gửi báo lỗi thất bại: ${res['message']}')),
          );
        }
      },
      onError: (err) {
        setState(() {
          _isRunning = false;
          _logs.add('[LỖI] $err');
        });
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(24.0),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Left Side: Config
          Expanded(
            flex: 2,
            child: SingleChildScrollView(
              child: Padding(
                padding: const EdgeInsets.only(right: 16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Tạo Đề Trắc Nghiệm Mới',
                      style: Theme.of(context).textTheme.headlineSmall,
                    ),
                    const SizedBox(height: 32),
                    PathSelector(
                      label: 'File đáp án nguồn (PDF/DOCX)',
                      value: _answerFile,
                      isDirectory: false,
                      allowedExtensions: ['pdf', 'docx'],
                      onSelected: (val) {
                        setState(() => _answerFile = val);
                        _settings.setGenerateInputPath(val);
                      },
                    ),
                    const SizedBox(height: 16),
                    PathSelector(
                      label: 'Thư mục Output (DOCX)',
                      value: _outputDir,
                      onSelected: (val) {
                        setState(() => _outputDir = val);
                        _settings.setGenerateOutputPath(val);
                      },
                    ),
                    const SizedBox(height: 32),
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(16.0),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Tùy chọn tạo đề',
                              style: Theme.of(context).textTheme.titleMedium,
                            ),
                            const SizedBox(height: 16),
                            Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      RadioListTile<bool>(
                                        title: Text(
                                          'Chọn ngẫu nhiên (${_count.toInt()} câu)',
                                        ),
                                        value: false,
                                        groupValue: _useRange,
                                        onChanged: (val) {
                                          setState(() => _useRange = val!);
                                          _settings.setGenerateRangeMode(val!);
                                        },
                                        contentPadding: EdgeInsets.zero,
                                      ),
                                      Slider(
                                        value: _count,
                                        min: 1,
                                        max: 200,
                                        divisions: 199,
                                        label: _count.round().toString(),
                                        onChanged: _useRange
                                            ? null
                                            : (val) {
                                                setState(() => _count = val);
                                                _settings.setGenerateCount(val);
                                              },
                                      ),
                                      const Divider(),
                                      RadioListTile<bool>(
                                        title: const Text('Chọn theo khoảng câu'),
                                        value: true,
                                        groupValue: _useRange,
                                        onChanged: (val) {
                                          setState(() => _useRange = val!);
                                          _settings.setGenerateRangeMode(val!);
                                        },
                                        contentPadding: EdgeInsets.zero,
                                      ),
                                      Row(
                                        children: [
                                          const SizedBox(width: 32),
                                          const Text('Từ:'),
                                          const SizedBox(width: 8),
                                          SizedBox(
                                            width: 60,
                                            child: TextFormField(
                                              key: ValueKey('from_$_fromQ'),
                                              initialValue: _fromQ.toString(),
                                              keyboardType: TextInputType.number,
                                              enabled: _useRange,
                                              onChanged: (val) {
                                                _fromQ = int.tryParse(val) ?? 1;
                                                _settings.setGenerateFromQ(_fromQ);
                                              },
                                              decoration: const InputDecoration(
                                                isDense: true,
                                              ),
                                            ),
                                          ),
                                          const SizedBox(width: 16),
                                          const Text('Đến:'),
                                          const SizedBox(width: 8),
                                          SizedBox(
                                            width: 60,
                                            child: TextFormField(
                                              key: ValueKey('to_$_toQ'),
                                              initialValue: _toQ.toString(),
                                              keyboardType: TextInputType.number,
                                              enabled: _useRange,
                                              onChanged: (val) {
                                                _toQ = int.tryParse(val) ?? 0;
                                                _settings.setGenerateToQ(_toQ);
                                              },
                                              decoration: const InputDecoration(
                                                isDense: true,
                                              ),
                                            ),
                                          ),
                                          const SizedBox(width: 8),
                                          const Text('(0 = hết)'),
                                        ],
                                      ),
                                    ],
                                  ),
                                ),
                                const SizedBox(width: 32),
                                Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    CheckboxMenuButton(
                                      value: _genAnswer,
                                      onChanged: (val) {
                                        setState(() => _genAnswer = val ?? true);
                                        _settings.setGenerateDocx(val ?? true);
                                      },
                                      child: const Text('Tạo file đáp án DOCX'),
                                    ),
                                    CheckboxMenuButton(
                                      value: _isInteractive,
                                      onChanged: (val) {
                                        setState(() => _isInteractive = val ?? true);
                                        _settings.setGenerateJson(val ?? true);
                                      },
                                      child: const Text(
                                        'Tạo bài kiểm tra trực tuyến (JSON)',
                                      ),
                                    ),
                                    if (_isInteractive) ...[
                                      const SizedBox(height: 16),
                                      Padding(
                                        padding: const EdgeInsets.only(left: 16.0),
                                        child: Column(
                                          crossAxisAlignment: CrossAxisAlignment.start,
                                          children: [
                                            const Text('Thư mục đích (trong Exams):'),
                                            const SizedBox(height: 4),
                                            SizedBox(
                                              width: 200,
                                              child: DropdownButtonFormField<String>(
                                                initialValue: _targetFolder.isEmpty
                                                    ? null
                                                    : _targetFolder,
                                                hint: const Text('Thư mục gốc'),
                                                isExpanded: true,
                                                decoration: const InputDecoration(
                                                  isDense: true,
                                                  border: OutlineInputBorder(),
                                                ),
                                                items: [
                                                  const DropdownMenuItem(
                                                    value: '',
                                                    child: Text('Thư mục gốc'),
                                                  ),
                                                  ..._existingFolders.map(
                                                    (f) => DropdownMenuItem(
                                                      value: f,
                                                      child: Text(f),
                                                    ),
                                                  ),
                                                ],
                                                onChanged: (v) {
                                                  setState(() => _targetFolder = v ?? '');
                                                  _settings.setGenerateTargetFolder(
                                                    v ?? '',
                                                  );
                                                },
                                              ),
                                            ),
                                            const SizedBox(height: 12),
                                            const Text('Thời gian làm bài (phút):'),
                                            Row(
                                              children: [
                                                SizedBox(
                                                  width: 120,
                                                  child: Slider(
                                                    value: _timeLimit.toDouble(),
                                                    min: 5,
                                                    max: 180,
                                                    divisions: 35,
                                                    label: _timeLimit.toString(),
                                                    onChanged: (val) {
                                                      setState(
                                                        () => _timeLimit = val.toInt(),
                                                      );
                                                      _settings.setGenerateTimeLimit(
                                                        val.toInt(),
                                                      );
                                                    },
                                                  ),
                                                ),
                                                Text('${_timeLimit}p'),
                                              ],
                                            ),
                                          ],
                                        ),
                                      ),
                                    ],
                                  ],
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 32),
                    Wrap(
                      spacing: 16,
                      runSpacing: 12,
                      children: [
                        FilledButton.icon(
                          onPressed: _isRunning ? null : _runGenerate,
                          icon: _isRunning
                              ? const SizedBox(
                                  width: 18,
                                  height: 18,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                    color: Colors.white,
                                  ),
                                )
                              : const Icon(Icons.auto_fix_high),
                          label: const Text('Bắt đầu Tạo đề'),
                          style: FilledButton.styleFrom(minimumSize: const Size(200, 50)),
                        ),
                        OutlinedButton.icon(
                          onPressed: _isRunning ? null : _runDoubleCheck,
                          icon: const Icon(Icons.fact_check),
                          label: const Text('Kiểm định cấu trúc câu'),
                          style: OutlinedButton.styleFrom(minimumSize: const Size(200, 50)),
                        ),
                      ],
                    ),
                    const SizedBox(height: 32),
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(16.0),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Báo lỗi câu hỏi thủ công',
                              style: Theme.of(context).textTheme.titleMedium,
                            ),
                            const SizedBox(height: 12),
                            Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                SizedBox(
                                  width: 100,
                                  child: TextFormField(
                                    controller: _manualQIndexController,
                                    keyboardType: TextInputType.number,
                                    decoration: const InputDecoration(
                                      labelText: 'Số câu',
                                      isDense: true,
                                      border: OutlineInputBorder(),
                                    ),
                                  ),
                                ),
                                const SizedBox(width: 16),
                                Expanded(
                                  child: TextFormField(
                                    controller: _manualMsgController,
                                    decoration: const InputDecoration(
                                      labelText: 'Mô tả lỗi câu hỏi...',
                                      isDense: true,
                                      border: OutlineInputBorder(),
                                    ),
                                  ),
                                ),
                                const SizedBox(width: 16),
                                ElevatedButton.icon(
                                  onPressed: _isRunning ? null : _submitManualFeedback,
                                  icon: const Icon(Icons.send),
                                  label: const Text('Gửi báo lỗi'),
                                  style: ElevatedButton.styleFrom(
                                    minimumSize: const Size(120, 48),
                                  ),
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 32),
                    if (_lastGeneratedFile != null) ...[
                      Card(
                        color: Theme.of(context).colorScheme.primaryContainer.withOpacity(0.2),
                        child: Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 12.0),
                          child: Row(
                            children: [
                              Icon(Icons.check_circle, color: Theme.of(context).colorScheme.primary),
                              const SizedBox(width: 12),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    const Text(
                                      'Tạo đề thi thành công!',
                                      style: TextStyle(fontWeight: FontWeight.bold),
                                    ),
                                    Text(
                                      _lastGeneratedFile!,
                                      style: const TextStyle(fontSize: 12),
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                  ],
                                ),
                              ),
                              TextButton.icon(
                                onPressed: () {
                                  Process.run('explorer.exe', [_lastGeneratedFile!]);
                                },
                                icon: const Icon(Icons.open_in_new),
                                label: const Text('Mở file'),
                              ),
                              const SizedBox(width: 8),
                              TextButton.icon(
                                onPressed: () {
                                  Process.run('explorer.exe', ['/select,', _lastGeneratedFile!]);
                                },
                                icon: const Icon(Icons.folder_open),
                                label: const Text('Hiển thị'),
                              ),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(height: 16),
                    ],
                    if (_lastCheckedFile != null) ...[
                      Card(
                        color: _checkedFileHasErrors
                            ? Theme.of(context).colorScheme.errorContainer.withOpacity(0.2)
                            : Theme.of(context).colorScheme.primaryContainer.withOpacity(0.2),
                        child: Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 12.0),
                          child: Row(
                            children: [
                              Icon(
                                _checkedFileHasErrors ? Icons.warning : Icons.check_circle,
                                color: _checkedFileHasErrors
                                    ? Theme.of(context).colorScheme.error
                                    : Theme.of(context).colorScheme.primary,
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      _checkedFileHasErrors
                                          ? 'Phát hiện câu hỏi lỗi cấu trúc!'
                                          : 'Kiểm định cấu trúc thành công!',
                                      style: TextStyle(
                                        fontWeight: FontWeight.bold,
                                        color: _checkedFileHasErrors
                                            ? Theme.of(context).colorScheme.error
                                            : null,
                                      ),
                                    ),
                                    Text(
                                      _lastCheckedFile!,
                                      style: const TextStyle(fontSize: 12),
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                  ],
                                ),
                              ),
                              TextButton.icon(
                                onPressed: () {
                                  Process.run('explorer.exe', [_lastCheckedFile!]);
                                },
                                icon: const Icon(Icons.open_in_new),
                                label: const Text('Mở file lỗi/nguồn'),
                              ),
                              const SizedBox(width: 8),
                              TextButton.icon(
                                onPressed: () {
                                  Process.run('explorer.exe', ['/select,', _lastCheckedFile!]);
                                },
                                icon: const Icon(Icons.folder_open),
                                label: const Text('Hiển thị'),
                              ),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(height: 16),
                    ],
                  ],
                ),
              ),
            ),
          ),
          const SizedBox(width: 24),
          // Right Side: Logs
          Expanded(
            flex: 1,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Logs hệ thống',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 8),
                Expanded(child: LogConsole(logs: _logs)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

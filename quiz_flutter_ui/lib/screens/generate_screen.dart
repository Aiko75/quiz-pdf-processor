import 'package:flutter/material.dart';
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

  @override
  void initState() {
    super.initState();
    _loadSettings();
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
      _logs.add('\n--- Bắt đầu: Tạo đề mới ---');
    });

    BackendService().runAction(
      action: 'generate',
      params: {
        'answer-file': _answerFile,
        'output': _outputDir,
        'folder': _targetFolder,
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

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(24.0),
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
          const SizedBox(height: 32),
          Expanded(child: LogConsole(logs: _logs)),
        ],
      ),
    );
  }
}

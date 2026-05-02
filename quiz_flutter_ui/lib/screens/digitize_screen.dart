import 'dart:io';
import 'dart:async';
import 'package:flutter/material.dart';
import '../widgets/path_selector.dart';
import '../widgets/log_console.dart';
import '../services/backend_service.dart';
import '../services/settings_service.dart';

class DigitizeScreen extends StatefulWidget {
  const DigitizeScreen({super.key});

  @override
  State<DigitizeScreen> createState() => _DigitizeScreenState();
}

class _DigitizeScreenState extends State<DigitizeScreen> {
  String _inputDir = '';
  String _outputDir = '';
  final List<String> _logs = [];
  bool _isRunning = false;
  
  // D2/D3: File tracking
  List<Map<String, dynamic>> _files = [];
  bool _isLoaded = false;

  @override
  void initState() {
    super.initState();
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    final settings = await SettingsService.getInstance();
    setState(() {
      _inputDir = settings.digitizeInputPath;
      _outputDir = settings.digitizeOutputPath;
      _isLoaded = true;
    });
    if (_inputDir.isNotEmpty) {
      _scanFolder();
    }
  }

  Future<void> _savePaths() async {
    final settings = await SettingsService.getInstance();
    await settings.setDigitizeInputPath(_inputDir);
    await settings.setDigitizeOutputPath(_outputDir);
  }

  void _scanFolder() {
    if (_inputDir.isEmpty || !Directory(_inputDir).existsSync()) return;
    try {
      final dir = Directory(_inputDir);
      final pdfs = dir.listSync().whereType<File>().where((f) => f.path.endsWith('.pdf')).toList();
      
      setState(() {
        _files = pdfs.map((f) => {
          'path': f.path,
          'name': f.path.split(Platform.pathSeparator).last,
          'status': 'idle', // idle, running, success, error
          'message': '',
          'selected': true,
        }).toList();
      });
    } catch (e) {
      setState(() => _logs.add('[LỖI] Không thể quét thư mục: $e'));
    }
  }

  Future<void> _processAll() async {
    if (_files.isEmpty) return;
    setState(() => _isRunning = true);
    
    for (var i = 0; i < _files.length; i++) {
      if (!_files[i]['selected'] || _files[i]['status'] == 'success') continue;
      await _processFile(i);
    }
    
    setState(() => _isRunning = false);
  }

  Future<void> _processFile(int index) async {
    setState(() {
      _files[index]['status'] = 'running';
      _logs.add('Đang xử lý: ${_files[index]['name']}...');
    });

    final completer = Completer<void>();
    
    BackendService().runAction(
      action: 'process',
      params: {
        'input': _files[index]['path'],
        'output': _outputDir,
      },
      onLog: (msg) => setState(() => _logs.add(msg)),
      onResult: (res) {
        setState(() {
          _files[index]['status'] = res['status'] == 'success' ? 'success' : 'error';
          _files[index]['message'] = res['message'] ?? '';
        });
        if (!completer.isCompleted) completer.complete();
      },
      onError: (err) {
        setState(() {
          _files[index]['status'] = 'error';
          _files[index]['message'] = err;
          _logs.add('[LỖI] $err');
        });
        if (!completer.isCompleted) completer.complete();
      },
    );
    
    return completer.future;
  }

  void _previewFile(int index) {
    final file = _files[index];
    setState(() => _logs.add('Đang tải bản xem trước cho ${file['name']}...'));
    
    BackendService().runAction(
      action: 'preview',
      params: {'input': file['path']},
      onLog: (_) {},
      onResult: (res) {
        if (res['status'] == 'success') {
          _showPreviewModal(file['name'], res['questions'] as List);
        } else if (res['status'] == 'error') {
          setState(() => _logs.add('[LỖI] ${res['message']}'));
        }
      },
      onError: (err) {
        setState(() => _logs.add('[LỖI] $err'));
      },
    );
  }

  void _showPreviewModal(String title, List questions) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Xem trước: $title (${questions.length} câu)'),
        content: SizedBox(
          width: 800,
          height: 600,
          child: ListView.builder(
            itemCount: questions.length,
            itemBuilder: (context, i) {
              final q = questions[i];
              return Card(
                margin: const EdgeInsets.only(bottom: 12),
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Câu ${i + 1}: ${q['question']}', style: const TextStyle(fontWeight: FontWeight.bold)),
                      const SizedBox(height: 8),
                      ...(q['options'] as Map).entries.map((e) => Text('${e.key}. ${e.value}', 
                        style: TextStyle(color: q['correct_answer'] == e.key ? Colors.green : null, fontWeight: q['correct_answer'] == e.key ? FontWeight.bold : null))),
                    ],
                  ),
                ),
              );
            },
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Đóng')),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (!_isLoaded) return const Center(child: CircularProgressIndicator());
    
    final selectedCount = _files.where((f) => f['selected']).length;
    final allSelected = _files.isNotEmpty && selectedCount == _files.length;

    return Padding(
      padding: const EdgeInsets.all(24.0),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Left Side: Config & Files
          Expanded(
            flex: 2,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Số hóa & Kiểm tra Đề', style: Theme.of(context).textTheme.headlineSmall),
                const SizedBox(height: 32),
                PathSelector(
                  label: 'Thư mục PDF đầu vào',
                  value: _inputDir,
                  onSelected: (val) {
                    setState(() => _inputDir = val);
                    _savePaths();
                    _scanFolder();
                  },
                ),
                const SizedBox(height: 16),
                PathSelector(
                  label: 'Thư mục Output (DOCX)',
                  value: _outputDir,
                  onSelected: (val) {
                    setState(() => _outputDir = val);
                    _savePaths();
                  },
                ),
                const SizedBox(height: 24),
                Row(
                  children: [
                    FilledButton.icon(
                      onPressed: _isRunning || selectedCount == 0 ? null : _processAll,
                      icon: const Icon(Icons.play_arrow),
                      label: Text('Xử lý $selectedCount file được chọn'),
                    ),
                    const SizedBox(width: 12),
                    OutlinedButton.icon(
                      onPressed: _scanFolder,
                      icon: const Icon(Icons.refresh),
                      label: const Text('Quét lại thư mục'),
                    ),
                  ],
                ),
                const SizedBox(height: 24),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text('Danh sách file PDF (${_files.length})', style: Theme.of(context).textTheme.titleMedium),
                    if (_files.isNotEmpty)
                      Row(
                        children: [
                          const Text('Chọn tất cả', style: TextStyle(fontSize: 13)),
                          Checkbox(
                            value: allSelected,
                            onChanged: (val) {
                              setState(() {
                                for (var f in _files) {
                                  f['selected'] = val ?? false;
                                }
                              });
                            },
                          ),
                        ],
                      ),
                  ],
                ),
                const SizedBox(height: 4),
                Expanded(
                  child: Card(
                    child: ListView.builder(
                      itemCount: _files.length,
                      itemBuilder: (context, i) {
                        final f = _files[i];
                        return ListTile(
                          leading: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Checkbox(
                                value: f['selected'],
                                onChanged: _isRunning ? null : (val) {
                                  setState(() => f['selected'] = val ?? false);
                                },
                              ),
                              _buildStatusIcon(f['status']),
                            ],
                          ),
                          title: Text(f['name']),
                          subtitle: f['message'].isNotEmpty ? Text(f['message'], style: const TextStyle(fontSize: 11, color: Colors.red)) : null,
                          trailing: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              IconButton(
                                icon: const Icon(Icons.visibility_outlined),
                                tooltip: 'Xem trước câu hỏi',
                                onPressed: () => _previewFile(i),
                              ),
                              IconButton(
                                icon: const Icon(Icons.replay),
                                tooltip: 'Thử lại',
                                onPressed: _isRunning ? null : () => _processFile(i),
                              ),
                            ],
                          ),
                        );
                      },
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 24),
          // Right Side: Logs
          Expanded(
            flex: 1,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Logs hệ thống', style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 8),
                Expanded(child: LogConsole(logs: _logs)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatusIcon(String status) {
    switch (status) {
      case 'running': return const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2));
      case 'success': return const Icon(Icons.check_circle, color: Colors.green, size: 20);
      case 'error': return const Icon(Icons.error, color: Colors.red, size: 20);
      default: return const Icon(Icons.circle_outlined, color: Colors.grey, size: 20);
    }
  }
}


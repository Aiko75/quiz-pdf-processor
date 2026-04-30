import 'package:flutter/material.dart';
import '../widgets/path_selector.dart';
import '../widgets/log_console.dart';
import '../services/backend_service.dart';

class GenerateScreen extends StatefulWidget {
  const GenerateScreen({super.key});

  @override
  State<GenerateScreen> createState() => _GenerateScreenState();
}

class _GenerateScreenState extends State<GenerateScreen> {
  String _answerFile = '';
  String _outputDir = '';
  double _count = 40;
  int _fromQ = 1;
  int _toQ = 0;
  bool _genAnswer = true;
  final List<String> _logs = [];
  bool _isRunning = false;

  void _runGenerate() {
    if (_answerFile.isEmpty || _outputDir.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Vui lòng chọn đầy đủ file đáp án và thư mục output')),
      );
      return;
    }

    setState(() {
      _isRunning = true;
      _logs.add('\n--- Bắt đầu: Tạo đề mới ---');
    });

    BackendService().runAction(
      action: 'generate',
      params: {
        'answer-file': _answerFile,
        'output': _outputDir,
        'count': _count.toInt().toString(),
        'from-q': _fromQ.toString(),
        'to-q': _toQ.toString(),
        if (_genAnswer) 'gen-answer': '',
      },
      onLog: (msg) => setState(() => _logs.add(msg)),
      onResult: (res) {
        setState(() => _isRunning = false);
        if (res['status'] == 'success') {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Tạo đề hoàn tất: ${res['message']}')),
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
          Text('Tạo Đề Trắc Nghiệm Mới', style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 32),
          PathSelector(
            label: 'File đáp án nguồn (PDF/DOCX)',
            value: _answerFile,
            isDirectory: false,
            allowedExtensions: ['pdf', 'docx'],
            onSelected: (val) => setState(() => _answerFile = val),
          ),
          const SizedBox(height: 16),
          PathSelector(
            label: 'Thư mục Output',
            value: _outputDir,
            onSelected: (val) => setState(() => _outputDir = val),
          ),
          const SizedBox(height: 32),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Tùy chọn tạo đề', style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 16),
                  Row(
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('Số lượng câu muốn lấy: ${_count.toInt()}'),
                            Slider(
                              value: _count,
                              min: 1,
                              max: 200,
                              divisions: 199,
                              label: _count.round().toString(),
                              onChanged: (val) => setState(() => _count = val),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(width: 32),
                      CheckboxMenuButton(
                        value: _genAnswer,
                        onChanged: (val) => setState(() => _genAnswer = val ?? true),
                        child: const Text('Tạo file đáp án kèm theo'),
                      ),
                    ],
                  ),
                  const Divider(),
                  Row(
                    children: [
                      const Text('Hoặc chọn khoảng câu: Từ'),
                      const SizedBox(width: 8),
                      SizedBox(
                        width: 60,
                        child: TextFormField(
                          initialValue: _fromQ.toString(),
                          keyboardType: TextInputType.number,
                          onChanged: (val) => _fromQ = int.tryParse(val) ?? 1,
                          decoration: const InputDecoration(isDense: true),
                        ),
                      ),
                      const SizedBox(width: 8),
                      const Text('Đến'),
                      const SizedBox(width: 8),
                      SizedBox(
                        width: 60,
                        child: TextFormField(
                          initialValue: _toQ.toString(),
                          keyboardType: TextInputType.number,
                          onChanged: (val) => _toQ = int.tryParse(val) ?? 0,
                          decoration: const InputDecoration(isDense: true),
                        ),
                      ),
                      const SizedBox(width: 8),
                      const Text('(0 = hết)'),
                    ],
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 32),
          FilledButton.icon(
            onPressed: _isRunning ? null : _runGenerate,
            icon: const Icon(Icons.auto_fix_high),
            label: const Text('Bắt đầu Tạo đề'),
          ),
          const SizedBox(height: 32),
          Expanded(child: LogConsole(logs: _logs)),
        ],
      ),
    );
  }
}

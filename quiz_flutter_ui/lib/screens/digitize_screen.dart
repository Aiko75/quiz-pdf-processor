import 'package:flutter/material.dart';
import '../widgets/path_selector.dart';
import '../widgets/log_console.dart';
import '../services/backend_service.dart';

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

  void _runAction(String action) {
    if (_inputDir.isEmpty || _outputDir.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Vui lòng chọn đầy đủ thư mục đầu vào và đầu ra')),
      );
      return;
    }

    setState(() {
      _isRunning = true;
      _logs.add('\n--- Bắt đầu: $action ---');
    });

    BackendService().runAction(
      action: action,
      params: {
        'input': _inputDir,
        'output': _outputDir,
      },
      onLog: (msg) => setState(() => _logs.add(msg)),
      onResult: (res) {
        setState(() => _isRunning = false);
        if (res['status'] == 'success') {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Hoàn tất: ${res['message']}')),
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
          Text('Số hóa & Kiểm tra Đề', style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 8),
          Text(
            'Quy trình chuyển đổi từ PDF sang DOCX và kiểm tra tính chính xác của dữ liệu.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 32),
          PathSelector(
            label: 'Thư mục PDF đầu vào',
            value: _inputDir,
            onSelected: (val) => setState(() => _inputDir = val),
          ),
          const SizedBox(height: 16),
          PathSelector(
            label: 'Thư mục Output',
            value: _outputDir,
            onSelected: (val) => setState(() => _outputDir = val),
          ),
          const SizedBox(height: 32),
          Row(
            children: [
              FilledButton.icon(
                onPressed: _isRunning ? null : () => _runAction('process'),
                icon: _isRunning ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)) : const Icon(Icons.play_arrow),
                label: const Text('1) Xử lý PDF -> DOCX'),
              ),
              const SizedBox(width: 12),
              ElevatedButton.icon(
                onPressed: _isRunning ? null : () => _runAction('validate'),
                icon: const Icon(Icons.check_circle_outline),
                label: const Text('2) Kiểm tra đối chiếu'),
              ),
              const SizedBox(width: 12),
              OutlinedButton.icon(
                onPressed: _isRunning ? null : () => _runAction('report'),
                icon: const Icon(Icons.description),
                label: const Text('Báo cáo chi tiết'),
              ),
            ],
          ),
          const SizedBox(height: 32),
          Expanded(
            child: LogConsole(logs: _logs),
          ),
        ],
      ),
    );
  }
}

import 'package:flutter/material.dart';

class LogConsole extends StatefulWidget {
  final List<String> logs;
  const LogConsole({super.key, required this.logs});

  @override
  State<LogConsole> createState() => _LogConsoleState();
}

class _LogConsoleState extends State<LogConsole> {
  final ScrollController _scrollController = ScrollController();

  @override
  void didUpdateWidget(LogConsole oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.logs.length != oldWidget.logs.length) {
      _scrollToBottom();
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceContainerHighest.withOpacity(0.3),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Theme.of(context).dividerColor),
      ),
      padding: const EdgeInsets.all(8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              const Icon(Icons.terminal, size: 16),
              const SizedBox(width: 8),
              Text(
                'LOGS',
                style: Theme.of(context).textTheme.labelSmall?.copyWith(fontWeight: FontWeight.bold),
              ),
              const Spacer(),
              IconButton(
                icon: const Icon(Icons.delete_outline, size: 16),
                onPressed: () => widget.logs.clear(),
                tooltip: 'Clear logs',
              )
            ],
          ),
          const Divider(),
          Expanded(
            child: ListView.builder(
              controller: _scrollController,
              itemCount: widget.logs.length,
              itemBuilder: (context, index) {
                final log = widget.logs[index];
                Color color = Theme.of(context).colorScheme.onSurface;
                if (log.contains('[OK]')) color = Colors.green;
                if (log.contains('[BỎ QUA]') || log.contains('[LƯU Ý]')) color = Colors.orange;
                if (log.contains('[LỖI]') || log.contains('error')) color = Colors.red;
                if (log.startsWith('===')) color = Theme.of(context).colorScheme.primary;

                return Padding(
                  padding: const EdgeInsets.symmetric(vertical: 2),
                  child: Text(
                    log,
                    style: TextStyle(
                      fontFamily: 'monospace',
                      fontSize: 13,
                      color: color,
                    ),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

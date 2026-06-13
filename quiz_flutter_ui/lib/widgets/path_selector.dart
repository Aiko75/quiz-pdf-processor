import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'package:desktop_drop/desktop_drop.dart';

class PathSelector extends StatefulWidget {
  final String label;
  final String value;
  final bool isDirectory;
  final List<String>? allowedExtensions;
  final Function(String) onSelected;

  const PathSelector({
    super.key,
    required this.label,
    required this.value,
    this.isDirectory = true,
    this.allowedExtensions,
    required this.onSelected,
  });

  @override
  State<PathSelector> createState() => _PathSelectorState();
}

class _PathSelectorState extends State<PathSelector> {
  bool _dragging = false;

  Future<void> _pickPath() async {
    String? result;
    if (widget.isDirectory) {
      result = await FilePicker.getDirectoryPath();
    } else {
      final pickerResult = await FilePicker.pickFiles(
        type: widget.allowedExtensions != null ? FileType.custom : FileType.any,
        allowedExtensions: widget.allowedExtensions,
      );
      result = pickerResult?.files.single.path;
    }

    if (result != null) {
      widget.onSelected(result);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    
    return DropTarget(
      onDragEntered: (details) {
        setState(() {
          _dragging = true;
        });
      },
      onDragExited: (details) {
        setState(() {
          _dragging = false;
        });
      },
      onDragDone: (details) {
        setState(() {
          _dragging = false;
        });
        if (details.files.isNotEmpty) {
          final file = details.files.first;
          widget.onSelected(file.path);
        }
      },
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: _dragging ? theme.colorScheme.primary : Colors.transparent,
            width: 2,
          ),
          color: _dragging
              ? theme.colorScheme.primaryContainer.withOpacity(0.15)
              : Colors.transparent,
        ),
        padding: const EdgeInsets.all(4),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              widget.label,
              style: theme.textTheme.labelLarge?.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: TextFormField(
                    initialValue: widget.value,
                    key: ValueKey(widget.value),
                    readOnly: true,
                    decoration: InputDecoration(
                      isDense: true,
                      border: const OutlineInputBorder(),
                      filled: true,
                      fillColor: theme.colorScheme.surfaceContainerLow,
                      hintText: _dragging
                          ? 'Thả tệp vào đây...'
                          : (widget.isDirectory ? 'Kéo thả thư mục hoặc click Chọn...' : 'Kéo thả tệp hoặc click Chọn...'),
                      prefixIcon: _dragging 
                          ? Icon(Icons.download, color: theme.colorScheme.primary)
                          : const Icon(Icons.arrow_downward_outlined, size: 18),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                FilledButton.tonalIcon(
                  onPressed: _pickPath,
                  icon: const Icon(Icons.folder_open),
                  label: const Text('Chọn...'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

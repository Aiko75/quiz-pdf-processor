import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';

class PathSelector extends StatelessWidget {
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

  Future<void> _pickPath() async {
    String? result;
    if (isDirectory) {
      result = await FilePicker.getDirectoryPath();
    } else {
      final pickerResult = await FilePicker.pickFiles(
        type: allowedExtensions != null ? FileType.custom : FileType.any,
        allowedExtensions: allowedExtensions,
      );
      result = pickerResult?.files.single.path;
    }

    if (result != null) {
      onSelected(result);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: Theme.of(context).textTheme.labelLarge?.copyWith(fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(
              child: TextFormField(
                initialValue: value,
                key: ValueKey(value),
                readOnly: true,
                decoration: InputDecoration(
                  isDense: true,
                  border: const OutlineInputBorder(),
                  filled: true,
                  fillColor: Theme.of(context).colorScheme.surfaceContainerLow,
                  hintText: isDirectory ? 'Chọn thư mục...' : 'Chọn file...',
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
    );
  }
}

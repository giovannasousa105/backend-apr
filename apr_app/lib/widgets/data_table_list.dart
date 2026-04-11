import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import 'neon_card.dart';

class DataTableList extends StatefulWidget {
  final String searchHint;
  final List<String> columns;
  final List<Map<String, String>> rows; // keys = columns
  final VoidCallback onAdd;
  final void Function(Map<String, String> row) onEdit;
  final void Function(Map<String, String> row) onDelete;

  const DataTableList({
    super.key,
    required this.searchHint,
    required this.columns,
    required this.rows,
    required this.onAdd,
    required this.onEdit,
    required this.onDelete,
  });

  @override
  State<DataTableList> createState() => _DataTableListState();
}

class _DataTableListState extends State<DataTableList> {
  String q = '';

  @override
  Widget build(BuildContext context) {
    final filtered = widget.rows.where((r) {
      if (q.trim().isEmpty) return true;
      final hay = r.values.join(' ').toLowerCase();
      return hay.contains(q.toLowerCase());
    }).toList();

    return Padding(
      padding: const EdgeInsets.all(18),
      child: Column(
        children: [
          Row(
            children: [
              Expanded(
                child: TextField(
                  onChanged: (v) => setState(() => q = v),
                  decoration: InputDecoration(
                    prefixIcon: const Icon(Icons.search),
                    hintText: widget.searchHint,
                  ),
                ),
              ),
              const SizedBox(width: 12),
              FilledButton.icon(
                onPressed: widget.onAdd,
                icon: const Icon(Icons.add),
                label: const Text('Adicionar'),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Expanded(
            child: NeonCard(
              child: Column(
                children: [
                  _header(),
                  const Divider(height: 1),
                  Expanded(
                    child: ListView.separated(
                      itemCount: filtered.length,
                      separatorBuilder: (_, index) => const Divider(height: 1),
                      itemBuilder: (_, i) => _row(filtered[i]),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _header() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(14, 14, 14, 12),
      child: Row(
        children: [
          const SizedBox(
            width: 94,
            child: Text('Ações', style: TextStyle(color: AppTheme.subtext)),
          ),
          Expanded(
            child: Row(
              children: widget.columns
                  .map(
                    (c) => Expanded(
                      child: Text(
                        c,
                        style: const TextStyle(color: AppTheme.subtext),
                      ),
                    ),
                  )
                  .toList(),
            ),
          ),
          const Icon(Icons.swap_vert, size: 18, color: AppTheme.subtext),
        ],
      ),
    );
  }

  Widget _row(Map<String, String> r) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
      child: Row(
        children: [
          SizedBox(
            width: 94,
            child: Row(
              children: [
                IconButton(
                  tooltip: 'Editar',
                  onPressed: () => widget.onEdit(r),
                  icon: const Icon(Icons.edit_outlined),
                ),
                IconButton(
                  tooltip: 'Excluir',
                  onPressed: () => widget.onDelete(r),
                  icon: const Icon(Icons.delete_outline),
                ),
              ],
            ),
          ),
          Expanded(
            child: Row(
              children: widget.columns
                  .map(
                    (c) => Expanded(
                      child: Text(
                        r[c] ?? '-',
                        style: const TextStyle(fontWeight: FontWeight.w600),
                      ),
                    ),
                  )
                  .toList(),
            ),
          ),
        ],
      ),
    );
  }
}

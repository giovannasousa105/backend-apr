import 'package:flutter/material.dart';
import '../../widgets/data_table_list.dart';
import '../../data/mock_data.dart';

class SitesPage extends StatefulWidget {
  const SitesPage({super.key});

  @override
  State<SitesPage> createState() => _SitesPageState();
}

class _SitesPageState extends State<SitesPage> {
  final rows = List<Map<String, String>>.from(mockSites);

  void _toast(String msg) =>
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));

  @override
  Widget build(BuildContext context) {
    return DataTableList(
      searchHint: 'Pesquisar por site',
      columns: const ['Site'],
      rows: rows,
      onAdd: () => _toast('Abrir modal: Adicionar Site'),
      onEdit: (r) => _toast('Editar: ${r['Site']}'),
      onDelete: (r) {
        setState(() => rows.remove(r));
        _toast('Excluído: ${r['Site']}');
      },
    );
  }
}

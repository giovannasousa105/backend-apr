import 'package:flutter/material.dart';
import '../../widgets/data_table_list.dart';
import '../../data/mock_data.dart';

class ActivityCharacteristicsPage extends StatefulWidget {
  const ActivityCharacteristicsPage({super.key});

  @override
  State<ActivityCharacteristicsPage> createState() =>
      _ActivityCharacteristicsPageState();
}

class _ActivityCharacteristicsPageState
    extends State<ActivityCharacteristicsPage> {
  final rows = List<Map<String, String>>.from(mockActivityCharacteristics);

  void _toast(String msg) =>
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));

  @override
  Widget build(BuildContext context) {
    return DataTableList(
      searchHint: 'Pesquisar',
      columns: const ['Características da Atividade'],
      rows: rows,
      onAdd: () => _toast('Abrir modal: Adicionar Característica'),
      onEdit: (r) => _toast('Editar: ${r['Características da Atividade']}'),
      onDelete: (r) {
        setState(() => rows.remove(r));
        _toast('Excluído: ${r['Características da Atividade']}');
      },
    );
  }
}

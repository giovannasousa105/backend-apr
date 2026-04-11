import 'package:flutter/material.dart';
import '../../widgets/data_table_list.dart';
import '../../data/mock_data.dart';

class UsersPage extends StatefulWidget {
  const UsersPage({super.key});

  @override
  State<UsersPage> createState() => _UsersPageState();
}

class _UsersPageState extends State<UsersPage> {
  final rows = List<Map<String, String>>.from(mockUsers);

  void _toast(String msg) =>
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));

  @override
  Widget build(BuildContext context) {
    return DataTableList(
      searchHint: 'Pesquisar por Usuários',
      columns: const ['Tipo', 'Nome'],
      rows: rows,
      onAdd: () => _toast('Abrir modal: Adicionar Usuário'),
      onEdit: (r) => _toast('Editar: ${r['Nome']}'),
      onDelete: (r) {
        setState(() => rows.remove(r));
        _toast('Excluído: ${r['Nome']}');
      },
    );
  }
}

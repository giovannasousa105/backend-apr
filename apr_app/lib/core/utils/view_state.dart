class ViewState<T> {
  const ViewState({this.loading = false, this.data, this.error});

  final bool loading;
  final T? data;
  final String? error;

  ViewState<T> copyWith({
    bool? loading,
    T? data,
    String? error,
    bool clearError = false,
    bool clearData = false,
  }) {
    return ViewState<T>(
      loading: loading ?? this.loading,
      data: clearData ? null : (data ?? this.data),
      error: clearError ? null : (error ?? this.error),
    );
  }
}

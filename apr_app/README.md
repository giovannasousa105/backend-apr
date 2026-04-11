# apr_app

A new Flutter project.

## Environment variables

See `.env.sample` for the variables that control how the app talks to the backend and to Supabase. At minimum you should configure:

- `API_BASE_URL`: URL where the `/auth` and `/v1` endpoints are hosted (defaults to `http://localhost:8000` in dev). Update `lib/config/api_config_io.dart` if your backend runs elsewhere.
- `SUPABASE_URL` and `SUPABASE_ANON_KEY`: point to the Supabase project that exposes the `carts` table used by the floating panel. The app reads them through `lib/config/supabase_config.dart`.
- `SUPABASE_PRODUCTION`: set to `true` (or pass `--dart-define=SUPABASE_PRODUCTION=true`) when the production Supabase instance should be used instead of the dev defaults. Optional `SUPABASE_ANALYTICS_DEV` and `_PROD` tags are logged with analytics events.

You can load these variables in your terminal before running Flutter (e.g., `set SUPABASE_URL=...` on Windows) or pass them directly when launching:

```
flutter run -d chrome \
  --dart-define=API_BASE_URL=http://localhost:8000 \
  --dart-define=SUPABASE_URL=https://<your>.supabase.co \
  --dart-define=SUPABASE_ANON_KEY=<anon-key>
```

If you change to a new Supabase URL/key in the future, simply update the values above or switch the defaults in `lib/config/supabase_config.dart`.

## Iniciar a API antes do Flutter

Use `scripts/start-dev.ps1` para lembrar o fluxo de dois passos durante o desenvolvimento:

- Passo 1: execute o backend local (ex.: `npm run dev`, `dotnet run` ou `python app.py`) de modo que `http://localhost:8000` responda em `/auth/login`.
- Passo 2: quando o backend estiver pronto, execute o Flutter web com as variáveis do Supabase já configuradas ou passe os `--dart-define` mostrados acima:

```
flutter run -d chrome --dart-define=API_BASE_URL=http://localhost:8000 \
  --dart-define=SUPABASE_URL=https://hrtpniackgdogtmrgrop.supabase.co \
  --dart-define=SUPABASE_ANON_KEY=sb_publishable_KP6E26haQmh9p7WuzLOqgw__50ekqo4
```

O script apenas imprime o passo a passo e os argumentos recomendados. Substitua os comandos e URLs por aqueles que correspondem à sua stack se o backend estiver em outro lugar.

## Getting Started

This project is a starting point for a Flutter application.

A few resources to get you started if this is your first Flutter project:

- [Lab: Write your first Flutter app](https://docs.flutter.dev/get-started/codelab)
- [Cookbook: Useful Flutter samples](https://docs.flutter.dev/cookbook)

For help getting started with Flutter development, view the
[online documentation](https://docs.flutter.dev/), which offers tutorials,
samples, guidance on mobile development, and a full API reference.

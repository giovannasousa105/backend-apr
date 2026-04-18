param(
    [string]$ApiUrl = 'http://localhost:8000',
    [string]$SupabaseUrl = 'https://hrtpniackgdogtmrgrop.supabase.co',
    [string]$SupabaseAnonKey =
        'sb_publishable_KP6E26haQmh9p7WuzLOqgw__50ekqo4'
)

Write-Host '1. Certifique-se de que a API esteja rodando (o Flutter web usa /auth/login em $ApiUrl).'
Write-Host '   Exemplo de comando (substua conforme o backend real):'
Write-Host '     cd ..\my-backend'
Write-Host '     npm run dev'
Write-Host '2. Aguarde até o servidor responder em http://localhost:8000 (ou o valor de $ApiUrl).'
Write-Host '3. Em seguida execute o Flutter web com as definições:'
Write-Host "     flutter run -d chrome --dart-define=API_BASE_URL=$ApiUrl --dart-define=SUPABASE_URL=$SupabaseUrl --dart-define=SUPABASE_ANON_KEY=$SupabaseAnonKey"
Write-Host
Write-Host 'Caso o backend utilize outra porta/domínio, atualize $ApiUrl e a variável API_BASE_URL antes de executar.'

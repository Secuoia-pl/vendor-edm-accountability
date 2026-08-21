# Powiadomienia: ntfy + Signal

Pipeline (`analyze.py`, `bot.py`) woła `notify.py` — **bez Telegrama**.

## ntfy (szybki start)

1. Wymyśl tajny topic (traktuj jak hasło), np. generator:
   ```powershell
   -join ((48..57 + 97..122) | Get-Random -Count 24 | ForEach-Object {[char]$_})
   ```
2. W `.env`:
   ```
   NTFY_SERVER=https://ntfy.sh
   NTFY_TOPIC=twoj-tajny-topic
   ```
3. Telefon: zainstaluj [ntfy](https://ntfy.sh) → Subscribe → wklej ten sam topic.
4. Test:
   ```powershell
   .\.venv\Scripts\python.exe notify.py --title "Test" --message "Dziala"
   ```

Opcjonalnie `NTFY_TOKEN` jeśli używasz chronionego topica / własnego serwera.

## Signal

Signal **nie ma** prostego oficjalnego API jak Telegram Bot. Dwie ścieżki:

### A) Docker: signal-cli-rest-api (wygodniejsze na Windows)

1. Uruchom kontener ([bbernhard/signal-cli-rest-api](https://github.com/bbernhard/signal-cli-rest-api)).
2. Zlinkuj urządzenie (QR) albo zarejestruj numer — według ich README.
3. W `.env`:
   ```
   SIGNAL_REST_URL=http://127.0.0.1:8080
   SIGNAL_NUMBER=+48twojnumer
   SIGNAL_RECIPIENTS=+48twojnumer
   ```
   (`RECIPIENTS` = ten sam numer = Note to Self).

4. Test: `.\.venv\Scripts\python.exe notify.py --message "Signal test"`

### B) Lokalny `signal-cli`

1. Zainstaluj [signal-cli](https://github.com/AsamK/signal-cli), zlinkuj konto.
2. W `.env`:
   ```
   SIGNAL_CLI_PATH=signal-cli
   SIGNAL_NUMBER=+48twojnumer
   SIGNAL_RECIPIENTS=+48twojnumer
   ```

Jeśli ustawisz **i** REST, i CLI — używany jest **REST**.

## Co dostajesz w alercie

Krótki sygnał (bez sekretów), np.:
- `update_hub=True`
- skrót rationale
- nazwa pliku w `drafts/`
- „otwórz Streamlit → Drafty”

## Status kanałów

```powershell
.\.venv\Scripts\python.exe notify.py --channels
```

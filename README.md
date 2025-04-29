# Clone Neighborhood Tool voor Juniper SSR Routers

## Overzicht

Dit project bevat een Python-script en library om automatisch een "neighborhood" te clonen op een hub-router en optioneel toe te voegen aan spoke-routers.

## Structuur

- `ssr_api_lib.py` — Bevat alle API-functies (login, ophalen interfaces, clonen, toevoegen).
- `clone_neighborhood.py` — Het hoofdscript dat gebruikersinteractie verzorgt en workflows aanstuurt.
- `script-log.log` — Logbestand waarin alle API-calls en responses worden vastgelegd.

## Vereisten

- Python 3.8+
- Python-modules:
  - `requests`

Installeer dependencies met:
```bash
pip install requests
```

## Gebruik

1. Zorg dat je de bestanden `ssr_api_lib.py` en `clone_neighborhood.py` in dezelfde directory hebt staan.
2. Start het script:
```bash
python clone_neighborhood.py
```
3. Volg de prompts:
   - Voer FQDN/IP, gebruikersnaam en wachtwoord in.
   - Selecteer de hub-router en clone een bestaande neighborhood.
   - Na 5 seconden synchronisatietijd wordt gecontroleerd of de nieuwe neighborhood is aangemaakt.
   - Je krijgt de optie om de nieuwe neighborhood toe te voegen aan spoke-routers (gebaseerd op naam-prefix).
   - Alleen network-interfaces met "wan" in de naam worden bijgewerkt.

## Belangrijke Opmerkingen

- SSL-certificaatcontrole is uitgeschakeld (`verify=False`) voor gebruiksgemak.
- Gevoelige informatie zoals tokens wordt niet gelogd (token wordt vervangen door "SECRET").
- Het script verwacht dat de Juniper SSR API bereikbaar is en correct antwoordt.

## Toekomstige uitbreidingen

- Ondersteuning voor parallelle verwerking van spoke-routers.
- Meer foutafhandeling bij mislukte API-calls.
- Mogelijkheid om meerdere neighborhoods in batch toe te voegen.

## Disclaimer

Gebruik dit script zorgvuldig, zeker in productie-omgevingen. Zorg voor een back-up of snapshot van configuraties voordat je massale wijzigingen uitvoert.

---
© 2025 SSR Automation Project

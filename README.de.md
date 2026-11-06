# EOS – Home Assistant Integration für die Lenovo Smart Clock 2

Home Assistant Seite von [EOS](https://github.com/Hendy59/helios-eos), einer Android
App, die eine Lenovo Smart Clock 2 in ein Home-Assistant-Dashboard und einen Sprach-Satelliten
verwandelt. Die Uhr verbindet sich über eine eigene WebSocket-Verbindung mit Home Assistant;
diese Integration registriert das Gerät und seine Entities, koppelt die Uhr mit einem
sechsstelligen Code und liefert ihr alles, was sie zum Betrieb braucht.

Keine pip-Abhängigkeiten, push only (`iot_class: local_push`).

## Was du bekommst

| Entity | Quelle auf der Uhr |
| --- | --- |
| `sensor` App-Version (diagnostisch) | die EOS-APK-Version |
| `sensor` Sprachstatus | idle / listening / processing / responding / error |
| `sensor` Dock-Version (diagnostisch) | Firmware der Ladeschale |
| `binary_sensor` Dock verbunden | der OEM-Dock-Listener |
| `binary_sensor` Telefon lädt | Qi-Lade-Listener; ohne Dock nicht verfügbar |
| `light` Dock-Lampe | Ein/Aus aus dem OEM-Service, Helligkeit 1–10 |
| `number` Gerätelautstärke | `STREAM_MUSIC` 0–100 %, alle 3 s abgefragt |
| `media_player` Uhr-Lautsprecher | dieselbe Gerätelautstärke als Player (`volume_set` / `volume_step` only), damit Assist „lauter“ im Bereich der Uhr versteht; Musik selbst läuft über einen separaten Music-Assistant-Player |
| `assist_satellite` Satellit | die Uhr als Sprach-Satellit registriert: ihr Sprachstatus (idle / listening / processing / responding) und `announce`-Wiedergabe einer TTS- oder Medien-URL auf der Uhr |

Der Satellit ist, wie Home Assistant die Uhr als Sprachgerät sieht: Er erscheint in den
Einstellungen des Sprachassistenten und akzeptiert `assist_satellite.announce`. Home Assistant
löst die Ansage in einen signierten TTS-Stream oder eine Medien-URL auf, und die Uhr spielt sie
ab (`announce.play`, wie jeder Befehl bestätigt oder fehlgeschlagen, nie wiederholt; eine EOS-App,
der der Befehl unbekannt ist, lässt den Service-Call fehlschlagen).

Das Gerät trägt die stabile Installations-ID der Uhr, deshalb wird der in Home Assistant
zugewiesene Bereich zum Raumkontext jedes Sprachbefehls (die `device_id`, die an
`assist_pipeline/run` übergeben wird).

## Installation

1. HACS -> Integrationen -> Drei-Punkt-Menü -> **Benutzerdefinierte Repositories** -> URL dieses
   Repositories hinzufügen, Kategorie *Integration*.
2. **EOS** installieren und Home Assistant neu starten.
3. Auf der Uhr (EOS 0.9.0 oder neuer): EOS halten -> **Mit HA koppeln** -> Home Assistant aus der
   mDNS-Liste wählen oder die Adresse eingeben.
4. Einstellungen -> Geräte & Dienste -> **Integration hinzufügen** -> EOS. Home Assistant zeigt
   einen sechsstelligen Code, fünf Minuten gültig. Diesen Dialog offen lassen – er schließt die
   Kopplung ab.
5. Auf der Uhr **Weiter** tippen und den Code eingeben. Die Uhr erhält ihr eigenes
   Home-Assistant-Token, und wenn die Music-Assistant-Integration vorhanden ist, auch
   Musikzugriff.
6. Das Gerät einem Bereich zuweisen.

Eine erneute Kopplung derselben Uhr aktualisiert den bestehenden Eintrag: neuer User und neues
Token, die alten werden erst entfernt, wenn die neue Kopplung erfolgreich war.

## Sicherheitsmodell

Diese Integration legt einen Home-Assistant-User an und mintet ein Token über einen Endpunkt,
der **nicht authentifiziert** ist – deshalb lohnt es sich, genau zu sagen, was das bedeutet,
bevor du sie installierst.

- **Was angelegt wird.** Bei erfolgreicher Kopplung legt die Integration einen Home-Assistant-User
  pro Uhr an: systemgeneriert, **kein Administrator**, `local_only` (nicht außerhalb deines LAN
  nutzbar), in der normalen Benutzergruppe. Sein Token ist ein System-Token mit zehn Jahren
  Laufzeit. Dieses Token ist die einzige Credential, die die Uhr je besitzt; du fügst niemals
  ein langlebiges Admin-Token in das Gerät ein.
- **Wer koppeln darf.** `POST /api/helios/pair` ist unauthentifiziert, weil eine noch nicht
  gekoppelte Uhr keine Credential hat, mit der sie sich authentifizieren könnte. Es akzeptiert
  nur einen sechsstelligen Code, den **du** moments zuvor in der Home-Assistant-Oberfläche
  erzeugt hast und der fünf Minuten gültig ist. Fünf falsche Codes von einer Adresse sperren
  diese Adresse für fünf Minuten. Fehlerantworten sind einheitlich und verraten nichts; weder
  Code noch Token werden jemals geloggt.
- **Was die Uhr damit kann.** Der Geräte-Kanal akzeptiert nur Verbindungen dieses Users, und die
  Befehls-Allowlist ist geschlossen: `lamp.turn_on`, `lamp.turn_off`, `lamp.set_brightness`,
  `audio.set_device_volume`, `music.play`, `music.pause`, `music.stop`, `announce.play`. Home
  Assistant wartet bis zu 10 s auf eine Bestätigung und wiederholt nie.
- **Entfernen räumt auf.** Das Löschen des Config-Eintrags löscht den User der Uhr, ihr
  Music-Assistant-Token und ihr gespeichertes Hintergrundbild. Die Uhr merkt das, hört auf,
  sich zu verbinden, und bittet um erneute Kopplung.
- **Music-Assistant-Credentials.** Die Integration liest Adresse und Token des
  `music_assistant`-Config-Eintrags, um ein eigenes Token für die Uhr zu minten (es erscheint in
  der Token-Liste von Music Assistant selbst). Das ist ein bewusstes cross-Integrations-Lesen
  fremder Eintragsdaten; wenn du das nicht möchtest, lass Music Assistant weg – die Uhr läuft
  dann einfach ohne Musik. Läuft Music Assistant als Add-on, verweigert es das Minten eines
  brauchbaren Tokens komplett, und du fügst selbst eines in den Optionen ein – siehe unten.

## Protokoll

Der WebSocket-Kanal (`helios/connect`, `helios/state`, `helios/result`), der Pairing-Austausch
(`GET`/`POST /api/helios/pair`) und das `connection`-Event sind in
**[docs/PROTOCOL.md](docs/PROTOCOL.md)** beschrieben.

## Verhalten

- Entities bleiben `unavailable`, bis die Uhr ihren ersten Snapshot schickt; eine getrennte
  Socket-Verbindung markiert sie ohne zusätzliche Heartbeats als `unavailable`.
- Befehle werden bestätigt oder sie schlagen fehl: ein zweiter Befehl für dieselbe Ressource,
  während der erste läuft, bekommt `busy`.
- Music Assistant als Add-on authentifiziert Home Assistant als System-User, und Music Assistant
  verweigert solche Tokens auf seinem LAN-Webserver. Füge einmalig ein Token ein unter
  Einstellungen -> Geräte & Dienste -> EOS -> Konfigurieren -> *Music-Assistant-Token für die
  Uhr*. Es wird ungeprüft gespeichert, nie widerrufen, und eine Änderung aktualisiert die Musik
  beim nächsten Connect der Uhr. Eine später gekoppelte Uhr übernimmt ein bereits eingefügtes
  Token und spielt von Anfang an Musik. Eine Uhr ohne Musik, während Music Assistant läuft,
  erscheint unter Einstellungen -> Reparaturen (Repairs).

## Uhr-Optik

Einstellungen -> Geräte & Dienste -> EOS -> die Uhr -> **Konfigurieren**: Farbschema
(warmes Graphit / Nachtblau), Hintergrund (Farbschema-Farbe, aktuelles Foto behalten oder neues
JPEG/PNG bis 10 MB hochladen), Abdunklung 35–80 % und ein Fokuspunkt, dazu die Sendspin-,
Diagnose- und Music-Assistant-Overrides.

Ein hochgeladenes Foto wird in Home Assistant normalisiert (EXIF-Orientierung angewendet,
Metadaten entfernt, Transparenz flachgerechnet, auf 1600x960 begrenzt, JPEG unter 2 MB) und
privat in `config/helios/<entry_id>/` gespeichert. Die Uhr ruft es mit einem authentifizierten
`GET /api/helios/appearance/<entry_id>/<image_id>` ab, der nur das aktuelle Bild und nur für den
User dieser Uhr oder einen Administrator ausliefert.

## Dashboard-Editor

Der Sidebar-Eintrag **EOS** (nur Administratoren) ist ein visueller Editor für das Layout der
Uhr: eine 4x3-Leinwand, Seiten, ein Formular pro Karte. Klick auf eine leere Zelle fügt eine
Karte hinzu, Klick auf eine Karte bearbeitet oder löscht sie. Entity- und Icon-Picker sind die
von Home Assistant selbst (`ha-form`); wenn sie nicht laden, fällt das Panel auf einfache
Eingabefelder mit einer Datalist deiner Entities zurück. Der Editor validiert mit denselben Regeln
und derselben Formulierung wie die Uhr, sodass ein akzeptiertes Layout auch von der Uhr akzeptiert
wird.

Der Editor hat einen Tab pro gekoppelter Uhr, benannt nach ihrem Home-Assistant-Gerät, und jeder
Tab bearbeitet das Dashboard, das diese Uhr zeigt. Jede Uhr startet auf dem geteilten
`helios-clock`; **Eigenes Dashboard** auf einem Tab kopiert das aktuelle Dokument in ein neues
verstecktes Dashboard (`helios-<Uhrname>`) und schaltet diese Uhr sofort darauf um, ohne Neustart.
Der Pfad wird im Config-Eintrag der Uhr gespeichert und im `connection`-Event an die App gesendet.

Die Kartenliste umfasst **Energy (PV, Haus, Batterie)** (`energy`, EOS 0.14 oder neuer auf der
Uhr): PV-Produktion und Hauslast oben, darunter die Batterieladung groß; ohne Batteriesensor ist
das Paar Produktion/Last der Wert.

**Thermostat** (`climate`, EOS 0.16 oder neuer): die gemessene Temperatur groß, darunter der
Sollwert; auf der Uhr öffnet ein Tap das komplette Bedienfeld (Sollwert, Modus, Preset, Lüfter,
Schwingung).

**Readings (1–3 Entities)** (`entities`): ein bis drei geordnete Zeilen, jeweils mit einer Entity
und einem optionalen kurzen Label. Wähle die Entities im Listen-Editor der Karte; jede
HA-Entity-Domain ist erlaubt. Numerische Zustände zeigen höchstens eine Nachkommastelle und ihre
HA-Einheiten; ein fehlender, unbekannter oder nicht verfügbarer Wert zeigt `—`, ohne die anderen
Zeilen auszublenden. Die Karte zeigt nur Werte an. Ihr Titel ist standardmäßig `Odczyty`, ihr
Header-Icon `mdi:format-list-bulleted`. Aktualisiere die Uhr auf EOS 0.19 oder neuer, bevor du
diese Karte speicherst; ältere Uhren lehnen das Dokument ab und behalten ihr bisheriges Layout.
Das Dashboard-Schema bleibt bei Version 6. Ziehe Listeneinträge an ihren Griffen, um die
Anzeigereihenfolge zu ändern.

**Alerts** (`alerts`, EOS 0.17 oder neuer): jede Warnung in einer 1x1-, 1x2- oder 2x1-Kachel –
die Anzahl und die neuesten paar; auf der Uhr schiebt ein Tap die komplette Liste mit
„aktiv seit“-Zeiten und einem optionalen „Lichter ausschalten“-Button ein. Jede Quelle ist eine
Text-Entity plus eine Bedingung (`when`); eine optionale Ersatzkarte (`empty`: energy, climate,
weather, clock oder tile) nimmt den Platz der Kachel ein, solange alles bekannt ist und nichts
zutrifft.

Er bearbeitet den `helios`-Abschnitt eines Storage-Mode-Dashboards über die Frontend-Befehle
`lovelace/config` und `lovelace/config/save`; alles andere in diesem Dashboard bleibt unberührt.
Vor dem Speichern liest er das Dashboard erneut und verweigert das Überschreiben einer Version,
die inzwischen woanders geändert wurde. Ein Dokument in Schema 2–5 lädt als eine Seite und wird
beim ersten Speichern auf Schema 6 angehoben – das braucht EOS 0.12 auf der Uhr; eine ältere Uhr
lehnt das neue Dokument ab und behält ihr bisheriges Layout. Das JavaScript ist öffentlich (keine
Secrets darin); der einzige Mutation-Pfad ist `lovelace/config/save`, den Home Assistant auf
Administratoren beschränkt.

# EOS – Home Assistant Integration für die Lenovo Smart Clock 2

EOS ist eine benutzerdefinierte [Home-Assistant](https://www.home-assistant.io/)-Integration für die [Helios/EOS Android-App](https://github.com/Hendy59/helios-eos). Sie verwandelt eine Lenovo Smart Clock 2 in ein Home-Assistant-Dashboard und einen Sprach-Satelliten.

Die Uhr kommuniziert mit Home Assistant über eine lokale WebSocket-Verbindung. Die Integration übernimmt Kopplung, Geräteregistrierung, Entities, Sprachbefehle, Dashboard-Konfiguration, Optik-Einstellungen und die optionale Music-Assistant-Unterstützung.

> **Status:** Diese Integration ist für den lokalen Einsatz mit Home Assistant gedacht und wird über HACS als benutzerdefiniertes Repository verteilt.

## Funktionen

- Lokale Push-Kommunikation über WebSocket
- Sechsstelliger Kopplungscode, von Home Assistant generiert
- Home-Assistant-Geräte- und Bereichsregistrierung
- Sprachstatus- und Diagnosesensoren
- Dock- und Lade-Binärsensoren
- Dock-Lampensteuerung mit Helligkeit
- Gerätelautstärke, Media-Player-Unterstützung (Lautstärke, Transport, play_media) und ein Assist-Sprach-Satellit mit Ansagen
- EOS-Dashboard-Editor in der Home-Assistant-Seitenleiste
- Pro-Uhr-Dashboards und geteilte Dashboards
- Eigene Farbschemata, Hintergründe, Abdunklung und Fokuspunkt-Einstellungen
- Automatische Music-Assistant-Integration (Token wird gemintet und an die Uhr gepusht, auch wenn Music Assistant später startet)
- Unterstützung für Dashboard-Karten:
  - Energy
  - Thermostat
  - Readings
  - Alerts

Die Integration hat keine zusätzlichen Python-Laufzeitabhängigkeiten.

## Entities

| Plattform | Entity | Beschreibung |
| --- | --- | --- |
| `sensor` | App-Version | EOS-Anwendungsversion auf der Uhr |
| `sensor` | Sprachstatus | Idle, listening, processing, responding oder error |
| `sensor` | Dock-Version | Firmware-Version der Ladeschale |
| `binary_sensor` | Dock verbunden | ob die OEM-Schale verbunden ist |
| `binary_sensor` | Telefon lädt | Qi-Ladestatus; erfordert ein Dock |
| `light` | Dock-Lampe | Ein/Aus und Helligkeit von 1–10 |
| `number` | Gerätelautstärke | `STREAM_MUSIC`-Lautstärke von 0–100 % |
| `media_player` | Uhr-Lautsprecher | Lautstärke, Transport und play_media (TTS, Medien, Music-Assistant-Streams) für Home Assistant Assist und den Medienbrowser |
| `assist_satellite` | Satellit | Sprach-Satellit: spiegelt den Sprachstatus der Uhr und akzeptiert Ansagen |

Entities bleiben `unavailable`, bis die Uhr ihren ersten Zustands-Snapshot schickt. Geht die WebSocket-Verbindung verloren, markiert die Integration die Entities als `unavailable`.

## Voraussetzungen

- Home Assistant
- Eine Lenovo Smart Clock 2
- Die EOS/Helios-Android-App auf der Uhr installiert
- EOS 0.9.0 oder neuer für die Kopplung
- HACS oder manuelle Installation als benutzerdefinierte Integration

Einige Dashboard-Karten brauchen neuere EOS-Versionen:

- Energy: EOS 0.14 oder neuer
- Thermostat: EOS 0.16 oder neuer
- Alerts: EOS 0.17 oder neuer
- Readings: EOS 0.19 oder neuer

## Installation mit HACS

1. **HACS** in Home Assistant öffnen.
2. Zu **Integrationen** gehen.
3. Das Drei-Punkt-Menü öffnen und **Benutzerdefinierte Repositories** wählen.
4. Diese Repository-URL hinzufügen:

   `https://github.com/Hendy59/ha-Eos`

5. **Integration** als Kategorie wählen.
6. **EOS** installieren.
7. Home Assistant neu starten.

## Uhr koppeln

1. Auf der Uhr EOS öffnen und **Mit HA koppeln** wählen.
2. Home Assistant aus der mDNS-Liste wählen oder die Adresse manuell eingeben.
3. In Home Assistant **Einstellungen → Geräte & Dienste** öffnen.
4. **Integration hinzufügen** wählen und **EOS** auswählen.
5. Home Assistant zeigt einen sechsstelligen Kopplungscode, fünf Minuten gültig.
6. Auf der Uhr **Weiter** tippen und den Code eingeben.
7. Das neue Gerät einem Bereich zuweisen.

Der zugewiesene Home-Assistant-Bereich des Geräts wird als Raumkontext für Sprachbefehle verwendet. Eine erneute Kopplung derselben Uhr aktualisiert ihre bestehenden Zugangsdaten, nachdem die neue Kopplung erfolgreich war.

## Sicherheit

Der Kopplungs-Endpunkt ist absichtlich unauthentifiziert, weil eine neue Uhr noch keine Zugangsdaten hat. Er akzeptiert nur einen kurzen, sechsstelligen Code, der in der Home-Assistant-Oberfläche erzeugt wurde.

Nach der Kopplung legt die Integration einen eigenen Home-Assistant-User für die Uhr an:

- Der User ist kein Administrator.
- Der User ist auf das lokale Netzwerk beschränkt.
- Die Uhr erhält ihr eigenes langlebiges System-Token.
- Das Token ist kein Administrator-Token.
- Die Geräteverbindung akzeptiert nur die Befehle, die die Uhr braucht.
- Kopplungscodes laufen nach fünf Minuten ab.
- Wiederholte ungültige Versuche werden rate-limitiert.
- Kopplungscodes und Tokens werden nicht in die Logs geschrieben.

Das Entfernen des EOS-Config-Eintrags entfernt auch den Uhr-User, das Music-Assistant-Token und das gespeicherte Hintergrundbild, die zu diesem Gerät gehören.

Die vollständige Protokoll- und Sicherheitsdokumentation findest du in [docs/PROTOCOL.md](docs/PROTOCOL.md).

## Dashboard-Editor

Das Seitenleisten-Panel **EOS** steht Home-Assistant-Administratoren zur Verfügung. Es bietet einen visuellen Editor für das Uhr-Layout:

- 4×3-Dashboard-Leinwand
- Mehrere Seiten
- Entity- und Icon-Auswahl
- Karten hinzufügen, bearbeiten, verschieben und löschen
- Geteilte Dashboards oder ein separates Dashboard pro Uhr
- Validierung mit denselben Regeln wie die EOS-App

Der Editor verändert nur den `helios`-Abschnitt eines Storage-Mode-Lovelace-Dashboards. Andere Dashboard-Inhalte bleiben erhalten.

## Optik-Konfiguration

**Einstellungen → Geräte & Dienste → EOS → Konfigurieren** öffnen, um zu ändern:

- Farbschema
- Hintergrundbild
- Abdunklung
- Bild-Fokuspunkt
- Sendspin-Einstellungen
- Diagnose
- Music-Assistant-Optionen

Hochgeladene Bilder werden lokal von Home Assistant verarbeitet. Die EXIF-Orientierung wird angewendet, Metadaten werden entfernt, Transparenz wird flachgerechnet und das Bild wird vor der privaten Speicherung verkleinert.

## Music Assistant

Music-Assistant-Unterstützung ist optional und automatisch. Wenn eine Music-Assistant-Integration geladen ist, mintet EOS ein eigenes Token für die Uhr und pusht Adresse, Token und Sendspin-Adresse dorthin. Das passiert auch, wenn Music Assistant später startet (ein Add-on, das nach Home Assistant bootet) oder installiert wird, während bereits eine Uhr verbunden ist: Die Uhr verbindet sich dann selbst mit Music Assistant und erscheint dort als Player.

Die Uhr ist in Home Assistant außerdem ein Media Player: `media_player.play_media` spielt TTS, Mediendateien und Music-Assistant-Streams auf ihr ab.

Läuft Music Assistant als Add-on und kann nicht automatisch ein brauchbares Token ausstellen, hinterlege ein Token unter:

**Einstellungen → Geräte & Dienste → EOS → Konfigurieren → Music-Assistant-Token für die Uhr**

Das Token wird so gespeichert, wie du es einfügst, und beim Connect an die Uhr gesendet.

## Protokoll-Dokumentation

Die WebSocket-Kanäle, der Kopplungs-Austausch, das Connection-Event und der Befehlsfluss sind in [docs/PROTOCOL.md](docs/PROTOCOL.md) dokumentiert.

## Entwicklung

Test-Abhängigkeiten installieren:

```bash
pip install -r requirements_test.txt
```

Python-Tests ausführen:

```bash
python -m pytest tests
```

JavaScript-Panel-Tests ausführen:

```bash
node --test tests/panel/schema.test.mjs
```

Das Projekt entwickelt mit Python 3.14. GitHub Actions führt die Home-Assistant- und HACS-Validierung, Python-Tests, JavaScript-Tests und einen Import-Check aus.

Übersetzungen liegen in:

- `strings.json` — Englisch
- `translations/de.json` — Deutsch
- `translations/pl.json` — Polnisch

Das polnische README ist als [README.pl.md](README.pl.md) verfügbar, das englische als [README.md](README.md).

## Lizenz

Dieses Projekt ist unter der **MIT-Lizenz** lizenziert.

Copyright © 2026 Mateusz Sych.

Den vollständigen Lizenztext findest du in [LICENSE](LICENSE).

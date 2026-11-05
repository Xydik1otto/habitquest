# 📱 Мобільні застосунки (Android / iOS)

HabitQuest доступний на мобільних через **Capacitor 6**. Застосунок — не самодостатня
копія: це **оболонка, що підключається до вашого сервера** (self-hosted етос проєкту).
При першому запуску з'являється екран із полем «Адреса сервера» — URL зберігається
в Preferences пристрою, далі застосунок одразу відкриває ваш сервер.

## Чесні обмеження

| Платформа | Шлях | Ціна |
|---|---|---|
| **Android** | APK з CI (GitHub Releases) → sideload | Безкоштовно, повністю |
| **iOS** | Unsigned ZIP з CI → AltStore / Sideloadly | Безкоштовно, але re-sign кожні 7 днів |

- App Store вимагає Apple Developer ($99/рік) — це **не в бюджеті** проєкту, тому
  офіційного iPhone-білда немає. Unsigned-артефакт з Actions можна ставити через
  AltStore/Sideloadly (потрібен комп'ютер із Apple ID; безкоштовний сертифікат
  живе 7 днів, тож доведеться перезапускати). TestFlight можливий у майбутньому.
- Застосунок підключається до **свого сервера**: локальна мережа (http у LAN
  дозволено) або віддалений доступ через Tailscale / WireGuard (безкоштовно).

## Завантажити готові збірки

1. Відкрийте [Releases](https://github.com/xydik1otto/habitquest/releases).
2. Android: скачайте `app-debug.apk` (або unsigned release APK) з останнього релізу
   чи з артефактів [Actions](https://github.com/xydik1otto/habitquest/actions)
   (артефакти зберігаються 30 днів).
3. iOS: скачайте `habitquest-ios-unsigned.zip` з артефактів Actions.

## Встановлення Android (sideload)

1. Скачайте APK на телефон.
2. Дозвольте «Встановлення невідомих застосунків» для браузера/файлового менеджера
   (Налаштування → Безпека).
3. Відкрийте APK → Встановити.
4. Запустіть HabitQuest → введіть адресу сервера (наприклад, `http://192.168.1.10:8000`).

## Встановлення iOS (AltStore / Sideloadly)

1. Скачайте та розпакуйте `habitquest-ios-unsigned.zip` (усередині `App.app`).
2. Встановіть [AltServer](https://altstore.io) (Windows/macOS) або Sideloadly.
3. Підключіть iPhone кабелем → відправте `App.app` через AltStore/Sideloadly.
4. На iPhone: Налаштування → Основні → VPN і керування пристроєм → довірити
   свій Apple ID сертифікат.
5. Перший запуск: введіть адресу сервера. Re-sign кожні 7 днів (AltStore
   оновлює підпис сам, якщо комп'ютер із AltServer доступний).

## Адреса сервера

- Формат: `http://<IP-адреса>:<порт>` у локальній мережі або домен/ tunnel-адреса.
- Дізнатися IP сервера: `ipconfig` / `ifconfig` на машині, де запущено HabitQuest
  (`habitquest` CLI або `uvicorn app.main:app --host 0.0.0.0 --port 8000`).
- Сервер має слухати не тільки localhost (`--host 0.0.0.0`).
- Змінити збережену адресу: натисніть «Назад» у застосунку — екран адреси
  відкриється знову з попереднім значенням.

## Tailscale-гайд (віддалений доступ, безкоштовно)

1. Встановіть Tailscale на комп'ютер із сервером і на телефоні, увійдіть в один акаунт.
2. Дізнайтеся Tailscale-IP сервера (100.x.y.z) в аплеті Tailscale.
3. Запустіть сервер: `habitquest --port 8000` (він слухає на всіх інтерфейсах).
4. У застосунку введіть `http://100.x.y.z:8000` — сервер доступний звідусіль,
   де є Tailscale, без відкриття портів у роутері.

## Збірка локально

Вимоги: Node 22+, JDK 17 (+ Android SDK для Android), Xcode 15+ та CocoaPods для iOS.

```bash
npm ci
npx cap sync
# Android
cd android && ./gradlew assembleDebug   # APK: app/build/outputs/apk/debug/
# iOS (macOS)
cd ios/App && pod install
xcodebuild -workspace App.xcworkspace -scheme App -configuration Release \
  -destination 'generic/platform=iOS' CODE_SIGNING_ALLOWED=NO build
```

CI збирає обидва автоматично на кожен push (`.github/workflows/android-build.yml`,
`ios-build.yml`).

---

# 📱 Mobile apps (Android / iOS) — English

HabitQuest ships on mobile via **Capacitor 6**. The app is not a standalone copy:
it is a **shell that connects to your own server** (self-hosted ethos). On first
launch a screen asks for the server address; the URL is stored in device
Preferences and the app opens your server from then on.

## Honest limitations

| Platform | Path | Cost |
|---|---|---|
| **Android** | APK from CI (GitHub Releases) → sideload | Completely free |
| **iOS** | Unsigned ZIP from CI → AltStore / Sideloadly | Free, but re-sign every 7 days |

- The App Store requires Apple Developer ($99/year) — **out of budget** for this
  project, so there is no official iPhone build. The unsigned artifact from Actions
  can be installed via AltStore/Sideloadly (needs a computer with an Apple ID; the
  free certificate lasts 7 days). TestFlight may come later.
- The app connects to **your server**: plain http on the LAN is allowed, or remote
  access via Tailscale / WireGuard (free).

## Download prebuilt builds

1. Open the [Releases](https://github.com/xydik1otto/habitquest/releases) page.
2. Android: grab `app-debug.apk` (or the unsigned release APK) from the latest
   release, or from [Actions](https://github.com/xydik1otto/habitquest) artifacts
   (kept 30 days).
3. iOS: grab `habitquest-ios-unsigned.zip` from the Actions artifacts.

## Android install (sideload)

1. Download the APK onto the phone.
2. Allow installing apps from unknown sources for your browser/file manager.
3. Open the APK → Install.
4. Launch HabitQuest → enter the server address (e.g. `http://192.168.1.10:8000`).

## iOS install (AltStore / Sideloadly)

1. Download and unpack `habitquest-ios-unsigned.zip` (contains `App.app`).
2. Install [AltServer](https://altstore.io) (Windows/macOS) or Sideloadly.
3. Connect the iPhone via cable → sideload `App.app`.
4. On the iPhone: Settings → General → VPN & Device Management → trust your
   Apple ID certificate.
5. First launch: enter the server address. Re-sign every 7 days (AltStore
   refreshes the signature automatically while AltServer is reachable).

## Server address

- Format: `http://<IP>:<port>` on the LAN, or a domain / tunnel URL.
- Find the server IP with `ipconfig` / `ifconfig` on the machine running
  HabitQuest (`habitquest` CLI or `uvicorn app.main:app --host 0.0.0.0 --port 8000`).
- The server must listen beyond localhost (`--host 0.0.0.0`).
- To change the stored address: press Back in the app — the address screen
  re-opens pre-filled with the previous value.

## Tailscale guide (remote access, free)

1. Install Tailscale on the server machine and on the phone, sign in to one account.
2. Get the server's Tailscale IP (100.x.y.z) from the Tailscale applet.
3. Start the server: `habitquest --port 8000` (listens on all interfaces).
4. In the app enter `http://100.x.y.z:8000` — reachable anywhere with Tailscale,
   no router port forwarding needed.

## Build locally

Requirements: Node 22+, JDK 17 (+ Android SDK for Android), Xcode 15+ and
CocoaPods for iOS.

```bash
npm ci
npx cap sync
# Android
cd android && ./gradlew assembleDebug   # APK: app/build/outputs/apk/debug/
# iOS (macOS)
cd ios/App && pod install
xcodebuild -workspace App.xcworkspace -scheme App -configuration Release \
  -destination 'generic/platform=iOS' CODE_SIGNING_ALLOWED=NO build
```

CI builds both automatically on every push (`.github/workflows/android-build.yml`,
`ios-build.yml`).

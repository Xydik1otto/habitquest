import type { CapacitorConfig } from '@capacitor/cli';

/**
 * HabitQuest mobile shell (Capacitor 6).
 *
 * The bundled `www/` directory contains only the first-launch splash screen
 * that asks for the user's own HabitQuest server address and stores it in
 * Preferences. The app itself is NOT bundled — the shell connects to the
 * self-hosted server (local network or via Tailscale/WireGuard).
 */
const config: CapacitorConfig = {
  appId: 'io.github.xydik1otto.habitquest',
  appName: 'HabitQuest',
  webDir: 'www',
  android: {
    allowMixedContent: false,
  },
  ios: {
    contentInset: 'always',
  },
  server: {
    androidScheme: 'https',
  },
};

export default config;

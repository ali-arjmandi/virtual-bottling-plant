// Settings for the UNS tests: environment first, then the repo's .env (docker compose's).
import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const repo = resolve(import.meta.dirname, '../../..');

function dotenv(): Record<string, string> {
  const file = resolve(repo, '.env');
  if (!existsSync(file)) return {};
  return Object.fromEntries(
    readFileSync(file, 'utf8')
      .split('\n')
      .filter((l) => /^[A-Z_]+=/.test(l))
      .map((l) => {
        const i = l.indexOf('=');
        return [
          l.slice(0, i),
          l
            .slice(i + 1)
            .split(/\s+#/)[0]!
            .trim(),
        ];
      }),
  );
}

const file = dotenv();
const get = (key: string, fallback?: string): string => {
  const value = process.env[key] ?? file[key] ?? fallback;
  if (value === undefined) throw new Error(`${key} not set (environment or .env)`);
  return value;
};

export const testEnv = {
  repo,
  brokerUrl: get('UNS_TEST_BROKER_URL', 'mqtts://localhost:8883'),
  caFile: get('UNS_TEST_CA_FILE', resolve(repo, 'infra/certs/out/ca.crt')),
  simUrl: get('UNS_TEST_SIM_URL', 'http://127.0.0.1:8000'),
  simSpeed: Number(get('UNS_TEST_SIM_SPEED', '10')),
  password: (user: 'ignition' | 'mes-api' | 'edge-bridge') =>
    get(`MQTT_${user.replace('-', '_').toUpperCase()}_PASSWORD`),
};

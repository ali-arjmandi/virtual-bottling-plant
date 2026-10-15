// Validated environment (architecture.md §2 rule 4). Fails at start-up on a bad value.
import { z } from 'zod';

const schema = z.object({
  PLC_HOST: z.string().min(1).default('plc'),
  PLC_PORT: z.coerce.number().int().positive().default(502),
  PLC_TIMEOUT_MS: z.coerce.number().int().positive().default(200),
  BRIDGE_POLL_MS: z.coerce.number().int().min(50).default(250),
  MQTT_URL: z.string().url().default('mqtts://broker:8883'),
  MQTT_USERNAME: z.string().min(1).default('edge-bridge'),
  MQTT_PASSWORD: z.string().min(1),
  MQTT_CA_FILE: z.string().optional(),
  SIM_EPOCH: z.string().datetime({ offset: true }).default('2026-10-05T05:30:00Z'),
  HEALTH_PORT: z.coerce.number().int().positive().default(8081),
  LOG_LEVEL: z.enum(['debug', 'info', 'warn', 'error']).default('info'),
});

export type Env = z.infer<typeof schema>;

export function loadEnv(source: NodeJS.ProcessEnv = process.env): Env {
  const parsed = schema.safeParse(source);
  if (!parsed.success) {
    const issues = parsed.error.issues.map((i) => `${i.path.join('.')}: ${i.message}`);
    throw new Error(`invalid environment: ${issues.join('; ')}`);
  }
  return parsed.data;
}

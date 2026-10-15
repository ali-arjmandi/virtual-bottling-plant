// Edge bridge entry point: wiring only (l2-edge-uns.md).
import { readFileSync } from 'node:fs';
import { pino } from 'pino';
import { buildMetricCatalog, jsonTopic } from '@vbp/contracts';
import { loadEnv } from './config/env.js';
import { PlcClient } from './modbus/plc-client.js';
import { BlockReader } from './modbus/block-reader.js';
import { buildReadPlan } from './modbus/read-plan.js';
import { NodeSession } from './sparkplug/node-session.js';
import { MetricPublisher } from './sparkplug/metric-publisher.js';
import { QualityTracker } from './sparkplug/quality-tracker.js';
import { SimTimestamp } from './time/sim-timestamp.js';
import { EventPublisher } from './events/event-publisher.js';
import { StateChangeDetector } from './events/state-change-detector.js';
import { ProcessEventDetector } from './events/process-event-detector.js';
import { DcmdHandler } from './commands/dcmd-handler.js';
import { RecipeHandshake } from './commands/recipe-handshake.js';
import { LineBridge } from './bridge/line-bridge.js';
import { startHealthServer } from './health/health-server.js';

const env = loadEnv();
const log = pino({ level: env.LOG_LEVEL, base: { service: 'edge-bridge' } });
const catalog = buildMetricCatalog();

const plc = new PlcClient(
  { host: env.PLC_HOST, port: env.PLC_PORT, timeoutMs: env.PLC_TIMEOUT_MS },
  log,
);
const session = new NodeSession(
  {
    url: env.MQTT_URL,
    username: env.MQTT_USERNAME,
    password: env.MQTT_PASSWORD,
    ca: env.MQTT_CA_FILE ? readFileSync(env.MQTT_CA_FILE) : undefined,
  },
  log,
);

const bridge = new LineBridge({
  plc,
  session,
  catalog,
  log,
  pollMs: env.BRIDGE_POLL_MS,
  reader: new BlockReader(plc, buildReadPlan(catalog)),
  metrics: new MetricPublisher(),
  quality: new QualityTracker(),
  simTime: new SimTimestamp(Date.parse(env.SIM_EPOCH)),
  events: new EventPublisher(
    (topic, body, retain) => session.publishJson(topic, body, retain),
    log,
  ),
  states: new StateChangeDetector(),
  process: new ProcessEventDetector(),
  dcmd: new DcmdHandler(catalog, log),
  handshake: new RecipeHandshake(),
});

session.onJson(jsonTopic('recipe'), (payload) => bridge.onRecipe(payload));
session.start();
bridge.start();
const health = startHealthServer(env.HEALTH_PORT, () => ({
  plc: bridge.linkState,
  mqtt: session.connected,
}));
log.info(
  { devices: Object.keys(catalog).length, pollMs: env.BRIDGE_POLL_MS },
  'edge bridge started',
);

async function shutdown(signal: string): Promise<void> {
  log.info({ signal }, 'shutting down');
  bridge.stop();
  health.close();
  await session.stop().catch(() => {});
  await plc.close();
  process.exit(0);
}
process.on('SIGTERM', () => void shutdown('SIGTERM'));
process.on('SIGINT', () => void shutdown('SIGINT'));

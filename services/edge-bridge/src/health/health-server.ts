// GET /health for the compose health check: 200 when the PLC link and the broker are both up.
import { createServer, type Server } from 'node:http';

export type HealthProbe = () => { plc: string; mqtt: boolean };

export function startHealthServer(port: number, probe: HealthProbe): Server {
  const server = createServer((req, res) => {
    if (req.url !== '/health') {
      res.writeHead(404).end();
      return;
    }
    const status = probe();
    const ok = status.plc === 'online' && status.mqtt;
    res
      .writeHead(ok ? 200 : 503, { 'content-type': 'application/json' })
      .end(JSON.stringify(status));
  });
  server.listen(port);
  return server;
}

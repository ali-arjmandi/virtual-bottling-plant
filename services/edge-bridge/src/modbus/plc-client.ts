// The bridge's single Modbus TCP connection to the PLC (contracts.md §2), with reconnect.
// Addresses here are %MW / %MD numbers; the holding-register offsets come from plc-io.yaml.
import { createRequire } from 'node:module';
import type { ModbusRTU as ModbusRTUClass } from 'modbus-serial/ModbusRTU.js';
import type { Logger } from 'pino';
import { plcIoDoc } from '@vbp/contracts';
import { WriteQueue } from './write-queue.js';

// modbus-serial is CommonJS (`module.exports = ModbusRTU`) but its typings declare a default
// export, which NodeNext resolves wrongly; load it with require and keep its declared type.
const ModbusRTU = createRequire(import.meta.url)('modbus-serial') as typeof ModbusRTUClass;

export type PlcClientOptions = { host: string; port: number; timeoutMs: number };

export class PlcClient {
  private readonly modbus = new ModbusRTU();
  private readonly queue = new WriteQueue();
  private connecting: Promise<void> | null = null;
  private readonly mwBase = plcIoDoc.addressing.mw_holding_base;
  private readonly mdBase = plcIoDoc.addressing.md_holding_base;

  constructor(
    private readonly opts: PlcClientOptions,
    private readonly log: Logger,
  ) {}

  get connected(): boolean {
    return this.modbus.isOpen;
  }

  readMw(mw: number, count: number): Promise<number[]> {
    return this.transact(
      async () => (await this.modbus.readHoldingRegisters(this.mwBase + mw, count)).data,
    );
  }

  readMdWords(md: number, count: number): Promise<number[]> {
    return this.transact(
      async () => (await this.modbus.readHoldingRegisters(this.mdBase + 2 * md, 2 * count)).data,
    );
  }

  /** Writes consecutive %MW words in one request (FC16). Values are signed or unsigned 16-bit. */
  writeMw(mw: number, values: number[]): Promise<void> {
    const words = values.map((v) => v & 0xffff);
    return this.transact(async () => {
      if (words.length === 1) await this.modbus.writeRegister(this.mwBase + mw, words[0]!);
      else await this.modbus.writeRegisters(this.mwBase + mw, words);
    });
  }

  async close(): Promise<void> {
    if (this.modbus.isOpen)
      await new Promise<void>((resolve) => this.modbus.close(() => resolve()));
  }

  private transact<T>(job: () => Promise<T>): Promise<T> {
    return this.queue.run(async () => {
      await this.ensureConnected();
      try {
        return await job();
      } catch (err) {
        // A timeout leaves the TCP stream in an unknown state: drop it and reconnect next time.
        // Destroy, not close: a graceful close waits for a FIN that a frozen PLC never sends.
        if (isConnectionError(err)) this.modbus.destroy(() => {});
        throw err;
      }
    });
  }

  private ensureConnected(): Promise<void> {
    if (this.modbus.isOpen) return Promise.resolve();
    this.connecting ??= (async () => {
      try {
        await withTimeout(
          this.modbus.connectTCP(this.opts.host, { port: this.opts.port }),
          CONNECT_TIMEOUT_MS,
        );
        this.modbus.setID(1);
        this.modbus.setTimeout(this.opts.timeoutMs);
        this.log.info({ host: this.opts.host, port: this.opts.port }, 'PLC connected');
      } finally {
        this.connecting = null;
      }
    })();
    return this.connecting;
  }
}

const CONNECT_TIMEOUT_MS = 2000;

function withTimeout<T>(promise: Promise<T>, ms: number): Promise<T> {
  let timer: NodeJS.Timeout | undefined;
  const timeout = new Promise<never>((_, reject) => {
    timer = setTimeout(
      () => reject(Object.assign(new Error('connect timed out'), { errno: 'ETIMEDOUT' })),
      ms,
    );
  });
  return Promise.race([promise, timeout]).finally(() => clearTimeout(timer));
}

function isConnectionError(err: unknown): boolean {
  const e = err as { name?: string; errno?: string; code?: string };
  return (
    e?.name === 'TransactionTimedOutError' ||
    e?.errno === 'ETIMEDOUT' ||
    e?.name === 'PortNotOpenError' ||
    e?.code === 'ECONNRESET' ||
    e?.code === 'EPIPE' ||
    e?.code === 'ECONNREFUSED'
  );
}

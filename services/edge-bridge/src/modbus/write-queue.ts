// One queue for every Modbus transaction (EDG-12): polls, commands and recipe writes run one at
// a time and never interleave, and a slow PLC cannot pile up concurrent requests.
export class WriteQueue {
  private tail: Promise<unknown> = Promise.resolve();
  private pending = 0;

  run<T>(job: () => Promise<T>): Promise<T> {
    this.pending++;
    const result = this.tail.then(job, job);
    this.tail = result.then(
      () => this.pending--,
      () => this.pending--,
    );
    return result;
  }

  get size(): number {
    return this.pending;
  }
}

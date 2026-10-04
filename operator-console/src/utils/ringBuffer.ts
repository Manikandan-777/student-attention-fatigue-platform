// Bounded FIFO ring buffer for time-series chart points
export class RingBuffer<T> {
  private buffer: T[] = [];
  private capacity: number;

  constructor(capacity = 60) {
    this.capacity = capacity;
  }

  push(item: T): void {
    if (this.buffer.length >= this.capacity) {
      this.buffer.shift();
    }
    this.buffer.push(item);
  }

  getItems(): T[] {
    return [...this.buffer];
  }

  clear(): void {
    this.buffer = [];
  }

  size(): number {
    return this.buffer.length;
  }
}

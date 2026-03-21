/**
 * Sistema de throttling y batching para peticiones API
 * Reduce la carga del servidor limitando peticiones simultÃ¡neas
 */

interface QueuedRequest {
  fn: () => Promise<any>;
  resolve: (value: any) => void;
  reject: (error: any) => void;
  priority: number;
}

class RequestThrottler {
  private queue: QueuedRequest[] = [];
  private activeRequests = 0;
  private maxConcurrent: number;
  private batchDelay: number;

  constructor(maxConcurrent = 5, batchDelay = 100) {
    this.maxConcurrent = maxConcurrent;
    this.batchDelay = batchDelay;
  }

  /**
   * Ejecuta una peticiÃ³n con throttling
   */
  async execute<T>(fn: () => Promise<T>, priority = 0): Promise<T> {
    return new Promise<T>((resolve, reject) => {
      this.queue.push({
        fn,
        resolve,
        reject,
        priority,
      });

      // Ordenar por prioridad (mayor = mÃ¡s importante)
      this.queue.sort((a, b) => b.priority - a.priority);

      this.processQueue();
    });
  }

  /**
   * Procesa la cola de peticiones
   */
  private async processQueue() {
    // Si ya hay demasiadas peticiones activas o la cola estÃ¡ vacÃ­a, no hacer nada
    if (this.activeRequests >= this.maxConcurrent || this.queue.length === 0) {
      return;
    }

    // Tomar la siguiente peticiÃ³n de la cola
    const request = this.queue.shift();
    if (!request) return;

    this.activeRequests++;

    try {
      const result = await request.fn();
      request.resolve(result);
    } catch (error) {
      request.reject(error);
    } finally {
      this.activeRequests--;
      // Procesar siguiente peticiÃ³n despuÃ©s de un pequeÃ±o delay
      setTimeout(() => this.processQueue(), this.batchDelay);
    }
  }

  /**
   * Ejecuta mÃºltiples peticiones en batches
   */
  async executeBatch<T>(
    requests: Array<() => Promise<T>>,
    batchSize = 3,
    delayBetweenBatches = 200
  ): Promise<T[]> {
    const results: T[] = [];

    for (let i = 0; i < requests.length; i += batchSize) {
      const batch = requests.slice(i, i + batchSize);
      const batchResults = await Promise.allSettled(
        batch.map(req => this.execute(req))
      );

      // Procesar resultados
      batchResults.forEach((result, index) => {
        if (result.status === 'fulfilled') {
          results.push(result.value);
        } else {
          // En caso de error, agregar undefined o lanzar error segÃºn necesidad
          results.push(undefined as T);
        }
      });

      // Delay entre batches (excepto el Ãºltimo)
      if (i + batchSize < requests.length) {
        await new Promise(resolve => setTimeout(resolve, delayBetweenBatches));
      }
    }

    return results;
  }

  /**
   * Limpia la cola de peticiones pendientes
   */
  clear() {
    this.queue.forEach(req => {
      req.reject(new Error('Request queue cleared'));
    });
    this.queue = [];
  }
}

// Instancia singleton
export const requestThrottler = new RequestThrottler(5, 100);

/**
 * Wrapper para ejecutar peticiones con throttling
 */
export async function throttledRequest<T>(
  fn: () => Promise<T>,
  priority = 0
): Promise<T> {
  return requestThrottler.execute(fn, priority);
}

/**
 * Ejecuta mÃºltiples peticiones en batches controlados
 */
export async function batchedRequests<T>(
  requests: Array<() => Promise<T>>,
  batchSize = 3,
  delayBetweenBatches = 200
): Promise<T[]> {
  return requestThrottler.executeBatch(requests, batchSize, delayBetweenBatches);
}


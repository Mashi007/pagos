export function chunkItems<T>(items: T[], maxChunkSize: number): T[][] {
  if (!Number.isInteger(maxChunkSize) || maxChunkSize <= 0) {
    throw new Error('maxChunkSize must be a positive integer')
  }

  const chunks: T[][] = []

  for (let start = 0; start < items.length; start += maxChunkSize) {
    chunks.push(items.slice(start, start + maxChunkSize))
  }

  return chunks
}

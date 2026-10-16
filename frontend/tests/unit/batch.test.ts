import { describe, expect, it } from 'vitest'

import { chunkItems } from '@/utils/batch'

describe('chunkItems', () => {
  it('splits arrays without exceeding the requested chunk size', () => {
    const items = Array.from({ length: 1201 }, (_, index) => index)

    const chunks = chunkItems(items, 500)

    expect(chunks).toHaveLength(3)
    expect(chunks.map(chunk => chunk.length)).toEqual([500, 500, 201])
    expect(chunks.flat()).toEqual(items)
  })

  it('rejects invalid chunk sizes', () => {
    expect(() => chunkItems([1], 0)).toThrow('positive integer')
    expect(() => chunkItems([1], 1.5)).toThrow('positive integer')
  })
})

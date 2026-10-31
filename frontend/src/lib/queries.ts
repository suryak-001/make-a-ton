import { useQuery } from '@tanstack/react-query'
import { api, type Page, qs } from './api'
import type { Plan, Product } from './types'

/** All products for pickers (one page of 100 is plenty for a catalogue picker). */
export function useProducts() {
  return useQuery({
    queryKey: ['products', 'picker'],
    queryFn: () => api.get<Page<Product>>(`/products${qs({ page_size: 100 })}`).then((p) => p.items),
    staleTime: 30_000,
  })
}

/** Plans for pickers. `available` = only those that can be picked for a new subscription today. */
export function usePlans(available?: boolean) {
  return useQuery({
    queryKey: ['plans', 'picker', available],
    queryFn: () => api.get<Page<Plan>>(`/plans${qs({ page_size: 100, available })}`).then((p) => p.items),
    staleTime: 30_000,
  })
}

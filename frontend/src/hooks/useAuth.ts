import { useSimpleAuth as useAuthStore } from '../store/simpleAuthStore'

// Re-export del hook del store para mantener consistencia
export const useAuth = useAuthStore

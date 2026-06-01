import { createLocalDataAdapter } from './localDataAdapter'
import { createRemoteDataAdapter } from './remoteDataAdapter'

// Controlled by VITE_DATA_MODE at build/dev time.
// Set VITE_DATA_MODE=remote in .env.local to test against the live Frappe backend.
// Defaults to 'local' so seed-data mode remains the safe default until Phase 9.
const DEFAULT_MODE = import.meta.env.VITE_DATA_MODE || 'local'

export function createDataAdapter(store, mode = DEFAULT_MODE) {
  if (mode === 'remote') {
    return createRemoteDataAdapter()
  }
  return createLocalDataAdapter(store)
}

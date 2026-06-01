import { createLocalDataAdapter } from './localDataAdapter'
import { createRemoteDataAdapter } from './remoteDataAdapter'

// Controlled by VITE_DATA_MODE at build/dev time.
// Set VITE_DATA_MODE=local in .env.local to force seed-data mode.
// Defaults to 'remote' for the current read-only Doctype list slice.
const DEFAULT_MODE = import.meta.env.VITE_DATA_MODE || 'remote'

export function createDataAdapter(store, mode = DEFAULT_MODE) {
  if (mode === 'remote') {
    return createRemoteDataAdapter()
  }
  return createLocalDataAdapter(store)
}

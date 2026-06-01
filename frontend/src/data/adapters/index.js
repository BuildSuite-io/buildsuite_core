import { createLocalDataAdapter } from './localDataAdapter'

const DEFAULT_MODE = 'local'

export function createDataAdapter(store, mode = DEFAULT_MODE) {
  // Remote mode is reserved for phased API migration; local mode keeps current behavior.
  if (mode === 'remote') {
    console.warn('[buildsuite] Remote data adapter is not implemented yet; falling back to local mode')
  }

  return createLocalDataAdapter(store)
}

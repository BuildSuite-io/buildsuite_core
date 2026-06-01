import { createLocalDataAdapter } from './localDataAdapter'
import { createRemoteDataAdapter } from './remoteDataAdapter'

const DEFAULT_MODE = 'local'

export function createDataAdapter(store, mode = DEFAULT_MODE) {
  if (mode === 'remote') {
    return createRemoteDataAdapter()
  }
  return createLocalDataAdapter(store)
}

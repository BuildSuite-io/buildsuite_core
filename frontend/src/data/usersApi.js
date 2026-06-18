import { frappeRequest } from 'frappe-ui-frappe-request'
import { parseFrappeError } from '@/utils/frappeError'

async function call(method, args) {
  try {
    return await frappeRequest({
      url: `buildsuite_core.api.users.${method}`,
      params: args || {},
    })
  } catch (err) {
    throw new Error(parseFrappeError(err).summary || 'Request failed.')
  }
}

export const listBuildsuiteUsers = () => call('list_buildsuite_users')
export const createBuildsuiteUser = (args) => call('create_buildsuite_user', args)
export const updateBuildsuiteUser = (args) => call('update_buildsuite_user', args)
export const sendUserWelcome = (email) => call('send_user_welcome', { email })
export const sendUserPasswordReset = (email) => call('send_user_password_reset', { email })
export const deleteBuildsuiteUser = (email) => call('delete_buildsuite_user', { email })
export const outgoingEmailConfigured = () => call('outgoing_email_configured')

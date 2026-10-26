import { BrowserCacheLocation, PublicClientApplication } from '@azure/msal-browser'

const clientId = import.meta.env.VITE_ENTRA_CLIENT_ID?.trim()
const tenantId = import.meta.env.VITE_ENTRA_TENANT_ID?.trim()
const redirectUri = import.meta.env.VITE_ENTRA_REDIRECT_URI?.trim()
const scopes = (import.meta.env.VITE_ENTRA_SCOPES || 'openid profile email').split(/\s+/).filter(Boolean)
const guidPattern = /^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$/i
const interactionStatusKey = 'msal.interaction.status'

let client
let initialisePromise
let redirectResult
let interactionBusy = false

function checkConfiguration() {
  const missing = []
  if (!clientId) missing.push('VITE_ENTRA_CLIENT_ID')
  if (!tenantId) missing.push('VITE_ENTRA_TENANT_ID')
  if (!redirectUri) missing.push('VITE_ENTRA_REDIRECT_URI')
  if (missing.length) {
    throw new Error(`Microsoft sign-in is not configured. Set ${missing.join(' and ')} in frontend/.env.local.`)
  }
  if (!guidPattern.test(clientId)) throw new Error('VITE_ENTRA_CLIENT_ID must be a GUID.')
  if (!guidPattern.test(tenantId)) throw new Error('VITE_ENTRA_TENANT_ID must be a GUID.')
  if (redirectUri !== 'http://localhost:5173/login') {
    throw new Error('VITE_ENTRA_REDIRECT_URI must match the registered SPA redirect URI: http://localhost:5173/login.')
  }
  if (!['openid', 'profile', 'email'].every(scope => scopes.includes(scope))) {
    throw new Error('VITE_ENTRA_SCOPES must include openid profile email.')
  }
}

function getClient() {
  checkConfiguration()
  if (!client) {
    client = new PublicClientApplication({
      auth: {
        clientId,
        authority: `https://login.microsoftonline.com/${tenantId}`,
        redirectUri,
      },
      cache: { cacheLocation: BrowserCacheLocation.SessionStorage },
      system: { windowHashTimeout: 60000, iframeHashTimeout: 10000 },
    })
  }
  return client
}

export async function initialiseMicrosoftAuth() {
  const application = getClient()
  if (!initialisePromise) {
    initialisePromise = (async () => {
      await application.initialize()
      redirectResult = await application.handleRedirectPromise()
      if (redirectResult?.account) application.setActiveAccount(redirectResult.account)
    })().catch(error => {
      initialisePromise = null
      throw error
    })
  }
  return initialisePromise
}

export async function takeMicrosoftRedirectResult() {
  await initialiseMicrosoftAuth()
  const result = redirectResult
  redirectResult = null
  return result
}

function isInteractionInProgress() {
  if (interactionBusy) return true
  try {
    const status = JSON.parse(window.sessionStorage.getItem(interactionStatusKey) || 'null')
    return Boolean(status && status.clientId === clientId)
  } catch {
    console.warn('[PlaceSync Microsoft sign-in] session_storage_check_failed')
    return false
  }
}

function clearFailedInteractionLock() {
  interactionBusy = false
  try {
    const status = JSON.parse(window.sessionStorage.getItem(interactionStatusKey) || 'null')
    if (!status || status.clientId === clientId) {
      window.sessionStorage.removeItem(interactionStatusKey)
    }
  } catch {
    try {
      window.sessionStorage.removeItem(interactionStatusKey)
    } catch {
      console.warn('[PlaceSync Microsoft sign-in] session_storage_cleanup_failed')
    }
  }
}

export function microsoftErrorMessage(error) {
  const code = error?.errorCode || error?.code || ''
  const message = error?.errorMessage || error?.message || ''
  const detail = `${code} ${message}`.toLowerCase()

  if (code === 'user_cancelled' || detail.includes('user_cancelled')) {
    return 'Microsoft sign-in was cancelled. You can try again or use your PlaceSync password.'
  }
  if (code === 'interaction_in_progress' || detail.includes('interaction_in_progress')) {
    return 'A Microsoft sign-in is already in progress. Finish it or refresh this page before retrying.'
  }
  if (code === 'timed_out' || detail.includes('timed_out')) {
    return 'Microsoft sign-in timed out. Refresh this page and try again.'
  }
  if (detail.includes('aadsts90002') || detail.includes('tenant not found')) {
    return 'Microsoft could not find the configured tenant. Check VITE_ENTRA_TENANT_ID and restart Vite.'
  }
  return message || 'Microsoft sign-in could not be completed. Please retry or use your PlaceSync password.'
}

export async function signInWithMicrosoft(nonce) {
  await initialiseMicrosoftAuth()
  if (!nonce) throw new Error('Microsoft sign-in could not start. Retry to request a fresh security nonce.')
  if (isInteractionInProgress()) {
    throw Object.assign(new Error('A Microsoft sign-in is already in progress.'), { errorCode: 'interaction_in_progress' })
  }

  interactionBusy = true
  try {
    await client.loginRedirect({ scopes, prompt: 'select_account', nonce })
    interactionBusy = false
  } catch (error) {
    const code = error?.errorCode || error?.code || 'unknown_error'
    if (code !== 'interaction_in_progress') clearFailedInteractionLock()
    else interactionBusy = false
    console.warn('[PlaceSync Microsoft sign-in]', code)
    throw error
  }
}

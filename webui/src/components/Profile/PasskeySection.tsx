import { useState } from 'react'
import { Alert, Button, Form, Spinner } from 'react-bootstrap'
import { APIMethod, http } from '../../utils/network'
import { base64urlToBuffer, bufferToBase64url, serializeAttestationCredential } from '../../utils/webauthn'
import { PasskeyInfo } from '../../types/Passkey'

interface PasskeySectionProps {
  passkeys: PasskeyInfo[]
  onPasskeysChange: (passkeys: PasskeyInfo[]) => void
}

const webAuthnSupported = typeof window !== 'undefined' && !!window.PublicKeyCredential

const PasskeySection = ({ passkeys, onPasskeysChange }: PasskeySectionProps) => {
  const [registering, setRegistering] = useState(false)
  const [newKeyName, setNewKeyName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<number | null>(null)

  if (!webAuthnSupported) {
    return <p className="text-muted">Your browser does not support passkeys.</p>
  }

  const handleRegister = async () => {
    setRegistering(true)
    setError(null)

    const beginRes = await http<{ publicKey: any; name: string }>({
      method: APIMethod.post,
      path: '/api/passkey/register/begin',
      data: { name: newKeyName },
    })

    if (beginRes.error || !beginRes.value) {
      setError(beginRes.error || 'Failed to begin registration')
      setRegistering(false)
      return
    }

    let credential: Credential | null
    try {
      const keyString = beginRes.value.publicKey
      const options = JSON.parse(keyString);
      const creationOptions: CredentialCreationOptions = {
        publicKey: {
          ...options,
          challenge: base64urlToBuffer(options.challenge),
          user: { ...options.user, id: base64urlToBuffer(options.user.id) },
          excludeCredentials: (options.excludeCredentials || []).map((c: any) => ({
            ...c,
            id: base64urlToBuffer(c.id),
          })),
        },
      }

      credential = await navigator.credentials.create(creationOptions)
    } catch {
      setError('Passkey creation was cancelled.')
      setRegistering(false)
      return
    }

    if (!credential) {
      setError('Passkey creation was cancelled.')
      setRegistering(false)
      return
    }

    const credJson = serializeAttestationCredential(credential as PublicKeyCredential)

    const completeRes = await http<PasskeyInfo>({
      method: APIMethod.post,
      path: '/api/passkey/register/complete',
      data: { credential: credJson, name: newKeyName },
    })

    if (completeRes.error || !completeRes.value) {
      setError(completeRes.error || 'Registration failed')
      setRegistering(false)
      return
    }

    onPasskeysChange([...passkeys, completeRes.value])
    setNewKeyName('')
    setRegistering(false)
  }

  const handleDelete = async (id: number) => {
    setDeletingId(id)
    await http({
      method: APIMethod.delete,
      path: `/api/passkey/${id}`,
    })
    onPasskeysChange(passkeys.filter(p => p.id !== id))
    setDeletingId(null)
  }

  return (
    <>
      {error && <Alert variant="danger" dismissible onClose={() => setError(null)}>{error}</Alert>}
      {passkeys.length === 0 && <p className="text-muted">No passkeys registered.</p>}
      {passkeys.map(p => (
        <div key={p.id} className="d-flex justify-content-between align-items-center mb-2">
          <span>
            <strong>{p.name || 'Unnamed passkey'}</strong>
            {' — '}
            {new Date(p.created_at).toLocaleDateString()}
          </span>
          <Button
            variant="outline-danger"
            size="sm"
            disabled={deletingId === p.id}
            onClick={() => handleDelete(p.id)}
          >
            {deletingId === p.id ? <Spinner animation="border" size="sm" /> : 'Delete'}
          </Button>
        </div>
      ))}
      <Form.Group className="mt-3 d-flex gap-2">
        <Form.Control
          type="text"
          placeholder="Passkey name (optional)"
          value={newKeyName}
          onChange={e => setNewKeyName(e.target.value)}
          disabled={registering}
        />
        <Button onClick={handleRegister} disabled={registering}>
          {registering ? <Spinner animation="border" size="sm" /> : 'Register new passkey'}
        </Button>
      </Form.Group>
    </>
  )
}

export default PasskeySection

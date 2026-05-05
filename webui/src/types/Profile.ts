import { PasskeyInfo } from './Passkey'

interface Profile {
    email: string
    first_name: string
    last_name: string
    has_2fa: boolean
    passkeys: PasskeyInfo[]
}

export default Profile

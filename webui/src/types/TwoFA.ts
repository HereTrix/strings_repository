import Profile from "./Profile"

export interface TwoFASetupResponse {
    otpauth_uri: string
    qr_code: string        // base64-encoded PNG
    backup_codes: string[] // 10 plaintext codes, shown once
}

export interface TwoFALoginResponse {
    user: Profile
    expired: string | null
}

export interface LoginWith2FAResponse {
    '2fa_required': true
    token: string
}

export interface LoginResponse {
    user: Profile
    token: string
    expired: string
}

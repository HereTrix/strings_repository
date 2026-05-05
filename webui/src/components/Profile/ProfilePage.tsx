import { useEffect, useState } from "react"
import { useSearchParams } from "react-router-dom"
import { APIMethod, http } from "../../utils/network"
import Profile from "../../types/Profile"
import CollapseSection from "../UI/CollapseSection"
import PasswordPage from "./PasswordPage"
import ProfileDetailsPage from "./ProfileDetails"
import ProfileActivatePage from "./ProfileActivate"
import TwoFASetupPage from "./TwoFASetupPage"

const ProfilePage = () => {
    const [profile, setProfile] = useState<Profile>()
    const [searchParams] = useSearchParams()
    const expand2fa = searchParams.get("expand") === "2fa"

    const loadProfile = async () => {
        const data = await http<Profile>({
            method: APIMethod.get,
            path: "/api/profile"
        })
        if (data.value) {
            setProfile(data.value)
        }
    }

    useEffect(() => {
        loadProfile()
    }, [])

    return (
        <>
            {profile &&
                <CollapseSection title="User details">
                    <ProfileDetailsPage profile={profile} />
                </CollapseSection>
            }
            <CollapseSection title="User password">
                <PasswordPage />
            </CollapseSection>
            <CollapseSection title="Project activation">
                <ProfileActivatePage />
            </CollapseSection>
            {profile &&
                <CollapseSection title="Two-Factor Authentication" defaultOpen={expand2fa}>
                    <TwoFASetupPage
                        hasTwoFA={profile.has_2fa}
                        onStatusChange={loadProfile}
                    />
                </CollapseSection>
            }
        </>
    )
}

export default ProfilePage

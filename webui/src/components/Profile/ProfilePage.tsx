import { useEffect, useState } from "react"
import { APIMethod, http } from "../../utils/network"
import Profile from "../../types/Profile"
import CollapseSection from "../UI/CollapseSection"
import PasswordPage from "./PasswordPage"
import ProfileDetailsPage from "./ProfileDetails"
import ProfileActivatePage from "./ProfileActivate"

const ProfilePage = () => {
    const [profile, setProfile] = useState<Profile>()

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
        </>
    )
}

export default ProfilePage

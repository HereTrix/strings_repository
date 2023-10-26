import { useEffect, useState } from "react"
import { Button, Collapse, Container, Stack } from "react-bootstrap"
import PasswordPage from "./PasswordPage"
import ProfileDetailsPage from "./ProfileDetails"
import { APIMethod, http } from "../Utils/network"
import Profile from "../model/Profile"
import ProfileActivatePage from "./ProfileActivate"

const ProfilePage = () => {

    const [passwordSectionOpen, setPasswordSectionOpen] = useState<boolean>(false)
    const [infoSectionOpen, setInfoSectionOpen] = useState<boolean>(false)
    const [activationSectionOpen, setActivationSectionOpen] = useState<boolean>(false)

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
                <Container className="square border rounded-3 my-2">
                    <Stack
                        direction="horizontal"
                        gap={3}
                        onClick={() => setInfoSectionOpen(!infoSectionOpen)}
                        className="my-2">
                        <label>User details</label>
                        <Button
                            className="ms-auto"
                            onClick={() => setInfoSectionOpen(!infoSectionOpen)}>
                            {infoSectionOpen ? "Collapse" : "Reveal"}
                        </Button>
                    </Stack>
                    <Collapse in={infoSectionOpen}>
                        <div>
                            <ProfileDetailsPage profile={profile} />
                        </div>
                    </Collapse>
                </Container>
            }
            <Container className="square border rounded-3 my-2">
                <Stack
                    direction="horizontal"
                    gap={3}
                    onClick={() => setPasswordSectionOpen(!passwordSectionOpen)}
                    className="my-2">
                    <label>User password</label>
                    <Button
                        className="ms-auto"
                        onClick={() => setPasswordSectionOpen(!passwordSectionOpen)}>
                        {passwordSectionOpen ? "Collapse" : "Reveal"}
                    </Button>
                </Stack>
                <Collapse in={passwordSectionOpen}>
                    <div>
                        <PasswordPage />
                    </div>
                </Collapse>
            </Container>
            <Container className="square border rounded-3 my-2">
                <Stack
                    direction="horizontal"
                    gap={3}
                    onClick={() => setActivationSectionOpen(!activationSectionOpen)}
                    className="my-2">
                    <label>Project activation</label>
                    <Button
                        className="ms-auto"
                        onClick={() => setActivationSectionOpen(!activationSectionOpen)}>
                        {passwordSectionOpen ? "Collapse" : "Reveal"}
                    </Button>
                </Stack>
                <Collapse in={activationSectionOpen}>
                    <div>
                        <ProfileActivatePage />
                    </div>
                </Collapse>
            </Container>
        </>
    )
}

export default ProfilePage
import { useEffect, useState } from 'react';
import LogoutButton from './Logout';
import { Container, Nav, Navbar, Image, Dropdown } from 'react-bootstrap';
import { APIMethod, http } from './Utils/network';
import Profile from './model/Profile';
import OptionalImage from './UI/OptionalImage';

const NavBar = () => {

    const [profile, setProfile] = useState<Profile>()

    const fetchProfile = async () => {
        const data = await http<Profile>({
            method: APIMethod.get,
            path: '/api/profile'
        })

        if (data.value) {
            setProfile(data.value)
        }
    }

    const userAlt = () => {
        if (!profile) {
            return ''
        }

        if (profile.first_name.length > 0) {
            if (profile.last_name.length > 0) {
                const name = profile.first_name[0] + profile.last_name[0]
                return name.toUpperCase()
            } else {
                if (profile.first_name.length > 1) {
                    const name = profile.first_name[0] + profile.first_name[1]
                    return name.toUpperCase()
                } else {
                    return profile.first_name[0].toUpperCase()
                }
            }
        }
        return ""
    }

    useEffect(() => {
        fetchProfile()
    }, [])

    return (
        <Navbar expand="lg" className="bg-body-tertiary">
            <Container>
                <Navbar.Brand>Strings Repository</Navbar.Brand>
                <Navbar.Collapse className="justify-content-end">
                    <Nav className='me-auto'>
                        <Nav.Link href='/'>Dashboard</Nav.Link>
                    </Nav>
                    <Nav>
                        <Dropdown>
                            <Dropdown.Toggle split variant="info" className='bg-transparent border-0'>
                                {profile &&
                                    <OptionalImage src={''} alt={userAlt()} />
                                }
                            </Dropdown.Toggle>
                            <Dropdown.Menu>
                                <Dropdown.Item href='/profile'>
                                    Profile
                                </Dropdown.Item>
                                <Dropdown.Item href='https://github.com/HereTrix/strings_repository/wiki'>
                                    Help
                                </Dropdown.Item>
                                <Dropdown.Item>
                                    <LogoutButton />
                                </Dropdown.Item>
                            </Dropdown.Menu>
                        </Dropdown>
                    </Nav>
                </Navbar.Collapse>
            </Container>
        </Navbar>
    )
}

export default NavBar;

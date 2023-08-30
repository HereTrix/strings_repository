import LogoutButton from './Logout';
import { Container, Nav, Navbar, Image, Dropdown } from 'react-bootstrap';

const NavBar = () => {
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
                            <Image src="" roundedCircle />
                            <Dropdown.Toggle />
                            <Dropdown.Menu>
                                <Dropdown.Item href='/profile'>
                                    Profile
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

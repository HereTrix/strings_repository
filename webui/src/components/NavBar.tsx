import LogoutButton from './Logout';
import { Container, Nav, Navbar } from 'react-bootstrap';

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
                        <LogoutButton />
                    </Nav>
                </Navbar.Collapse>
            </Container>
        </Navbar>
    )
}

export default NavBar;

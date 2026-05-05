import React, { useEffect } from 'react';
import { BrowserRouter, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { history } from '../utils/history'
import { setNavigate } from '../utils/navigation';
const LoginPage = React.lazy(() => import("./pages/LoginPage"))
const TwoFALoginPage = React.lazy(() => import("./Auth/TwoFALoginPage"))
const TwoFARequiredPage = React.lazy(() => import("./Auth/TwoFARequiredPage"))
const HomePage = React.lazy(() => import("./pages/HomePage"))
const RequireAuth = React.lazy(() => import("./Auth/PrivateRoute"))
const PageNotFound = React.lazy(() => import("./pages/PageNotFound"))
const ProjectPage = React.lazy(() => import("./Project/ProjectPage"))
const ProfilePage = React.lazy(() => import('./Profile/ProfilePage'))
const ActivateUserPage = React.lazy(() => import('./pages/ActivateUserPage'))
const LanguageTranslationsPage = React.lazy(() => import('./Translation/LanguageTranslationsPage'))

function NavigationRegister() {
  const navigate = useNavigate();

  useEffect(() => {
    setNavigate(navigate);
  }, [navigate]);

  return null;
}

function App() {

  return (
    <BrowserRouter>
      <NavigationRegister />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/2fa-login" element={<TwoFALoginPage />} />
        <Route path="/2fa-required" element={<RequireAuth><TwoFARequiredPage /></RequireAuth>} />
        <Route path="/activate" element={<ActivateUserPage />} />
        <Route path="/" element={<RequireAuth><HomePage /></RequireAuth>} />
        <Route path="/project/:id/:tab?" element={<RequireAuth><ProjectPage /></RequireAuth>} />
        <Route path="/project/:project_id/language/:code" element={<RequireAuth><LanguageTranslationsPage /></RequireAuth>} />
        <Route path="/profile" element={<RequireAuth><ProfilePage /></RequireAuth>} />
        <Route path="*" element={<PageNotFound />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
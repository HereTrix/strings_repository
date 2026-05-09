// Copyright (c) StringsRepository Contributors
// SPDX-License-Identifier: MIT

import React, { useEffect } from 'react';
import { BrowserRouter, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
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

const PAGE_TITLES: Record<string, string> = {
  '/': 'Dashboard',
  '/login': 'Login',
  '/2fa-login': 'Two-Factor Login',
  '/2fa-required': 'Two-Factor Authentication',
  '/activate': 'Activate Account',
  '/profile': 'Profile',
};

function PageTitleManager() {
  const { pathname } = useLocation();

  useEffect(() => {
    const base = 'Strings Repository';
    const segment = pathname.startsWith('/project') ? 'Project' : PAGE_TITLES[pathname];
    document.title = segment ? `${segment} – ${base}` : base;
  }, [pathname]);

  return null;
}

function App() {

  return (
    <BrowserRouter>
      <NavigationRegister />
      <PageTitleManager />
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
import React from 'react';
import { BrowserRouter, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { history } from './Utils/history'
const LoginPage = React.lazy(() => import("./LoginPage"))
const HomePage = React.lazy(() => import("./HomePage"))
const RequireAuth = React.lazy(() => import("./Auth/PrivateRoute"))
const PageNotFound = React.lazy(() => import("./PageNotFound"))
const ProjectPage = React.lazy(() => import("./Project/ProjectPage"))
const ProfilePage = React.lazy(() => import('./Profile/ProfilePage'))
const ActivateUserPage = React.lazy(() => import('./ActivateUserPage'))
const LanguageTranslationsPage = React.lazy(() => import('./Translation/LanguageTranslationsPage'))

// Set up the history object to be used in the app
function HistorySetter() {
  if (!history.navigate) {
    history.navigate = useNavigate();
    history.location = useLocation();
  }
  return null;
}

function App() {

  return (
    <BrowserRouter>
      <HistorySetter />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/activate" element={<ActivateUserPage />} />
        <Route path="/" element={<RequireAuth><HomePage /></RequireAuth>} />
        <Route path="/project/:id" element={<RequireAuth><ProjectPage /></RequireAuth>} />
        <Route path="/project/:project_id/language/:code" element={<RequireAuth><LanguageTranslationsPage /></RequireAuth>} />
        <Route path="/profile" element={<RequireAuth><ProfilePage /></RequireAuth>} />
        <Route path="*" element={<PageNotFound />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
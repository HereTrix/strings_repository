import { BrowserRouter, Route, Routes } from 'react-router-dom'
import LoginPage from "./LoginPage"
import HomePage from "./HomePage"
import RequireAuth from "./Auth/PrivateRoute";
import PageNotFound from "./PageNotFound";
import ProjectPage from "./Project/ProjectPage";
import ProfilePage from './Profile/ProfilePage';
import ActivateUserPage from './ActivateUserPage';
import LanguageTranslationsPage from './Translation/LanguageTranslationsPage';

function App() {
  return (
    <BrowserRouter>
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
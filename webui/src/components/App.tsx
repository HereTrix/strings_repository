import { BrowserRouter, Route, Routes } from 'react-router-dom'
import LoginPage from "./LoginPage"
import HomePage from "./HomePage"
import RequireAuth from "./Auth/PrivateRoute";
import PageNotFound from "./PageNotFound";
import ProjectPage from "./Project/ProjectPage";
import TranslationPage from './Translation/TranslationPage';
import ProfilePage from './Profile/ProfilePage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<RequireAuth><HomePage /></RequireAuth>} />
        <Route path="/project/:id" element={<RequireAuth><ProjectPage /></RequireAuth>} />
        <Route path="/project/:project_id/language/:code" element={<RequireAuth><TranslationPage /></RequireAuth>} />
        <Route path="/profile" element={<RequireAuth><ProfilePage /></RequireAuth>} />
        <Route path="*" element={<PageNotFound />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
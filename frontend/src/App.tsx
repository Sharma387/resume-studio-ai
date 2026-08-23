import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import AdminLayout from './components/admin/AdminLayout';
import Home from './pages/Home';
import ReviewPage from './pages/ReviewPage';
import ReviewGuard from './components/ReviewGuard';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import ProfilePage from './pages/ProfilePage';
import TemplateGalleryPage from './pages/TemplateGalleryPage';
import TemplateDesignerPage from './pages/TemplateDesignerPage';
import DashboardPage from './pages/admin/DashboardPage';
import AIConfigPage from './pages/admin/AIConfigPage';
import DatabasePage from './pages/admin/DatabasePage';
import StoragePage from './pages/admin/StoragePage';
import FeaturesPage from './pages/admin/FeaturesPage';
import HealthPage from './pages/admin/HealthPage';
import ParseTestPage from './pages/admin/ParseTestPage';
import StorageManagementPage from './pages/admin/StorageManagementPage';
import DevelopmentPage from './pages/admin/DevelopmentPage';
import ConfigurationDiagnosticsPage from './pages/admin/ConfigurationDiagnosticsPage';
import UsersPage from './pages/admin/UsersPage';

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/landing" element={<Home />} />

          {/* Protected routes */}
          <Route path="/" element={<ProtectedRoute><Home /></ProtectedRoute>} />
          <Route path="/review" element={<ProtectedRoute><ReviewGuard><ReviewPage /></ReviewGuard></ProtectedRoute>} />
          <Route path="/profile" element={<ProtectedRoute><ProfilePage /></ProtectedRoute>} />
          <Route path="/templates" element={<ProtectedRoute><TemplateGalleryPage /></ProtectedRoute>} />
          <Route path="/designer" element={<ProtectedRoute><TemplateDesignerPage /></ProtectedRoute>} />

          {/* Admin routes (protected + require_admin checked on backend) */}
          <Route path="/admin" element={<ProtectedRoute><AdminLayout /></ProtectedRoute>}>
            <Route index element={<DashboardPage />} />
            <Route path="users" element={<UsersPage />} />
            <Route path="ai" element={<AIConfigPage />} />
            <Route path="parse-test" element={<ParseTestPage />} />
            <Route path="database" element={<DatabasePage />} />
            <Route path="storage" element={<StoragePage />} />
            <Route path="storage-management" element={<StorageManagementPage />} />
            <Route path="features" element={<FeaturesPage />} />
            <Route path="health" element={<HealthPage />} />
            <Route path="development" element={<DevelopmentPage />} />
            <Route path="configuration" element={<ConfigurationDiagnosticsPage />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;

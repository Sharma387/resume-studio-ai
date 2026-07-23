import { Typography } from '@mui/material';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Home from './pages/Home';
import ReviewPage from './pages/ReviewPage';
import DashboardPage from './pages/DashboardPage';
import DashboardLayout from './components/dashboard/DashboardLayout';

function PlaceholderPage({ title }: { title: string }) {
  return <Typography variant="h5" sx={{ fontWeight: 700 }}>{title}</Typography>;
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Legacy route (backward compatible) */}
        <Route path="/landing" element={<Home />} />

        {/* New workspace routes */}
        <Route path="/" element={<DashboardLayout><DashboardPage /></DashboardLayout>} />
        <Route path="/resumes" element={<DashboardLayout><ReviewPage /></DashboardLayout>} />
        <Route path="/review" element={<DashboardLayout><ReviewPage /></DashboardLayout>} />
        <Route path="/cover-letters" element={<DashboardLayout><PlaceholderPage title="Cover Letters" /></DashboardLayout>} />
        <Route path="/applications" element={<DashboardLayout><PlaceholderPage title="Applications" /></DashboardLayout>} />
        <Route path="/interview" element={<DashboardLayout><PlaceholderPage title="Interview Prep" /></DashboardLayout>} />
        <Route path="/settings" element={<DashboardLayout><PlaceholderPage title="Settings" /></DashboardLayout>} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;

import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from '@/components/Layout';
import Dashboard from '@/pages/Dashboard';
import IncidentsPage from '@/pages/IncidentsPage';
import ConfigPage from '@/pages/ConfigPage';
import PluginsPage from '@/pages/PluginsPage';
import EnvironmentPage from '@/pages/EnvironmentPage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/incidents" element={<IncidentsPage />} />
          <Route path="/config" element={<ConfigPage />} />
          <Route path="/plugins" element={<PluginsPage />} />
          <Route path="/environment" element={<EnvironmentPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;

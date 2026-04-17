import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider } from './utils/ThemeContext';
import { ToastProvider } from './components/Toast/ToastContext';
import { Sidebar } from './components/SideBar/SideBar';
import { Header } from './components/Header/Header';
import { LiteratureSearch } from './pages/Search';
import { LiteratureSearchTask } from './pages/SearchTask';
import { LiteratureSearchResult } from './pages/SearchResult';
import { RecentFiles } from './pages/Files';
import { GlobalWatermark } from './components/GlobalWatermark/GlobalWatermark'
import './styles/global.css';
import './styles/LargeScreenLayout.css';

function App() {
  return (
    <ThemeProvider>
      <ToastProvider>
        <Router>
          <Routes>
            {/* Main app pages with Sidebar and Header */}
            <Route
              path="/*"
              element={
                <div className="app-container">
                  <GlobalWatermark />
                  <Sidebar>
                    <main className="main-content">
                      <Header />
                      <Routes>
                        <Route path="/" element={<LiteratureSearch />} />
                        <Route path="/search" element={<LiteratureSearch />} />
                        <Route path="/search/task" element={<LiteratureSearchTask />} />
                        <Route path="/search/result" element={<LiteratureSearchResult />} />
                        <Route path="/files" element={<RecentFiles />} />
                      </Routes>
                    </main>
                  </Sidebar>
                </div>
              }
            />
          </Routes>
        </Router>
      </ToastProvider>
    </ThemeProvider>
  );
}

export default App;

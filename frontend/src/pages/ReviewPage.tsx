import { useState, useEffect, useCallback } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Button,
  CircularProgress,
  Alert,
  IconButton,
  Toolbar,
  AppBar,
  Drawer,
} from '@mui/material';
import ArrowBack from '@mui/icons-material/ArrowBack';
import SaveOutlined from '@mui/icons-material/SaveOutlined';
import CancelOutlined from '@mui/icons-material/CancelOutlined';
import PersonOutlined from '@mui/icons-material/PersonOutlined';
import DescriptionOutlined from '@mui/icons-material/DescriptionOutlined';
import CodeOutlined from '@mui/icons-material/CodeOutlined';
import BusinessCenterOutlined from '@mui/icons-material/BusinessCenterOutlined';
import SchoolOutlined from '@mui/icons-material/SchoolOutlined';
import VerifiedOutlined from '@mui/icons-material/VerifiedOutlined';
import FolderOutlined from '@mui/icons-material/FolderOutlined';
import PictureAsPdfOutlined from '@mui/icons-material/PictureAsPdfOutlined';
import DownloadOutlined from '@mui/icons-material/DownloadOutlined';
import TravelExploreOutlined from '@mui/icons-material/TravelExploreOutlined';
import HistoryOutlined from '@mui/icons-material/HistoryOutlined';
import type { Resume } from '../types/resume';
import { fetchResume, saveResume, generatePdf, getPdfDownloadUrl } from '../services/resumeService';
import SectionNav from '../components/review/SectionNav';
import PersonalInfoSection from '../components/review/PersonalInfoSection';
import SummarySection from '../components/review/SummarySection';
import SkillsSection from '../components/review/SkillsSection';
import ExperienceSection from '../components/review/ExperienceSection';
import EducationSection from '../components/review/EducationSection';
import CertificationsSection from '../components/review/CertificationsSection';
import ProjectsSection from '../components/review/ProjectsSection';
import MatchSection from '../components/review/MatchSection';
import VersionHistory from '../components/review/VersionHistory';
import type { NavItem } from '../components/review/SectionNav';

const sections: NavItem[] = [
  { id: 'personal', label: 'Personal Info', icon: <PersonOutlined fontSize="small" /> },
  { id: 'summary', label: 'Summary', icon: <DescriptionOutlined fontSize="small" /> },
  { id: 'skills', label: 'Skills', icon: <CodeOutlined fontSize="small" /> },
  { id: 'experience', label: 'Experience', icon: <BusinessCenterOutlined fontSize="small" /> },
  { id: 'education', label: 'Education', icon: <SchoolOutlined fontSize="small" /> },
  { id: 'projects', label: 'Projects', icon: <FolderOutlined fontSize="small" /> },
  { id: 'certifications', label: 'Certifications', icon: <VerifiedOutlined fontSize="small" /> },
  { id: 'match', label: 'ATS Match', icon: <TravelExploreOutlined fontSize="small" /> },
];

function ReviewPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const fileParam = searchParams.get('file');

  const [resume, setResume] = useState<Resume | null>(null);
  const [original, setOriginal] = useState<Resume | null>(null);
  const [activeSection, setActiveSection] = useState('personal');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [pdfGenerating, setPdfGenerating] = useState(false);
  const [pdfReady, setPdfReady] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!fileParam) {
      setError('No resume file specified');
      setLoading(false);
      return;
    }
    setLoading(true);
    fetchResume(fileParam)
      .then((res) => {
        setResume(res.data);
        setOriginal(JSON.parse(JSON.stringify(res.data)) as Resume);
      })
      .catch(() => setError('Failed to load resume'))
      .finally(() => setLoading(false));
  }, [fileParam]);

  const hasChanges = useCallback(() => {
    if (!resume || !original) return false;
    return JSON.stringify(resume) !== JSON.stringify(original);
  }, [resume, original]);

  const handleSave = async () => {
    if (!resume || !fileParam) return;
    setSaving(true);
    try {
      const result = await saveResume(fileParam, resume);
      setOriginal(JSON.parse(JSON.stringify(result.data)) as Resume);
    } catch {
      setError('Failed to save resume');
    } finally {
      setSaving(false);
    }
  };

  const handleGeneratePdf = async () => {
    if (!fileParam) return;
    setPdfGenerating(true);
    try {
      await generatePdf(fileParam);
      setPdfReady(true);
    } catch {
      setError('Failed to generate PDF');
    } finally {
      setPdfGenerating(false);
    }
  };

  const handleCancel = () => {
    if (original) setResume(JSON.parse(JSON.stringify(original)) as Resume);
  };

  const handleResumeUpdated = () => {
    if (fileParam) {
      fetchResume(fileParam).then((res) => {
        setResume(res.data);
        setOriginal(JSON.parse(JSON.stringify(res.data)) as Resume);
      });
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 4 }}>
        <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>
        <Button onClick={() => navigate('/')}>Back to Home</Button>
      </Box>
    );
  }

  if (!resume) return null;

  const changed = hasChanges();

  return (
    <Box sx={{ height: '100vh', display: 'flex', flexDirection: 'column', bgcolor: 'background.default' }}>
      <AppBar position="static" elevation={0} sx={{ bgcolor: 'background.paper', borderBottom: 1, borderColor: 'divider' }}>
        <Toolbar>
          <IconButton edge="start" onClick={() => navigate('/')} sx={{ mr: 1 }}>
            <ArrowBack />
          </IconButton>
          <Typography variant="h6" sx={{ fontWeight: 700, flexGrow: 1 }}>
            Review Resume
          </Typography>
          {changed && (
            <Typography variant="caption" sx={{ color: 'warning.main', mr: 2 }}>
              Unsaved changes
            </Typography>
          )}
          <Button
            variant="outlined"
            startIcon={<CancelOutlined />}
            onClick={handleCancel}
            disabled={!changed}
            sx={{ mr: 1, textTransform: 'none', borderRadius: 2 }}
          >
            Cancel
          </Button>
          <Button
            variant="contained"
            startIcon={saving ? <CircularProgress size={16} /> : <SaveOutlined />}
            onClick={handleSave}
            disabled={!changed || saving}
            sx={{ textTransform: 'none', borderRadius: 2, mr: 1 }}
          >
            {saving ? 'Saving...' : 'Save'}
          </Button>
          {!pdfReady ? (
            <Button
              variant="outlined"
              startIcon={pdfGenerating ? <CircularProgress size={16} /> : <PictureAsPdfOutlined />}
              onClick={handleGeneratePdf}
              disabled={pdfGenerating}
              sx={{ textTransform: 'none', borderRadius: 2, mr: 1 }}
            >
              {pdfGenerating ? 'Generating...' : 'Generate PDF'}
            </Button>
          ) : (
            <Button
              variant="contained"
              color="success"
              startIcon={<DownloadOutlined />}
              component="a"
              href={getPdfDownloadUrl(fileParam || '')}
              download
              sx={{ textTransform: 'none', borderRadius: 2, mr: 1 }}
            >
              Download PDF
            </Button>
          )}
          <IconButton onClick={() => setHistoryOpen(true)} sx={{ color: 'text.secondary' }}>
            <HistoryOutlined />
          </IconButton>
        </Toolbar>
      </AppBar>

      <Drawer anchor="right" open={historyOpen} onClose={() => setHistoryOpen(false)}
        slotProps={{ paper: { sx: { width: 340, p: 2 } } }}>
        <VersionHistory resumeId={fileParam || ''} onRestored={handleResumeUpdated} />
      </Drawer>

      <Box sx={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <SectionNav items={sections} active={activeSection} onChange={setActiveSection} />

        <Box sx={{ flex: 1, overflow: 'auto', p: { xs: 2, md: 4 } }}>
          <Box sx={{ maxWidth: 800, mx: 'auto' }}>
            {activeSection === 'personal' && <PersonalInfoSection resume={resume} onChange={setResume} />}
            {activeSection === 'summary' && <SummarySection resume={resume} onChange={setResume} />}
            {activeSection === 'skills' && <SkillsSection resume={resume} onChange={setResume} />}
            {activeSection === 'experience' && <ExperienceSection resume={resume} onChange={setResume} />}
            {activeSection === 'education' && <EducationSection resume={resume} onChange={setResume} />}
            {activeSection === 'certifications' && <CertificationsSection resume={resume} onChange={setResume} />}
            {activeSection === 'projects' && <ProjectsSection resume={resume} onChange={setResume} />}
            {activeSection === 'match' && <MatchSection resumeId={fileParam || ''} onResumeUpdated={handleResumeUpdated} />}
          </Box>
        </Box>
      </Box>
    </Box>
  );
}

export default ReviewPage;

import { useState, useRef, type DragEvent, type ChangeEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Button,
  Chip,
  CircularProgress,
  LinearProgress,
  Snackbar,
  Alert,
} from '@mui/material';
import CloudUploadOutlined from '@mui/icons-material/CloudUploadOutlined';
import InsertDriveFileOutlined from '@mui/icons-material/InsertDriveFileOutlined';
import CheckCircleOutlined from '@mui/icons-material/CheckCircleOutlined';
import ErrorOutlined from '@mui/icons-material/ErrorOutlined';
import { useThemeMode } from '../contexts/useThemeMode';
import {
  uploadResume,
  extractResume,
  parseResume,
  type UploadProgress,
  type ExtractData,
} from '../services/uploadService';
import ExtractResultCard from './ExtractResultCard';

const SUPPORTED_FORMATS = ['PDF'];
const MAX_SIZE_MB = 10;

type UploadStatus = 'idle' | 'dragging' | 'uploading' | 'extracting' | 'parsing' | 'success' | 'error';

function UploadZone() {
  const { mode } = useThemeMode();
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const [status, setStatus] = useState<UploadStatus>('idle');
  const [fileName, setFileName] = useState('');
  const [fileSize, setFileSize] = useState(0);
  const [errorMsg, setErrorMsg] = useState('');
  const [progress, setProgress] = useState(0);
  const [extractData, setExtractData] = useState<ExtractData | null>(null);
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false,
    message: '',
    severity: 'success',
  });

  const reset = () => {
    setStatus('idle');
    setFileName('');
    setFileSize(0);
    setErrorMsg('');
    setProgress(0);
    setExtractData(null);
  };

  const handleProgress = (p: UploadProgress) => {
    setProgress(p.percent);
  };

  const uploadFile = async (file: File) => {
    const ext = file.name.split('.').pop()?.toLowerCase() ?? '';
    if (ext !== 'pdf') {
      setStatus('error');
      setErrorMsg('Only PDF files are accepted.');
      return;
    }

    if (file.size > MAX_SIZE_MB * 1024 * 1024) {
      setStatus('error');
      setErrorMsg(`File exceeds ${MAX_SIZE_MB}MB limit.`);
      return;
    }

    setStatus('uploading');
    setFileName(file.name);
    setFileSize(file.size);

    try {
      const uploadResult = await uploadResume(file, handleProgress);

      setStatus('extracting');
      setSnackbar({ open: true, message: 'Processing resume...', severity: 'success' });

      const extractResult = await extractResume(uploadResult.filename);
      setExtractData(extractResult.data);

      setStatus('parsing');
      const parseResult = await parseResume(extractResult.data.text, uploadResult.filename);
      setStatus('success');
      if (parseResult.id) {
        navigate(`/review?file=${parseResult.id}`);
      }
    } catch (err) {
      setStatus('error');
      const msg = err instanceof Error ? err.message : 'Processing failed';
      setErrorMsg(msg);
      setSnackbar({ open: true, message: msg, severity: 'error' });
    }
  };

  const handleDragOver = (e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (status === 'idle') setStatus('dragging');
  };

  const handleDragLeave = (e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (status === 'dragging') setStatus('idle');
  };

  const handleDrop = (e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const files = e.dataTransfer.files;
    if (files.length > 0) uploadFile(files[0]);
  };

  const handleFileSelect = (e: ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) uploadFile(files[0]);
    e.target.value = '';
  };

  const isDragging = status === 'dragging';

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <Box
      sx={{
        width: '100%',
        maxWidth: 560,
        mx: 'auto',
        animation: 'fadeIn 0.8s ease-out 0.1s both',
      }}
    >
      <Typography
        variant="h3"
        sx={{
          fontWeight: 700,
          mb: 1.5,
          fontSize: { xs: '1.75rem', sm: '2rem', md: '2.5rem' },
          color: 'text.primary',
        }}
      >
        Build a Better Resume
      </Typography>

      <Typography
        variant="body1"
        sx={{ color: 'text.secondary', mb: 4, maxWidth: 440, lineHeight: 1.7 }}
      >
        Upload your resume and let AI optimize it for ATS systems, improve your scoring, and land more interviews.
      </Typography>

      <input
        ref={inputRef}
        type="file"
        accept=".pdf"
        onChange={handleFileSelect}
        style={{ display: 'none' }}
      />

      <Box
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => status === 'idle' && inputRef.current?.click()}
        sx={{
          border: '2px dashed',
          borderColor:
            status === 'error'
              ? 'error.main'
              : isDragging
                ? 'primary.main'
                : mode === 'dark'
                  ? 'rgba(255,255,255,0.15)'
                  : 'rgba(0,0,0,0.15)',
          borderRadius: 4,
          p: { xs: 4, sm: 5 },
          mb: 2.5,
          textAlign: 'center',
          background:
            status === 'error'
              ? 'rgba(244,67,54,0.06)'
              : isDragging
                ? 'rgba(124, 77, 255, 0.08)'
                : mode === 'dark'
                  ? 'rgba(255,255,255,0.02)'
                  : 'rgba(0,0,0,0.02)',
          transition: 'all 0.3s ease',
          cursor: status === 'idle' ? 'pointer' : 'default',
          '&:hover': {
            borderColor: status === 'idle' ? 'primary.main' : undefined,
            background:
              status === 'idle'
                ? mode === 'dark'
                  ? 'rgba(124, 77, 255, 0.06)'
                  : 'rgba(124, 77, 255, 0.04)'
                : undefined,
          },
        }}
      >
        {status === 'uploading' && (
          <Box sx={{ mb: 2 }}>
            <CircularProgress
              size={48}
              variant="determinate"
              value={progress}
              sx={{ color: 'primary.main', mb: 1 }}
            />
            <Typography variant="body2" sx={{ color: 'text.secondary', mb: 0.5 }}>
              Uploading {fileName}
            </Typography>
            <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mb: 1 }}>
              {progress}% · {formatSize(fileSize)}
            </Typography>
            <LinearProgress
              variant="determinate"
              value={progress}
              sx={{ borderRadius: 1, maxWidth: 280, mx: 'auto' }}
            />
          </Box>
        )}

        {status === 'extracting' && (
          <Box sx={{ mb: 2 }}>
            <CircularProgress size={48} sx={{ color: 'primary.main', mb: 1 }} />
            <Typography variant="body2" sx={{ color: 'text.secondary', mb: 0.5 }}>
              Extracting text from {fileName}...
            </Typography>
            <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block' }}>
              Analyzing document structure
            </Typography>
          </Box>
        )}

        {status === 'parsing' && (
          <Box sx={{ mb: 2 }}>
            <CircularProgress size={48} sx={{ color: 'primary.main', mb: 1 }} />
            <Typography variant="body2" sx={{ color: 'text.secondary', mb: 0.5 }}>
              Parsing resume data...
            </Typography>
            <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block' }}>
              Extracting structured information
            </Typography>
          </Box>
        )}

        {status === 'success' && (
          <Box sx={{ animation: 'fadeIn 0.5s ease-out' }}>
            <Box
              sx={{
                width: 72,
                height: 72,
                borderRadius: '50%',
                background: 'rgba(76, 175, 80, 0.15)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                mx: 'auto',
                mb: 2,
              }}
            >
              <CheckCircleOutlined sx={{ fontSize: 36, color: 'success.main' }} />
            </Box>
            <Typography variant="h6" sx={{ fontWeight: 600, mb: 0.5, color: 'text.primary' }}>
              Resume Processed
            </Typography>
            <Typography variant="body2" sx={{ color: 'text.secondary', mb: 0.5 }}>
              {fileName}
            </Typography>
            <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mb: 2 }}>
              {formatSize(fileSize)}
            </Typography>
            <Button
              variant="outlined"
              size="small"
              onClick={(e) => { e.stopPropagation(); reset(); }}
              sx={{ textTransform: 'none', borderRadius: 2 }}
            >
              Upload Another
            </Button>
          </Box>
        )}

        {status === 'error' && (
          <Box>
            <Box
              sx={{
                width: 72,
                height: 72,
                borderRadius: '50%',
                background: 'rgba(244, 67, 54, 0.15)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                mx: 'auto',
                mb: 2,
              }}
            >
              <ErrorOutlined sx={{ fontSize: 36, color: 'error.main' }} />
            </Box>
            <Typography variant="h6" sx={{ fontWeight: 600, mb: 0.5, color: 'text.primary' }}>
              Processing Failed
            </Typography>
            <Typography variant="body2" sx={{ color: 'error.main', mb: 2 }}>
              {errorMsg}
            </Typography>
            <Button
              variant="outlined"
              size="small"
              onClick={(e) => { e.stopPropagation(); reset(); }}
              sx={{ textTransform: 'none', borderRadius: 2 }}
            >
              Try Again
            </Button>
          </Box>
        )}

        {(status === 'idle' || isDragging) && (
          <>
            <Box
              sx={{
                width: 72,
                height: 72,
                borderRadius: '50%',
                background: 'linear-gradient(135deg, rgba(124,77,255,0.15) 0%, rgba(0,229,255,0.15) 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                mx: 'auto',
                mb: 2,
                transition: 'transform 0.3s ease',
                transform: isDragging ? 'scale(1.1)' : 'scale(1)',
              }}
            >
              <CloudUploadOutlined
                sx={{
                  fontSize: 36,
                  color: 'primary.main',
                  animation: isDragging ? 'none' : 'float 3s ease-in-out infinite',
                }}
              />
            </Box>

            <Typography variant="h6" sx={{ fontWeight: 600, mb: 0.5, color: 'text.primary' }}>
              {isDragging ? 'Drop your file here' : 'Upload Your Resume'}
            </Typography>

            <Typography variant="body2" sx={{ color: 'text.secondary', mb: 2 }}>
              Drag & drop your PDF or click to browse
            </Typography>

            <Box sx={{ display: 'flex', gap: 1, justifyContent: 'center', flexWrap: 'wrap' }}>
              {SUPPORTED_FORMATS.map((fmt) => (
                <Chip
                  key={fmt}
                  icon={<InsertDriveFileOutlined sx={{ fontSize: 16 }} />}
                  label={fmt}
                  size="small"
                  variant="outlined"
                  sx={{
                    borderColor: mode === 'dark' ? 'rgba(255,255,255,0.15)' : 'rgba(0,0,0,0.15)',
                    color: 'text.secondary',
                    fontWeight: 500,
                    borderRadius: 1,
                  }}
                />
              ))}
              <Chip
                label={`Max ${MAX_SIZE_MB}MB`}
                size="small"
                variant="outlined"
                sx={{
                  borderColor: mode === 'dark' ? 'rgba(255,255,255,0.15)' : 'rgba(0,0,0,0.15)',
                  color: 'text.secondary',
                  fontWeight: 500,
                  borderRadius: 1,
                }}
              />
            </Box>
          </>
        )}
      </Box>

      {status === 'idle' && (
        <Button
          variant="contained"
          size="large"
          fullWidth
          onClick={() => inputRef.current?.click()}
          sx={{
            py: 1.6,
            borderRadius: 3,
            background: 'linear-gradient(135deg, #7c4dff 0%, #00e5ff 100%)',
            fontSize: '1rem',
            fontWeight: 600,
            textTransform: 'none',
            '&:hover': {
              background: 'linear-gradient(135deg, #6c3df0 0%, #00d0e6 100%)',
              boxShadow: '0 8px 32px rgba(124, 77, 255, 0.3)',
            },
          }}
        >
          Choose File
        </Button>
      )}

      {extractData && <ExtractResultCard data={extractData} />}

      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={() => setSnackbar((s) => ({ ...s, open: false }))}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          onClose={() => setSnackbar((s) => ({ ...s, open: false }))}
          severity={snackbar.severity}
          variant="filled"
          sx={{ borderRadius: 2 }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}

export default UploadZone;

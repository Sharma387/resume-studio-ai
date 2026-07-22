import { useState } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  IconButton,
  Button,
  Chip,
} from '@mui/material';
import ContentCopyOutlined from '@mui/icons-material/ContentCopyOutlined';
import CheckOutlined from '@mui/icons-material/CheckOutlined';
import KeyboardArrowUp from '@mui/icons-material/KeyboardArrowUp';
import KeyboardArrowDown from '@mui/icons-material/KeyboardArrowDown';
import type { ExtractData } from '../services/uploadService';

interface ExtractResultCardProps {
  data: ExtractData;
}

function ExtractResultCard({ data }: ExtractResultCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);
  const textPreview = data.text.slice(0, 1000);
  const isTruncated = data.text.length > 1000;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(data.text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // fallback
    }
  };

  return (
    <Card
      sx={{
        mt: 3,
        p: 2.5,
        animation: 'fadeIn 0.5s ease-out',
      }}
    >
      <CardContent sx={{ p: 0, '&:last-child': { pb: 0 } }}>
        <Typography variant="h6" sx={{ fontWeight: 600, mb: 2, color: 'text.primary' }}>
          Extract Results
        </Typography>

        <Box sx={{ display: 'flex', gap: 1.5, mb: 2, flexWrap: 'wrap' }}>
          <Chip
            label={`${data.pages} page${data.pages !== 1 ? 's' : ''}`}
            color="primary"
            variant="outlined"
            size="small"
          />
          <Chip
            label={`${data.characters.toLocaleString()} characters`}
            color="primary"
            variant="outlined"
            size="small"
          />
        </Box>

        <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1, color: 'text.secondary' }}>
          Text Preview
        </Typography>

        <Box
          sx={{
            position: 'relative',
            background: (t) => (t.palette.mode === 'dark' ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)'),
            borderRadius: 2,
            p: 2,
            maxHeight: expanded ? 'none' : 200,
            overflow: expanded ? 'visible' : 'hidden',
            transition: 'max-height 0.3s ease',
            fontFamily: 'monospace',
            fontSize: '0.85rem',
            lineHeight: 1.6,
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
            color: 'text.primary',
          }}
        >
          {textPreview}
          {expanded && isTruncated && data.text.slice(1000)}

          {!expanded && isTruncated && (
            <Box
              sx={{
                position: 'absolute',
                bottom: 0,
                left: 0,
                right: 0,
                height: 60,
                background: 'linear-gradient(transparent, rgba(0,0,0,0.6))',
                borderRadius: '0 0 8px 8px',
              }}
            />
          )}
        </Box>

        <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 1.5 }}>
          <Box sx={{ display: 'flex', gap: 1 }}>
            {isTruncated && (
              <Button
                size="small"
                onClick={() => setExpanded(!expanded)}
                startIcon={expanded ? <KeyboardArrowUp /> : <KeyboardArrowDown />}
                sx={{ textTransform: 'none', borderRadius: 2 }}
              >
                {expanded ? 'Collapse' : `Show all (${data.characters.toLocaleString()} chars)`}
              </Button>
            )}
          </Box>

          <IconButton
            size="small"
            onClick={handleCopy}
            sx={{ color: copied ? 'success.main' : 'text.secondary' }}
          >
            {copied ? <CheckOutlined fontSize="small" /> : <ContentCopyOutlined fontSize="small" />}
          </IconButton>
        </Box>
      </CardContent>
    </Card>
  );
}

export default ExtractResultCard;

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box, Card, CardContent, Typography, TextField, Button, Alert, Tabs, Tab, CircularProgress,
  IconButton,
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import { useAuth } from '../contexts/AuthContext';
import { authFetch } from '../services/authFetch';
import API_URL from '../config';

export default function ProfilePage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [tab, setTab] = useState(0);

  // Change password
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const changePassword = async () => {
    setMessage(null);
    if (newPassword !== confirmPassword) {
      setMessage({ type: 'error', text: 'Passwords do not match' });
      return;
    }
    setSaving(true);
    try {
      const res = await authFetch(`${API_URL}/auth/me/password`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
      });
      const body = await res.json();
      if (body.success) {
        setMessage({ type: 'success', text: 'Password updated successfully' });
        setCurrentPassword('');
        setNewPassword('');
        setConfirmPassword('');
      } else {
        setMessage({ type: 'error', text: body.detail || 'Failed to update password' });
      }
    } catch (e) {
      setMessage({ type: 'error', text: String(e) });
    }
    setSaving(false);
  };

  return (
    <Box sx={{ maxWidth: 600, mx: 'auto', py: 4, px: 2 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
        <IconButton onClick={() => navigate(-1)} size="small"><ArrowBackIcon /></IconButton>
        <Typography variant="h4" sx={{ fontWeight: 700 }}>Profile</Typography>
      </Box>

      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 3 }}>
        <Tab label="My Profile" />
        <Tab label="Security" />
      </Tabs>

      {tab === 0 && (
        <Card>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 2 }}>Account Information</Typography>
            {[
              ['Name', user?.full_name],
              ['Email', user?.email],
              ['Role', user?.role],
              ['User ID', user?.id],
            ].map(([label, value]) => (
              <Box key={label} sx={{ display: 'flex', justifyContent: 'space-between', py: 1 }}>
                <Typography color="text.secondary">{label}</Typography>
                <Typography sx={{ fontWeight: 600 }}>{value || '—'}</Typography>
              </Box>
            ))}
          </CardContent>
        </Card>
      )}

      {tab === 1 && (
        <Card>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 2 }}>Change Password</Typography>
            {message && <Alert severity={message.type} sx={{ mb: 2 }}>{message.text}</Alert>}
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <TextField label="Current Password" type="password" size="small"
                value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} fullWidth />
              <TextField label="New Password" type="password" size="small"
                value={newPassword} onChange={(e) => setNewPassword(e.target.value)} fullWidth
                helperText="Minimum 12 characters, uppercase, lowercase, digit, special character" />
              <TextField label="Confirm New Password" type="password" size="small"
                value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} fullWidth />
              <Button variant="contained" onClick={changePassword} disabled={saving}
                sx={{ alignSelf: 'flex-start' }}>
                {saving ? <CircularProgress size={20} /> : 'Update Password'}
              </Button>
            </Box>
          </CardContent>
        </Card>
      )}
    </Box>
  );
}

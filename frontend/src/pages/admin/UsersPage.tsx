import { useState, useEffect, useCallback } from 'react';
import {
  Box, Typography, Button, TextField, Select, MenuItem, FormControl, InputLabel,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper,
  Chip, CircularProgress, Alert, Dialog, DialogTitle, DialogContent,
  DialogActions, IconButton, Tooltip, TablePagination,
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import BlockIcon from '@mui/icons-material/Block';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ArrowUpwardIcon from '@mui/icons-material/ArrowUpward';
import ArrowDownwardIcon from '@mui/icons-material/ArrowDownward';
import LockResetIcon from '@mui/icons-material/LockReset';
import VisibilityIcon from '@mui/icons-material/Visibility';
import { authFetch } from '../../services/authFetch';
import API_URL from '../../config';
import type { AdminUser, UserListResponse } from '../../types/user';

export default function UsersPage() {
  const [data, setData] = useState<UserListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [page, setPage] = useState(0);
  const [pageSize] = useState(20);
  const [error, setError] = useState<string | null>(null);

  // View dialog
  const [viewUser, setViewUser] = useState<AdminUser | null>(null);

  // Password reset dialog
  const [pwdDialogOpen, setPwdDialogOpen] = useState(false);
  const [pwdUserId, setPwdUserId] = useState<string | null>(null);
  const [tempPwd, setTempPwd] = useState<string | null>(null);
  const [customPwd, setCustomPwd] = useState('');
  const [pwdSaving, setPwdSaving] = useState(false);

  // Confirmation dialog
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmAction, setConfirmAction] = useState<{ label: string; url: string } | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ page: String(page + 1), page_size: String(pageSize) });
      if (search) params.set('search', search);
      if (roleFilter) params.set('role', roleFilter);
      const res = await authFetch(`${API_URL}/admin/users?${params}`);
      let body: any = {};
      try { body = await res.json(); } catch { body = { success: false, detail: 'Empty response' }; }
      if (!res.ok) { setError(body.detail || 'Failed to load'); return; }
      if (body.success) setData(body.data);
    } catch (e) { setError(String(e)); }
    setLoading(false);
  }, [page, pageSize, search, roleFilter]);

  useEffect(() => { load(); }, [load]);

  const doAction = async (path: string, method = 'POST') => {
    setError(null);
    try {
      const res = await authFetch(`${API_URL}${path}`, { method });
      let body: any = {};
      try { body = await res.json(); } catch { body = { success: false, detail: 'Empty response from server' }; }
      if (!res.ok) { setError(body.detail || `Request failed: ${res.status}`); return; }
      if (!body.success) { setError(body.detail || 'Action failed'); }
      await load();
    } catch (e) { setError(String(e)); }
  };

  const confirmThenAction = (label: string, url: string) => {
    setConfirmAction({ label, url });
    setConfirmOpen(true);
  };

  const executeConfirmedAction = async () => {
    if (!confirmAction) return;
    setConfirmOpen(false);
    await doAction(confirmAction.url);
    setConfirmAction(null);
  };

  const openResetPwd = (userId: string) => {
    setPwdUserId(userId);
    setTempPwd(null);
    setCustomPwd('');
    setPwdDialogOpen(true);
  };

  const executeResetPwd = async (useCustom: boolean) => {
    if (!pwdUserId) return;
    setPwdSaving(true);
    setError(null);
    try {
      const body: any = {};
      if (useCustom && customPwd) body.custom_password = customPwd;
      const res = await authFetch(`${API_URL}/admin/users/${pwdUserId}/reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      let data: any = {};
      try { data = await res.json(); } catch { data = { success: false, detail: 'Empty response' }; }
      if (!res.ok) { setError(data.detail || `Request failed: ${res.status}`); setPwdSaving(false); return; }
      if (data.success && data.data) {
        setTempPwd(data.data.temporary_password);
        await load();
      } else { setError(data.detail || 'Reset failed'); }
    } catch (e) { setError(String(e)); }
    setPwdSaving(false);
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h5" sx={{ fontWeight: 700 }}>Users</Typography>
        <Button startIcon={<RefreshIcon />} onClick={load}>Refresh</Button>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>}

      <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
        <TextField size="small" placeholder="Search name or email..." value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(0); }} sx={{ minWidth: 280 }} />
        <FormControl size="small" sx={{ minWidth: 140 }}>
          <InputLabel>Role</InputLabel>
          <Select value={roleFilter} label="Role" onChange={(e) => { setRoleFilter(e.target.value); setPage(0); }}>
            <MenuItem value="">All</MenuItem>
            <MenuItem value="admin">Admin</MenuItem>
            <MenuItem value="user">User</MenuItem>
          </Select>
        </FormControl>
      </Box>

      {loading ? <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}><CircularProgress /></Box> : data ? (
        <>
          <TableContainer component={Paper} variant="outlined">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 700 }}>Name</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>Email</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>Role</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>Status</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>Created</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>Last Login</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data.users.map((u) => (
                  <TableRow key={u.id} hover>
                    <TableCell sx={{ fontWeight: 600 }}>{u.full_name}</TableCell>
                    <TableCell>{u.email}</TableCell>
                    <TableCell><Chip size="small" color={u.role === 'admin' ? 'primary' : 'default'} label={u.role} /></TableCell>
                    <TableCell><Chip size="small" color={u.disabled ? 'error' : 'success'} label={u.disabled ? 'Disabled' : 'Active'} /></TableCell>
                    <TableCell>{u.created_at?.slice(0, 10)}</TableCell>
                    <TableCell>{u.last_login_at?.slice(0, 10) || '—'}</TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', gap: 0.5 }}>
                        <Tooltip title="View"><IconButton size="small" onClick={() => setViewUser(u)}><VisibilityIcon fontSize="small" /></IconButton></Tooltip>
                        {!u.disabled ? (
                          <Tooltip title="Disable"><IconButton size="small" onClick={() => confirmThenAction('Disable', `/admin/users/${u.id}/disable`)}><BlockIcon fontSize="small" color="error" /></IconButton></Tooltip>
                        ) : (
                          <Tooltip title="Enable"><IconButton size="small" onClick={() => confirmThenAction('Enable', `/admin/users/${u.id}/enable`)}><CheckCircleIcon fontSize="small" color="success" /></IconButton></Tooltip>
                        )}
                        {u.role === 'user' ? (
                          <Tooltip title="Promote to Admin"><IconButton size="small" onClick={() => confirmThenAction('Promote to Admin', `/admin/users/${u.id}/promote`)}><ArrowUpwardIcon fontSize="small" color="primary" /></IconButton></Tooltip>
                        ) : (
                          <Tooltip title="Demote to User"><IconButton size="small" onClick={() => confirmThenAction('Demote to User', `/admin/users/${u.id}/demote`)}><ArrowDownwardIcon fontSize="small" /></IconButton></Tooltip>
                        )}
                        <Tooltip title="Reset Password"><IconButton size="small" onClick={() => openResetPwd(u.id)}><LockResetIcon fontSize="small" /></IconButton></Tooltip>
                      </Box>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
          <TablePagination component="div" count={data.total} page={page} onPageChange={(_, p) => setPage(p)}
            rowsPerPage={pageSize} rowsPerPageOptions={[pageSize]} />
        </>
      ) : null}

      {/* View User Dialog */}
      <Dialog open={!!viewUser} onClose={() => setViewUser(null)} maxWidth="sm" fullWidth>
        <DialogTitle>User Details</DialogTitle>
        <DialogContent>
          {viewUser && (
            <Box sx={{ pt: 1 }}>
              {[
                ['Name', viewUser.full_name],
                ['Email', viewUser.email],
                ['Role', viewUser.role],
                ['Status', viewUser.disabled ? 'Disabled' : 'Active'],
                ['Must Change Password', viewUser.must_change_password ? 'Yes' : 'No'],
                ['Created', viewUser.created_at],
                ['Last Login', viewUser.last_login_at || '—'],
                ['Last Password Change', viewUser.last_password_change || '—'],
              ].map(([label, value]) => (
                <Box key={label} sx={{ display: 'flex', justifyContent: 'space-between', py: 0.5 }}>
                  <Typography variant="body2" color="text.secondary">{label}</Typography>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>{value as string}</Typography>
                </Box>
              ))}
            </Box>
          )}
        </DialogContent>
        <DialogActions><Button onClick={() => setViewUser(null)}>Close</Button></DialogActions>
      </Dialog>

      {/* Confirmation Dialog */}
      <Dialog open={confirmOpen} onClose={() => setConfirmOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle>Confirm Action</DialogTitle>
        <DialogContent>
          <Typography>Are you sure you want to {confirmAction?.label?.toLowerCase()} this user?</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmOpen(false)}>Cancel</Button>
          <Button variant="contained" color="warning" onClick={executeConfirmedAction}>Confirm</Button>
        </DialogActions>
      </Dialog>

      {/* Password Reset Dialog */}
      <Dialog open={pwdDialogOpen} onClose={() => { if (!pwdSaving) setPwdDialogOpen(false); }} maxWidth="sm" fullWidth>
        <DialogTitle>Reset Password</DialogTitle>
        <DialogContent>
          {!tempPwd ? (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}>
              <Typography variant="subtitle2">Option 1: Generate system password</Typography>
              <Button variant="outlined" onClick={() => executeResetPwd(false)} disabled={pwdSaving} fullWidth>
                {pwdSaving ? 'Generating...' : 'Generate Secure Password'}
              </Button>

              <Box sx={{ borderTop: 1, borderColor: 'divider', my: 1 }} />

              <Typography variant="subtitle2">Option 2: Set custom password</Typography>
              <TextField size="small" type="password" label="Custom Password" fullWidth
                value={customPwd} onChange={(e) => setCustomPwd(e.target.value)}
                helperText="Min 12 chars, uppercase, lowercase, digit, special" />
              <Button variant="contained" onClick={() => executeResetPwd(true)}
                disabled={pwdSaving || !customPwd} fullWidth>
                {pwdSaving ? 'Applying...' : 'Set Custom Password'}
              </Button>
            </Box>
          ) : (
            <Box sx={{ pt: 1 }}>
              <Alert severity="warning" sx={{ mb: 2 }}>
                Copy this password now. It will not be shown again.
              </Alert>
              <Paper variant="outlined" sx={{ p: 2, textAlign: 'center', bgcolor: 'grey.100' }}>
                <Typography variant="h5" sx={{ fontFamily: 'monospace', fontWeight: 700, letterSpacing: 2 }}>
                  {tempPwd}
                </Typography>
              </Paper>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          {tempPwd ? (
            <Button onClick={() => { navigator.clipboard.writeText(tempPwd || ''); setPwdDialogOpen(false); }} variant="contained">
              Copy & Close
            </Button>
          ) : (
            <Button onClick={() => setPwdDialogOpen(false)} disabled={pwdSaving}>Cancel</Button>
          )}
        </DialogActions>
      </Dialog>
    </Box>
  );
}

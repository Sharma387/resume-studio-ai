import { Box, Typography, List, ListItemButton, ListItemText, Divider } from '@mui/material';

export interface NavItem {
  id: string;
  label: string;
  icon: React.ReactNode;
}

interface SectionNavProps {
  items: NavItem[];
  active: string;
  onChange: (id: string) => void;
}

function SectionNav({ items, active, onChange }: SectionNavProps) {
  return (
    <Box
      sx={{
        width: 240,
        flexShrink: 0,
        borderRight: '1px solid',
        borderColor: 'divider',
        height: '100%',
        overflow: 'auto',
        display: { xs: 'none', md: 'block' },
      }}
    >
      <Box sx={{ px: 2, py: 2 }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 700, color: 'text.primary' }}>
          Sections
        </Typography>
      </Box>
      <Divider />
      <List dense>
        {items.map((item) => (
          <ListItemButton
            key={item.id}
            selected={active === item.id}
            onClick={() => onChange(item.id)}
            sx={{
              px: 2,
              py: 1.2,
              '&.Mui-selected': {
                bgcolor: 'primary.main',
                color: 'primary.contrastText',
                '&:hover': { bgcolor: 'primary.dark' },
                '& .MuiListItemText-primary': { color: 'primary.contrastText', fontWeight: 600 },
              },
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mr: 1, color: active === item.id ? 'inherit' : 'text.secondary' }}>
              {item.icon}
            </Box>
            <ListItemText primary={item.label} />
          </ListItemButton>
        ))}
      </List>
    </Box>
  );
}

export default SectionNav;

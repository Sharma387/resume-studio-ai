export interface AdminUser {
  id: string;
  email: string;
  full_name: string;
  role: string;
  status: string;
  disabled: boolean;
  must_change_password: boolean;
  created_at: string;
  last_login: string | null;
  last_login_at: string | null;
  last_password_change: string | null;
}

export interface UserListResponse {
  users: AdminUser[];
  total: number;
  page: number;
  page_size: number;
}

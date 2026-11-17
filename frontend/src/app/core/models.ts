export type Role = 'admin' | 'member';

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  role: Role;
  must_change_password: boolean;
}

export interface CurrentUser {
  id: number;
  username: string;
  email: string | null;
  role: Role;
  is_active: boolean;
  must_change_password: boolean;
  member_id: number | null;
  full_name: string | null;
}

export interface TrainerBrief {
  id: number;
  full_name: string;
  mobile: string;
  specialization: string | null;
}

export type MembershipState = 'active' | 'expired' | 'upcoming' | 'none';

export interface Member {
  id: number;
  member_code: string;
  full_name: string;
  mobile: string;
  email: string | null;
  gender: 'male' | 'female' | 'other' | null;
  date_of_birth: string | null;
  address: string | null;
  photo_url: string | null;
  joining_date: string;
  trainer_id: number | null;
  trainer: TrainerBrief | null;
  status: 'active' | 'inactive';
  created_at: string;
  updated_at: string;
  membership_state?: MembershipState;
  current_expiry_date?: string | null;
  current_package_name?: string | null;
}

export interface Trainer {
  id: number;
  trainer_code: string;
  full_name: string;
  mobile: string;
  email: string | null;
  specialization: string | null;
  experience_years: number | null;
  notes: string | null;
  status: 'active' | 'inactive';
  assigned_members: number;
}

export type DurationUnit = 'days' | 'months';

export interface Package {
  id: number;
  name: string;
  duration_value: number;
  duration_unit: DurationUnit;
  price: string;
  description: string | null;
  is_active?: boolean;
}

export type SubscriptionState = 'upcoming' | 'active' | 'expired' | 'suspended' | 'cancelled';

export interface MemberBrief {
  id: number;
  member_code: string;
  full_name: string;
  mobile: string;
}

export interface Subscription {
  id: number;
  member_id: number;
  member: MemberBrief;
  package_id: number;
  package_name: string;
  duration_value: number;
  duration_unit: DurationUnit;
  start_date: string;
  expiry_date: string;
  amount: string;
  amount_paid: string;
  status: 'active' | 'suspended' | 'cancelled';
  state: SubscriptionState;
  remaining_days: number;
  renewed_from_id: number | null;
  notes: string | null;
  created_at: string;
}

export type PaymentMethod = 'cash' | 'upi' | 'card' | 'bank_transfer' | 'cheque' | 'other';
export type PaymentStatus = 'paid' | 'pending' | 'failed' | 'refunded';
export const PAYMENT_METHODS: PaymentMethod[] = ['cash', 'upi', 'card', 'bank_transfer', 'cheque', 'other'];
export const PAYMENT_STATUSES: PaymentStatus[] = ['paid', 'pending', 'failed', 'refunded'];

export interface Payment {
  id: number;
  member_id: number;
  member: MemberBrief;
  subscription_id: number | null;
  package_name: string | null;
  amount: string;
  payment_date: string;
  method: PaymentMethod;
  reference: string | null;
  status: PaymentStatus;
  notes: string | null;
  created_at: string;
}

export interface PaymentSummary {
  year: number;
  month: number;
  total_paid: string;
  count_paid: number;
  total_pending: string;
  count_pending: number;
  by_method: Record<string, string>;
}

export interface Attendance {
  id: number;
  member_id: number;
  member: MemberBrief;
  attendance_date: string;
  checked_in_at: string;
  source: 'qr' | 'manual';
}

export interface AppNotification {
  id: number;
  type: 'expiry_reminder' | 'expired' | 'general';
  title: string;
  body: string;
  subscription_id: number | null;
  read_at: string | null;
  created_at: string;
}

export interface AdminDashboard {
  as_of: string;
  year: number;
  month: number;
  total_members: number;
  active_members: number;
  expired_members: number;
  inactive_accounts: number;
  todays_attendance: number;
  total_trainers: number;
  monthly_revenue: string;
  new_members_this_month: number;
  upcoming_expiries: Subscription[];
  recently_expired: Subscription[];
}

export interface MemberDashboard {
  as_of: string;
  profile: Member;
  current_subscription: Subscription | null;
  upcoming_subscription: Subscription | null;
  latest_subscription: Subscription | null;
  remaining_days: number;
  checked_in_today: boolean;
  todays_checkin: Attendance | null;
  total_attendance: number;
  attendance_this_month: number;
  recent_notifications: AppNotification[];
  unread_notifications: number;
}

export interface Policy {
  gym_name: string;
  timezone: string;
  gym_day_start_hour: number;
  today: string;
  attendance_max_checkins_per_day: number;
  attendance_require_active_subscription: boolean;
  qr_token_ttl_seconds: number;
  reminder_days_before_expiry: number[];
  member_editable_fields: string[];
}

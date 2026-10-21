export type Role = "rh" | "lider" | "instrutor" | "funcionario";

export type AppUser = {
  id: number;
  name: string;
  email: string;
  role: Role;
  leader_id: number | null;
  must_change_password: boolean;
  face_enrolled: boolean;
  is_active: boolean;
};

export type StatItem = {
  label: string;
  value: string;
  hint?: string;
};

export type TrainingSummary = {
  id: number;
  title: string;
  date: string;
  start_time: string;
  end_time: string;
  location: string;
  status: string;
  instructor: string;
  seats: number;
  reserved: number;
  available: number;
  workload_hours: number;
  attendance_count?: number;
  certificate_count?: number;
};

export type TeamMember = {
  id: number;
  name: string;
  email: string;
  face_enrolled: boolean;
  must_change_password: boolean;
};

export type ReservationSummary = {
  id: number;
  training_id: number;
  title: string;
  date: string;
  start_time: string;
  location: string;
  status: string;
  instructor: string;
};

export type CertificateSummary = {
  id: number;
  title: string;
  code: string;
  issued_at: string;
  date: string;
  workload_hours: number;
};

export type HomeData = {
  role: Role;
  stats: StatItem[];
  trainings?: TrainingSummary[];
  team?: TeamMember[];
  reservations?: ReservationSummary[];
  certificates?: CertificateSummary[];
  people_count?: number;
  today?: string;
};

export type AuthResponse = {
  user: AppUser;
  next_step: string;
  dev_mode?: boolean;
};

export type MeResponse = AuthResponse & {
  dev_mode: boolean;
};

export type CertificateVerification = {
  valid: boolean;
  holder_name: string;
  training_title: string;
  training_date: string;
  workload_hours: number;
  code: string;
  issued_at: string;
};

export type PersonRecord = {
  id: number;
  name: string;
  email: string;
  role: Role;
  leader_id: number | null;
  leader_name: string | null;
  must_change_password: boolean;
  face_enrolled: boolean;
  is_active: boolean;
  last_login_at: string | null;
  created_at: string;
};

export type PersonOption = {
  id: number;
  name: string;
  email: string;
};

export type RhOptions = {
  leaders: PersonOption[];
  instructors: PersonOption[];
};

export type PeopleData = {
  people: PersonRecord[];
  total: number;
  active: number;
};

export type TrainingRecord = TrainingSummary & {
  description: string;
  instructor_id: number;
  end_time: string;
  reservation_count: number;
  attendance_count: number;
  certificate_count: number;
  can_edit: boolean;
  can_cancel: boolean;
  can_delete: boolean;
  team_reserved_ids?: number[];
};

export type TrainingsData = {
  trainings: TrainingRecord[];
};

export type OutboxMessage = {
  id: number;
  recipient: string;
  subject: string;
  body: string;
  created_at: string;
  sent: boolean;
  error: string | null;
};

export type OutboxData = {
  emails: OutboxMessage[];
  smtp_enabled: boolean;
  dev_mode: boolean;
};

export type LeaderReservationItem = {
  id: number;
  employee_id: number;
  employee_name: string;
  training_id: number;
  title: string;
  date: string;
  start_time: string;
  end_time: string;
  location: string;
  instructor: string;
  training_status: string;
  status: string;
  created_at: string;
  cancelled_at: string | null;
};

export type LeaderReservationsData = {
  team: TeamMember[];
  trainings: TrainingRecord[];
  reservations: LeaderReservationItem[];
  today: string;
};

export type FaceConsentSection = {
  heading: string;
  body: string;
};

export type FaceConsentTerm = {
  version: string;
  updated_at: string;
  title: string;
  summary: string;
  sections: FaceConsentSection[];
};

export type FaceEnrollmentStatus = {
  term: {
    current_version: string;
    accepted: boolean;
    accepted_at: string | null;
    needs_acceptance: boolean;
  };
  enrollment: {
    samples: number;
    required: number;
    complete: boolean;
    can_capture: boolean;
  };
  model: {
    name: string;
    provider: string;
    preload: boolean;
    loaded: boolean;
  };
};

export type FaceSampleResponse = {
  status: FaceEnrollmentStatus;
  sample: {
    index: number;
    quality: number;
    message: string;
  };
};

export type AttendanceMethod = "face" | "manual";

export type AttendanceRecord = {
  id: number;
  employee_id: number;
  method: AttendanceMethod;
  score: number | null;
  justification: string | null;
  recorded_at: string;
  instructor: string;
};

export type CallCertificate = {
  id: number;
  employee_id: number;
  employee_name: string;
  code: string;
  issued_at: string;
};

export type CallParticipant = {
  employee_id: number;
  name: string;
  email: string;
  face_enrolled: boolean;
  status: "presente" | "pendente";
  attendance: AttendanceRecord | null;
  certificate: CallCertificate | null;
};

export type CallCompletion = {
  can_complete: boolean;
  blocked_reason: string | null;
  warnings: string[];
  reserved: number;
  present: number;
  pending: number;
  eligible_count: number;
  certificate_count: number;
  completed_at: string | null;
};

export type InstructorCallData = {
  training: {
    id: number;
    title: string;
    description: string;
    date: string;
    start_time: string;
    end_time: string;
    location: string;
    status: string;
    instructor: string;
    reserved: number;
    certificate_count: number;
    completed_at: string | null;
  };
  participants: CallParticipant[];
  summary: {
    reserved: number;
    present: number;
    pending: number;
    face: number;
    manual: number;
  };
  recognition: {
    enrolled_candidates: number;
    threshold: number;
    margin: number;
  };
  completion: CallCompletion;
  can_record: boolean;
  blocked_reason: string | null;
  is_today: boolean;
};

export type AttendanceMutationResponse = {
  ok: boolean;
  already_recorded?: boolean;
  employee: {
    id: number;
    name: string;
    email: string;
    face_enrolled: boolean;
  };
  attendance: AttendanceRecord;
  summary: InstructorCallData["summary"];
};

export type TrainingCompletionResponse = {
  ok: boolean;
  certificates_issued: number;
  certificates: CallCertificate[];
  training: InstructorCallData["training"];
  completion: CallCompletion;
};

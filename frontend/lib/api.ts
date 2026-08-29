import { supabase } from "./supabase";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export type CloudProvider = "aws" | "azure" | "gcp";

export interface ServiceRow {
  service_name: string;
  total_cost_usd: number;
  line_item_count: number;
  default_tier: 1 | 2 | 3;
}

export interface UploadCsvResponse {
  upload_id: string;
  cloud_provider: CloudProvider;
  service_count: number;
  services: ServiceRow[];
  warnings: string[];
}

export interface EssentialService {
  service_name: string;
  tier: 1 | 2 | 3;
  notes?: string;
}

export interface RunPipelineResponse {
  report_id: string;
  status: string;
  estimated_seconds: number;
}

export interface PipelineStatusResponse {
  report_id: string;
  status: string;
}

export interface ReportSummary {
  id: string;
  upload_id: string;
  status: string;
  total_savings_min: number | null;
  total_savings_max: number | null;
  prescription_count: number | null;
  conflict_count: number | null;
  created_at: string;
  expires_at: string | null;
}

export interface Prescription {
  id: string;
  report_id: string;
  service_name: string;
  anomaly_score: number;
  pattern_id: string;
  recommended_action: string;
  savings_min: number;
  savings_max: number;
  engineering_hours: number;
  risk_level: "Low" | "Medium" | "High";
  failure_cost_estimate: number | null;
  roi_score: number;
  rank_position: number;
  is_conflicted: boolean;
  conflict_reason: string | null;
  tier: 1 | 2 | 3;
}

export interface ReportDetail extends ReportSummary {
  prescriptions: Prescription[];
}

/** Thrown for any non-2xx response, carrying the backend's {error, detail, code} shape. */
export class ApiError extends Error {
  code: number;
  errorType: string;
  constructor(detail: string, code: number, errorType: string) {
    super(detail);
    this.code = code;
    this.errorType = errorType;
  }
}

// Single-tenant mode: there's no login/signup UI anymore, so there's usually
// no Supabase session at all. The backend's DEFAULT_USER_ID fallback
// (backend/api/auth.py) handles that -- omit the header rather than block
// the request. If a session DOES exist (e.g. a leftover one from before this
// change), still send it so nothing regresses for that case.
async function authHeader(): Promise<Record<string, string>> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    let errorType = "http_error";
    try {
      const body = await res.json();
      detail = body.detail || detail;
      errorType = body.error || errorType;
    } catch {
      // non-JSON error body; fall back to statusText
    }
    throw new ApiError(detail, res.status, errorType);
  }
  return res.json() as Promise<T>;
}

export async function getMe(): Promise<{ user_id: string; email: string }> {
  const headers = await authHeader();
  const res = await fetch(`${API_BASE_URL}/auth/me`, { headers });
  return handleResponse(res);
}

export async function uploadCsv(file: File, cloudProvider: CloudProvider): Promise<UploadCsvResponse> {
  const headers = await authHeader();
  const form = new FormData();
  form.append("file", file);
  form.append("cloud_provider", cloudProvider);
  const res = await fetch(`${API_BASE_URL}/upload/csv`, {
    method: "POST",
    headers,
    body: form,
  });
  return handleResponse(res);
}

export async function getUploadServices(uploadId: string): Promise<UploadCsvResponse> {
  const headers = await authHeader();
  const res = await fetch(`${API_BASE_URL}/upload/${uploadId}/services`, { headers });
  return handleResponse(res);
}

export async function runPipeline(
  uploadId: string,
  essentialServices: EssentialService[]
): Promise<RunPipelineResponse> {
  const headers = await authHeader();
  const res = await fetch(`${API_BASE_URL}/pipeline/run`, {
    method: "POST",
    headers: { ...headers, "Content-Type": "application/json" },
    body: JSON.stringify({ upload_id: uploadId, essential_services: essentialServices }),
  });
  return handleResponse(res);
}

export async function getPipelineStatus(reportId: string): Promise<PipelineStatusResponse> {
  const headers = await authHeader();
  const res = await fetch(`${API_BASE_URL}/pipeline/${reportId}/status`, { headers });
  return handleResponse(res);
}

export async function listReports(): Promise<{ reports: ReportSummary[] }> {
  const headers = await authHeader();
  const res = await fetch(`${API_BASE_URL}/reports`, { headers });
  return handleResponse(res);
}

export async function getReport(reportId: string): Promise<ReportDetail> {
  const headers = await authHeader();
  const res = await fetch(`${API_BASE_URL}/reports/${reportId}`, { headers });
  return handleResponse(res);
}

export async function deleteReport(reportId: string): Promise<{ report_id: string; deleted: boolean }> {
  const headers = await authHeader();
  const res = await fetch(`${API_BASE_URL}/reports/${reportId}`, {
    method: "DELETE",
    headers,
  });
  return handleResponse(res);
}

/** Downloads the report PDF and triggers a browser save via a throwaway object URL. */
export async function downloadReportPdf(reportId: string): Promise<void> {
  const headers = await authHeader();
  const res = await fetch(`${API_BASE_URL}/reports/${reportId}/pdf`, { headers });
  if (!res.ok) {
    throw new ApiError(`Failed to download PDF (${res.status})`, res.status, "http_error");
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `cliprx-report-${reportId}.pdf`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

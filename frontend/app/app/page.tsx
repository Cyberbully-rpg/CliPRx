"use client";

import { useState } from "react";
import Sidebar from "@/components/dashboard/Sidebar";
import UploadScreen from "@/components/dashboard/UploadScreen";
import TiersScreen from "@/components/dashboard/TiersScreen";
import PipelineScreen from "@/components/dashboard/PipelineScreen";
import ReportsScreen from "@/components/dashboard/ReportsScreen";
import DetailScreen from "@/components/dashboard/DetailScreen";
import {
  ApiError,
  CloudProvider,
  ReportDetail,
  ReportSummary,
  ServiceRow,
  deleteReport,
  downloadReportPdf,
  getReport,
  listReports,
  runPipeline,
  uploadCsv,
} from "@/lib/api";

type Screen = "upload" | "tiers" | "pipeline" | "reports" | "detail";

function errMessage(e: unknown): string {
  if (e instanceof ApiError) return e.message;
  if (e instanceof Error) return e.message;
  return "Something went wrong.";
}

export default function AppDashboard() {
  const [screen, setScreen] = useState<Screen>("upload");

  // upload
  const [provider, setProvider] = useState<CloudProvider>("aws");
  const [file, setFile] = useState<File | null>(null);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  // tiers
  const [uploadId, setUploadId] = useState<string | null>(null);
  const [services, setServices] = useState<ServiceRow[]>([]);
  // Non-fatal parse notices from the backend (e.g. a FOCUS export naming a cloud
  // provider we have no pattern library for). Shown on the tier screen, since
  // that's where the user is deciding what the analysis will cover.
  const [uploadWarnings, setUploadWarnings] = useState<string[]>([]);
  const [tiers, setTiers] = useState<Record<string, 1 | 2 | 3>>({});
  const [runLoading, setRunLoading] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);

  // pipeline
  const [pipelineDone, setPipelineDone] = useState(false);

  // reports
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [reportsLoading, setReportsLoading] = useState(false);
  const [reportsError, setReportsError] = useState<string | null>(null);

  // detail
  const [reportId, setReportId] = useState<string | null>(null);
  const [reportDetail, setReportDetail] = useState<ReportDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);

  function resetUploadFlow() {
    setFile(null);
    setUploadId(null);
    setServices([]);
    setUploadWarnings([]);
    setTiers({});
    setUploadError(null);
    setRunError(null);
    setScreen("upload");
  }

  async function handleContinueUpload() {
    if (!file) return;
    setUploadLoading(true);
    setUploadError(null);
    try {
      const res = await uploadCsv(file, provider);
      setUploadId(res.upload_id);
      setServices(res.services);
      setUploadWarnings(res.warnings ?? []);
      const initialTiers: Record<string, 1 | 2 | 3> = {};
      res.services.forEach((s) => (initialTiers[s.service_name] = s.default_tier));
      setTiers(initialTiers);
      setScreen("tiers");
    } catch (e) {
      setUploadError(errMessage(e));
    } finally {
      setUploadLoading(false);
    }
  }

  function setTier(serviceName: string, tier: 1 | 2 | 3) {
    setTiers((s) => ({ ...s, [serviceName]: tier }));
  }

  async function handleRunPipeline() {
    if (!uploadId) return;
    setRunLoading(true);
    setRunError(null);
    setPipelineDone(false);
    setScreen("pipeline");
    try {
      const essentialServices = services.map((s) => ({
        service_name: s.service_name,
        tier: tiers[s.service_name] ?? s.default_tier,
      }));
      const res = await runPipeline(uploadId, essentialServices);
      setPipelineDone(true);
      const detail = await getReport(res.report_id);
      setReportId(res.report_id);
      setReportDetail(detail);
      setTimeout(() => setScreen("detail"), 500);
    } catch (e) {
      setRunError(errMessage(e));
      setScreen("tiers");
    } finally {
      setRunLoading(false);
    }
  }

  async function loadReports() {
    setReportsLoading(true);
    setReportsError(null);
    try {
      const res = await listReports();
      setReports(res.reports);
    } catch (e) {
      setReportsError(errMessage(e));
    } finally {
      setReportsLoading(false);
    }
  }

  function goReports() {
    setScreen("reports");
    loadReports();
  }

  async function openReport(id: string) {
    setScreen("detail");
    setDetailLoading(true);
    setDetailError(null);
    setReportDetail(null);
    setReportId(id);
    try {
      const detail = await getReport(id);
      setReportDetail(detail);
    } catch (e) {
      setDetailError(errMessage(e));
    } finally {
      setDetailLoading(false);
    }
  }

  async function handleDownloadPdf() {
    if (!reportId) return;
    setPdfLoading(true);
    setDetailError(null);
    try {
      await downloadReportPdf(reportId);
    } catch (e) {
      setDetailError(errMessage(e));
    } finally {
      setPdfLoading(false);
    }
  }

  async function handleDeleteReport() {
    if (!reportId) return;
    setDeleteLoading(true);
    setDetailError(null);
    try {
      await deleteReport(reportId);
      goReports();
    } catch (e) {
      setDetailError(errMessage(e));
    } finally {
      setDeleteLoading(false);
    }
  }

  return (
    <div className="d-shell">
      <Sidebar
        screen={screen}
        goUpload={resetUploadFlow}
        goReports={goReports}
      />
      <main className="d-main">
        {screen === "upload" && (
          <UploadScreen
            provider={provider}
            setProvider={setProvider}
            file={file}
            setFile={setFile}
            onContinue={handleContinueUpload}
            loading={uploadLoading}
            error={uploadError}
          />
        )}
        {screen === "tiers" && (
          <TiersScreen
            services={services}
            warnings={uploadWarnings}
            tiers={tiers}
            setTier={setTier}
            onBack={() => setScreen("upload")}
            onRun={handleRunPipeline}
            loading={runLoading}
            error={runError}
          />
        )}
        {screen === "pipeline" && (
          <PipelineScreen serviceCount={services.length} provider={provider} done={pipelineDone} />
        )}
        {screen === "reports" && (
          <ReportsScreen
            reports={reports}
            loading={reportsLoading}
            error={reportsError}
            onOpen={openReport}
            onNew={resetUploadFlow}
          />
        )}
        {screen === "detail" && (
          <DetailScreen
            report={reportDetail}
            loading={detailLoading}
            error={detailError}
            onBack={goReports}
            onDownloadPdf={handleDownloadPdf}
            onDelete={handleDeleteReport}
            pdfLoading={pdfLoading}
            deleteLoading={deleteLoading}
          />
        )}
      </main>
    </div>
  );
}

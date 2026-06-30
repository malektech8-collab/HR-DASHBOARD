import React, { useEffect, useState } from 'react';
import { GovernanceWidget } from '../components/widgets/GovernanceWidget';
import { 
  fetchCommandCenterOverview,
  fetchCommandCenterModuleHealth,
  fetchCommandCenterPriorityAlerts,
  fetchCommandCenterExceptions,
  fetchCommandCenterDataFreshness,
  fetchCommandCenterNavigationStatus,
  fetchCommandCenterQaIndex
} from '../lib/api';
import type { 
  CommandCenterOverviewData,
  ModuleHealthItem,
  PriorityAlertItem,
  ExceptionSummaryItem,
  FreshnessItem,
  NavigationStatusItem,
  QaIndexItem
} from '../lib/types';
import { 
  Shield, 
  ShieldAlert, 
  ShieldCheck, 
  Users, 
  CreditCard, 
  Clock, 
  Scale, 
  UserPlus, 
  Star, 
  AlertTriangle, 
  Activity, 
  Calendar, 
  RefreshCw, 
  ExternalLink,
  ChevronRight,
  Database,
  FileText,
  Image,
  Layers,
  Sparkles
} from 'lucide-react';

interface CommandCenterProps {
  onNavigate: (page: string) => void;
}

export const CommandCenter: React.FC<CommandCenterProps> = ({ onNavigate }) => {
  const [overview, setOverview] = useState<CommandCenterOverviewData | null>(null);
  const [modules, setModules] = useState<ModuleHealthItem[]>([]);
  const [alerts, setAlerts] = useState<PriorityAlertItem[]>([]);
  const [exceptions, setExceptions] = useState<ExceptionSummaryItem[]>([]);
  const [freshness, setFreshness] = useState<FreshnessItem[]>([]);
  const [navStatus, setNavStatus] = useState<NavigationStatusItem[]>([]);
  const [qaIndex, setQaIndex] = useState<QaIndexItem[]>([]);
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  async function loadData() {
    try {
      setLoading(true);
      setError(null);
      const [
        overviewData,
        modulesData,
        alertsData,
        exceptionsData,
        freshnessData,
        navData,
        qaData
      ] = await Promise.all([
        fetchCommandCenterOverview(),
        fetchCommandCenterModuleHealth(),
        fetchCommandCenterPriorityAlerts(),
        fetchCommandCenterExceptions(),
        fetchCommandCenterDataFreshness(),
        fetchCommandCenterNavigationStatus(),
        fetchCommandCenterQaIndex()
      ]);
      
      setOverview(overviewData);
      setModules(modulesData.modules);
      setAlerts(alertsData.alerts);
      setExceptions(exceptionsData.exceptions);
      setFreshness(freshnessData.freshness);
      setNavStatus(navData.navigation);
      setQaIndex(qaData.qa_index);
      console.debug("Navigation targets loaded:", navData.navigation.length);
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'Failed to connect to backend FastAPI services.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[500px] gap-4 text-muted-foreground">
        <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
        <p className="text-sm font-semibold tracking-wider uppercase animate-pulse">Assembling Command Center...</p>
      </div>
    );
  }

  if (error || !overview) {
    return (
      <div className="bg-destructive/5 border border-destructive/20 rounded-xl p-8 max-w-lg mx-auto text-center my-16 text-foreground">
        <ShieldAlert className="w-16 h-16 text-destructive mx-auto mb-6 animate-bounce" />
        <h3 className="text-xl font-bold tracking-tight">API Handshake Failed</h3>
        <p className="text-sm text-muted-foreground mt-3 leading-relaxed">
          {error || 'The Command Center is unable to query backend service status. Ensure FastAPI is running.'}
        </p>
        <button
          onClick={loadData}
          className="mt-8 px-5 py-2.5 bg-primary text-primary-foreground rounded-lg font-semibold text-xs uppercase tracking-wider hover:opacity-90 transition shadow-md"
        >
          Retry Connection
        </button>
      </div>
    );
  }

  // Format currency
  const formatSAR = (value: number) => {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'SAR', maximumFractionDigits: 0 }).format(value);
  };

  // Helper for status indicators
  const getStatusBadge = (status: 'Healthy' | 'Warning' | 'Critical' | 'Unknown') => {
    switch (status) {
      case 'Healthy':
        return <span className="px-2 py-0.5 text-[11px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-md">Healthy</span>;
      case 'Warning':
        return <span className="px-2 py-0.5 text-[11px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20 rounded-md animate-pulse">Warning</span>;
      case 'Critical':
        return <span className="px-2 py-0.5 text-[11px] font-semibold bg-red-500/10 text-red-400 border border-red-500/20 rounded-md animate-pulse">Critical</span>;
      default:
        return <span className="px-2 py-0.5 text-[11px] font-semibold bg-slate-500/10 text-slate-400 border border-slate-500/20 rounded-md">Unknown</span>;
    }
  };

  // Map module icon
  const getModuleIcon = (key: string) => {
    switch (key) {
      case 'executive': return <Activity className="w-5 h-5 text-indigo-400" />;
      case 'workforce': return <Users className="w-5 h-5 text-sky-400" />;
      case 'payroll': return <CreditCard className="w-5 h-5 text-teal-400" />;
      case 'attendance': return <Clock className="w-5 h-5 text-amber-400" />;
      case 'compliance': return <ShieldCheck className="w-5 h-5 text-emerald-400" />;
      case 'er': return <Scale className="w-5 h-5 text-purple-400" />;
      case 'recruitment': return <UserPlus className="w-5 h-5 text-pink-400" />;
      case 'talent': return <Star className="w-5 h-5 text-yellow-400" />;
      default: return <Shield className="w-5 h-5 text-slate-400" />;
    }
  };

  console.debug("navStatus", navStatus);

  return (
    <div className="space-y-8 pb-16">
      {/* 1. Header Row */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-card/40 backdrop-blur-md border border-border p-6 rounded-2xl">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-1.5 bg-primary/10 text-primary rounded-lg">
              <Layers className="w-5 h-5" />
            </span>
            <h1 className="text-2xl font-bold tracking-tight">HR Command Center</h1>
            <span className="px-2 py-0.5 text-[10px] uppercase font-bold tracking-widest bg-primary/20 text-primary rounded border border-primary/20">
              INTEGRATION LAYER
            </span>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Executive control panel & health monitor across all operational sub-dashboards.
          </p>
        </div>
        
        <div className="flex flex-wrap items-center gap-4 text-xs">
          <div className="flex items-center gap-2 bg-slate-900/40 px-3 py-2 rounded-xl border border-border">
            <Calendar className="w-3.5 h-3.5 text-muted-foreground" />
            <span className="text-muted-foreground">Report Month:</span>
            <span className="font-semibold">{overview.latest_source_business_date ? overview.latest_source_business_date.slice(0,7) : '2026-06'}</span>
          </div>
          <div className="flex items-center gap-2 bg-slate-900/40 px-3 py-2 rounded-xl border border-border">
            <Calendar className="w-3.5 h-3.5 text-muted-foreground" />
            <span className="text-muted-foreground">Business Cutoff:</span>
            <span className="font-semibold">{overview.latest_source_business_date || '2026-06-30'}</span>
          </div>
          <div className="flex items-center gap-2 bg-slate-900/40 px-3 py-2 rounded-xl border border-border">
            <RefreshCw className="w-3.5 h-3.5 text-muted-foreground animate-spin-slow" />
            <span className="text-muted-foreground">Warehouse Sync:</span>
            <span className="font-semibold text-emerald-400">
              {new Date(overview.last_data_refresh).toLocaleTimeString()}
            </span>
          </div>
        </div>
      </div>

      {/* Governance Gate Status */}
      <GovernanceWidget />

      {/* 2. Overview Cards Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
        {/* HC */}
        <button 
          onClick={() => onNavigate('workforce')} 
          className="group text-left p-4 bg-card/60 hover:bg-card border border-border hover:border-primary/40 rounded-xl hover:-translate-y-1 hover:shadow-lg transition-all duration-300 relative overflow-hidden"
        >
          <div className="absolute right-0 bottom-0 opacity-[0.02] group-hover:opacity-[0.05] transition-all">
            <Users className="w-24 h-24" />
          </div>
          <p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">Active Headcount</p>
          <div className="flex items-baseline gap-2 mt-2">
            <span className="text-2xl font-bold tracking-tight text-sky-400">{overview.active_headcount}</span>
            <span className="text-[10px] text-muted-foreground">employees</span>
          </div>
          <div className="flex items-center gap-1 text-[11px] text-sky-400/80 mt-2 font-medium">
            <span>Workforce summary</span>
            <ChevronRight className="w-3 h-3 group-hover:translate-x-1 transition-transform" />
          </div>
        </button>

        {/* Payroll */}
        <button 
          onClick={() => onNavigate('payroll')} 
          className="group text-left p-4 bg-card/60 hover:bg-card border border-border hover:border-primary/40 rounded-xl hover:-translate-y-1 hover:shadow-lg transition-all duration-300 relative overflow-hidden"
        >
          <div className="absolute right-0 bottom-0 opacity-[0.02] group-hover:opacity-[0.05] transition-all">
            <CreditCard className="w-24 h-24" />
          </div>
          <p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">Gross Payroll</p>
          <div className="flex items-baseline gap-1 mt-2">
            <span className="text-2xl font-bold tracking-tight text-teal-400">{formatSAR(overview.payroll_cost)}</span>
          </div>
          <div className="flex items-center gap-1 text-[11px] text-teal-400/80 mt-2 font-medium">
            <span>Payroll dashboard</span>
            <ChevronRight className="w-3 h-3 group-hover:translate-x-1 transition-transform" />
          </div>
        </button>

        {/* Attendance */}
        <button 
          onClick={() => onNavigate('attendance')} 
          className="group text-left p-4 bg-card/60 hover:bg-card border border-border hover:border-primary/40 rounded-xl hover:-translate-y-1 hover:shadow-lg transition-all duration-300 relative overflow-hidden"
        >
          <div className="absolute right-0 bottom-0 opacity-[0.02] group-hover:opacity-[0.05] transition-all">
            <Clock className="w-24 h-24" />
          </div>
          <p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">Attendance Compliance</p>
          <div className="flex items-baseline gap-1 mt-2">
            <span className="text-2xl font-bold tracking-tight text-amber-400">
              {(overview.attendance_compliance_pct * 100).toFixed(1)}%
            </span>
          </div>
          <div className="flex items-center gap-1 text-[11px] text-amber-400/80 mt-2 font-medium">
            <span>Attendance details</span>
            <ChevronRight className="w-3 h-3 group-hover:translate-x-1 transition-transform" />
          </div>
        </button>

        {/* Compliance */}
        <button 
          onClick={() => onNavigate('compliance')} 
          className="group text-left p-4 bg-card/60 hover:bg-card border border-border hover:border-primary/40 rounded-xl hover:-translate-y-1 hover:shadow-lg transition-all duration-300 relative overflow-hidden"
        >
          <div className="absolute right-0 bottom-0 opacity-[0.02] group-hover:opacity-[0.05] transition-all">
            <ShieldCheck className="w-24 h-24" />
          </div>
          <p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">Saudization Rate</p>
          <div className="flex items-baseline gap-1 mt-2">
            <span className="text-2xl font-bold tracking-tight text-emerald-400">
              {overview.saudization_pct.toFixed(1)}%
            </span>
          </div>
          <div className="flex items-center gap-1 text-[11px] text-emerald-400/80 mt-2 font-medium">
            <span>Saudization logs</span>
            <ChevronRight className="w-3 h-3 group-hover:translate-x-1 transition-transform" />
          </div>
        </button>

        {/* ER */}
        <button 
          onClick={() => onNavigate('er')} 
          className="group text-left p-4 bg-card/60 hover:bg-card border border-border hover:border-primary/40 rounded-xl hover:-translate-y-1 hover:shadow-lg transition-all duration-300 relative overflow-hidden"
        >
          <div className="absolute right-0 bottom-0 opacity-[0.02] group-hover:opacity-[0.05] transition-all">
            <Scale className="w-24 h-24" />
          </div>
          <p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">Open ER Cases</p>
          <div className="flex items-baseline gap-2 mt-2">
            <span className="text-2xl font-bold tracking-tight text-purple-400">{overview.open_er_cases}</span>
            <span className="text-[10px] text-muted-foreground">active</span>
          </div>
          <div className="flex items-center gap-1 text-[11px] text-purple-400/80 mt-2 font-medium">
            <span>Labor cases panel</span>
            <ChevronRight className="w-3 h-3 group-hover:translate-x-1 transition-transform" />
          </div>
        </button>

        {/* Recruitment */}
        <button 
          onClick={() => onNavigate('recruitment')} 
          className="group text-left p-4 bg-card/60 hover:bg-card border border-border hover:border-primary/40 rounded-xl hover:-translate-y-1 hover:shadow-lg transition-all duration-300 relative overflow-hidden"
        >
          <div className="absolute right-0 bottom-0 opacity-[0.02] group-hover:opacity-[0.05] transition-all">
            <UserPlus className="w-24 h-24" />
          </div>
          <p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">Open Requisitions</p>
          <div className="flex items-baseline gap-2 mt-2">
            <span className="text-2xl font-bold tracking-tight text-pink-400">{overview.open_requisitions}</span>
            <span className="text-[10px] text-muted-foreground">reqs</span>
          </div>
          <div className="flex items-center gap-1 text-[11px] text-pink-400/80 mt-2 font-medium">
            <span>Hiring dashboard</span>
            <ChevronRight className="w-3 h-3 group-hover:translate-x-1 transition-transform" />
          </div>
        </button>

        {/* Talent */}
        <button 
          onClick={() => onNavigate('talent')} 
          className="group text-left p-4 bg-card/60 hover:bg-card border border-border hover:border-primary/40 rounded-xl hover:-translate-y-1 hover:shadow-lg transition-all duration-300 relative overflow-hidden"
        >
          <div className="absolute right-0 bottom-0 opacity-[0.02] group-hover:opacity-[0.05] transition-all">
            <Star className="w-24 h-24" />
          </div>
          <p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">Talent Review Rate</p>
          <div className="flex items-baseline gap-1 mt-2">
            <span className="text-2xl font-bold tracking-tight text-yellow-400">
              {overview.review_completion_pct.toFixed(1)}%
            </span>
          </div>
          <div className="flex items-center gap-1 text-[11px] text-yellow-400/80 mt-2 font-medium">
            <span>Talent & succession</span>
            <ChevronRight className="w-3 h-3 group-hover:translate-x-1 transition-transform" />
          </div>
        </button>

        {/* Combined Exceptions */}
        <button 
          onClick={() => onNavigate('data-quality')} 
          className="group text-left p-4 bg-card/60 hover:bg-card border border-border hover:border-primary/40 rounded-xl hover:-translate-y-1 hover:shadow-lg transition-all duration-300 relative overflow-hidden"
        >
          <div className="absolute right-0 bottom-0 opacity-[0.02] group-hover:opacity-[0.05] transition-all">
            <AlertTriangle className="w-24 h-24" />
          </div>
          <p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">Active Exceptions</p>
          <div className="flex items-baseline gap-2 mt-2">
            <span className="text-2xl font-bold tracking-tight text-red-400">{overview.total_active_exceptions}</span>
            <span className="text-[10px] text-muted-foreground">issues</span>
          </div>
          <div className="flex items-center gap-1 text-[11px] text-red-400/80 mt-2 font-medium">
            <span>Exceptions list</span>
            <ChevronRight className="w-3 h-3 group-hover:translate-x-1 transition-transform" />
          </div>
        </button>

        {/* Modules Healthy */}
        <div className="p-4 bg-card/60 border border-border rounded-xl relative overflow-hidden">
          <p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">System Integration</p>
          <div className="flex items-baseline gap-2 mt-2">
            <span className="text-2xl font-bold tracking-tight text-emerald-400">
              {overview.modules_healthy}
            </span>
            <span className="text-sm font-semibold text-muted-foreground">/ 9 healthy</span>
          </div>
          <p className="text-[10px] text-muted-foreground mt-2 font-medium">All sub-modules monitored</p>
        </div>

        {/* DQ Score */}
        <button 
          onClick={() => onNavigate('data-quality')} 
          className="group text-left p-4 bg-card/60 hover:bg-card border border-border hover:border-primary/40 rounded-xl hover:-translate-y-1 hover:shadow-lg transition-all duration-300 relative overflow-hidden"
        >
          <div className="absolute right-0 bottom-0 opacity-[0.02] group-hover:opacity-[0.05] transition-all">
            <Shield className="w-24 h-24" />
          </div>
          <p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">Data Quality Score</p>
          <div className="flex items-baseline gap-1 mt-2">
            <span className="text-2xl font-bold tracking-tight text-indigo-400">
              {(overview.data_quality_score * 100).toFixed(1)}%
            </span>
          </div>
          <div className="flex items-center gap-1 text-[11px] text-indigo-400/80 mt-2 font-medium">
            <span>Quality assertions</span>
            <ChevronRight className="w-3 h-3 group-hover:translate-x-1 transition-transform" />
          </div>
        </button>
      </div>

      {/* 3. Module Health Grid Row */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold tracking-tight flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-primary animate-pulse" />
            Module Governance Registry
          </h2>
          <span className="text-xs text-muted-foreground">9 monitored sub-systems</span>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {modules.map((mod) => (
            <div 
              key={mod.module_key}
              className="bg-card/50 backdrop-blur-sm border border-border rounded-xl p-5 hover:shadow-md transition-all duration-200 flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between gap-2 border-b border-border/60 pb-3 mb-4">
                  <div className="flex items-center gap-2.5">
                    <span className="p-1.5 bg-slate-900/60 border border-border/80 rounded-lg">
                      {getModuleIcon(mod.module_key)}
                    </span>
                    <div>
                      <h4 className="font-bold text-sm tracking-tight text-foreground">{mod.module_label}</h4>
                      <p className="text-[10px] text-muted-foreground uppercase tracking-widest">{mod.owner_domain} OWNER</p>
                    </div>
                  </div>
                  {getStatusBadge(mod.status)}
                </div>

                <div className="grid grid-cols-2 gap-4 text-xs mb-6">
                  <div>
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Assertions & Metrics</p>
                    <p className="font-semibold text-foreground mt-0.5">{mod.primary_kpi_count} registered KPIs</p>
                  </div>
                  <div>
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Sync State</p>
                    <p className={`font-semibold mt-0.5 ${mod.stale_flag ? 'text-amber-400' : 'text-emerald-400'}`}>
                      {mod.stale_flag ? 'Stale Data' : 'Current'}
                    </p>
                  </div>
                  <div>
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider">API Connection</p>
                    <p className={`font-semibold mt-0.5 ${mod.api_health_status === 'Healthy' ? 'text-emerald-400' : 'text-red-400'}`}>
                      {mod.api_health_status}
                    </p>
                  </div>
                  <div>
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Exceptions Queue</p>
                    <p className="font-semibold text-foreground mt-0.5">
                      {mod.critical_exception_count} Critical / {mod.warning_exception_count} Warn
                    </p>
                  </div>
                </div>
              </div>

              {/* Action buttons/Links */}
              <div className="flex items-center justify-between border-t border-border/60 pt-4 mt-2 gap-2 flex-wrap">
                <button 
                  onClick={() => onNavigate(mod.module_key)}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-primary/10 text-primary hover:bg-primary hover:text-primary-foreground text-xs font-semibold rounded-lg transition"
                >
                  <span>Open Page</span>
                  <ExternalLink className="w-3 h-3" />
                </button>
                
                <div className="flex items-center gap-1.5">
                  {/* QA Report */}
                  <a 
                    href={`/qa-report?module=${mod.module_key}`}
                    target="_blank"
                    rel="noreferrer"
                    className="p-1.5 bg-slate-900/60 hover:bg-slate-900 border border-border/60 hover:border-border text-muted-foreground hover:text-foreground rounded-lg transition"
                    title="View QA markdown report"
                  >
                    <FileText className="w-3.5 h-3.5" />
                  </a>
                  {/* Screenshot */}
                  <a 
                    href={`/screenshot?module=${mod.module_key}`}
                    target="_blank"
                    rel="noreferrer"
                    className="p-1.5 bg-slate-900/60 hover:bg-slate-900 border border-border/60 hover:border-border text-muted-foreground hover:text-foreground rounded-lg transition"
                    title="View latest system screenshot"
                  >
                    <Image className="w-3.5 h-3.5" />
                  </a>
                  {/* Raw JSON */}
                  <a 
                    href={`/raw-api?module=${mod.module_key}`}
                    target="_blank"
                    rel="noreferrer"
                    className="p-1.5 bg-slate-900/60 hover:bg-slate-900 border border-border/60 hover:border-border text-muted-foreground hover:text-foreground rounded-lg transition font-mono text-[9px] font-bold"
                    title="View raw API endpoint JSON"
                  >
                    JSON
                  </a>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 4. Data Freshness Monitor Row */}
      <div className="bg-card/40 backdrop-blur-md border border-border rounded-2xl p-6">
        <h3 className="text-lg font-bold tracking-tight flex items-center gap-2 mb-4">
          <Database className="w-4 h-4 text-sky-400 animate-pulse" />
          Data Freshness & Sync Monitor
        </h3>
        
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left border-collapse">
            <thead>
              <tr className="border-b border-border/80 text-muted-foreground text-xs font-semibold uppercase tracking-wider">
                <th className="py-3 px-4">Sub-System</th>
                <th className="py-3 px-4">Underlying Source Mart/Table</th>
                <th className="py-3 px-4">Latest Transaction Date</th>
                <th className="py-3 px-4">Refresh Timestamp</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/65">
              {freshness.map((row) => (
                <tr key={row.module_key} className="hover:bg-slate-950/20 transition-colors">
                  <td className="py-3.5 px-4 font-bold text-foreground capitalize">{row.module_label}</td>
                  <td className="py-3.5 px-4 font-mono text-xs text-indigo-300">{row.source_table}</td>
                  <td className="py-3.5 px-4 font-mono text-xs">
                    {row.max_source_date ? row.max_source_date : 'N/A'}
                  </td>
                  <td className="py-3.5 px-4 font-mono text-xs text-muted-foreground">
                    {new Date(row.last_refresh_timestamp).toLocaleString()}
                  </td>
                  <td className="py-3.5 px-4">
                    {row.stale_flag ? (
                      <span className="px-2 py-0.5 text-[10px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20 rounded">STALE</span>
                    ) : (
                      <span className="px-2 py-0.5 text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded">CURRENT</span>
                    )}
                  </td>
                  <td className="py-3.5 px-4 text-xs text-muted-foreground max-w-xs truncate" title={row.stale_reason}>
                    {row.stale_reason}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 5. Priority Alerts Queue Row */}
      <div className="bg-card/40 backdrop-blur-md border border-border rounded-2xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold tracking-tight flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-400 animate-bounce" />
            Executive Priority Alerts Queue
          </h3>
          <span className="px-2 py-0.5 text-[10px] font-bold bg-amber-500/20 text-amber-400 rounded">
            {alerts.length} Critical/Warning items
          </span>
        </div>

        {alerts.length === 0 ? (
          <div className="text-center p-8 bg-slate-900/10 border border-dashed border-border rounded-xl">
            <p className="text-sm text-muted-foreground font-semibold">Queue Clear — No high priority alerts pending.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {alerts.map((al) => (
              <div 
                key={al.alert_id}
                className={`p-4 rounded-xl border flex justify-between items-start gap-4 transition hover:shadow-md ${
                  al.severity === 'Critical' 
                    ? 'bg-red-500/5 border-red-500/20 hover:border-red-500/40' 
                    : 'bg-amber-500/5 border-amber-500/20 hover:border-amber-500/40'
                }`}
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className={`px-1.5 py-0.5 text-[9px] uppercase font-bold rounded ${
                      al.severity === 'Critical' ? 'bg-red-500/20 text-red-400' : 'bg-amber-500/20 text-amber-400'
                    }`}>
                      {al.severity}
                    </span>
                    <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                      {al.module_label}
                    </span>
                  </div>
                  <h4 className="font-bold text-sm text-foreground">{al.issue_type}</h4>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Found <span className="font-semibold text-foreground">{al.issue_count}</span> instances. 
                    {al.recommended_action && ` Recommendation: ${al.recommended_action}`}
                  </p>
                </div>
                
                <button 
                  onClick={() => onNavigate(al.module_key)}
                  className="p-1.5 bg-slate-900/60 hover:bg-slate-900 border border-border/80 text-muted-foreground hover:text-foreground rounded-lg transition self-center"
                  title="Drill down to exception source"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 6. Exception Summary Table Row */}
      <div className="bg-card/40 backdrop-blur-md border border-border rounded-2xl p-6">
        <h3 className="text-lg font-bold tracking-tight flex items-center gap-2 mb-4">
          <ShieldAlert className="w-4 h-4 text-red-400 animate-pulse" />
          Cross-Module Exception Summary Matrix
        </h3>

        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left border-collapse">
            <thead>
              <tr className="border-b border-border/80 text-muted-foreground text-xs font-semibold uppercase tracking-wider">
                <th className="py-3 px-4">Module</th>
                <th className="py-3 px-4">Severity</th>
                <th className="py-3 px-4">Issue Description</th>
                <th className="py-3 px-4">Total Failures</th>
                <th className="py-3 px-4">Recommended Remediation Action</th>
                <th className="py-3 px-4">Audit Trace</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/65">
              {exceptions.map((ex, index) => (
                <tr key={`${ex.module_key}_${ex.issue_type}_${index}`} className="hover:bg-slate-950/20 transition-colors">
                  <td className="py-3 px-4 font-bold text-foreground capitalize">{ex.module_label}</td>
                  <td className="py-3 px-4">
                    <span className={`px-2 py-0.5 text-[10px] font-bold rounded ${
                      ex.severity === 'Critical' ? 'bg-red-500/10 text-red-400 border border-red-500/20' :
                      ex.severity === 'Warning' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
                      'bg-slate-500/10 text-slate-400 border border-slate-500/20'
                    }`}>
                      {ex.severity}
                    </span>
                  </td>
                  <td className="py-3 px-4 font-medium text-foreground">{ex.issue_type}</td>
                  <td className="py-3 px-4 font-mono font-bold text-red-400">{ex.exception_count}</td>
                  <td className="py-3 px-4 text-xs text-muted-foreground">{ex.recommended_action || 'Review details.'}</td>
                  <td className="py-3 px-4">
                    <button
                      onClick={() => onNavigate(ex.module_key)}
                      className="text-xs text-primary hover:underline font-semibold"
                    >
                      Audit
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 7. Regression QA Status Index Row */}
      <div className="bg-card/40 backdrop-blur-md border border-border rounded-2xl p-6">
        <h3 className="text-lg font-bold tracking-tight flex items-center gap-2 mb-4">
          <ShieldCheck className="w-4 h-4 text-emerald-400 animate-pulse" />
          Regression Testing & QA Status Index
        </h3>

        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left border-collapse">
            <thead>
              <tr className="border-b border-border/80 text-muted-foreground text-xs font-semibold uppercase tracking-wider">
                <th className="py-3 px-4">Sub-System Dashboard</th>
                <th className="py-3 px-4">Verification screenshot.png</th>
                <th className="py-3 px-4">Milestone qa_report.md</th>
                <th className="py-3 px-4">FastAPI raw_api_output.json</th>
                <th className="py-3 px-4">Regression Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/65">
              {qaIndex.map((qa) => (
                <tr key={qa.module_key} className="hover:bg-slate-950/20 transition-colors">
                  <td className="py-3.5 px-4 font-bold text-foreground">{qa.module_label}</td>
                  <td className="py-3.5 px-4 text-xs font-mono">
                    <span className={qa.screenshot_exists ? 'text-emerald-400 font-semibold' : 'text-muted-foreground'}>
                      {qa.screenshot_exists ? '✅ PRESENT' : '⚠️ MISSING'}
                    </span>
                    <span className="text-[10px] text-muted-foreground block font-sans mt-0.5">{qa.screenshot_path}</span>
                  </td>
                  <td className="py-3.5 px-4 text-xs font-mono">
                    <span className={qa.qa_report_exists ? 'text-emerald-400 font-semibold' : 'text-muted-foreground'}>
                      {qa.qa_report_exists ? '✅ PRESENT' : '⚠️ MISSING'}
                    </span>
                    <span className="text-[10px] text-muted-foreground block font-sans mt-0.5">{qa.qa_report_path}</span>
                  </td>
                  <td className="py-3.5 px-4 text-xs font-mono">
                    <span className={qa.raw_api_exists ? 'text-emerald-400 font-semibold' : 'text-muted-foreground'}>
                      {qa.raw_api_exists ? '✅ PRESENT' : '⚠️ MISSING'}
                    </span>
                    <span className="text-[10px] text-muted-foreground block font-sans mt-0.5">{qa.raw_api_path}</span>
                  </td>
                  <td className="py-3.5 px-4">
                    {qa.status === 'Complete' ? (
                      <span className="px-2 py-0.5 text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded">PASSED</span>
                    ) : (
                      <span className="px-2 py-0.5 text-[10px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20 rounded animate-pulse">PENDING</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

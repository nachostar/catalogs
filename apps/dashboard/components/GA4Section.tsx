'use client'
import { useState, useEffect } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

interface Property { accountName: string; propertyId: string; propertyName: string }
interface DayRow {
  date: string; sessions: number; users: number; pageviews: number
  conversions: number; revenue: number; bounceRate: number; avgSessionDuration: number
}
interface LandingRow {
  page: string; sessions: number; users: number; conversions: number
  bounceRate: number; avgSessionDuration: number; pageviews: number
}
interface EventRow { event: string; count: number; conversions: number; users: number }

function fmt(v: number, dec = 0) {
  return (v||0).toLocaleString('es-CL', { maximumFractionDigits: dec })
}
function fmtDuration(secs: number) {
  const m = Math.floor(secs / 60); const s = Math.round(secs % 60)
  return `${m}:${String(s).padStart(2,'0')}`
}
function Card({ label, value, sub, color }: { label: string; value: string; sub?: string; color: string }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <div className={`text-xs font-medium uppercase tracking-wide mb-1 ${color}`}>{label}</div>
      <div className="text-2xl font-bold text-gray-800">{value}</div>
      {sub && <div className="text-xs text-gray-400 mt-1">{sub}</div>}
    </div>
  )
}

const FILTER_LABELS: Record<string, string> = {
  sessionSource:              'Fuente',
  sessionMedium:              'Medio',
  sessionDefaultChannelGroup: 'Canal',
  sessionCampaignName:        'Campaña',
  eventName:                  'Evento clave',
}
const FILTER_PARAMS: Record<string, string> = {
  sessionSource: 'source', sessionMedium: 'medium',
  sessionDefaultChannelGroup: 'channel', sessionCampaignName: 'campaign',
  eventName: 'event',
}

export default function GA4Section({ dateFrom, dateTo }: { dateFrom: string; dateTo: string }) {
  const [properties, setProperties]   = useState<Property[]>([])
  const [selectedProp, setSelectedProp] = useState(() =>
    typeof window !== 'undefined' ? localStorage.getItem('ga4_property') || '' : ''
  )
  const [trend, setTrend]             = useState<DayRow[]>([])
  const [landings, setLandings]       = useState<LandingRow[]>([])
  const [events, setEvents]           = useState<EventRow[]>([])
  const [filterValues, setFilterValues] = useState<Record<string, string[]>>({})
  const [activeFilters, setActiveFilters] = useState<Record<string, string>>({})
  const [loading, setLoading]         = useState(false)
  const [error, setError]             = useState('')
  const [metric, setMetric]           = useState<keyof DayRow>('sessions')

  useEffect(() => {
    fetch('/api/ga4/properties').then(r => r.json()).then(d => {
      if (Array.isArray(d)) {
        setProperties(d)
        // Solo setear el primero si no hay nada guardado en localStorage
        if (d.length > 0 && !localStorage.getItem('ga4_property')) {
          setSelectedProp(d[0].propertyId)
        }
      } else setError(d.error || 'Error')
    })
  }, [])

  // Guardar selección en localStorage cuando cambia
  useEffect(() => {
    if (selectedProp) localStorage.setItem('ga4_property', selectedProp)
  }, [selectedProp])

  // Cargar valores de filtros cuando cambia propiedad
  useEffect(() => {
    if (!selectedProp) return
    fetch(`/api/ga4/metrics?propertyId=${encodeURIComponent(selectedProp)}&dateFrom=${dateFrom}&dateTo=${dateTo}&type=filters`)
      .then(r => r.json())
      .then(d => { if (!d.error) setFilterValues(d) })
  }, [selectedProp, dateFrom, dateTo])

  // Cargar métricas
  useEffect(() => {
    if (!selectedProp) return
    setLoading(true); setError('')
    const params = new URLSearchParams({
      propertyId: selectedProp, dateFrom, dateTo,
      ...Object.fromEntries(
        Object.entries(activeFilters)
          .filter(([,v]) => v)
          .map(([dim, val]) => [FILTER_PARAMS[dim], val])
      )
    })
    fetch(`/api/ga4/metrics?${params}`).then(r => r.json()).then(d => {
      if (d.error) setError(d.error)
      else { setTrend(d.trend||[]); setLandings(d.landings||[]); setEvents(d.events||[]) }
      setLoading(false)
    })
  }, [selectedProp, dateFrom, dateTo, activeFilters])

  const totals = {
    sessions:   trend.reduce((s,r) => s + r.sessions, 0),
    users:      trend.reduce((s,r) => s + r.users, 0),
    pageviews:  trend.reduce((s,r) => s + r.pageviews, 0),
    conversions:trend.reduce((s,r) => s + r.conversions, 0),
    revenue:    trend.reduce((s,r) => s + r.revenue, 0),
    bounceRate: trend.length ? trend.reduce((s,r) => s + r.bounceRate, 0) / trend.length : 0,
    avgDuration:trend.length ? trend.reduce((s,r) => s + r.avgSessionDuration, 0) / trend.length : 0,
  }

  const METRICS = [
    { key: 'sessions' as keyof DayRow,           label: 'Sesiones',         color: '#3b82f6' },
    { key: 'users' as keyof DayRow,              label: 'Usuarios',         color: '#8b5cf6' },
    { key: 'pageviews' as keyof DayRow,          label: 'Páginas vistas',   color: '#10b981' },
    { key: 'conversions' as keyof DayRow,        label: 'Conversiones',     color: '#f59e0b' },
    { key: 'avgSessionDuration' as keyof DayRow, label: 'Tiempo en página', color: '#ec4899' },
    { key: 'bounceRate' as keyof DayRow,         label: 'Bounce rate',      color: '#6b7280' },
  ]
  const activeMetric = METRICS.find(m => m.key === metric) || METRICS[0]
  const hasFilters = Object.values(activeFilters).some(Boolean)

  return (
    <div className="space-y-4">
      {/* Propiedad */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 flex items-center gap-4 flex-wrap">
        <span className="text-sm font-medium text-gray-600">Propiedad GA4:</span>
        {error && <span className="text-sm text-red-500">{error}</span>}
        {properties.length > 0 && (
          <select value={selectedProp} onChange={e => setSelectedProp(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white min-w-[280px]">
            {properties.map(p => (
              <option key={p.propertyId} value={p.propertyId}>{p.accountName} → {p.propertyName}</option>
            ))}
          </select>
        )}
      </div>

      {/* Filtros */}
      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-medium text-gray-700">Filtros</span>
          {hasFilters && (
            <button onClick={() => setActiveFilters({})}
              className="text-xs text-blue-500 hover:underline">Limpiar filtros</button>
          )}
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
          {Object.keys(FILTER_LABELS).map(dim => (
            <div key={dim}>
              <div className="text-xs text-gray-500 mb-1">{FILTER_LABELS[dim]}</div>
              <select
                value={activeFilters[dim] || ''}
                onChange={e => setActiveFilters(f => ({ ...f, [dim]: e.target.value }))}
                className="w-full border border-gray-300 rounded-lg px-2 py-1.5 text-xs bg-white"
              >
                <option value="">Todos</option>
                {(filterValues[dim] || []).map(v => <option key={v} value={v}>{v}</option>)}
              </select>
            </div>
          ))}
        </div>
      </div>

      {loading && <div className="text-center py-10 text-gray-400">Cargando...</div>}

      {!loading && trend.length > 0 && (
        <>
          {/* Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
            <Card label="Sesiones"       value={fmt(totals.sessions)}            color="text-blue-500" />
            <Card label="Usuarios"       value={fmt(totals.users)}              color="text-purple-500" />
            <Card label="Páginas vistas" value={fmt(totals.pageviews)}           color="text-green-500" />
            <Card label="Conversiones"   value={fmt(totals.conversions)}         color="text-yellow-500" />
            <Card label="Revenue"        value={`$${fmt(totals.revenue, 2)}`}    color="text-red-500" />
            <Card label="Bounce rate"    value={`${fmt(totals.bounceRate, 1)}%`} color="text-gray-500" />
            <Card label="Tiempo en pág." value={fmtDuration(totals.avgDuration)} sub="prom. por sesión" color="text-pink-500" />
          </div>

          {/* Gráfico */}
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="flex items-center gap-2 mb-4 flex-wrap">
              <span className="text-sm font-medium text-gray-600">Métrica:</span>
              {METRICS.map(m => (
                <button key={m.key} onClick={() => setMetric(m.key)}
                  className={`text-xs px-3 py-1 rounded-full transition ${metric === m.key ? 'bg-blue-500 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
                  {m.label}
                </button>
              ))}
            </div>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={trend} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={d => d ? `${d.slice(6,8)}/${d.slice(4,6)}` : ''} />
                <YAxis tick={{ fontSize: 11 }} tickFormatter={v => metric === 'avgSessionDuration' ? fmtDuration(Number(v)) : String(v)} />
                <Tooltip
                  labelFormatter={d => `${String(d).slice(6,8)}/${String(d).slice(4,6)}/${String(d).slice(0,4)}`}
                  formatter={(v: any) => [metric === 'avgSessionDuration' ? fmtDuration(Number(v)) : Number(v).toLocaleString('es-CL',{maximumFractionDigits:2}), activeMetric.label]}
                />
                <Line type="monotone" dataKey={metric} stroke={activeMetric.color} strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 5 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Eventos clave */}
          {events.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 overflow-x-auto">
              <div className="px-4 py-3 border-b border-gray-100 font-semibold text-sm text-gray-700">Eventos clave</div>
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-gray-500 text-xs uppercase border-b border-gray-200">
                  <tr>
                    <th className="px-4 py-3 text-left">Evento</th>
                    <th className="px-4 py-3 text-right">Disparos</th>
                    <th className="px-4 py-3 text-right">Conversiones</th>
                    <th className="px-4 py-3 text-right">Usuarios</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {events.map((r, i) => (
                    <tr key={i} className="hover:bg-gray-50">
                      <td className="px-4 py-2 font-mono text-xs text-gray-700">{r.event}</td>
                      <td className="px-4 py-2 text-right">{fmt(r.count)}</td>
                      <td className="px-4 py-2 text-right font-medium text-green-600">{fmt(r.conversions)}</td>
                      <td className="px-4 py-2 text-right">{fmt(r.users)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Páginas de destino */}
          {landings.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 overflow-x-auto">
              <div className="px-4 py-3 border-b border-gray-100 font-semibold text-sm text-gray-700">Páginas de destino</div>
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-gray-500 text-xs uppercase border-b border-gray-200">
                  <tr>
                    <th className="px-4 py-3 text-left">Página</th>
                    <th className="px-4 py-3 text-right">Sesiones</th>
                    <th className="px-4 py-3 text-right">Usuarios</th>
                    <th className="px-4 py-3 text-right">Páginas vistas</th>
                    <th className="px-4 py-3 text-right">Conversiones</th>
                    <th className="px-4 py-3 text-right">Bounce</th>
                    <th className="px-4 py-3 text-right">Tiempo prom.</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {landings.map((r, i) => (
                    <tr key={i} className="hover:bg-gray-50">
                      <td className="px-4 py-2 text-gray-700 max-w-xs truncate font-mono text-xs">{r.page}</td>
                      <td className="px-4 py-2 text-right">{fmt(r.sessions)}</td>
                      <td className="px-4 py-2 text-right">{fmt(r.users)}</td>
                      <td className="px-4 py-2 text-right">{fmt(r.pageviews)}</td>
                      <td className="px-4 py-2 text-right">{fmt(r.conversions)}</td>
                      <td className="px-4 py-2 text-right">{fmt(r.bounceRate, 1)}%</td>
                      <td className="px-4 py-2 text-right">{fmtDuration(r.avgSessionDuration)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  )
}

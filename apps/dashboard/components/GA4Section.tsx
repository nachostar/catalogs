'use client'
import { useState, useEffect } from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts'

interface Property {
  accountName: string
  propertyId: string
  propertyName: string
}

interface DayRow {
  date: string
  sessions: number
  users: number
  pageviews: number
  conversions: number
  revenue: number
  bounceRate: number
  avgSessionDuration: number
}

function fmt(v: number, dec = 0) {
  return (v||0).toLocaleString('es-CL', { maximumFractionDigits: dec })
}

function SummaryCard({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <div className={`text-xs font-medium uppercase tracking-wide mb-1 ${color}`}>{label}</div>
      <div className="text-2xl font-bold text-gray-800">{value}</div>
    </div>
  )
}

export default function GA4Section({ dateFrom, dateTo }: { dateFrom: string; dateTo: string }) {
  const [properties, setProperties] = useState<Property[]>([])
  const [selectedProp, setSelectedProp] = useState('')
  const [rows, setRows] = useState<DayRow[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [metric, setMetric] = useState<keyof DayRow>('sessions')

  // Cargar propiedades al montar
  useEffect(() => {
    fetch('/api/ga4/properties')
      .then(r => r.json())
      .then(d => {
        if (Array.isArray(d)) {
          setProperties(d)
          if (d.length > 0) setSelectedProp(d[0].propertyId)
        } else {
          setError(d.error || 'Error cargando propiedades')
        }
      })
  }, [])

  // Cargar métricas cuando cambia propiedad o fechas
  useEffect(() => {
    if (!selectedProp) return
    setLoading(true)
    setError('')
    const from = dateFrom.replace(/-/g, '') === '' ? '7daysAgo' : dateFrom
    const to   = dateTo.replace(/-/g, '')   === '' ? 'today'    : dateTo
    fetch(`/api/ga4/metrics?propertyId=${encodeURIComponent(selectedProp)}&dateFrom=${from}&dateTo=${to}`)
      .then(r => r.json())
      .then(d => {
        if (Array.isArray(d)) setRows(d)
        else setError(d.error || 'Error cargando métricas')
        setLoading(false)
      })
  }, [selectedProp, dateFrom, dateTo])

  const totals = {
    sessions:   rows.reduce((s,r) => s + r.sessions, 0),
    users:      rows.reduce((s,r) => s + r.users, 0),
    pageviews:  rows.reduce((s,r) => s + r.pageviews, 0),
    conversions:rows.reduce((s,r) => s + r.conversions, 0),
    revenue:    rows.reduce((s,r) => s + r.revenue, 0),
    bounceRate: rows.length ? rows.reduce((s,r) => s + r.bounceRate, 0) / rows.length : 0,
  }

  const METRICS: { key: keyof DayRow; label: string; color: string }[] = [
    { key: 'sessions',    label: 'Sesiones',     color: '#3b82f6' },
    { key: 'users',       label: 'Usuarios',     color: '#8b5cf6' },
    { key: 'pageviews',   label: 'Páginas vistas', color: '#10b981' },
    { key: 'conversions', label: 'Conversiones', color: '#f59e0b' },
    { key: 'revenue',     label: 'Revenue',      color: '#ef4444' },
  ]

  const activeMetric = METRICS.find(m => m.key === metric) || METRICS[0]

  return (
    <div className="space-y-4">
      {/* Selector de propiedad */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 flex items-center gap-4 flex-wrap">
        <span className="text-sm font-medium text-gray-600">Propiedad GA4:</span>
        {properties.length === 0 && !error && (
          <span className="text-sm text-gray-400">Cargando propiedades...</span>
        )}
        {error && (
          <span className="text-sm text-red-500">{error} — <a href="/api/auth/signin" className="underline">reconectar</a></span>
        )}
        {properties.length > 0 && (
          <select
            value={selectedProp}
            onChange={e => setSelectedProp(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white min-w-[280px]"
          >
            {properties.map(p => (
              <option key={p.propertyId} value={p.propertyId}>
                {p.accountName} → {p.propertyName}
              </option>
            ))}
          </select>
        )}
      </div>

      {loading && <div className="text-center py-10 text-gray-400">Cargando métricas GA4...</div>}

      {!loading && rows.length > 0 && (
        <>
          {/* Summary cards */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            <SummaryCard label="Sesiones"      value={fmt(totals.sessions)}    color="text-blue-500" />
            <SummaryCard label="Usuarios"      value={fmt(totals.users)}       color="text-purple-500" />
            <SummaryCard label="Páginas vistas" value={fmt(totals.pageviews)}  color="text-green-500" />
            <SummaryCard label="Conversiones"  value={fmt(totals.conversions)} color="text-yellow-500" />
            <SummaryCard label="Revenue"       value={`$${fmt(totals.revenue, 2)}`} color="text-red-500" />
            <SummaryCard label="Bounce rate"   value={`${fmt(totals.bounceRate, 1)}%`} color="text-gray-500" />
          </div>

          {/* Chart */}
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="flex items-center gap-2 mb-4 flex-wrap">
              <span className="text-sm font-medium text-gray-600">Métrica:</span>
              {METRICS.map(m => (
                <button key={m.key} onClick={() => setMetric(m.key)}
                  className={`text-xs px-3 py-1 rounded-full transition ${
                    metric === m.key ? 'bg-blue-500 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >{m.label}</button>
              ))}
            </div>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={rows} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }}
                  tickFormatter={d => d ? `${d.slice(6,8)}/${d.slice(4,6)}` : ''} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip
                  labelFormatter={d => `${String(d).slice(6,8)}/${String(d).slice(4,6)}/${String(d).slice(0,4)}`}
                  formatter={(v: any) => [Number(v).toLocaleString('es-CL', { maximumFractionDigits: 2 }), activeMetric.label]}
                />
                <Line type="monotone" dataKey={metric} stroke={activeMetric.color}
                  strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 5 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Tabla diaria */}
          <div className="bg-white rounded-xl border border-gray-200 overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-500 text-xs uppercase border-b border-gray-200">
                <tr>
                  <th className="px-4 py-3 text-left">Fecha</th>
                  <th className="px-4 py-3 text-right">Sesiones</th>
                  <th className="px-4 py-3 text-right">Usuarios</th>
                  <th className="px-4 py-3 text-right">Páginas</th>
                  <th className="px-4 py-3 text-right">Conversiones</th>
                  <th className="px-4 py-3 text-right">Revenue</th>
                  <th className="px-4 py-3 text-right">Bounce</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {rows.map(r => (
                  <tr key={r.date} className="hover:bg-gray-50">
                    <td className="px-4 py-2 text-gray-700">
                      {r.date ? `${r.date.slice(6,8)}/${r.date.slice(4,6)}/${r.date.slice(0,4)}` : ''}
                    </td>
                    <td className="px-4 py-2 text-right">{fmt(r.sessions)}</td>
                    <td className="px-4 py-2 text-right">{fmt(r.users)}</td>
                    <td className="px-4 py-2 text-right">{fmt(r.pageviews)}</td>
                    <td className="px-4 py-2 text-right">{fmt(r.conversions)}</td>
                    <td className="px-4 py-2 text-right">${fmt(r.revenue, 2)}</td>
                    <td className="px-4 py-2 text-right">{fmt(r.bounceRate, 1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}

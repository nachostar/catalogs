'use client'
import { useState } from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts'
import { format, startOfWeek, startOfMonth, parseISO } from 'date-fns'

interface TrendRow {
  date: string
  spend: number
  impressions: number
  clicks: number
  purchase: number
  roas: number
}

interface Props {
  data: TrendRow[]
  metric: 'spend' | 'impressions' | 'clicks' | 'purchase' | 'roas'
}

const METRIC_LABELS: Record<string, string> = {
  spend: 'Gasto ($)',
  impressions: 'Impresiones',
  clicks: 'Clics',
  purchase: 'Compras',
  roas: 'ROAS',
}

type Granularity = 'day' | 'week' | 'month'

function groupData(data: TrendRow[], granularity: Granularity, metric: keyof TrendRow) {
  const buckets: Record<string, { sum: number; count: number; label: string }> = {}

  for (const row of data) {
    const raw = (row.date as any)?.value ?? row.date ?? ''
    if (!raw) continue
    let date: Date
    try { date = parseISO(raw) } catch { continue }

    let key: string
    let label: string

    if (granularity === 'day') {
      key = raw
      label = format(date, 'dd MMM')
    } else if (granularity === 'week') {
      const w = startOfWeek(date, { weekStartsOn: 1 })
      key = format(w, 'yyyy-MM-dd')
      label = format(w, "dd MMM")
    } else {
      const m = startOfMonth(date)
      key = format(m, 'yyyy-MM')
      label = format(m, 'MMM yyyy')
    }

    if (!buckets[key]) buckets[key] = { sum: 0, count: 0, label }
    const val = Number(row[metric as keyof TrendRow]) || 0
    buckets[key].sum += val
    buckets[key].count += 1
  }

  return Object.entries(buckets)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([, v]) => ({
      date: v.label,
      value: metric === 'roas' ? v.sum / v.count : v.sum,
    }))
}

export default function MetricsChart({ data, metric }: Props) {
  const [granularity, setGranularity] = useState<Granularity>('day')

  const formatted = groupData(data, granularity, metric)

  const GRAINS: { key: Granularity; label: string }[] = [
    { key: 'day',   label: 'Día' },
    { key: 'week',  label: 'Semana' },
    { key: 'month', label: 'Mes' },
  ]

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
        <h3 className="font-semibold text-gray-700">{METRIC_LABELS[metric]}</h3>
        <div className="flex gap-1">
          {GRAINS.map(g => (
            <button
              key={g.key}
              onClick={() => setGranularity(g.key)}
              className={`text-xs px-3 py-1 rounded-full border transition ${
                granularity === g.key
                  ? 'bg-blue-500 text-white border-blue-500'
                  : 'bg-white text-gray-500 border-gray-300 hover:bg-gray-50'
              }`}
            >
              {g.label}
            </button>
          ))}
        </div>
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={formatted} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="date" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} />
          <Tooltip formatter={(v: any) => typeof v === 'number' ? v.toLocaleString('es-CL', { maximumFractionDigits: 2 }) : v} />
          <Line
            type="monotone" dataKey="value"
            stroke="#3b82f6" strokeWidth={2} dot={{ r: 3 }}
            activeDot={{ r: 5 }} name={METRIC_LABELS[metric]}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

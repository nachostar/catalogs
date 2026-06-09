'use client'

interface Summary {
  totalSpend: number
  totalImpressions: number
  totalClicks: number
  totalPurchases: number
  totalRevenue: number
  avgRoas: number
  avgCtr: number
}

function fmt(n: number, dec = 0) {
  return (n || 0).toLocaleString('es-CL', { maximumFractionDigits: dec })
}

function Delta({ current, prev }: { current: number; prev: number }) {
  if (!prev || prev === 0) return null
  const pct = ((current - prev) / prev) * 100
  const up = pct >= 0
  return (
    <span className={`text-xs font-medium ${up ? 'text-green-500' : 'text-red-500'}`}>
      {up ? '↑' : '↓'} {Math.abs(pct).toFixed(1)}%
    </span>
  )
}

function Card({
  label, value, sub, color, current, prev
}: {
  label: string; value: string; sub?: string; color: string
  current: number; prev: number
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <div className={`text-xs font-medium uppercase tracking-wide mb-1 ${color}`}>{label}</div>
      <div className="text-2xl font-bold text-gray-800">{value}</div>
      <div className="flex items-center gap-2 mt-1">
        {sub && <span className="text-xs text-gray-400">{sub}</span>}
        <Delta current={current} prev={prev} />
      </div>
      {prev > 0 && (
        <div className="text-xs text-gray-300 mt-0.5">anterior: {fmt(prev)}</div>
      )}
    </div>
  )
}

export default function SummaryCards({ data, prev }: { data: Summary; prev?: Summary }) {
  const p = prev || { totalSpend: 0, totalImpressions: 0, totalClicks: 0, totalPurchases: 0, totalRevenue: 0, avgRoas: 0 }
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
      <Card label="Gasto total"   value={`$${fmt(data.totalSpend)}`}      color="text-blue-500"    current={data.totalSpend}       prev={p.totalSpend} />
      <Card label="Impresiones"   value={fmt(data.totalImpressions)}       color="text-purple-500"  current={data.totalImpressions}  prev={p.totalImpressions} />
      <Card label="Clics"         value={fmt(data.totalClicks)}            color="text-indigo-500"  current={data.totalClicks}       prev={p.totalClicks}
        sub={`CTR ${data.totalImpressions ? ((data.totalClicks/data.totalImpressions)*100).toFixed(2) : 0}%`} />
      <Card label="Compras"       value={fmt(data.totalPurchases)}         color="text-green-500"   current={data.totalPurchases}    prev={p.totalPurchases} />
      <Card label="Revenue"       value={`$${fmt(data.totalRevenue)}`}     color="text-emerald-500" current={data.totalRevenue}      prev={p.totalRevenue} />
      <Card label="CTR"            value={`${fmt(data.avgCtr, 2)}%`}        color="text-orange-500"  current={data.avgCtr}            prev={p.avgCtr}
        sub="Clics / Impresiones" />
    </div>
  )
}

'use client'
import { subDays, startOfYear, format } from 'date-fns'

interface FiltersProps {
  dateFrom: string
  dateTo: string
  campaign: string
  campaigns: string[]
  search: string
  onDateFrom: (v: string) => void
  onDateTo: (v: string) => void
  onCampaign: (v: string) => void
  onSearch: (v: string) => void
}

const today = () => format(new Date(), 'yyyy-MM-dd')

const PRESETS = [
  { label: '7d',     from: () => format(subDays(new Date(), 7),  'yyyy-MM-dd') },
  { label: '14d',    from: () => format(subDays(new Date(), 14), 'yyyy-MM-dd') },
  { label: '30d',    from: () => format(subDays(new Date(), 30), 'yyyy-MM-dd') },
  { label: '60d',    from: () => format(subDays(new Date(), 60), 'yyyy-MM-dd') },
  { label: 'Este año', from: () => format(startOfYear(new Date()), 'yyyy-MM-dd') },
]

export default function Filters({
  dateFrom, dateTo, campaign, campaigns, search,
  onDateFrom, onDateTo, onCampaign, onSearch,
}: FiltersProps) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 flex flex-wrap gap-4 items-end">
      {/* Presets */}
      <div className="flex gap-1 flex-wrap">
        {PRESETS.map(p => (
          <button
            key={p.label}
            onClick={() => { onDateFrom(p.from()); onDateTo(today()) }}
            className={`text-xs px-3 py-1.5 rounded-full border transition font-medium ${
              dateFrom === p.from() && dateTo === today()
                ? 'bg-blue-500 text-white border-blue-500'
                : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50'
            }`}
          >
            {p.label}
          </button>
        ))}
      </div>
      <div>
        <label className="block text-xs font-medium text-gray-500 mb-1">Fecha inicio</label>
        <input
          type="date" value={dateFrom}
          onChange={e => onDateFrom(e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
        />
      </div>
      <div>
        <label className="block text-xs font-medium text-gray-500 mb-1">Fecha fin</label>
        <input
          type="date" value={dateTo}
          onChange={e => onDateTo(e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
        />
      </div>
      <div>
        <label className="block text-xs font-medium text-gray-500 mb-1">Campaña</label>
        <select
          value={campaign}
          onChange={e => onCampaign(e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none bg-white min-w-[180px]"
        >
          <option value="">Todas las campañas</option>
          {campaigns.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>
      <div className="flex-1 min-w-[200px]">
        <label className="block text-xs font-medium text-gray-500 mb-1">Buscar producto</label>
        <input
          type="text" value={search} placeholder="Nombre del producto..."
          onChange={e => onSearch(e.target.value)}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
        />
      </div>
    </div>
  )
}

'use client'

interface PlacementRow {
  platform?: string
  age?: string
  impressions: number
  reach: number
  clicks: number
  ctr: number
  spend: number
  view_content: number
  add_to_cart: number
  purchase: number
  purchase_value: number
  roas: number
}

const METRIC_COLS = [
  { key: 'impressions',    label: 'Impresiones' },
  { key: 'reach',          label: 'Alcance' },
  { key: 'clicks',         label: 'Clics' },
  { key: 'ctr',            label: 'CTR',     pct: true },
  { key: 'spend',          label: 'Gasto',   money: true },
  { key: 'view_content',   label: '👁 View' },
  { key: 'add_to_cart',    label: '🛒 Cart' },
  { key: 'purchase',       label: '✅ Compras' },
  { key: 'purchase_value', label: 'Revenue', money: true },
  { key: 'roas',           label: 'ROAS',    dec: true },
]

function fmt(v: any, money?: boolean, pct?: boolean, dec?: boolean) {
  if (typeof v === 'string') return v || '—'
  if (pct)   return `${(v||0).toFixed(2)}%`
  if (dec)   return (v||0).toFixed(2)
  if (money) return `$${(v||0).toLocaleString('es-CL',{maximumFractionDigits:0})}`
  return (v||0).toLocaleString()
}

function totals(rows: PlacementRow[]): PlacementRow {
  const spend = rows.reduce((s,r) => s + (Number(r.spend)||0), 0)
  const impr  = rows.reduce((s,r) => s + (Number(r.impressions)||0), 0)
  const clics = rows.reduce((s,r) => s + (Number(r.clicks)||0), 0)
  const rev   = rows.reduce((s,r) => s + (Number(r.purchase_value)||0), 0)
  return {
    impressions:   impr,
    reach:         rows.reduce((s,r) => s + (Number(r.reach)||0), 0),
    clicks:        clics,
    ctr:           impr > 0 ? (clics/impr)*100 : 0,
    spend,
    view_content:  rows.reduce((s,r) => s + (Number(r.view_content)||0), 0),
    add_to_cart:   rows.reduce((s,r) => s + (Number(r.add_to_cart)||0), 0),
    purchase:      rows.reduce((s,r) => s + (Number(r.purchase)||0), 0),
    purchase_value: rev,
    roas:          spend > 0 ? rev/spend : 0,
  }
}

function Table({
  title, rows, labelKey, color
}: {
  title: string
  rows: PlacementRow[]
  labelKey: 'platform' | 'age'
  color: string
}) {
  if (!rows.length) return null
  const total = totals(rows)
  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className={`px-4 py-3 border-b border-gray-100 font-semibold text-sm ${color}`}>{title}</div>
      <table className="w-full text-sm">
        <thead className="bg-gray-50 text-gray-400 text-xs uppercase">
          <tr>
            <th className="px-4 py-2 text-left">{labelKey === 'platform' ? 'Plataforma' : 'Edad'}</th>
            {METRIC_COLS.map(c => <th key={c.key} className="px-4 py-2 text-right">{c.label}</th>)}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {rows.map((r, i) => (
            <tr key={i} className="hover:bg-gray-50">
              <td className="px-4 py-2 capitalize text-gray-700 font-medium">
                {(r[labelKey] || '—').replace(/_/g,' ')}
              </td>
              {METRIC_COLS.map(c => (
                <td key={c.key} className="px-4 py-2 text-right text-gray-600">
                  {fmt((r as any)[c.key], c.money, c.pct, c.dec)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
        <tfoot className="bg-gray-50 font-semibold text-gray-700 border-t-2 border-gray-200">
          <tr>
            <td className="px-4 py-2">Total</td>
            {METRIC_COLS.map(c => (
              <td key={c.key} className="px-4 py-2 text-right">
                {fmt((total as any)[c.key], c.money, c.pct, c.dec)}
              </td>
            ))}
          </tr>
        </tfoot>
      </table>
    </div>
  )
}

export default function PlacementsTable({
  platforms, ages, selectedAge
}: {
  platforms: PlacementRow[]
  ages: PlacementRow[]
  selectedAge?: string
}) {
  const filteredAges = selectedAge
    ? ages.filter(r => r.age === selectedAge)
    : ages

  const instagram = platforms.filter(r => r.platform === 'instagram')
  const facebook  = platforms.filter(r => r.platform === 'facebook')
  const others    = platforms.filter(r => !['instagram','facebook'].includes(r.platform || ''))

  return (
    <div className="space-y-4">
      <Table title="Instagram"  rows={instagram}    labelKey="platform" color="text-pink-600" />
      <Table title="Facebook"   rows={facebook}     labelKey="platform" color="text-blue-600" />
      {others.length > 0 && <Table title="Otros"    rows={others}       labelKey="platform" color="text-gray-600" />}
      {filteredAges.length > 0 && (
        <Table
          title={selectedAge ? `Edad: ${selectedAge}` : 'Por edad'}
          rows={filteredAges}
          labelKey="age"
          color="text-violet-600"
        />
      )}
    </div>
  )
}

'use client'
import { useSession, signOut } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import Filters from '@/components/Filters'
import ProductCard from '@/components/ProductCard'
import MetricsChart from '@/components/MetricsChart'
import SummaryCards from '@/components/SummaryCards'
import PlacementsTable from '@/components/PlacementsTable'
import GA4Section from '@/components/GA4Section'
import { subDays, format, differenceInDays, parseISO } from 'date-fns'

const today = format(new Date(), 'yyyy-MM-dd')
const thirtyAgo = format(subDays(new Date(), 30), 'yyyy-MM-dd')

type ChartMetric = 'spend' | 'impressions' | 'clicks' | 'purchase' | 'roas'

function calcSummary(rows: any[]) {
  const totalSpend       = rows.reduce((a, r) => a + (Number(r.spend) || 0), 0)
  const totalImpressions = rows.reduce((a, r) => a + (Number(r.impressions) || 0), 0)
  const totalClicks      = rows.reduce((a, r) => a + (Number(r.clicks) || 0), 0)
  return {
    totalSpend,
    totalImpressions,
    totalClicks,
    totalPurchases: rows.reduce((a, r) => a + (Number(r.purchase) || 0), 0),
    totalRevenue:   rows.reduce((a, r) => a + (Number(r.purchase_value) || 0), 0),
    avgRoas: totalSpend > 0
      ? rows.reduce((a, r) => a + (Number(r.purchase_value) || 0), 0) / totalSpend
      : 0,
    avgCtr: totalImpressions > 0 ? (totalClicks / totalImpressions) * 100 : 0,
  }
}

export default function Dashboard() {
  const { data: session, status } = useSession()
  const router = useRouter()

  const [dateFrom, setDateFrom] = useState(thirtyAgo)
  const [dateTo, setDateTo] = useState(today)
  const [campaign, setCampaign] = useState('')
  const [search, setSearch] = useState('')
  const [chartMetric, setChartMetric] = useState<ChartMetric>('spend')

  const [campaigns, setCampaigns] = useState<string[]>([])
  const [metrics, setMetrics] = useState<any[]>([])
  const [adMetrics, setAdMetrics] = useState<any[]>([])
  const [prevMetrics, setPrevMetrics] = useState<any[]>([])
  const [trend, setTrend] = useState<any[]>([])
  const [catalog, setCatalog] = useState<Map<string, any>>(new Map())
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'products' | 'ads' | 'placements' | 'ga4'>('products')
  const [placementPlatforms, setPlacementPlatforms] = useState<any[]>([])
  const [placementAges, setPlacementAges] = useState<any[]>([])
  const [ageFilter, setAgeFilter] = useState('')
  const [availableAges, setAvailableAges] = useState<string[]>([])
  const [placementCampaign, setPlacementCampaign] = useState('')
  const [placementAdset, setPlacementAdset] = useState('')
  const [placementAd, setPlacementAd] = useState('')
  const [placementDims, setPlacementDims] = useState<{campaigns:string[];adsets:string[];ads:string[]}>({campaigns:[],adsets:[],ads:[]})
  const [sortCol, setSortCol] = useState<string>('spend')
  const [sortDir, setSortDir] = useState<'desc' | 'asc'>('desc')

  function toggleSort(col: string) {
    if (sortCol === col) setSortDir(d => d === 'desc' ? 'asc' : 'desc')
    else { setSortCol(col); setSortDir('desc') }
  }

  useEffect(() => {
    if (status === 'unauthenticated') router.push('/login')
  }, [status, router])

  // Load campaigns once
  useEffect(() => {
    fetch('/api/metrics?type=campaigns')
      .then(r => r.json())
      .then(d => setCampaigns(Array.isArray(d) ? d : []))
    fetch('/api/placements?type=ages')
      .then(r => r.json())
      .then(d => setAvailableAges(Array.isArray(d) ? d : []))
    fetch(`/api/placements?type=dimensions&dateFrom=${thirtyAgo}&dateTo=${today}`)
      .then(r => r.json())
      .then(d => d?.campaigns && setPlacementDims(d))
  }, [])

  // Load catalog
  useEffect(() => {
    fetch(`/api/catalog${search ? `?search=${encodeURIComponent(search)}` : ''}`)
      .then(r => r.json())
      .then((rows: any) => {
        const arr = Array.isArray(rows) ? rows : []
        setCatalog(new Map(arr.map((r: any) => [r.family_id, r])))
      })
  }, [search])

  // Load metrics + trend + previous period
  useEffect(() => {
    if (!dateFrom || !dateTo) return
    console.log('🔄 Fetching:', dateFrom, '→', dateTo)
    setLoading(true)

    const params = new URLSearchParams({ dateFrom, dateTo })
    if (campaign) params.set('campaign', campaign)

    const days = differenceInDays(parseISO(dateTo), parseISO(dateFrom)) + 1
    const prevTo   = format(subDays(parseISO(dateFrom), 1), 'yyyy-MM-dd')
    const prevFrom = format(subDays(parseISO(dateFrom), days), 'yyyy-MM-dd')
    const prevParams = new URLSearchParams({ dateFrom: prevFrom, dateTo: prevTo })
    if (campaign) prevParams.set('campaign', campaign)

    Promise.all([
      fetch(`/api/metrics?${params}`).then(r => r.json()),
      fetch(`/api/metrics?type=trend&${params}`).then(r => r.json()),
      fetch(`/api/metrics?${prevParams}`).then(r => r.json()),
      fetch(`/api/placements?${params}${ageFilter?`&age=${encodeURIComponent(ageFilter)}`:''}${placementCampaign?`&campaign=${encodeURIComponent(placementCampaign)}`:''}${placementAdset?`&adset=${encodeURIComponent(placementAdset)}`:''}${placementAd?`&ad=${encodeURIComponent(placementAd)}`:''}`).then(r => r.json()),
    ]).then(([m, t, pm, pl]) => {
      setMetrics(m?.products || [])
      setAdMetrics(m?.ads || [])
      setTrend(Array.isArray(t) ? t : [])
      setPrevMetrics(pm?.products || [])
      setPlacementPlatforms(pl?.platforms || [])
      setPlacementAges(pl?.ages || [])
      console.log('placements:', pl?.platforms?.length, 'platforms,', pl?.ages?.length, 'ages')
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [dateFrom, dateTo, campaign, ageFilter, placementCampaign, placementAdset, placementAd])

  if (status === 'loading' || !session) return null

  // Enrich metrics with catalog data — match by family_id or by title
  const catalogByTitle = new Map(
    Array.from(catalog.values()).map(v => [v.title?.toLowerCase(), v])
  )

  const enriched = metrics.map(row => {
    const byId    = catalog.get(row.product_id)
    const byTitle = catalogByTitle.get(row.product_name?.toLowerCase())
    const cat     = byId || byTitle
    return {
      ...row,
      image_link:   cat?.image_link || '',
      price:        cat?.price || null,
      availability: cat?.availability || '',
      product_url:  row.product_url || cat?.link || '',
      brand:        cat?.brand || '',
    }
  })

  // Products only (with product_id)
  const productRows = [...enriched].sort((a, b) => {
    const va = Number(a[sortCol]) || 0
    const vb = Number(b[sortCol]) || 0
    return sortDir === 'desc' ? vb - va : va - vb
  })

  const adRows = [...adMetrics].sort((a, b) => {
    const va = Number(a[sortCol]) || 0
    const vb = Number(b[sortCol]) || 0
    return sortDir === 'desc' ? vb - va : va - vb
  })

  // Total: ad-level sin product breakdown (evita doble conteo con catálogo)
  const summary = calcSummary(adMetrics)
  const prevSummary = calcSummary(prevMetrics)

  // Resumen solo de productos (para cards encima de la tabla)
  const ps = productRows
  const prodSummary = {
    totalSpend: ps.reduce((s,r) => s + (Number(r.spend)||0), 0),
    totalImpr:  ps.reduce((s,r) => s + (Number(r.impressions)||0), 0),
    totalClics: ps.reduce((s,r) => s + (Number(r.clicks)||0), 0),
    totalCart:  ps.reduce((s,r) => s + (Number(r.add_to_cart)||0), 0),
    totalPurch: ps.reduce((s,r) => s + (Number(r.purchase)||0), 0),
    totalRev:   ps.reduce((s,r) => s + (Number(r.purchase_value)||0), 0),
  }

  const brandMap = new Map<string, any>()
  for (const row of enriched) {
    const b = row.brand || 'Sin marca'
    if (!brandMap.has(b)) brandMap.set(b, { brand: b, products: 0, spend: 0, impressions: 0, clicks: 0, view_content: 0, add_to_cart: 0, purchase: 0, purchase_value: 0 })
    const e = brandMap.get(b)!
    e.products++;
    e.spend          += Number(row.spend) || 0
    e.impressions    += Number(row.impressions) || 0
    e.clicks         += Number(row.clicks) || 0
    e.view_content   += Number(row.view_content) || 0
    e.add_to_cart    += Number(row.add_to_cart) || 0
    e.purchase       += Number(row.purchase) || 0
    e.purchase_value += Number(row.purchase_value) || 0
  }
  const brandRows = Array.from(brandMap.values())
    .map(b => ({ ...b, ctr: b.impressions > 0 ? (b.clicks / b.impressions) * 100 : 0, roas: b.spend > 0 ? b.purchase_value / b.spend : 0 }))
    .sort((a, b) => b.spend - a.spend)

  const CHART_METRICS: ChartMetric[] = ['spend', 'impressions', 'clicks', 'purchase', 'roas']

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between sticky top-0 z-10">
        <div className="flex items-center gap-2">
          <span className="text-xl">📊</span>
          <span className="font-bold text-gray-800">Catalog Dashboard</span>
        </div>
        <div className="flex items-center gap-3">
          <img src={session.user?.image || ''} className="w-8 h-8 rounded-full" />
          <span className="text-sm text-gray-600 hidden md:block">{session.user?.name}</span>
          <button
            onClick={() => signOut({ callbackUrl: '/login' })}
            className="text-sm text-gray-400 hover:text-gray-600 transition"
          >
            Salir
          </button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6 space-y-5">
        {/* Filters */}
        <Filters
          dateFrom={dateFrom} dateTo={dateTo}
          campaign={campaign} campaigns={campaigns}
          search={search}
          onDateFrom={setDateFrom} onDateTo={setDateTo}
          onCampaign={setCampaign} onSearch={setSearch}
        />

        {/* Período activo */}
        <div className="text-xs text-gray-400 -mt-2">
          Mostrando: <span className="font-medium text-gray-600">{dateFrom}</span> → <span className="font-medium text-gray-600">{dateTo}</span>
          {loading && <span className="ml-2 text-blue-400">Cargando...</span>}
        </div>

        {/* Summary */}
        <SummaryCards data={summary} prev={prevSummary} />

        {/* Charts */}
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <div className="flex items-center gap-2 mb-4 flex-wrap">
            <span className="text-sm font-medium text-gray-600">Métrica:</span>
            {CHART_METRICS.map(m => (
              <button
                key={m}
                onClick={() => setChartMetric(m)}
                className={`text-xs px-3 py-1 rounded-full transition ${
                  chartMetric === m
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {m === 'spend' ? 'Gasto' : m === 'impressions' ? 'Impresiones' : m === 'clicks' ? 'Clics' : m === 'purchase' ? 'Compras' : 'ROAS'}
              </button>
            ))}
          </div>
          <MetricsChart data={trend} metric={chartMetric} />
        </div>

        {/* Tabs */}
        <div className="flex gap-2 border-b border-gray-200">
          {(['products', 'ads', 'placements', 'ga4'] as const).map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
                activeTab === tab
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab === 'products' ? `Productos (${productRows.length})` : tab === 'ads' ? `Anuncios (${adRows.length})` : tab === 'placements' ? 'Placements' : '📊 Google Analytics'}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="text-center py-20 text-gray-400">Cargando datos...</div>
        ) : activeTab === 'products' ? (
          productRows.length === 0 ? (
            <div className="text-center py-20 text-gray-400">No hay datos de productos para este período.</div>
          ) : (
            <>
            <div className="grid grid-cols-3 md:grid-cols-4 lg:grid-cols-7 gap-3">
              {[
                { label: 'Gasto',       value: `$${prodSummary.totalSpend.toLocaleString('es-CL',{maximumFractionDigits:0})}`, color: 'text-blue-500' },
                { label: 'Impresiones', value: prodSummary.totalImpr.toLocaleString(),  color: 'text-purple-500' },
                { label: 'Clics',       value: prodSummary.totalClics.toLocaleString(), color: 'text-indigo-500' },
                { label: 'CTR',         value: `${prodSummary.totalImpr > 0 ? ((prodSummary.totalClics/prodSummary.totalImpr)*100).toFixed(2) : '0'}%`, color: 'text-gray-500' },
                { label: 'Add to cart', value: prodSummary.totalCart.toLocaleString(),  color: 'text-yellow-500' },
                { label: 'Compras',     value: prodSummary.totalPurch.toLocaleString(), color: 'text-green-600' },
                { label: 'ROAS',        value: prodSummary.totalSpend > 0 ? (prodSummary.totalRev/prodSummary.totalSpend).toFixed(2) : '0', color: 'text-orange-500' },
              ].map(c => (
                <div key={c.label} className="bg-white rounded-xl border border-gray-200 px-4 py-3">
                  <div className={`text-xs font-medium uppercase tracking-wide mb-1 ${c.color}`}>{c.label}</div>
                  <div className="text-xl font-bold text-gray-800">{c.value}</div>
                </div>
              ))}
            </div>
            <div className="bg-white rounded-xl border border-gray-200 overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-gray-500 text-xs uppercase border-b border-gray-200">
                  <tr>
                    <th className="px-4 py-3 text-left">Producto</th>
                    <th className="px-4 py-3 text-right">Precio</th>
                    {[
                      { key: 'spend',          label: 'Gasto' },
                      { key: 'impressions',    label: 'Impresiones' },
                      { key: 'clicks',         label: 'Clics' },
                      { key: 'ctr',            label: 'CTR' },
                      { key: 'view_content',   label: '👁 View' },
                      { key: 'add_to_cart',    label: '🛒 Cart' },
                      { key: 'purchase',       label: '✅ Compras' },
                      { key: 'purchase_value', label: 'Revenue' },
                      { key: 'roas',           label: 'ROAS' },
                    ].map(({ key, label }) => (
                      <th key={key}
                        className="px-4 py-3 text-right cursor-pointer hover:bg-gray-100 select-none whitespace-nowrap"
                        onClick={() => toggleSort(key)}
                      >
                        <span className="inline-flex items-center gap-1 justify-end">
                          {label}
                          <span className="text-gray-300">
                            {sortCol === key ? (sortDir === 'desc' ? '↓' : '↑') : '↕'}
                          </span>
                        </span>
                      </th>
                    ))}
                    <th className="px-4 py-3 text-center">Stock</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {productRows.map((p, i) => {
                    const img = p.image_link
                    return (
                      <tr key={`${p.product_id}-${i}`} className="hover:bg-gray-50 transition">
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-3">
                            <div className="text-xs text-gray-400 flex-shrink-0 w-10 text-right leading-tight">
                              {p.product_id}
                            </div>
                            <div className="w-14 h-14 rounded-lg overflow-hidden bg-gray-100 flex-shrink-0">
                              {img
                                ? <img src={img} alt="" className="w-full h-full object-cover" />
                                : <span className="flex items-center justify-center w-full h-full text-lg">🛍️</span>
                              }
                            </div>
                            <div className="flex items-center gap-2">
                              <div className="font-medium text-gray-800 max-w-[220px] truncate">
                                {p.product_name || p.product_id}
                              </div>
                              {p.product_url && (
                                <a href={p.product_url} target="_blank" rel="noopener noreferrer"
                                  className="flex-shrink-0 text-xs bg-blue-50 text-blue-600 border border-blue-200 rounded px-1.5 py-0.5 hover:bg-blue-100 transition"
                                  title={p.product_url}
                                >
                                  ↗
                                </a>
                              )}
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-right text-gray-500">
                          {p.price ? `$${(p.price).toLocaleString('es-CL')}` : '—'}
                        </td>
                        <td className="px-4 py-3 text-right font-medium">${(p.spend||0).toLocaleString('es-CL',{maximumFractionDigits:0})}</td>
                        <td className="px-4 py-3 text-right text-gray-600">{(p.impressions||0).toLocaleString()}</td>
                        <td className="px-4 py-3 text-right text-gray-600">{(p.clicks||0).toLocaleString()}</td>
                        <td className="px-4 py-3 text-right text-gray-500">{(p.ctr||0).toFixed(2)}%</td>
                        <td className="px-4 py-3 text-right text-blue-500">{(p.view_content||0).toLocaleString()}</td>
                        <td className="px-4 py-3 text-right text-yellow-500">{(p.add_to_cart||0).toLocaleString()}</td>
                        <td className="px-4 py-3 text-right text-green-600 font-medium">{(p.purchase||0).toLocaleString()}</td>
                        <td className="px-4 py-3 text-right">${(p.purchase_value||0).toLocaleString('es-CL',{maximumFractionDigits:0})}</td>
                        <td className="px-4 py-3 text-right font-semibold text-blue-600">{(p.roas||0).toFixed(2)}</td>
                        <td className="px-4 py-3 text-center">
                          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                            p.availability === 'in_stock'
                              ? 'bg-green-100 text-green-700'
                              : 'bg-gray-100 text-gray-500'
                          }`}>
                            {p.availability === 'in_stock' ? '✓' : '—'}
                          </span>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>

            {/* Tabla por marca */}
            {brandRows.length > 0 && (
              <div className="bg-white rounded-xl border border-gray-200 overflow-x-auto">
                <div className="px-4 py-3 border-b border-gray-100 font-semibold text-sm text-gray-700">
                  Por marca <span className="text-xs font-normal text-gray-400 ml-1">({brandRows.length})</span>
                </div>
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 text-gray-500 text-xs uppercase border-b border-gray-200">
                    <tr>
                      <th className="px-4 py-3 text-left">Marca</th>
                      <th className="px-4 py-3 text-right">Productos</th>
                      <th className="px-4 py-3 text-right">Gasto</th>
                      <th className="px-4 py-3 text-right">Impresiones</th>
                      <th className="px-4 py-3 text-right">Clics</th>
                      <th className="px-4 py-3 text-right">CTR</th>
                      <th className="px-4 py-3 text-right">👁 View</th>
                      <th className="px-4 py-3 text-right">🛒 Cart</th>
                      <th className="px-4 py-3 text-right">✅ Compras</th>
                      <th className="px-4 py-3 text-right">Revenue</th>
                      <th className="px-4 py-3 text-right">ROAS</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {brandRows.map((b, i) => (
                      <tr key={i} className="hover:bg-gray-50 transition">
                        <td className="px-4 py-2.5 font-medium text-gray-800">{b.brand}</td>
                        <td className="px-4 py-2.5 text-right text-gray-500">{b.products}</td>
                        <td className="px-4 py-2.5 text-right font-medium">${b.spend.toLocaleString('es-CL',{maximumFractionDigits:0})}</td>
                        <td className="px-4 py-2.5 text-right text-gray-600">{b.impressions.toLocaleString()}</td>
                        <td className="px-4 py-2.5 text-right text-gray-600">{b.clicks.toLocaleString()}</td>
                        <td className="px-4 py-2.5 text-right text-gray-500">{b.ctr.toFixed(2)}%</td>
                        <td className="px-4 py-2.5 text-right text-blue-500">{b.view_content.toLocaleString()}</td>
                        <td className="px-4 py-2.5 text-right text-yellow-500">{b.add_to_cart.toLocaleString()}</td>
                        <td className="px-4 py-2.5 text-right text-green-600 font-medium">{b.purchase.toLocaleString()}</td>
                        <td className="px-4 py-2.5 text-right">${b.purchase_value.toLocaleString('es-CL',{maximumFractionDigits:0})}</td>
                        <td className="px-4 py-2.5 text-right font-semibold text-blue-600">{b.roas.toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            </>
          )
        ) : activeTab === 'ads' ? (
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
                <tr>
                  {['', 'Anuncio', 'Campaña', 'Gasto', 'Clics', 'CTR', 'Compras', 'ROAS'].map(h => (
                    <th key={h} className="px-4 py-3 text-left">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {adRows.map((r, i) => (
                  <tr key={i} className="hover:bg-gray-50 transition">
                    <td className="px-3 py-2">
                      <div className="w-12 h-12 rounded-lg overflow-hidden bg-gray-100 flex-shrink-0">
                        {r.thumbnail_url
                          ? <img src={r.thumbnail_url} alt="" className="w-full h-full object-cover" />
                          : <span className="flex items-center justify-center w-full h-full text-gray-300 text-lg">▶</span>
                        }
                      </div>
                    </td>
                    <td className="px-4 py-3 font-medium text-gray-800 max-w-xs truncate">{r.ad_name}</td>
                    <td className="px-4 py-3 text-gray-500 truncate max-w-[150px]">{r.campaign_name}</td>
                    <td className="px-4 py-3">${(r.spend||0).toLocaleString('es-CL')}</td>
                    <td className="px-4 py-3">{(r.clicks||0).toLocaleString()}</td>
                    <td className="px-4 py-3">{((r.ctr||0)*100).toFixed(2)}%</td>
                    <td className="px-4 py-3">{r.purchase||0}</td>
                    <td className="px-4 py-3 font-semibold text-blue-600">{(r.roas||0).toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : activeTab === 'ga4' ? (
          <GA4Section dateFrom={dateFrom} dateTo={dateTo} />
        ) : activeTab === 'placements' ? (
          <div className="space-y-4">
            {/* Filtros de placement */}
            <div className="bg-white rounded-xl border border-gray-200 p-4 flex flex-wrap gap-4 items-end">
              {/* Edad */}
              {availableAges.length > 0 && (
                <div>
                  <div className="text-xs font-medium text-gray-500 mb-1">Edad</div>
                  <div className="flex gap-1 flex-wrap">
                    {['', ...availableAges].map(a => (
                      <button key={a||'all'} onClick={() => setAgeFilter(a)}
                        className={`text-xs px-2.5 py-1 rounded-full border transition ${ageFilter===a?'bg-blue-500 text-white border-blue-500':'bg-white text-gray-600 border-gray-300 hover:bg-gray-50'}`}>
                        {a || 'Todas'}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              {/* Campaña */}
              {placementDims.campaigns.length > 0 && (
                <div>
                  <div className="text-xs font-medium text-gray-500 mb-1">Campaña</div>
                  <select value={placementCampaign} onChange={e => setPlacementCampaign(e.target.value)}
                    className="border border-gray-300 rounded-lg px-3 py-1.5 text-xs bg-white min-w-[160px]">
                    <option value="">Todas</option>
                    {placementDims.campaigns.map(c => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>
              )}
              {/* Adset */}
              {placementDims.adsets.length > 0 && (
                <div>
                  <div className="text-xs font-medium text-gray-500 mb-1">Grupo de anuncios</div>
                  <select value={placementAdset} onChange={e => setPlacementAdset(e.target.value)}
                    className="border border-gray-300 rounded-lg px-3 py-1.5 text-xs bg-white min-w-[160px]">
                    <option value="">Todos</option>
                    {placementDims.adsets.map(a => <option key={a} value={a}>{a}</option>)}
                  </select>
                </div>
              )}
              {/* Anuncio */}
              {placementDims.ads.length > 0 && (
                <div>
                  <div className="text-xs font-medium text-gray-500 mb-1">Anuncio</div>
                  <select value={placementAd} onChange={e => setPlacementAd(e.target.value)}
                    className="border border-gray-300 rounded-lg px-3 py-1.5 text-xs bg-white min-w-[160px]">
                    <option value="">Todos</option>
                    {placementDims.ads.map(a => <option key={a} value={a}>{a}</option>)}
                  </select>
                </div>
              )}
            </div>
            {/* debug */}
            <div className="text-xs text-gray-400">platforms: {placementPlatforms.length} | ages: {placementAges.length} | filtro: "{ageFilter}"</div>
            <PlacementsTable platforms={placementPlatforms} ages={placementAges} selectedAge={ageFilter} />
          </div>
        ) : null}
      </main>
    </div>
  )
}

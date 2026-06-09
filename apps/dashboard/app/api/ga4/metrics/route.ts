import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'

const GA4_URL = 'https://analyticsdata.googleapis.com/v1beta'

async function runReport(propertyId: string, token: string, body: any) {
  const res = await fetch(`${GA4_URL}/${propertyId}:runReport`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) { const e = await res.json(); throw new Error(e.error?.message || res.statusText) }
  return res.json()
}

// Construye dimensionFilter desde los filtros activos
function buildFilter(filters: Record<string, string>) {
  const exprs = Object.entries(filters)
    .filter(([, v]) => v)
    .map(([dim, val]) => ({
      filter: {
        fieldName: dim,
        stringFilter: { matchType: 'EXACT', value: val, caseSensitive: false },
      },
    }))
  if (!exprs.length) return undefined
  return exprs.length === 1 ? exprs[0] : { andGroup: { expressions: exprs } }
}

export async function GET(req: NextRequest) {
  const session = await getServerSession(authOptions) as any
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const token      = session.access_token
  const p          = req.nextUrl.searchParams
  const propertyId = p.get('propertyId')
  const dateFrom   = p.get('dateFrom') || '7daysAgo'
  const dateTo     = p.get('dateTo')   || 'today'
  const type       = p.get('type')     || 'full'

  if (!propertyId) return NextResponse.json({ error: 'Falta propertyId' }, { status: 400 })
  if (!token)      return NextResponse.json({ error: 'No access token' }, { status: 401 })

  const dateRanges = [{ startDate: dateFrom, endDate: dateTo }]

  // Filtros activos
  const activeFilters: Record<string, string> = {
    sessionSource:               p.get('source')   || '',
    sessionMedium:               p.get('medium')   || '',
    sessionDefaultChannelGroup:  p.get('channel')  || '',
    sessionCampaignName:         p.get('campaign') || '',
    eventName:                   p.get('event')    || '',
  }
  const dimensionFilter = buildFilter(activeFilters)

  try {
    // Obtener valores disponibles para los filtros
    if (type === 'filters') {
      const dims = [
        'sessionSource', 'sessionMedium',
        'sessionDefaultChannelGroup', 'sessionCampaignName', 'eventName',
      ]
      const results = await Promise.all(dims.map(dim =>
        runReport(propertyId, token, {
          dateRanges,
          dimensions: [{ name: dim }],
          metrics: [{ name: 'sessions' }],
          orderBys: [{ metric: { metricName: 'sessions' }, desc: true }],
          limit: 50,
        }).then(d => ({
          dim,
          values: (d.rows || []).map((r: any) => r.dimensionValues?.[0]?.value).filter(Boolean),
        }))
      ))
      const out: Record<string, string[]> = {}
      results.forEach(r => { out[r.dim] = r.values })
      return NextResponse.json(out)
    }

    // Reports principales
    const base = { dateRanges, ...(dimensionFilter ? { dimensionFilter } : {}) }

    const [trendData, landingData, eventsData] = await Promise.all([
      // Tendencia diaria
      runReport(propertyId, token, {
        ...base,
        dimensions: [{ name: 'date' }],
        metrics: [
          { name: 'sessions' }, { name: 'totalUsers' }, { name: 'screenPageViews' },
          { name: 'conversions' }, { name: 'purchaseRevenue' },
          { name: 'bounceRate' }, { name: 'averageSessionDuration' },
        ],
        orderBys: [{ dimension: { dimensionName: 'date' } }],
      }),
      // Páginas de destino
      runReport(propertyId, token, {
        ...base,
        dimensions: [{ name: 'landingPage' }],
        metrics: [
          { name: 'sessions' }, { name: 'totalUsers' }, { name: 'conversions' },
          { name: 'bounceRate' }, { name: 'averageSessionDuration' }, { name: 'screenPageViews' },
        ],
        orderBys: [{ metric: { metricName: 'sessions' }, desc: true }],
        limit: 50,
      }),
      // Eventos clave por nombre
      runReport(propertyId, token, {
        ...base,
        dimensions: [{ name: 'eventName' }],
        metrics: [{ name: 'eventCount' }, { name: 'conversions' }, { name: 'totalUsers' }],
        orderBys: [{ metric: { metricName: 'eventCount' }, desc: true }],
        limit: 30,
      }),
    ])

    const trend = (trendData.rows || []).map((row: any) => {
      const d = row.dimensionValues || []; const m = row.metricValues || []
      return {
        date: d[0]?.value || '',
        sessions: Number(m[0]?.value||0), users: Number(m[1]?.value||0),
        pageviews: Number(m[2]?.value||0), conversions: Number(m[3]?.value||0),
        revenue: parseFloat(m[4]?.value||'0'),
        bounceRate: parseFloat(m[5]?.value||'0') * 100,
        avgSessionDuration: parseFloat(m[6]?.value||'0'),
      }
    })

    const landings = (landingData.rows || []).map((row: any) => {
      const d = row.dimensionValues || []; const m = row.metricValues || []
      return {
        page: d[0]?.value || '/', sessions: Number(m[0]?.value||0),
        users: Number(m[1]?.value||0), conversions: Number(m[2]?.value||0),
        bounceRate: parseFloat(m[3]?.value||'0') * 100,
        avgSessionDuration: parseFloat(m[4]?.value||'0'),
        pageviews: Number(m[5]?.value||0),
      }
    })

    const events = (eventsData.rows || []).map((row: any) => {
      const d = row.dimensionValues || []; const m = row.metricValues || []
      return {
        event: d[0]?.value || '',
        count: Number(m[0]?.value||0),
        conversions: Number(m[1]?.value||0),
        users: Number(m[2]?.value||0),
      }
    })

    return NextResponse.json({ trend, landings, events })
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 500 })
  }
}

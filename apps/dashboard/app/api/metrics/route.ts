import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { queryMetrics, queryTrend, queryCampaigns } from '@/lib/bigquery'

export async function GET(req: NextRequest) {
  const session = await getServerSession(authOptions)
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const { searchParams } = req.nextUrl
  const type      = searchParams.get('type') || 'metrics'
  const dateFrom  = searchParams.get('dateFrom') || '2026-06-01'
  const dateTo    = searchParams.get('dateTo')   || '2026-06-07'
  const campaign  = searchParams.get('campaign') || undefined
  const productId = searchParams.get('productId') || undefined

  try {
    // Normaliza objetos BigQuery a valores serializables
    const normalize = (rows: any[]) => rows.map(row => {
      const out: any = {}
      for (const [k, v] of Object.entries(row)) {
        out[k] = (v && typeof v === 'object' && 'value' in (v as any))
          ? (v as any).value
          : v
      }
      return out
    })

    if (type === 'trend') {
      const data = await queryTrend({ dateFrom, dateTo, campaign })
      return NextResponse.json(normalize(data))
    }
    if (type === 'campaigns') {
      const data = await queryCampaigns()
      return NextResponse.json(data)
    }
    const data = await queryMetrics({ dateFrom, dateTo, campaign, productId })
    return NextResponse.json({
      products: normalize(data.products as any[]),
      ads: normalize(data.ads as any[]),
    })
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 500 })
  }
}

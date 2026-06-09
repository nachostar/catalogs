import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'

export async function GET(req: NextRequest) {
  const session = await getServerSession(authOptions) as any
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const token      = session.access_token
  const p          = req.nextUrl.searchParams
  const propertyId = p.get('propertyId')   // "properties/XXXXXXX"
  const dateFrom   = p.get('dateFrom') || '7daysAgo'
  const dateTo     = p.get('dateTo')   || 'today'

  if (!propertyId) return NextResponse.json({ error: 'Falta propertyId' }, { status: 400 })
  if (!token)      return NextResponse.json({ error: 'No access token' }, { status: 401 })

  const body = {
    dateRanges: [{ startDate: dateFrom, endDate: dateTo }],
    dimensions: [{ name: 'date' }],
    metrics: [
      { name: 'sessions' },
      { name: 'totalUsers' },
      { name: 'screenPageViews' },
      { name: 'conversions' },
      { name: 'purchaseRevenue' },
      { name: 'bounceRate' },
      { name: 'averageSessionDuration' },
    ],
    orderBys: [{ dimension: { dimensionName: 'date' } }],
  }

  try {
    const res = await fetch(
      `https://analyticsdata.googleapis.com/v1beta/${propertyId}:runReport`,
      {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      }
    )
    if (!res.ok) {
      const err = await res.json()
      return NextResponse.json({ error: err.error?.message || res.statusText }, { status: res.status })
    }
    const data = await res.json()

    // Transformar a array de objetos
    const rows = (data.rows || []).map((row: any) => {
      const dims   = row.dimensionValues || []
      const mets   = row.metricValues    || []
      return {
        date:                    dims[0]?.value || '',
        sessions:                Number(mets[0]?.value || 0),
        users:                   Number(mets[1]?.value || 0),
        pageviews:               Number(mets[2]?.value || 0),
        conversions:             Number(mets[3]?.value || 0),
        revenue:                 parseFloat(mets[4]?.value || '0'),
        bounceRate:              parseFloat(mets[5]?.value || '0') * 100,
        avgSessionDuration:      parseFloat(mets[6]?.value || '0'),
      }
    })
    return NextResponse.json(rows)
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 500 })
  }
}

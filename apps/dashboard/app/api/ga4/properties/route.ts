import { NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'

export async function GET() {
  const session = await getServerSession(authOptions) as any
  if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const token = session.access_token
  if (!token) return NextResponse.json({ error: 'No access token — vuelve a iniciar sesión' }, { status: 401 })

  try {
    // Listar cuentas y propiedades GA4
    const res = await fetch(
      'https://analyticsadmin.googleapis.com/v1beta/accountSummaries',
      { headers: { Authorization: `Bearer ${token}` } }
    )
    if (!res.ok) {
      const err = await res.json()
      return NextResponse.json({ error: err.error?.message || res.statusText }, { status: res.status })
    }
    const data = await res.json()

    // Aplanar: lista de { accountName, propertyId, propertyName }
    const properties: any[] = []
    for (const account of data.accountSummaries || []) {
      for (const prop of account.propertySummaries || []) {
        properties.push({
          accountName:  account.displayName,
          propertyId:   prop.property,          // formato "properties/XXXXXXX"
          propertyName: prop.displayName,
        })
      }
    }
    return NextResponse.json(properties)
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 500 })
  }
}

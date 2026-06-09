'use client'

interface ProductMetrics {
  product_id: string
  product_name: string
  product_url: string
  image_link?: string
  price?: number
  availability?: string
  spend: number
  impressions: number
  clicks: number
  ctr: number
  view_content: number
  add_to_cart: number
  purchase: number
  purchase_value: number
  roas: number
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="text-center">
      <div className="text-base font-bold text-gray-800">{value}</div>
      <div className="text-xs text-gray-400">{label}</div>
    </div>
  )
}

function fmt(n: number, decimals = 0) {
  return n?.toLocaleString('es-CL', { maximumFractionDigits: decimals }) ?? '—'
}

export default function ProductCard({ product }: { product: ProductMetrics }) {
  const isAvailable = product.availability === 'in_stock'

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden hover:shadow-md transition group">
      {/* Imagen */}
      <div className="relative h-48 bg-gray-100">
        {product.image_link ? (
          <img
            src={product.image_link} alt={product.product_name}
            className="w-full h-full object-cover group-hover:scale-105 transition duration-300"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-300 text-4xl">🛍️</div>
        )}
        {product.availability && (
          <span className={`absolute top-2 right-2 text-xs font-medium px-2 py-1 rounded-full ${
            isAvailable ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
          }`}>
            {isAvailable ? 'En stock' : 'Agotado'}
          </span>
        )}
      </div>

      {/* Info */}
      <div className="p-3">
        <div className="font-medium text-sm text-gray-800 truncate mb-1">
          {product.product_name || product.product_id}
        </div>
        {product.price && (
          <div className="text-xs text-gray-500 mb-2">
            ${fmt(product.price)} CLP
          </div>
        )}
        {product.product_url && (
          <a href={product.product_url} target="_blank" rel="noopener noreferrer"
            className="text-xs text-blue-500 hover:underline truncate block mb-3">
            Ver producto →
          </a>
        )}

        {/* Métricas */}
        <div className="grid grid-cols-3 gap-2 border-t border-gray-100 pt-3">
          <Stat label="Gasto" value={`$${fmt(product.spend)}`} />
          <Stat label="Clics" value={fmt(product.clicks)} />
          <Stat label="ROAS" value={fmt(product.roas, 2)} />
        </div>
        <div className="grid grid-cols-3 gap-2 mt-2">
          <Stat label="Impresiones" value={fmt(product.impressions)} />
          <Stat label="Add cart" value={fmt(product.add_to_cart)} />
          <Stat label="Compras" value={fmt(product.purchase)} />
        </div>

        {/* Funnel mini */}
        <div className="mt-3 flex gap-1 text-xs text-gray-400">
          <span className="bg-blue-50 text-blue-600 rounded px-1.5 py-0.5">
            👁 {fmt(product.view_content)}
          </span>
          <span>→</span>
          <span className="bg-yellow-50 text-yellow-600 rounded px-1.5 py-0.5">
            🛒 {fmt(product.add_to_cart)}
          </span>
          <span>→</span>
          <span className="bg-green-50 text-green-600 rounded px-1.5 py-0.5">
            ✅ {fmt(product.purchase)}
          </span>
        </div>
      </div>
    </div>
  )
}

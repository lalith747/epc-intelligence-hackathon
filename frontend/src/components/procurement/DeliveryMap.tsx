import React, { useEffect, useMemo, useState } from 'react'
import { MapContainer, TileLayer, Marker, Popup, Polyline, Tooltip, useMap } from 'react-leaflet'
import L from 'leaflet'
import { resolveLocation, resolveLocationString, LatLng } from '@/lib/geo'
import { formatCurrency, formatDate } from '@/lib/utils'

interface PurchaseOrder {
  id: string
  po_number: string
  supplier_id: string
  issue_date: string
  expected_delivery_date: string | null
  actual_delivery_date: string | null
  total_amount: number | null
  currency: string
  status: string
}

interface Supplier {
  id: string
  name: string
  city: string | null
  country: string | null
}

const STATUS_META: Record<string, { color: string; label: string }> = {
  pending: { color: '#facc15', label: 'Pending' },
  ordered: { color: '#3b82f6', label: 'Ordered' },
  shipped: { color: '#f97316', label: 'In Transit' },
  in_transit: { color: '#f97316', label: 'In Transit' },
  delivered: { color: '#22c55e', label: 'Delivered' },
  delayed: { color: '#ef4444', label: 'Delayed' },
  cancelled: { color: '#9ca3af', label: 'Cancelled' },
}

function pinIcon(color: string, opts: { pulse?: boolean; size?: number } = {}) {
  const size = opts.size ?? 30
  const pulse = opts.pulse
    ? `<span style="position:absolute;inset:-6px;border-radius:9999px;background:${color};opacity:0.45;animation:pulse-ring 1.8s ease-out infinite"></span>`
    : ''
  return L.divIcon({
    className: '',
    html: `
      <div style="position:relative;width:${size}px;height:${size}px;">
        ${pulse}
        <svg viewBox="0 0 24 24" width="${size}" height="${size}" style="position:relative;filter:drop-shadow(0 2px 3px rgba(0,0,0,0.5))">
          <path d="M12 0C7 0 3 4 3 9c0 6.5 9 15 9 15s9-8.5 9-15c0-5-4-9-9-9z" fill="${color}" stroke="white" stroke-width="1.2"/>
          <circle cx="12" cy="9" r="3.4" fill="white"/>
        </svg>
      </div>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size],
    popupAnchor: [0, -size],
  })
}

function siteIcon() {
  const size = 36
  return L.divIcon({
    className: '',
    html: `
      <div style="position:relative;width:${size}px;height:${size}px;">
        <span style="position:absolute;inset:-8px;border-radius:9999px;background:#f97316;opacity:0.3;animation:pulse-ring 2.4s ease-out infinite"></span>
        <svg viewBox="0 0 24 24" width="${size}" height="${size}" style="position:relative;filter:drop-shadow(0 2px 4px rgba(0,0,0,0.6))">
          <circle cx="12" cy="12" r="10" fill="#111827" stroke="#f97316" stroke-width="2"/>
          <path d="M8 15l2-6 2 3 2-5 2 8" fill="none" stroke="#f97316" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </div>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -size / 2],
  })
}

/** Fraction of the way through a shipment's journey, based on real elapsed
 * time between issue and expected delivery. This is a simulated estimate —
 * there is no live GPS/telemetry feed behind it — but it genuinely moves
 * forward as real time passes. */
function progressRatio(issueDate: string, expectedDate: string | null, now: number): number {
  if (!expectedDate) return 0.5
  const start = new Date(issueDate).getTime()
  const end = new Date(expectedDate).getTime()
  if (end <= start) return 1
  return Math.min(1, Math.max(0, (now - start) / (end - start)))
}

/** Build a gently-arced "flight path" between two points instead of a flat
 * straight line, sampled into a polyline. */
function arcPoints(from: LatLng, to: LatLng, segments = 48): LatLng[] {
  const [lat1, lng1] = from
  const [lat2, lng2] = to
  const midLat = (lat1 + lat2) / 2
  const midLng = (lng1 + lng2) / 2
  const dist = Math.hypot(lat2 - lat1, lng2 - lng1)
  // Bow the control point toward the pole — a simple, predictable way to get
  // a pleasant flight-path curve regardless of which way the two points face.
  const controlLat = midLat + Math.min(dist * 0.22, 14)
  const controlLng = midLng

  const points: LatLng[] = []
  for (let i = 0; i <= segments; i++) {
    const t = i / segments
    const lat = (1 - t) * (1 - t) * lat1 + 2 * (1 - t) * t * controlLat + t * t * lat2
    const lng = (1 - t) * (1 - t) * lng1 + 2 * (1 - t) * t * controlLng + t * t * lng2
    points.push([lat, lng])
  }
  return points
}

function pointOnArc(path: LatLng[], t: number): LatLng {
  const idx = Math.min(path.length - 1, Math.max(0, Math.round(t * (path.length - 1))))
  return path[idx]
}

function FitBounds({ points }: { points: LatLng[] }) {
  const map = useMap()
  useEffect(() => {
    if (points.length === 0) return
    if (points.length === 1) {
      map.setView(points[0], 5)
      return
    }
    map.fitBounds(L.latLngBounds(points), { padding: [40, 40], maxZoom: 6 })
  }, [map, points])
  return null
}

interface DeliveryMapProps {
  suppliers: Supplier[]
  orders: PurchaseOrder[]
  projectLocation?: string | null
}

export default function DeliveryMap({ suppliers, orders, projectLocation }: DeliveryMapProps) {
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 4000)
    return () => clearInterval(id)
  }, [])

  const siteCoords = useMemo(
    () => resolveLocationString(projectLocation, 'site') || [20.5937, 78.9629],
    [projectLocation]
  )

  const supplierCoords = useMemo(() => {
    const map = new Map<string, LatLng>()
    suppliers.forEach((s) => {
      const coords = resolveLocation(s.city, s.country, s.id)
      if (coords) map.set(s.id, coords)
    })
    return map
  }, [suppliers])

  const supplierById = useMemo(() => new Map(suppliers.map((s) => [s.id, s])), [suppliers])

  const routableOrders = orders.filter((o) => supplierCoords.has(o.supplier_id) && o.status !== 'cancelled')

  const activeSupplierIds = new Set(orders.map((o) => o.supplier_id))
  const allPoints: LatLng[] = [
    siteCoords as LatLng,
    ...suppliers
      .filter((s) => activeSupplierIds.has(s.id) && supplierCoords.has(s.id))
      .map((s) => supplierCoords.get(s.id) as LatLng),
  ]

  const legendEntries = [
    { color: STATUS_META.pending.color, label: 'Pending' },
    { color: STATUS_META.ordered.color, label: 'Ordered' },
    { color: STATUS_META.shipped.color, label: 'In Transit' },
    { color: STATUS_META.delivered.color, label: 'Delivered' },
    { color: STATUS_META.delayed.color, label: 'Delayed' },
  ]

  return (
    <div className="relative rounded-lg overflow-hidden border border-border/70" style={{ height: 460 }}>
      <style>{`
        @keyframes pulse-ring {
          0% { transform: scale(0.6); opacity: 0.6; }
          100% { transform: scale(1.6); opacity: 0; }
        }
        @keyframes dash-flow {
          to { stroke-dashoffset: -200; }
        }
        .delivery-route-active {
          animation: dash-flow 6s linear infinite;
        }
        .delivery-popup .leaflet-popup-content-wrapper {
          background: #1c1917;
          color: #f5f5f4;
          border-radius: 10px;
          border: 1px solid rgba(249, 115, 22, 0.35);
        }
        .delivery-popup .leaflet-popup-tip { background: #1c1917; }
        .delivery-label {
          background: rgba(17, 24, 39, 0.85) !important;
          border: 1px solid rgba(249, 115, 22, 0.4) !important;
          color: #f5f5f4 !important;
          font-size: 11px !important;
          font-weight: 600;
          padding: 2px 7px !important;
          border-radius: 6px !important;
          box-shadow: none !important;
        }
        .delivery-label::before { display: none; }
      `}</style>

      <MapContainer
        center={siteCoords as LatLng}
        zoom={4}
        style={{ height: '100%', width: '100%', background: '#0b1220' }}
        scrollWheelZoom={true}
      >
        <TileLayer
          attribution="Tiles &copy; Esri"
          url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
        />
        <TileLayer
          url="https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"
        />

        <FitBounds points={allPoints.length > 1 ? allPoints : [siteCoords as LatLng]} />

        <Marker position={siteCoords as LatLng} icon={siteIcon()}>
          <Tooltip permanent direction="top" offset={[0, -20]} className="delivery-label">
            Project Site
          </Tooltip>
          <Popup className="delivery-popup">
            <strong>Project Site</strong>
            <br />
            {projectLocation || 'Location not set'}
          </Popup>
        </Marker>

        {suppliers.map((s) => {
          const coords = supplierCoords.get(s.id)
          const supplierOrders = orders.filter((o) => o.supplier_id === s.id)
          if (!coords || supplierOrders.length === 0) return null
          const worstStatus = supplierOrders.find((o) => o.status === 'delayed')
            ? 'delayed'
            : supplierOrders.find((o) => o.status === 'shipped' || o.status === 'in_transit')
            ? 'shipped'
            : supplierOrders[0]?.status || 'pending'
          const meta = STATUS_META[worstStatus] || STATUS_META.pending

          return (
            <Marker key={s.id} position={coords} icon={pinIcon(meta.color, { pulse: worstStatus === 'shipped' })}>
              <Tooltip permanent direction="top" offset={[0, -28]} className="delivery-label">
                {s.name}
              </Tooltip>
              <Popup className="delivery-popup">
                <strong>{s.name}</strong>
                <br />
                {[s.city, s.country].filter(Boolean).join(', ')}
                <br />
                {supplierOrders.length} purchase order{supplierOrders.length === 1 ? '' : 's'} &mdash; {meta.label}
              </Popup>
            </Marker>
          )
        })}

        {routableOrders.map((o) => {
          const supplier = supplierById.get(o.supplier_id)
          const from = supplierCoords.get(o.supplier_id)
          if (!from || !supplier) return null

          const isActive = o.status === 'shipped' || o.status === 'in_transit'
          const path = arcPoints(from, siteCoords as LatLng)
          const meta = STATUS_META[o.status] || STATUS_META.pending
          const t = progressRatio(o.issue_date, o.expected_delivery_date, now)
          const travelled = isActive ? path.slice(0, Math.max(2, Math.round(t * path.length))) : path
          const position = isActive ? pointOnArc(path, t) : null

          return (
            <React.Fragment key={o.id}>
              <Polyline
                positions={path}
                pathOptions={{ color: meta.color, weight: 1.5, opacity: 0.35, dashArray: '1 6' }}
              />
              {isActive && (
                <Polyline
                  positions={travelled}
                  pathOptions={{ color: meta.color, weight: 2.5, opacity: 0.9, dashArray: '10 8', className: 'delivery-route-active' }}
                />
              )}
              {isActive && position && (
                <Marker position={position} icon={pinIcon(meta.color, { pulse: true, size: 20 })}>
                  <Popup className="delivery-popup">
                    <strong>{o.po_number}</strong>
                    <br />
                    {supplier.name} &rarr; project site
                    <br />
                    {Math.round(t * 100)}% of the way (estimated from issue/expected delivery dates)
                    <br />
                    {o.total_amount ? formatCurrency(o.total_amount, o.currency) : ''}
                    <br />
                    Expected: {o.expected_delivery_date ? formatDate(o.expected_delivery_date) : 'TBD'}
                  </Popup>
                </Marker>
              )}
            </React.Fragment>
          )
        })}
      </MapContainer>

      <div className="absolute bottom-3 left-3 z-[400] glass-card bg-card/90 rounded-lg px-3 py-2 text-xs space-y-1 shadow-lg">
        {legendEntries.map((entry) => (
          <div key={entry.label} className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ background: entry.color }} />
            <span className="text-muted-foreground">{entry.label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

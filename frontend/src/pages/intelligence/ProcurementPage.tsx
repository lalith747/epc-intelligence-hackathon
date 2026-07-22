import { useQuery } from '@tanstack/react-query'
import { MapPin } from 'lucide-react'
import { intelligenceAPI } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

const lanes = ['Ordered', 'In Transit', 'Delivered', 'Installed']

export default function ProcurementPage() {
  const { data } = useQuery({ queryKey: ['procurement-intelligence'], queryFn: async () => (await intelligenceAPI.procurement()).data })
  const orders = data?.orders || []
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Procurement</h1>
        <p className="text-muted-foreground">Supply chain agent tracking orders, vendors, shipments, and critical-path risk</p>
      </div>
      <div className="grid gap-4 xl:grid-cols-4">
        {lanes.map((lane) => (
          <Card key={lane}>
            <CardHeader><CardTitle className="text-base">{lane}</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              {orders.filter((order: any) => order.status === lane).map((order: any) => (
                <div key={order.id} className="rounded-md border p-3">
                  <p className="font-medium">{order.material}</p>
                  <p className="text-sm text-muted-foreground">{order.id} · {order.supplier}</p>
                  <div className="mt-3 flex items-center justify-between">
                    <span className="text-xs">ETA {order.eta}</span>
                    <Badge variant={order.risk === 'red' ? 'destructive' : order.risk === 'yellow' ? 'warning' : 'success'}>{order.risk}</Badge>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        ))}
      </div>
      <div className="grid gap-6 xl:grid-cols-[1fr_360px]">
        <Card>
          <CardHeader><CardTitle>Shipment Map View</CardTitle></CardHeader>
          <CardContent className="relative h-80 overflow-hidden rounded-md bg-secondary">
            {orders.map((order: any, index: number) => (
              <div key={order.id} className="absolute rounded-md border bg-card p-2 text-xs shadow" style={{ left: `${14 + index * 17}%`, top: `${24 + (index % 3) * 18}%` }}>
                <MapPin className="inline h-3 w-3 text-orange-600" /> {order.material}
              </div>
            ))}
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Supplier Scorecards</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {(data?.scorecards || []).map((supplier: any) => (
              <div key={supplier.supplier} className="rounded-md border p-3">
                <div className="flex justify-between"><p className="font-medium">{supplier.supplier}</p><p>{supplier.score}</p></div>
                <div className="mt-2 h-2 rounded-full bg-secondary"><div className="h-2 rounded-full bg-orange-600" style={{ width: `${supplier.score}%` }} /></div>
                <p className="mt-1 text-xs text-muted-foreground">{supplier.orders} active order(s)</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

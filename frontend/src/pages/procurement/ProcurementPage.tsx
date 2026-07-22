import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { procurementAPI, suppliersAPI, agentsAPI } from '@/lib/api'
import { useProjectStore } from '@/lib/store'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Modal, DetailRow } from '@/components/ui/modal'
import DeliveryMap from '@/components/procurement/DeliveryMap'
import { Zap, ShoppingCart, MapPin, Boxes } from 'lucide-react'
import { formatDate, formatCurrency, cn } from '@/lib/utils'

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
  priority: string
}

interface Supplier {
  id: string
  name: string
  city: string | null
  country: string | null
}

interface InventoryStatus {
  inventory_id: string
  material_code: string
  material_name: string
  category: string | null
  unit: string | null
  unit_cost: number | null
  lead_time_days: number | null
  warehouse_location: string | null
  quantity_on_hand: number
  quantity_reserved: number
  quantity_available: number
  minimum_stock_level: number | null
  reorder_point: number | null
  reorder_quantity: number
  stock_status: 'ok' | 'reorder' | 'critical'
}

const statusVariant: Record<string, any> = {
  delivered: 'success',
  pending: 'warning',
  in_transit: 'orange',
  delayed: 'destructive',
  cancelled: 'secondary',
}

export default function ProcurementPage() {
  const { selectedProject } = useProjectStore()
  const queryClient = useQueryClient()
  const [selectedOrder, setSelectedOrder] = useState<PurchaseOrder | null>(null)

  const { data: orders, isLoading } = useQuery<PurchaseOrder[]>({
    queryKey: ['purchase-orders', selectedProject?.id],
    queryFn: async () => (await procurementAPI.list(selectedProject!.id)).data,
    enabled: !!selectedProject,
  })

  const { data: suppliers } = useQuery<Supplier[]>({
    queryKey: ['suppliers-lookup'],
    queryFn: async () => (await suppliersAPI.list()).data,
    enabled: !!selectedProject,
  })

  const { data: inventory } = useQuery<InventoryStatus[]>({
    queryKey: ['inventory', selectedProject?.id],
    queryFn: async () => (await procurementAPI.inventory(selectedProject!.id)).data,
    enabled: !!selectedProject,
  })

  const runAgent = useMutation({
    mutationFn: () =>
      agentsAPI.execute({
        agent_name: 'procurement_agent',
        project_id: selectedProject!.id,
        execution_type: 'on_demand',
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['purchase-orders', selectedProject?.id] }),
  })

  const supplierName = (id: string) => suppliers?.find((s) => s.id === id)?.name || id.slice(0, 8)

  if (!selectedProject) {
    return (
      <div className="text-center py-20">
        <h2 className="text-2xl font-semibold mb-4">Select a Project</h2>
        <p className="text-muted-foreground">Please select a project to view procurement</p>
      </div>
    )
  }

  const delayed = orders?.filter((o) => o.status === 'delayed').length || 0
  const totalValue = orders?.reduce((sum, o) => sum + (o.total_amount || 0), 0) || 0

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Procurement</h1>
          <p className="text-muted-foreground">{selectedProject.name}</p>
        </div>
        <Button className="orange-glow" onClick={() => runAgent.mutate()} disabled={runAgent.isPending}>
          <Zap className="w-4 h-4 mr-2" />
          {runAgent.isPending ? 'Running...' : 'Run Procurement Agent'}
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">Total Purchase Orders</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{orders?.length || 0}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">Delayed Orders</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-red-400">{delayed}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">Total Value</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{formatCurrency(totalValue)}</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <MapPin className="w-5 h-5 text-orange-600" />
            Delivery Map
          </CardTitle>
          <p className="text-xs text-muted-foreground">
            Supplier locations and in-transit shipments. Positions along the route are estimated from
            order issue/expected-delivery dates and update live — this is not a real GPS or camera feed.
          </p>
        </CardHeader>
        <CardContent>
          {!suppliers || !orders ? (
            <p className="text-muted-foreground text-center py-8">Loading map...</p>
          ) : (
            <DeliveryMap suppliers={suppliers} orders={orders} projectLocation={selectedProject.location} />
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Boxes className="w-5 h-5 text-orange-600" />
            Material Stock &amp; Reorder Status
          </CardTitle>
          <p className="text-xs text-muted-foreground">
            Live stock position per material — how much is left on site and how much to order now.
          </p>
        </CardHeader>
        <CardContent>
          {!inventory ? (
            <p className="text-muted-foreground">Loading...</p>
          ) : inventory.length === 0 ? (
            <p className="text-muted-foreground text-center py-8">No inventory records for this project.</p>
          ) : (
            <div className="space-y-3">
              {inventory.map((item) => {
                const denom = Math.max(
                  item.reorder_point != null ? item.reorder_point * 1.5 : item.quantity_on_hand,
                  item.quantity_on_hand,
                  1
                )
                const availPct = Math.min(100, (item.quantity_available / denom) * 100)
                return (
                  <div
                    key={item.inventory_id}
                    className={cn(
                      'p-4 rounded-lg border',
                      item.stock_status === 'critical' && 'border-red-500/50 bg-red-500/5',
                      item.stock_status === 'reorder' && 'border-orange-500/50 bg-orange-500/5',
                      item.stock_status === 'ok' && 'border-border/60'
                    )}
                  >
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div>
                        <p className="font-medium">
                          {item.material_name}
                          <span className="text-xs text-muted-foreground ml-2">{item.material_code}</span>
                        </p>
                        <p className="text-xs text-muted-foreground mt-0.5">
                          {item.warehouse_location || 'On site'}
                          {item.lead_time_days != null && ` · ${item.lead_time_days} day lead time`}
                        </p>
                      </div>
                      <Badge
                        variant={
                          item.stock_status === 'critical'
                            ? 'destructive'
                            : item.stock_status === 'reorder'
                            ? 'orange'
                            : 'success'
                        }
                      >
                        {item.stock_status === 'critical'
                          ? 'Critical — order now'
                          : item.stock_status === 'reorder'
                          ? 'Below reorder point'
                          : 'Stock OK'}
                      </Badge>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-3 text-sm">
                      <div>
                        <p className="text-xs text-muted-foreground">Available</p>
                        <p className="font-semibold">
                          {item.quantity_available.toLocaleString()} {item.unit}
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">On Hand / Reserved</p>
                        <p className="font-semibold">
                          {item.quantity_on_hand.toLocaleString()} / {item.quantity_reserved.toLocaleString()}
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Reorder Point</p>
                        <p className="font-semibold">
                          {item.reorder_point != null ? `${item.reorder_point.toLocaleString()} ${item.unit}` : '—'}
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Order Now</p>
                        <p
                          className={cn(
                            'font-semibold',
                            item.reorder_quantity > 0 ? 'text-orange-600' : 'text-green-600'
                          )}
                        >
                          {item.reorder_quantity > 0
                            ? `${item.reorder_quantity.toLocaleString()} ${item.unit}`
                            : 'Nothing'}
                        </p>
                      </div>
                    </div>

                    <div className="mt-3 w-full bg-secondary rounded-full h-1.5">
                      <div
                        className={cn(
                          'h-1.5 rounded-full',
                          item.stock_status === 'critical'
                            ? 'bg-red-500'
                            : item.stock_status === 'reorder'
                            ? 'bg-orange-500'
                            : 'bg-green-500'
                        )}
                        style={{ width: `${availPct}%` }}
                      />
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <ShoppingCart className="w-5 h-5 text-orange-600" />
            Purchase Orders
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-muted-foreground">Loading...</p>
          ) : !orders || orders.length === 0 ? (
            <p className="text-muted-foreground text-center py-8">No purchase orders yet for this project.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>PO Number</TableHead>
                  <TableHead>Supplier</TableHead>
                  <TableHead>Issue Date</TableHead>
                  <TableHead>Expected Delivery</TableHead>
                  <TableHead>Amount</TableHead>
                  <TableHead>Priority</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {orders.map((o) => (
                  <TableRow key={o.id} className="cursor-pointer" onClick={() => setSelectedOrder(o)}>
                    <TableCell className="font-medium">{o.po_number}</TableCell>
                    <TableCell>{supplierName(o.supplier_id)}</TableCell>
                    <TableCell>{formatDate(o.issue_date)}</TableCell>
                    <TableCell>{o.expected_delivery_date ? formatDate(o.expected_delivery_date) : '—'}</TableCell>
                    <TableCell>{o.total_amount ? formatCurrency(o.total_amount, o.currency) : '—'}</TableCell>
                    <TableCell className="capitalize">{o.priority}</TableCell>
                    <TableCell>
                      <Badge variant={statusVariant[o.status] || 'secondary'} className="capitalize">
                        {o.status.replace('_', ' ')}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Modal
        open={!!selectedOrder}
        onClose={() => setSelectedOrder(null)}
        title={selectedOrder?.po_number || ''}
        subtitle={selectedOrder ? supplierName(selectedOrder.supplier_id) : undefined}
      >
        {selectedOrder && (
          <div className="space-y-4">
            <Badge variant={statusVariant[selectedOrder.status] || 'secondary'} className="capitalize">
              {selectedOrder.status.replace('_', ' ')}
            </Badge>
            <div>
              <DetailRow label="Supplier" value={supplierName(selectedOrder.supplier_id)} />
              <DetailRow label="Issue Date" value={formatDate(selectedOrder.issue_date)} />
              <DetailRow
                label="Expected Delivery"
                value={selectedOrder.expected_delivery_date ? formatDate(selectedOrder.expected_delivery_date) : null}
              />
              <DetailRow
                label="Actual Delivery"
                value={selectedOrder.actual_delivery_date ? formatDate(selectedOrder.actual_delivery_date) : null}
              />
              <DetailRow
                label="Amount"
                value={selectedOrder.total_amount ? formatCurrency(selectedOrder.total_amount, selectedOrder.currency) : null}
              />
              <DetailRow label="Priority" value={<span className="capitalize">{selectedOrder.priority}</span>} />
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}

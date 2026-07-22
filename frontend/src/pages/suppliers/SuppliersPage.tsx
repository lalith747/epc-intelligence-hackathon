import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { suppliersAPI } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Modal, DetailRow } from '@/components/ui/modal'
import { Truck, Star } from 'lucide-react'
import { getHealthColor } from '@/lib/utils'

interface Supplier {
  id: string
  supplier_code: string
  name: string
  category: string | null
  contact_person: string | null
  email: string | null
  phone: string | null
  address: string | null
  country: string | null
  city: string | null
  rating: number
  total_orders: number
  on_time_delivery_rate: number
  quality_score: number
  is_preferred: boolean
  is_active: boolean
}

export default function SuppliersPage() {
  const [selectedSupplier, setSelectedSupplier] = useState<Supplier | null>(null)

  const { data: suppliers, isLoading } = useQuery<Supplier[]>({
    queryKey: ['suppliers'],
    queryFn: async () => (await suppliersAPI.list()).data,
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Suppliers</h1>
        <p className="text-muted-foreground">Supplier performance and risk across all projects</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Truck className="w-5 h-5 text-orange-600" />
            Supplier Directory
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-muted-foreground">Loading...</p>
          ) : !suppliers || suppliers.length === 0 ? (
            <p className="text-muted-foreground text-center py-8">No suppliers on file yet.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Supplier</TableHead>
                  <TableHead>Category</TableHead>
                  <TableHead>Country</TableHead>
                  <TableHead>Rating</TableHead>
                  <TableHead>On-Time Delivery</TableHead>
                  <TableHead>Quality Score</TableHead>
                  <TableHead>Orders</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {suppliers.map((s) => (
                  <TableRow key={s.id} className="cursor-pointer" onClick={() => setSelectedSupplier(s)}>
                    <TableCell>
                      <p className="font-medium">{s.name}</p>
                      <p className="text-xs text-muted-foreground">{s.supplier_code}</p>
                    </TableCell>
                    <TableCell>{s.category || '—'}</TableCell>
                    <TableCell>{s.country || '—'}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <Star className="w-4 h-4 text-orange-600 fill-orange-400" />
                        {s.rating.toFixed(1)}
                      </div>
                    </TableCell>
                    <TableCell className={getHealthColor(s.on_time_delivery_rate)}>
                      {Math.round(s.on_time_delivery_rate)}%
                    </TableCell>
                    <TableCell className={getHealthColor(s.quality_score)}>
                      {Math.round(s.quality_score)}%
                    </TableCell>
                    <TableCell>{s.total_orders}</TableCell>
                    <TableCell className="space-x-1">
                      {s.is_preferred && <Badge variant="orange">Preferred</Badge>}
                      <Badge variant={s.is_active ? 'success' : 'secondary'}>
                        {s.is_active ? 'Active' : 'Inactive'}
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
        open={!!selectedSupplier}
        onClose={() => setSelectedSupplier(null)}
        title={selectedSupplier?.name || ''}
        subtitle={selectedSupplier?.supplier_code}
      >
        {selectedSupplier && (
          <div className="space-y-4">
            <div className="flex gap-2">
              {selectedSupplier.is_preferred && <Badge variant="orange">Preferred</Badge>}
              <Badge variant={selectedSupplier.is_active ? 'success' : 'secondary'}>
                {selectedSupplier.is_active ? 'Active' : 'Inactive'}
              </Badge>
            </div>
            <div>
              <DetailRow label="Category" value={selectedSupplier.category} />
              <DetailRow
                label="Location"
                value={[selectedSupplier.city, selectedSupplier.country].filter(Boolean).join(', ') || null}
              />
              <DetailRow label="Contact" value={selectedSupplier.contact_person} />
              <DetailRow label="Email" value={selectedSupplier.email} />
              <DetailRow label="Phone" value={selectedSupplier.phone} />
              <DetailRow label="Rating" value={`${selectedSupplier.rating.toFixed(1)} / 5`} />
              <DetailRow
                label="On-Time Delivery"
                value={`${Math.round(selectedSupplier.on_time_delivery_rate)}%`}
              />
              <DetailRow label="Quality Score" value={`${Math.round(selectedSupplier.quality_score)}%`} />
              <DetailRow label="Total Orders" value={selectedSupplier.total_orders} />
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}

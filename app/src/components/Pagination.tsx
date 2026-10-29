import { Button } from '@/components/ui/button'
import { ChevronLeft, ChevronRight } from 'lucide-react'

interface PaginationProps {
  page: number
  total: number
  pageSize: number
  onChange: (page: number) => void
  /** 传入后显示「每页 N 条」选择器 */
  onPageSizeChange?: (pageSize: number) => void
  pageSizeOptions?: number[]
}

const DEFAULT_PAGE_SIZE_OPTIONS = [5, 10, 20, 50]

export default function Pagination({
  page,
  total,
  pageSize,
  onChange,
  onPageSizeChange,
  pageSizeOptions = DEFAULT_PAGE_SIZE_OPTIONS,
}: PaginationProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  // 单页且未提供每页条数选择时保持旧行为：不渲染
  if (total === 0 || (totalPages <= 1 && !onPageSizeChange)) return null

  // 生成页码列表（最多显示7个）
  const getPages = () => {
    if (totalPages <= 7) return Array.from({ length: totalPages }, (_, i) => i + 1)
    const pages: (number | '...')[] = []
    if (page <= 4) {
      pages.push(1, 2, 3, 4, 5, '...', totalPages)
    } else if (page >= totalPages - 3) {
      pages.push(1, '...', totalPages - 4, totalPages - 3, totalPages - 2, totalPages - 1, totalPages)
    } else {
      pages.push(1, '...', page - 1, page, page + 1, '...', totalPages)
    }
    return pages
  }

  return (
    <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-center gap-3 text-sm text-muted-foreground">
        <span>
          共 <span className="font-medium text-foreground">{total}</span> 条，第 {page} / {totalPages} 页
        </span>
        {onPageSizeChange && (
          <label className="flex items-center gap-1">
            每页
            <select
              aria-label="每页条数"
              className="h-8 rounded-md border border-input bg-transparent px-2 text-sm text-foreground outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
              value={pageSize}
              onChange={e => onPageSizeChange(Number(e.target.value))}
            >
              {pageSizeOptions.map(size => (
                <option key={size} value={size}>{size}</option>
              ))}
            </select>
            条
          </label>
        )}
      </div>
      {totalPages > 1 && (
        <div className="flex items-center gap-1">
          <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => onChange(page - 1)}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          {getPages().map((p, i) =>
            p === '...' ? (
              <span key={`ellipsis-${i}`} className="px-2 text-muted-foreground">…</span>
            ) : (
              <Button
                key={p}
                variant={p === page ? 'default' : 'outline'}
                size="sm"
                className="w-8"
                onClick={() => onChange(p as number)}
              >
                {p}
              </Button>
            )
          )}
          <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => onChange(page + 1)}>
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      )}
    </div>
  )
}

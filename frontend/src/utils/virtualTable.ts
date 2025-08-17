// Atomic, pure helpers for virtual table math and sizing
// These functions are intentionally side-effect free to enable isolated unit tests.

export function computePageRange(first: number, last: number, pageSize: number): {
    startPage: number
    endPage: number
} {
    // Normalize inputs
    const f = Math.max(0, Number.isFinite(first) ? Number(first) : 0)
    const lRaw = Number.isFinite(last) ? Number(last) : f
    const l = Math.max(f, lRaw)
    const ps = Math.max(1, Number.isFinite(pageSize) ? Number(pageSize) : 1)

    const startPage = Math.floor(f / ps) + 1
    const endPage = Math.floor(Math.max(0, l - 1) / ps) + 1
    return { startPage, endPage }
}

export function makeVirtualRows(total: number): any[] {
    const t = Math.max(0, Math.floor(Number.isFinite(total) ? Number(total) : 0))
    return Array.from({ length: t }, () => null as any)
}

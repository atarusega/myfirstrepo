// Знак STRUKTORUM из брендбука: пять смещённых кругов («подушка»), поле 200×200
export function BrandMark({ size = 40, className }: { size?: number; className?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 200 200" aria-hidden="true" className={className}>
      <circle cx="100" cy="100" r="100" fill="#F2642A" />
      <circle cx="108" cy="106" r="84" fill="#9FE3D4" />
      <circle cx="116" cy="113" r="67" fill="#3A3ED8" />
      <circle cx="128" cy="122" r="42" fill="#D9BDF2" />
      <circle cx="134" cy="127" r="24" fill="#F2B31A" />
    </svg>
  )
}

// Логотип: знак + слово. Unbounded 700, разрядка +8%, заглавные
export function BrandLogo({ size = 36 }: { size?: number }) {
  return (
    <span className="flex items-center gap-3">
      <BrandMark size={size} />
      <span className="font-bold uppercase leading-none tracking-[0.08em]" style={{ fontSize: size * 0.6 }}>
        Struktorum
      </span>
    </span>
  )
}

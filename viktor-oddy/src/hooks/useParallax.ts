import { useEffect, useRef, useState } from 'react'

export function useParallax(maxOffset = 200) {
  const ref = useRef<HTMLDivElement>(null)
  const [offset, setOffset] = useState(0)

  useEffect(() => {
    const el = ref.current
    if (!el) return

    let ticking = false
    let isInView = false

    const observer = new IntersectionObserver(
      ([entry]) => {
        isInView = entry.isIntersecting
      },
      { threshold: 0 }
    )

    const handleScroll = () => {
      if (!isInView || ticking) return
      ticking = true
      requestAnimationFrame(() => {
        const rect = el.getBoundingClientRect()
        const windowHeight = window.innerHeight
        const progress = (windowHeight - rect.top) / (windowHeight + rect.height)
        const clamped = Math.max(0, Math.min(1, progress))
        setOffset((clamped - 0.5) * maxOffset)
        ticking = false
      })
    }

    observer.observe(el)
    window.addEventListener('scroll', handleScroll, { passive: true })
    handleScroll()

    return () => {
      observer.disconnect()
      window.removeEventListener('scroll', handleScroll)
    }
  }, [maxOffset])

  return { ref, offset }
}

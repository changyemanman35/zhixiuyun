import { useEffect } from 'react'

export function useMouseTrail(count = 12) {
  useEffect(() => {
    const dots: HTMLDivElement[] = []
    const positions: { x: number; y: number }[] = []

    for (let i = 0; i < count; i++) {
      const dot = document.createElement('div')
      dot.className = 'mouse-trail-dot'
      dot.style.opacity = String(1 - i / count)
      dot.style.width = `${8 - i * 0.4}px`
      dot.style.height = `${8 - i * 0.4}px`
      document.body.appendChild(dot)
      dots.push(dot)
      positions.push({ x: 0, y: 0 })
    }

    let mouseX = 0
    let mouseY = 0
    let animId: number

    const handleMouseMove = (e: MouseEvent) => {
      mouseX = e.clientX
      mouseY = e.clientY
    }

    const animate = () => {
      positions[0].x += (mouseX - positions[0].x) * 0.3
      positions[0].y += (mouseY - positions[0].y) * 0.3

      for (let i = 1; i < count; i++) {
        positions[i].x += (positions[i - 1].x - positions[i].x) * 0.2
        positions[i].y += (positions[i - 1].y - positions[i].y) * 0.2
      }

      dots.forEach((dot, i) => {
        dot.style.transform = `translate(${positions[i].x - 4}px, ${positions[i].y - 4}px)`
      })

      animId = requestAnimationFrame(animate)
    }

    // Only enable on desktop
    const mq = window.matchMedia('(pointer: fine)')
    if (mq.matches) {
      window.addEventListener('mousemove', handleMouseMove)
      animId = requestAnimationFrame(animate)
    }

    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
      cancelAnimationFrame(animId)
      dots.forEach(d => d.remove())
    }
  }, [count])
}

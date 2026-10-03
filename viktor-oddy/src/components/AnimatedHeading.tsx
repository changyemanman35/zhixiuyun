import { useState, useEffect } from 'react'

interface AnimatedHeadingProps {
  text: string
  className?: string
}

export default function AnimatedHeading({
  text,
  className = '',
}: AnimatedHeadingProps) {
  const [hasStarted, setHasStarted] = useState(false)
  const lines = text.split('\n')
  const charDelay = 30 // ms
  const initialDelay = 200 // ms
  const transitionDuration = 500 // ms

  useEffect(() => {
    const timer = setTimeout(() => {
      setHasStarted(true)
    }, initialDelay)
    return () => clearTimeout(timer)
  }, [initialDelay])

  return (
    <h1
      className={`font-normal mb-4 text-4xl md:text-5xl lg:text-6xl xl:text-7xl ${className}`}
      style={{ letterSpacing: '-0.04em' }}
    >
      {lines.map((line, lineIndex) => {
        const lineLength = line.length
        return (
          <div key={lineIndex} className="block leading-[1.08]">
            {Array.from(line).map((char, charIndex) => {
              const delay =
                lineIndex * lineLength * charDelay + charIndex * charDelay
              const displayChar = char === ' ' ? '\u00A0' : char

              return (
                <span
                  key={charIndex}
                  className="inline-block transition-all ease-out"
                  style={{
                    opacity: hasStarted ? 1 : 0,
                    transform: hasStarted ? 'translateX(0)' : 'translateX(-18px)',
                    transitionDuration: `${transitionDuration}ms`,
                    transitionDelay: `${delay}ms`,
                  }}
                >
                  {displayChar}
                </span>
              )
            })}
          </div>
        )
      })}
    </h1>
  )
}

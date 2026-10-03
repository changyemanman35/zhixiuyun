import { Quote } from 'lucide-react'
import { useScrollAnimation } from '../hooks/useScrollAnimation'
import { useParallax } from '../hooks/useParallax'

export default function Testimonial() {
  const { ref: quoteRef, isVisible: quoteVisible } = useScrollAnimation(0.1)
  const { ref: textRef, isVisible: textVisible } = useScrollAnimation(0.2)
  const { ref: authorRef, isVisible: authorVisible } = useScrollAnimation(0.3)
  const { ref: brandRef, isVisible: brandVisible } = useScrollAnimation(0.4)
  const { ref: imageAnimRef, isVisible: imageVisible } = useScrollAnimation(0.5)
  const { ref: parallaxRef, offset } = useParallax(200)

  return (
    <section className="py-12 px-6 max-w-2xl mx-auto text-center">
      <div 
        ref={quoteRef}
        className={`flex justify-center transition-all duration-1000 ${quoteVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'}`}
      >
        <Quote className="w-6 h-6 text-slate-900 mb-6" />
      </div>

      <div 
        ref={textRef}
        className={`transition-all duration-1000 delay-100 ${textVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'}`}
      >
        <p className="text-[32px] md:text-[40px] lg:text-[44px] leading-[1.1] text-[#0D212C] tracking-tight">
          十五载实战功底，持证上岗。只为让<span className="font-serif">每台电器</span>焕发新生，让邻里更放心
        </p>
      </div>

      <div 
        ref={authorRef}
        className={`transition-all duration-1000 delay-200 ${authorVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'}`}
      >
        <p className="italic text-sm text-[#273C46] mt-6">
          — 张建国，金牌制冷与高级电工名师（国家特种作业持证认证）
        </p>
      </div>

      <div 
        ref={brandRef}
        className={`flex flex-wrap justify-center gap-4 sm:gap-8 mt-8 font-medium text-slate-900 transition-all duration-1000 delay-300 ${brandVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'}`}
      >
        <span className="text-xs sm:text-sm bg-slate-100 px-3 py-1.5 rounded-full text-slate-700">🛡️ 100% 实名背调</span>
        <span className="text-xs sm:text-sm bg-slate-100 px-3 py-1.5 rounded-full text-slate-700">📜 国家高级工证书</span>
        <span className="text-xs sm:text-sm bg-slate-100 px-3 py-1.5 rounded-full text-slate-700">⚡ 5分钟极速抢单</span>
        <span className="text-xs sm:text-sm bg-slate-100 px-3 py-1.5 rounded-full text-slate-700">⭐ 好评率 99.8%</span>
      </div>

      <div 
        ref={imageAnimRef}
        className={`mt-12 transition-all duration-1000 delay-400 ${imageVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'}`}
      >
        <div ref={parallaxRef}>
          <img 
            src="https://images.higgs.ai/?default=1&output=webp&url=https%3A%2F%2Fd8j0ntlcm91z4.cloudfront.net%2Fuser_38xzZboKViGWJOttwIXH07lWA1P%2Fhf_20260330_103804_7aa5494f-4d5b-432e-9dc7-20715275f143.png&w=1280&q=85" 
            alt="高级维修工程师" 
            onError={(e) => {
              const target = e.currentTarget
              const fallback = 'https://images.unsplash.com/photo-1581092160607-ee22621dd758?auto=format&fit=crop&w=800&q=80'
              if (target.src !== fallback) {
                target.src = fallback
              }
            }}
            className="w-full max-w-xs rounded-2xl shadow-lg mx-auto object-cover aspect-[4/5]"
            style={{ transform: `translateY(${offset}px)` }}
          />
        </div>
      </div>
    </section>
  )
}

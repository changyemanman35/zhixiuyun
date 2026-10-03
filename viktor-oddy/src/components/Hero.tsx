import { useScrollAnimation } from '../hooks/useScrollAnimation'

export default function Hero() {
  const { ref, isVisible } = useScrollAnimation(0.1)
  
  const anim = (delay: number) => ({
    className: isVisible ? 'animate-fade-in-up' : 'opacity-0',
    style: { animationDelay: `${delay}s` },
  })

  return (
    <section ref={ref} className="flex flex-col items-center">
      <div className="max-w-[440px] px-6 pt-12 md:pt-16">
        <div style={anim(0.1).style} className={`font-serif text-[32px] md:text-[40px] lg:text-[44px] font-semibold text-[#051A24] tracking-tight mb-4 ${anim(0.1).className}`}>
          家修无忧
        </div>
        <div style={anim(0.2).style} className={`font-mono text-xs md:text-sm text-[#051A24] mb-2 ${anim(0.2).className}`}>
          AI极速撮合 · 邻里家电快修服务平台
        </div>
        <h1 style={anim(0.3).style} className={`text-[32px] md:text-[40px] lg:text-[44px] leading-[1.1] text-[#0D212C] tracking-tight whitespace-nowrap ${anim(0.3).className}`}>
          <div>让故障家电<span className="font-serif">一键焕新，</span></div>
          <div><span className="font-serif">透明更省心。</span></div>
        </h1>
        <div style={anim(0.4).style} className={`flex flex-col gap-6 text-sm md:text-base text-[#051A24] leading-relaxed mt-5 md:mt-6 ${anim(0.4).className}`}>
          <p>去中介化的邻里 C2C 家电快修平台。AI 智能秘书 1 句话提炼电器故障与时段，30秒为您极速派单。</p>
          <p>线上平台安全托管 ¥30 基础排查上门费，老师傅现场出示工卡与核销码打卡；深度维修价格双方在线下面对面透明自决。</p>
          <p>周边 3-5 公里持证名师 5 分钟抢单响应，严控上门时效与服务质量。</p>
        </div>
        <div style={anim(0.5).style} className={`flex flex-col sm:flex-row gap-3 md:gap-4 mt-5 md:mt-6 ${anim(0.5).className}`}>
          <a href="/orders/new" className="inline-flex items-center justify-center bg-[#051A24] text-white rounded-full px-7 py-3 hover:opacity-90 transition font-medium text-center" style={{boxShadow: '0 0 0 1px rgba(5,26,36,0.08), 0 1px 2px rgba(5,26,36,0.15), 0 4px 8px rgba(5,26,36,0.1), inset 0 1px 0 rgba(255,255,255,0.06)'}}>
            ⚡ AI 极速报修
          </a>
          <a href="/register?role=technician" className="inline-flex items-center justify-center bg-white text-[#051A24] rounded-full px-7 py-3 hover:bg-gray-50 transition font-medium text-center" style={{boxShadow: '0 0 0 1px rgba(5,26,36,0.06), 0 1px 2px rgba(5,26,36,0.08)'}}>
            👨‍🔧 师傅入驻加盟
          </a>
        </div>
      </div>
    </section>
  )
}

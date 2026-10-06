import { useScrollAnimation } from '../hooks/useScrollAnimation'
import { Snowflake, WashingMachine, Wind, Flame, Zap, ThermometerSun } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

const icons: Record<string, LucideIcon> = {
  Snowflake,
  ThermometerSun,
  WashingMachine,
  Wind,
  Flame,
  Zap,
}

const projects = [
  { 
    title: '1. AI 一句话智能提取', 
    desc: '自然语言秒级解析电器型号与故障表象，免去繁琐打字', 
    icon: 'Zap', 
    image: 'https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=800&q=80',
    fallback: 'https://images.unsplash.com/photo-1550751827-4bd374c3f58b?auto=format&fit=crop&w=800&q=80',
    tag: '🤖 语义诊断'
  },
  { 
    title: '2. 线上托管预付 ¥30', 
    desc: '平台资金全程安全双向托管，师傅到场核销前可随时退', 
    icon: 'Snowflake', 
    image: 'https://images.unsplash.com/photo-1563013544-824ae1b704d3?auto=format&fit=crop&w=800&q=80',
    fallback: 'https://images.unsplash.com/photo-1559526324-4b87b5e36e44?auto=format&fit=crop&w=800&q=80',
    tag: '🔒 资金安全'
  },
  { 
    title: '3. 邻里名师极速接单', 
    desc: '周边 3-5 公里持证老师傅抢单，根据品类擅长与距离智能撮合', 
    icon: 'Wind', 
    image: 'https://images.unsplash.com/photo-1621905251189-08b45d6a269e?auto=format&fit=crop&w=800&q=80',
    fallback: 'https://images.unsplash.com/photo-1581092160607-ee22621dd758?auto=format&fit=crop&w=800&q=80',
    tag: '⚡ 智能撮合'
  },
  { 
    title: '4. 现场出示 6 位核销码', 
    desc: '师傅携证上门出工打卡，核销码验证成功方可解冻出工费', 
    icon: 'Flame', 
    image: 'https://images.unsplash.com/photo-1581092335397-9583fe92d232?auto=format&fit=crop&w=800&q=80',
    fallback: 'https://images.unsplash.com/photo-1581092580497-e0d23cbdf1dc?auto=format&fit=crop&w=800&q=80',
    tag: '🎫 现场打卡'
  },
  { 
    title: '5. 深度维修线下自决', 
    desc: '配件及大修费用双方脱离平台透明自愿协商，杜绝中介抽成', 
    icon: 'WashingMachine', 
    image: 'https://images.unsplash.com/photo-1584622650111-993a426fbf0a?auto=format&fit=crop&w=800&q=80',
    fallback: 'https://images.unsplash.com/photo-1581092160607-ee22621dd758?auto=format&fit=crop&w=800&q=80',
    tag: '🤝 透明自决'
  },
  { 
    title: '6. 服务评价与售后存证', 
    desc: '完工确认评价，全流程闭环存证，保障用户与技师双边权益', 
    icon: 'ThermometerSun', 
    image: 'https://images.unsplash.com/photo-1590381105924-c72589b9ef3f?auto=format&fit=crop&w=800&q=80',
    fallback: 'https://images.unsplash.com/photo-1581092335397-9583fe92d232?auto=format&fit=crop&w=800&q=80',
    tag: '⭐ 闭环存证'
  },
]

export default function Projects() {
  const { ref, isVisible } = useScrollAnimation(0.1)

  return (
    <section id="workflow" ref={ref} className={`py-12 px-6 max-w-4xl mx-auto transition-all duration-700 ease-out ${isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}>
      <div className="text-center mb-12">
        <h2 className="font-serif text-[32px] md:text-[40px] text-[#0D212C] tracking-tight">
          极速报修全流程
        </h2>
        <p className="text-sm md:text-base text-[#273C46] mt-2">
          高效便捷 6 步直达 · 平台资金双向托管 · 拒绝线下乱加价
        </p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {projects.map((project, index) => {
          const Icon = icons[project.icon]
          return (
            <div key={index} className="group cursor-pointer">
              <div className="relative rounded-2xl overflow-hidden h-[240px] bg-slate-900 group-hover:scale-[1.02] transition-transform duration-300 shadow-md">
                <img 
                  src={project.image} 
                  alt={project.title} 
                  loading="lazy"
                  onError={(e) => {
                    const target = e.currentTarget
                    if (target.src !== project.fallback) {
                      target.src = project.fallback
                    }
                  }}
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500 opacity-80"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/30 to-black/10" />
                <div className="absolute top-3 left-3 bg-black/60 backdrop-blur-md text-white text-xs px-2.5 py-1 rounded-full font-medium border border-white/20">
                  {project.tag}
                </div>
                <div className="absolute bottom-3 left-3 right-3 flex items-center justify-between text-white">
                  <div className="p-2 rounded-xl bg-white/20 backdrop-blur-md">
                    {Icon && <Icon className="w-5 h-5 text-white" />}
                  </div>
                </div>
              </div>
              <h3 className="text-lg font-medium mt-4 text-[#051A24]">{project.title}</h3>
              <p className="text-sm text-[#273C46] mt-1 leading-relaxed">{project.desc}</p>
            </div>
          )
        })}
      </div>
    </section>
  )
}

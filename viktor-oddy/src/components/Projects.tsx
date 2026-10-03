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
  { title: '1. AI 一句话智能提取', desc: '自然语言秒级解析电器型号与故障表象，免去繁琐打字', icon: 'Zap', bg: 'bg-blue-50' },
  { title: '2. 线上托管预付 ¥30', desc: '平台资金全程安全双向托管，师傅到场核销前可随时退', icon: 'Snowflake', bg: 'bg-emerald-50' },
  { title: '3. 邻里名师极速接单', desc: '周边 3-5 公里持证老师傅抢单，根据品类擅长与距离智能撮合', icon: 'Wind', bg: 'bg-indigo-50' },
  { title: '4. 现场出示 6 位核销码', desc: '师傅携证上门出工打卡，核销码验证成功方可解冻出工费', icon: 'Flame', bg: 'bg-amber-50' },
  { title: '5. 深度维修线下自决', desc: '配件及大修费用双方脱离平台透明自愿协商，杜绝中介抽成', icon: 'WashingMachine', bg: 'bg-orange-50' },
  { title: '6. 服务评价与售后存证', desc: '完工确认评价，全流程闭环存证，保障用户与技师双边权益', icon: 'ThermometerSun', bg: 'bg-cyan-50' },
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
          高效便捷 4 步直达 · 平台资金双向托管 · 拒绝线下乱加价
        </p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {projects.map((project, index) => {
          const Icon = icons[project.icon]
          return (
            <div key={index} className="group cursor-pointer">
              <div className={`rounded-2xl overflow-hidden h-[240px] ${project.bg} group-hover:scale-[1.02] transition duration-300 flex items-center justify-center`}>
                {Icon && <Icon className="w-16 h-16 text-gray-500" />}
              </div>
              <h3 className="text-lg font-medium mt-4 text-[#051A24]">{project.title}</h3>
              <p className="text-sm text-[#273C46] mt-1">{project.desc}</p>
            </div>
          )
        })}
      </div>
    </section>
  )
}

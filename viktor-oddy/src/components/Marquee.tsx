interface RepairScene {
  src: string
  title: string
  desc: string
  badge: string
}

const realApplianceRepairScenes: RepairScene[] = [
  {
    src: 'https://images.unsplash.com/photo-1621905251189-08b45d6a269e?auto=format&fit=crop&w=1200&q=85',
    title: '空调变频主板与电气箱测电检修',
    desc: '持证高级技工现场使用高精度数显万用表排查主控电路',
    badge: '❄️ 空调精修'
  },
  {
    src: 'https://images.unsplash.com/photo-1584622650111-993a426fbf0a?auto=format&fit=crop&w=1200&q=85',
    title: '对开门冰箱压缩机与制冷系统排查',
    desc: '上门现场诊断制冷剂压力与化霜传感器，透明报价',
    badge: '🧊 冰箱冷柜'
  },
  {
    src: 'https://images.unsplash.com/photo-1581092160607-ee22621dd758?auto=format&fit=crop&w=1200&q=85',
    title: '滚筒洗衣机减震阻尼与电机轴承排修',
    desc: '现场拆机彻底解决洗衣机脱水剧烈轰鸣震动与漏水隐患',
    badge: '🧺 洗衣机专修'
  },
  {
    src: 'https://images.unsplash.com/photo-1581092335397-9583fe92d232?auto=format&fit=crop&w=1200&q=85',
    title: '燃气与电热水器内胆安全巡检维护',
    desc: '专业更换防电墙与防腐镁棒，清理水垢保障洗浴用电安全',
    badge: '🔥 热水器维护'
  },
  {
    src: 'https://images.unsplash.com/photo-1590381105924-c72589b9ef3f?auto=format&fit=crop&w=1200&q=85',
    title: '大吸力油烟机电机与烟道深度拆检',
    desc: '拆解排查风轮卡滞与电机启动电容，吸力即刻恢复如新',
    badge: '💨 厨房烟灶'
  },
  {
    src: 'https://images.unsplash.com/photo-1581092580497-e0d23cbdf1dc?auto=format&fit=crop&w=1200&q=85',
    title: '智能液晶电视电源板芯片级电路排查',
    desc: '微距显微镜下精准更换滤波电容，费用直省 60%',
    badge: '📺 电视音响'
  },
  {
    src: 'https://images.unsplash.com/photo-1585338107529-13afc5f02586?auto=format&fit=crop&w=1200&q=85',
    title: '师傅携带专业成套工具箱入户实景',
    desc: '统一配备标准工具箱、绝缘检测仪与防护鞋套，文明出工',
    badge: '🧰 师傅入户'
  },
  {
    src: 'https://images.unsplash.com/photo-1581092162384-8987c1d64718?auto=format&fit=crop&w=1200&q=85',
    title: '师傅与客户面对面透明诊断讲解',
    desc: '出示故障实物与官方核销码，客户知情确认再决定是否维修',
    badge: '🤝 现场自决'
  }
]

const doubled = [...realApplianceRepairScenes, ...realApplianceRepairScenes]

export default function Marquee() {
  return (
    <div className="w-full mt-16 md:mt-20 mb-16 overflow-hidden">
      <div className="flex animate-marquee hover:[animation-play-state:paused]" style={{ width: 'max-content' }}>
        {doubled.map((scene, i) => (
          <div key={i} className="group relative h-[280px] md:h-[460px] w-[340px] md:w-[480px] mx-3 rounded-2xl overflow-hidden shadow-lg flex-shrink-0 bg-slate-900 cursor-pointer">
            <img
              src={scene.src}
              alt={scene.title}
              className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
            />
            {/* 顶部品类徽章 */}
            <div className="absolute top-4 left-4 z-10">
              <span className="inline-block bg-[#051A24]/80 backdrop-blur-md text-white text-xs font-semibold px-3 py-1.5 rounded-full border border-white/20 shadow-md">
                {scene.badge}
              </span>
            </div>
            {/* 底部渐变信息覆盖层 */}
            <div className="absolute inset-0 bg-gradient-to-t from-black/85 via-black/30 to-transparent flex flex-col justify-end p-5 md:p-6 text-white pointer-events-none">
              <h3 className="font-semibold text-base md:text-lg leading-snug drop-shadow-sm">
                {scene.title}
              </h3>
              <p className="text-xs md:text-sm text-slate-200/90 mt-1.5 line-clamp-2 leading-relaxed drop-shadow-sm">
                {scene.desc}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

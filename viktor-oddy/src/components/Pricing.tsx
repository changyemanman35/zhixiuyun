import { useScrollAnimation } from '../hooks/useScrollAnimation'

export default function Pricing() {
  const { ref: card1Ref, isVisible: card1Visible } = useScrollAnimation(0.1)
  const { ref: card2Ref, isVisible: card2Visible } = useScrollAnimation(0.2)

  return (
    <section id="pricing" className="w-full py-12 px-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto md:ml-auto">
        
        {/* 卡片1（深色） */}
        {/* 卡片1（深色：面向师傅加盟入驻） */}
        <div 
          ref={card1Ref}
          className={`bg-[#051A24] rounded-[40px] pl-10 pr-10 md:pr-24 pt-3 pb-10 shadow-[inset_0_1px_0_rgba(255,255,255,0.06)] transition-all duration-1000 ${card1Visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'}`}
        >
          <div className="flex items-center gap-2">
            <span className="text-xs bg-[#1677ff] text-white px-2 py-0.5 rounded-full font-semibold">供给端招募</span>
            <h3 className="text-[22px] font-medium text-[#F6FCFF]">师傅入驻加盟</h3>
          </div>
          <p className="text-[#E0EBF0] text-sm mt-2 leading-relaxed">
            附近 3-5 公里订单秒级直推 / 零抽成门槛 / 自由兼职全职
          </p>
          <div className="mt-6 flex items-baseline">
            <span className="text-[44px] font-semibold text-[#F6FCFF]">¥25</span>
            <span className="text-sm text-[#E0EBF0] ml-1">/单 基础出工劳务即时到账</span>
          </div>
          <ul className="mt-6 space-y-3 text-sm text-[#E0EBF0]">
            <li>✓ 平台周边海量真实工单就近雷达推送</li>
            <li>✓ 客户现场出示 6 位核销码打卡即解冻到钱包</li>
            <li>✓ 现场深度维修费用 100% 归师傅，平台不抽成</li>
            <li>✓ 自主配置服务半径与接单状态，多劳多得</li>
          </ul>
          <a href="/register?role=technician" className="inline-flex items-center justify-center bg-white text-[#051A24] rounded-full px-7 py-3 mt-8 font-medium hover:bg-gray-100 transition-colors text-center">
            👨‍🔧 立即注册成为师傅
          </a>
        </div>

        {/* 卡片2（浅色：面向报修客户） */}
        <div 
          ref={card2Ref}
          className={`bg-[#F6FCFF] border border-[#E0EBF0] rounded-[40px] pl-10 pr-10 md:pr-24 pt-3 pb-10 transition-all duration-1000 delay-100 ${card2Visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'}`}
        >
          <div className="flex items-center gap-2">
            <span className="text-xs bg-[#52c41a] text-white px-2 py-0.5 rounded-full font-semibold">需求端服务</span>
            <h3 className="text-[22px] font-medium text-[#051A24]">客户极速快修</h3>
          </div>
          <p className="text-[#273C46] text-sm mt-2 leading-relaxed">
            AI 秒速提单 / 线上资金安全托管 / 师傅到场前随时退
          </p>
          <div className="mt-6 flex items-baseline">
            <span className="text-[44px] font-semibold text-[#051A24]">¥30</span>
            <span className="text-sm text-[#273C46] ml-1">/次 基础排查上门费</span>
          </div>
          <ul className="mt-6 space-y-3 text-sm text-[#273C46]">
            <li>✓ AI 智能秘书 1 句话提取电器与故障，无需繁琐填单</li>
            <li>✓ 平台双向托管资金，严防线下师傅乱收出工费</li>
            <li>✓ 动态智能匹配周边持证且擅长此品类的老师傅</li>
            <li>✓ 师傅携证上门核销，深度维修价格面对面透明协商</li>
          </ul>
          <a href="/orders/new" className="inline-flex items-center justify-center bg-[#051A24] text-white rounded-full px-7 py-3 mt-8 font-medium hover:opacity-90 transition-opacity text-center">
            ⚡ 立即发起快修预约
          </a>
        </div>

      </div>
    </section>
  )
}
